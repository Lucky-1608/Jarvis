package com.jarvis.app

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.IBinder
import android.os.PowerManager
import android.util.Log
import androidx.core.app.NotificationCompat
import okhttp3.*
import org.json.JSONObject
import java.util.concurrent.TimeUnit

class JarvisBackgroundService : Service() {

    companion object {
        const val CHANNEL_ID = "JarvisServiceChannel"
        var instance: JarvisBackgroundService? = null
    }

    private var webSocket: WebSocket? = null
    private val client = OkHttpClient.Builder()
        .readTimeout(0, TimeUnit.MILLISECONDS)
        .build()
        
    private lateinit var ttsEngine: JarvisTTS
    private lateinit var wakeWordEngine: JarvisWakeWordEngine
    private var wakeLock: PowerManager.WakeLock? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        // Ensures the service is revived by Android if killed under memory pressure
        return START_STICKY
    }

    override fun onCreate() {
        super.onCreate()
        instance = this
        createNotificationChannel()

        // Acquire partial WakeLock so CPU keeps WebSocket and wake word alive while screen is off
        try {
            val powerManager = getSystemService(Context.POWER_SERVICE) as? PowerManager
            wakeLock = powerManager?.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "Jarvis::ServiceWakeLock")?.apply {
                setReferenceCounted(false)
                acquire(24 * 60 * 60 * 1000L) // 24 hours fallback limit
            }
        } catch (e: Exception) {
            Log.w("JarvisBackground", "Could not acquire WakeLock", e)
        }

        val notification: Notification = NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("Jarvis Background Service")
            .setContentText("Listening for wake word and backend commands...")
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setOngoing(true)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .build()
        
        startForeground(1, notification)

        ttsEngine = JarvisTTS(this)
        wakeWordEngine = JarvisWakeWordEngine(this) {
            // Wake word detected
            ttsEngine.speak("Yes, how can I help?")
            // We can also send a signal to the backend
            sendToBackend(JSONObject().apply {
                put("type", "wake_word_detected")
            })
        }
        wakeWordEngine.startListening()

        connectWebSocket()
    }

    private var urlsToTry = emptyList<String>()
    private var currentUrlIndex = 0

    private fun connectWebSocket() {
        if (urlsToTry.isEmpty()) {
            val envUrls = BuildConfig.VITE_API_BASE_URL
            urlsToTry = envUrls.split(",")
                .filter { it.isNotBlank() }
                .map { 
                    it.trim()
                        .replace("http://", "ws://")
                        .replace("https://", "wss://") + "/api/hud/ws?token=JARVIS_DEV_KEY"
                }
        }

        if (urlsToTry.isEmpty()) {
            Log.e("JarvisBackground", "No backend URLs configured in .env")
            return
        }

        val url = urlsToTry[currentUrlIndex]
        Log.d("JarvisBackground", "Attempting connection to: $url")
        val request = Request.Builder().url(url).build()
        
        webSocket = client.newWebSocket(request, object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                Log.d("JarvisBackground", "Connected to Jarvis backend")
                // Reset to first URL if connected successfully (assuming it's preferred)
                currentUrlIndex = 0
                sendToBackend(JSONObject().apply {
                    put("type", "mobile_node_connected")
                })
            }

            override fun onMessage(webSocket: WebSocket, text: String) {
                Log.d("JarvisBackground", "Received message: $text")
                try {
                    val json = JSONObject(text)
                    handleBackendCommand(json)
                } catch (e: Exception) {
                    Log.e("JarvisBackground", "Error parsing message", e)
                }
            }

            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                Log.e("JarvisBackground", "WebSocket Failure on $url", t)
                // Cycle to the next URL in the list
                currentUrlIndex = (currentUrlIndex + 1) % urlsToTry.size
                Thread.sleep(2000) // wait 2s before trying next
                connectWebSocket()
            }
        })
    }
    
    private fun handleBackendCommand(command: JSONObject) {
        val type = command.optString("type")
        val action = command.optString("action")

        val speechText = when {
            command.has("text") -> command.optString("text")
            command.has("data") -> {
                val dataObj = command.optJSONObject("data")
                dataObj?.optString("text") ?: ""
            }
            command.has("params") -> {
                val paramsObj = command.optJSONObject("params")
                paramsObj?.optString("text") ?: ""
            }
            else -> ""
        }

        if (type == "tts" || type == "tts.started" || action == "speak" || action == "play_audio") {
            if (speechText.isNotEmpty()) {
                ttsEngine.speak(speechText)
                return
            }
        }

        when (type) {
            "open_app" -> {
                val target = command.optString("target").ifBlank { command.optString("app_name") }
                val success = AppLauncher.openApp(this, target)
                sendToBackend(JSONObject().apply {
                    put("type", "action_result")
                    put("action", "open_app")
                    put("success", success)
                })
            }
            "close_app" -> {
                val target = command.optString("target").ifBlank { command.optString("app_name") }
                val success = AppLauncher.closeApp(this, target)
                sendToBackend(JSONObject().apply {
                    put("type", "action_result")
                    put("action", "close_app")
                    put("success", success)
                })
            }
            "perform_action" -> {
                val act = command.optString("action")
                val target = command.optString("target").ifBlank { command.optString("app_name") }
                val text = command.optString("text")
                val x = command.optDouble("x", 0.0).toFloat()
                val y = command.optDouble("y", 0.0).toFloat()
                val success = when (act) {
                    "open_app", "launch_app" -> AppLauncher.openApp(this, target)
                    "close_app", "close" -> AppLauncher.closeApp(this, target)
                    else -> JarvisAccessibilityService.instance?.performAction(act, target, x, y, text) ?: false
                }
                sendToBackend(JSONObject().apply {
                    put("type", "action_result")
                    put("action", act)
                    put("success", success)
                })
            }
            "read_screen" -> {
                val elements = JarvisAccessibilityService.instance?.readScreen() ?: "[]"
                sendToBackend(JSONObject().apply {
                    put("type", "screen_data")
                    put("elements", elements)
                })
            }
        }
    }

    fun sendToBackend(payload: JSONObject) {
        webSocket?.send(payload.toString())
    }

    override fun onDestroy() {
        super.onDestroy()
        wakeWordEngine.stopListening()
        ttsEngine.destroy()
        webSocket?.close(1000, "Service destroyed")
        try {
            if (wakeLock?.isHeld == true) {
                wakeLock?.release()
            }
        } catch (e: Exception) {
            Log.w("JarvisBackground", "Error releasing WakeLock", e)
        }
        wakeLock = null
        instance = null
    }

    override fun onBind(intent: Intent): IBinder? {
        return null
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val serviceChannel = NotificationChannel(
                CHANNEL_ID,
                "Jarvis Background Service Channel",
                NotificationManager.IMPORTANCE_DEFAULT
            )
            val manager = getSystemService(NotificationManager::class.java)
            manager?.createNotificationChannel(serviceChannel)
        }
    }
}
