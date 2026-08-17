package com.jarvis.app

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Intent
import android.os.Build
import android.os.IBinder
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

    override fun onCreate() {
        super.onCreate()
        instance = this
        createNotificationChannel()
        val notification: Notification = NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("Jarvis Background Service")
            .setContentText("Listening for wake word and backend commands...")
            .setSmallIcon(android.R.drawable.ic_dialog_info)
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
        when (type) {
            "tts" -> {
                val text = command.optString("text")
                if (text.isNotEmpty()) {
                    ttsEngine.speak(text)
                }
            }
            "perform_action" -> {
                val action = command.optString("action")
                val target = command.optString("target")
                val x = command.optDouble("x", 0.0).toFloat()
                val y = command.optDouble("y", 0.0).toFloat()
                val success = JarvisAccessibilityService.instance?.performAction(action, target, x, y) ?: false
                sendToBackend(JSONObject().apply {
                    put("type", "action_result")
                    put("action", action)
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
