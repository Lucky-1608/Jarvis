package com.jarvis.app

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.net.ConnectivityManager
import android.net.Network
import android.net.NetworkCapabilities
import android.net.NetworkRequest
import android.net.Uri
import android.os.BatteryManager
import android.os.Build
import android.os.IBinder
import android.os.PowerManager
import android.util.Log
import androidx.core.app.NotificationCompat
import okhttp3.*
import org.json.JSONObject
import java.util.concurrent.Executors
import java.util.concurrent.ScheduledExecutorService
import java.util.concurrent.ScheduledFuture
import java.util.concurrent.TimeUnit

class JarvisBackgroundService : Service() {

    companion object {
        const val CHANNEL_ID = "JarvisServiceChannel"
        const val ALERTS_CHANNEL_ID = "JarvisAlertsChannel"
        const val TAG = "JarvisBackground"
        var instance: JarvisBackgroundService? = null
    }

    private var webSocket: WebSocket? = null
    private val client = OkHttpClient.Builder()
        .readTimeout(0, TimeUnit.MILLISECONDS)
        .pingInterval(25, TimeUnit.SECONDS)
        .build()

    private lateinit var ttsEngine: JarvisTTS
    private lateinit var wakeWordEngine: JarvisWakeWordEngine
    private var wakeLock: PowerManager.WakeLock? = null

    private val scheduler: ScheduledExecutorService = Executors.newSingleThreadScheduledExecutor()
    private var heartbeatTask: ScheduledFuture<*>? = null
    private var reconnectTask: ScheduledFuture<*>? = null
    private var reconnectAttempts = 0
    private var lastPongTimestamp = System.currentTimeMillis()
    private var isDestroyed = false

    private var connectivityManager: ConnectivityManager? = null
    private var networkCallback: ConnectivityManager.NetworkCallback? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        // Ensures the service is revived by Android if killed under memory pressure
        return START_STICKY
    }

    override fun onCreate() {
        super.onCreate()
        instance = this
        isDestroyed = false
        createNotificationChannels()

        // Acquire partial WakeLock so CPU keeps WebSocket and background actions alive while screen is off
        try {
            val powerManager = getSystemService(Context.POWER_SERVICE) as? PowerManager
            wakeLock = powerManager?.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "Jarvis::ServiceWakeLock")?.apply {
                setReferenceCounted(false)
                acquire(24 * 60 * 60 * 1000L) // 24 hours fallback limit
            }
        } catch (e: Exception) {
            Log.w(TAG, "Could not acquire WakeLock", e)
        }

        val notification: Notification = NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("Jarvis Background Service")
            .setContentText("Connected and listening for commands...")
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setOngoing(true)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .build()

        startForeground(1, notification)

        ttsEngine = JarvisTTS(this)
        wakeWordEngine = JarvisWakeWordEngine(this) {
            ttsEngine.speak("Yes, how can I help?")
            sendToBackend(JSONObject().apply {
                put("type", "wake_word_detected")
            })
        }
        wakeWordEngine.startListening()

        // Register network callback to automatically reconnect when network changes or recovers
        registerNetworkCallback()

        // Start companion WebSocket connection
        connectWebSocket()
    }

    /**
     * Resolves the WebSocket URL for the companion connection:
     * 1. Checks SharedPreferences ("jarvis_prefs" -> "backend_url") saved by frontend.
     * 2. Falls back to BuildConfig.VITE_API_BASE_URL.
     */
    private fun getWebSocketUrls(): List<String> {
        val prefs = getSharedPreferences("jarvis_prefs", Context.MODE_PRIVATE)
        val savedUrl = prefs.getString("backend_url", null)
        val candidateBases = mutableListOf<String>()

        if (!savedUrl.isNullOrBlank()) {
            candidateBases.add(savedUrl)
        }

        val envUrls = BuildConfig.VITE_API_BASE_URL
        envUrls.split(",")
            .map { it.trim() }
            .filter { it.isNotBlank() }
            .forEach { if (!candidateBases.contains(it)) candidateBases.add(it) }

        if (candidateBases.isEmpty()) {
            candidateBases.add("http://10.0.2.2:8000")
        }

        return candidateBases.map { base ->
            val clean = base.trim().removeSuffix("/")
            val wsBase = clean.replace("http://", "ws://").replace("https://", "wss://")
            "$wsBase/api/ws/companion"
        }
    }

    private var currentUrlIndex = 0

    @Synchronized
    private fun connectWebSocket() {
        if (isDestroyed) return

        // Clean up any existing connection
        try {
            webSocket?.close(1000, "Reconnecting")
        } catch (ignored: Exception) {}
        webSocket = null

        val urls = getWebSocketUrls()
        if (urls.isEmpty()) {
            Log.e(TAG, "No backend URLs configured")
            return
        }

        if (currentUrlIndex >= urls.size) {
            currentUrlIndex = 0
        }
        val url = urls[currentUrlIndex]
        Log.d(TAG, "Attempting Companion WebSocket connection to: $url")

        val request = Request.Builder().url(url).build()
        webSocket = client.newWebSocket(request, object : WebSocketListener() {
            override fun onOpen(ws: WebSocket, response: Response) {
                Log.d(TAG, "Connected to Jarvis Companion endpoint: $url")
                reconnectAttempts = 0
                lastPongTimestamp = System.currentTimeMillis()

                // Register as mobile companion device with the backend
                sendToBackend(JSONObject().apply {
                    put("type", "register")
                    put("device", "mobile")
                })

                // Start application-level heartbeat ping
                startHeartbeat()
            }

            override fun onMessage(ws: WebSocket, text: String) {
                Log.d(TAG, "Received message from backend: $text")
                try {
                    val json = JSONObject(text)
                    handleBackendMessage(json)
                } catch (e: Exception) {
                    Log.e(TAG, "Error parsing message from backend", e)
                }
            }

            override fun onFailure(ws: WebSocket, t: Throwable, response: Response?) {
                Log.w(TAG, "WebSocket failure on $url: ${t.message}")
                stopHeartbeat()
                scheduleReconnect()
            }

            override fun onClosed(ws: WebSocket, code: Int, reason: String) {
                Log.d(TAG, "WebSocket closed ($code): $reason")
                stopHeartbeat()
                scheduleReconnect()
            }
        })
    }

    private fun handleBackendMessage(data: JSONObject) {
        val type = data.optString("type")
        if (type == "pong") {
            lastPongTimestamp = System.currentTimeMillis()
            return
        }

        val action = data.optString("action")
        val taskId = data.optString("task_id")
        val params = data.optJSONObject("params") ?: JSONObject()

        if (action.isBlank() && taskId.isBlank()) {
            return
        }

        Log.d(TAG, "Processing action: $action, taskId: $taskId")

        try {
            when (action) {
                "make_call" -> {
                    val number = params.optString("number")
                    if (number.isNotBlank()) {
                        val dialIntent = Intent(Intent.ACTION_DIAL).apply {
                            this.data = Uri.parse("tel:$number")
                            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                        }
                        startActivity(dialIntent)
                        sendResult(taskId, true, "Call initiated to $number", null)
                    } else {
                        sendResult(taskId, false, null, "Missing phone number")
                    }
                }
                "send_sms" -> {
                    val number = params.optString("number")
                    val message = params.optString("message")
                    if (number.isNotBlank()) {
                        val smsIntent = Intent(Intent.ACTION_SENDTO).apply {
                            this.data = Uri.parse("smsto:$number")
                            putExtra("sms_body", message)
                            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                        }
                        startActivity(smsIntent)
                        sendResult(taskId, true, "SMS composer opened for $number", null)
                    } else {
                        sendResult(taskId, false, null, "Missing destination phone number")
                    }
                }
                "show_notification" -> {
                    val title = params.optString("title").ifBlank { "Jarvis" }
                    val message = params.optString("message").ifBlank { params.optString("body") }
                    showNativeAlert(title, message)
                    sendResult(taskId, true, "Notification displayed", null)
                }
                "get_battery" -> {
                    val ifilter = IntentFilter(Intent.ACTION_BATTERY_CHANGED)
                    val batteryStatus: Intent? = registerReceiver(null, ifilter)
                    val level: Int = batteryStatus?.getIntExtra(BatteryManager.EXTRA_LEVEL, -1) ?: -1
                    val scale: Int = batteryStatus?.getIntExtra(BatteryManager.EXTRA_SCALE, -1) ?: -1
                    val batteryPct = if (level >= 0 && scale > 0) (level * 100 / scale) else 0
                    val status: Int = batteryStatus?.getIntExtra(BatteryManager.EXTRA_STATUS, -1) ?: -1
                    val isCharging = status == BatteryManager.BATTERY_STATUS_CHARGING || status == BatteryManager.BATTERY_STATUS_FULL
                    sendResult(taskId, true, "Battery level: $batteryPct%, Charging: $isCharging", null)
                }
                "open_app", "launch_app" -> {
                    val target = params.optString("app_name").ifBlank {
                        params.optString("name").ifBlank { params.optString("target") }
                    }
                    val success = AppLauncher.openApp(this, target)
                    sendResult(taskId, success, if (success) "Successfully opened $target" else null, if (!success) "Failed to open $target" else null)
                }
                "close_app" -> {
                    val target = params.optString("app_name").ifBlank {
                        params.optString("name").ifBlank { params.optString("target") }
                    }
                    val success = AppLauncher.closeApp(this, target.ifBlank { "current" })
                    sendResult(taskId, success, if (success) "Successfully closed $target" else null, if (!success) "Failed to close $target" else null)
                }
                "tap", "tapXY" -> {
                    val x = params.optDouble("x", 0.0).toFloat()
                    val y = params.optDouble("y", 0.0).toFloat()
                    val target = params.optString("target")
                    val success = JarvisAccessibilityService.instance?.performAction("tap", target, x, y, "") ?: false
                    sendResult(taskId, success, if (success) "Tapped element" else null, if (!success) "Accessibility service not running or tap failed" else null)
                }
                "type_text", "type" -> {
                    val text = params.optString("text").ifBlank { params.optString("target") }
                    val success = JarvisAccessibilityService.instance?.performAction("type_text", "", 0f, 0f, text) ?: false
                    sendResult(taskId, success, if (success) "Typed text" else null, if (!success) "Accessibility service not running or type failed" else null)
                }
                "scroll" -> {
                    val dir = params.optString("direction").ifBlank { params.optString("target").ifBlank { "down" } }
                    val success = JarvisAccessibilityService.instance?.performAction("scroll", dir, 0f, 0f, "") ?: false
                    sendResult(taskId, success, if (success) "Scrolled $dir" else null, if (!success) "Accessibility service not running or scroll failed" else null)
                }
                "back", "home", "recents", "notifications" -> {
                    val success = JarvisAccessibilityService.instance?.performAction(action, "", 0f, 0f, "") ?: false
                    sendResult(taskId, success, if (success) "Performed $action" else null, if (!success) "Accessibility action $action failed" else null)
                }
                "read_screen" -> {
                    val elements = JarvisAccessibilityService.instance?.readScreen() ?: "[]"
                    sendResult(taskId, true, elements, null)
                }
                "speak", "tts", "play_audio" -> {
                    val speechText = params.optString("text")
                    if (speechText.isNotBlank()) {
                        ttsEngine.speak(speechText)
                    }
                    sendResult(taskId, true, "Spoken successfully", null)
                }
                else -> {
                    sendResult(taskId, false, null, "Action '$action' not supported on mobile companion")
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error executing action: $action", e)
            sendResult(taskId, false, null, e.message ?: "Execution failed")
        }
    }

    private fun sendResult(taskId: String, success: Boolean, output: String?, error: String?) {
        if (taskId.isBlank()) return
        val res = JSONObject().apply {
            put("task_id", taskId)
            put("status", if (success) "success" else "error")
            if (output != null) put("output", output)
            if (error != null) put("error", error)
        }
        sendToBackend(res)
    }

    private fun showNativeAlert(title: String, message: String) {
        try {
            val nm = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            val notif = NotificationCompat.Builder(this, ALERTS_CHANNEL_ID)
                .setContentTitle(title)
                .setContentText(message)
                .setSmallIcon(android.R.drawable.ic_dialog_info)
                .setAutoCancel(true)
                .setPriority(NotificationCompat.PRIORITY_HIGH)
                .build()
            nm.notify(System.currentTimeMillis().toInt(), notif)
        } catch (e: Exception) {
            Log.w(TAG, "Error showing alert notification", e)
        }
    }

    fun sendToBackend(payload: JSONObject) {
        try {
            webSocket?.send(payload.toString())
        } catch (e: Exception) {
            Log.w(TAG, "Failed sending to backend", e)
        }
    }

    /** Heartbeat ping every 25 seconds; checks if connection is stale */
    private fun startHeartbeat() {
        stopHeartbeat()
        heartbeatTask = scheduler.scheduleAtFixedRate({
            if (isDestroyed) return@scheduleAtFixedRate
            // Check if last pong was more than 40s ago
            if (System.currentTimeMillis() - lastPongTimestamp > 40000L) {
                Log.w(TAG, "Heartbeat timeout — no pong received. Reconnecting...")
                stopHeartbeat()
                scheduleReconnect()
                return@scheduleAtFixedRate
            }

            try {
                sendToBackend(JSONObject().apply {
                    put("type", "ping")
                })
            } catch (e: Exception) {
                Log.w(TAG, "Heartbeat ping send failed", e)
            }
        }, 25, 25, TimeUnit.SECONDS)
    }

    private fun stopHeartbeat() {
        heartbeatTask?.cancel(true)
        heartbeatTask = null
    }

    /** Exponential backoff reconnect: 1s, 2s, 4s, 8s, up to 60s max */
    @Synchronized
    private fun scheduleReconnect() {
        if (isDestroyed) return
        if (reconnectTask?.isDone == false) return

        val urls = getWebSocketUrls()
        if (urls.isNotEmpty()) {
            currentUrlIndex = (currentUrlIndex + 1) % urls.size
        }

        val delaySeconds = Math.min(1L shl Math.min(reconnectAttempts, 6), 60L)
        reconnectAttempts++
        Log.d(TAG, "Scheduling reconnect in ${delaySeconds}s (attempt $reconnectAttempts)...")

        reconnectTask = scheduler.schedule({
            connectWebSocket()
        }, delaySeconds, TimeUnit.SECONDS)
    }

    /** Called by DeviceHandsPlugin when frontend resolves a new backend URL */
    fun updateBackendUrl(newUrl: String) {
        Log.d(TAG, "Backend URL updated from frontend: $newUrl")
        currentUrlIndex = 0
        reconnectAttempts = 0
        reconnectTask?.cancel(true)
        connectWebSocket()
    }

    private fun registerNetworkCallback() {
        try {
            connectivityManager = getSystemService(Context.CONNECTIVITY_SERVICE) as? ConnectivityManager
            val request = NetworkRequest.Builder()
                .addCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
                .build()

            networkCallback = object : ConnectivityManager.NetworkCallback() {
                override fun onAvailable(network: Network) {
                    Log.d(TAG, "Network connection restored, checking WebSocket...")
                    // If not currently connected, trigger immediate reconnect
                    if (webSocket == null || reconnectTask?.isDone == false) {
                        reconnectAttempts = 0
                        reconnectTask?.cancel(true)
                        connectWebSocket()
                    }
                }
            }
            connectivityManager?.registerNetworkCallback(request, networkCallback!!)
        } catch (e: Exception) {
            Log.w(TAG, "Failed registering network callback", e)
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        isDestroyed = true
        stopHeartbeat()
        reconnectTask?.cancel(true)
        scheduler.shutdownNow()

        try {
            if (networkCallback != null && connectivityManager != null) {
                connectivityManager?.unregisterNetworkCallback(networkCallback!!)
            }
        } catch (ignored: Exception) {}

        wakeWordEngine.stopListening()
        ttsEngine.destroy()
        try {
            webSocket?.close(1000, "Service destroyed")
        } catch (ignored: Exception) {}
        webSocket = null

        try {
            if (wakeLock?.isHeld == true) {
                wakeLock?.release()
            }
        } catch (e: Exception) {
            Log.w(TAG, "Error releasing WakeLock", e)
        }
        wakeLock = null
        instance = null
    }

    override fun onBind(intent: Intent): IBinder? {
        return null
    }

    private fun createNotificationChannels() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val manager = getSystemService(NotificationManager::class.java)

            val serviceChannel = NotificationChannel(
                CHANNEL_ID,
                "Jarvis Background Service Channel",
                NotificationManager.IMPORTANCE_LOW
            )
            manager?.createNotificationChannel(serviceChannel)

            val alertsChannel = NotificationChannel(
                ALERTS_CHANNEL_ID,
                "Jarvis Alerts Channel",
                NotificationManager.IMPORTANCE_HIGH
            )
            manager?.createNotificationChannel(alertsChannel)
        }
    }
}
