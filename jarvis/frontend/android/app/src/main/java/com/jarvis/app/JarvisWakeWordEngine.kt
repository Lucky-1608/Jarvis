package com.jarvis.app

import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.util.Log

class JarvisWakeWordEngine(
    private val context: Context,
    private val onWakeWordDetected: () -> Unit
) {
    companion object {
        private const val TAG = "JarvisWakeWord"
        private val WAKE_WORDS = listOf(
            "jarvis",
            "hey jarvis",
            "hi jarvis",
            "ok jarvis",
            "okay jarvis",
            "hello jarvis"
        )
        private const val TRIGGER_COOLDOWN_MS = 2500L
    }

    private var speechRecognizer: SpeechRecognizer? = null
    private var isListening = false
    private val mainHandler = Handler(Looper.getMainLooper())
    private var restartRunnable: Runnable? = null
    private var lastTriggerTime = 0L

    fun startListening() {
        mainHandler.post {
            isListening = true
            initAndStartRecognizer()
        }
    }

    private fun initAndStartRecognizer() {
        if (!isListening) return

        cleanupRecognizer()

        if (!SpeechRecognizer.isRecognitionAvailable(context)) {
            Log.e(TAG, "Speech recognition not available on this device")
            scheduleRestart(5000L)
            return
        }

        try {
            // Prefer on-device speech recognizer on Android 12+ (API 31+) if available
            // to avoid network timeouts, server rate-limits, and background throttling
            val recognizer = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S &&
                SpeechRecognizer.isOnDeviceRecognitionAvailable(context)
            ) {
                Log.d(TAG, "Using on-device SpeechRecognizer")
                SpeechRecognizer.createOnDeviceSpeechRecognizer(context)
            } else {
                SpeechRecognizer.createSpeechRecognizer(context)
            }

            recognizer.setRecognitionListener(object : RecognitionListener {
                override fun onReadyForSpeech(params: Bundle?) {}
                override fun onBeginningOfSpeech() {}
                override fun onRmsChanged(rmsdB: Float) {}
                override fun onBufferReceived(buffer: ByteArray?) {}
                override fun onEndOfSpeech() {}

                override fun onError(error: Int) {
                    Log.d(TAG, "SpeechRecognizer error code: $error")
                    if (!isListening) return

                    // Use appropriate delay based on error type to prevent infinite busy loops:
                    // Error 6: SPEECH_TIMEOUT, Error 7: NO_MATCH (normal silence timeouts)
                    // Error 8: RECOGNIZER_BUSY, Error 5: CLIENT error (require backoff)
                    val delay = when (error) {
                        SpeechRecognizer.ERROR_SPEECH_TIMEOUT,
                        SpeechRecognizer.ERROR_NO_MATCH -> 400L
                        SpeechRecognizer.ERROR_RECOGNIZER_BUSY -> 1500L
                        SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS -> 5000L
                        else -> 1000L
                    }
                    scheduleRestart(delay)
                }

                override fun onResults(results: Bundle?) {
                    val matches = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                    if (matches != null) {
                        for (match in matches) {
                            Log.d(TAG, "Heard (final): $match")
                            if (checkAndHandleWakeWord(match)) {
                                return
                            }
                        }
                    }
                    if (isListening) {
                        scheduleRestart(300L)
                    }
                }

                override fun onPartialResults(partialResults: Bundle?) {
                    // Enable early detection without waiting for end-of-speech silence
                    val matches = partialResults?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                    if (matches != null) {
                        for (match in matches) {
                            Log.d(TAG, "Heard (partial): $match")
                            if (checkAndHandleWakeWord(match)) {
                                return
                            }
                        }
                    }
                }

                override fun onEvent(eventType: Int, params: Bundle?) {}
            })

            speechRecognizer = recognizer

            val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
                putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                putExtra(RecognizerIntent.EXTRA_CALLING_PACKAGE, context.packageName)
                putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
                putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 3)
            }

            recognizer.startListening(intent)
        } catch (e: Exception) {
            Log.e(TAG, "Error starting SpeechRecognizer", e)
            scheduleRestart(2000L)
        }
    }

    private fun checkAndHandleWakeWord(text: String): Boolean {
        val clean = text.lowercase().replace(Regex("[^a-z0-9\\s]"), " ").trim()
        val detected = WAKE_WORDS.any { clean.contains(it) }

        if (detected) {
            val now = System.currentTimeMillis()
            if (now - lastTriggerTime < TRIGGER_COOLDOWN_MS) {
                Log.d(TAG, "Wake word detected during cooldown, ignoring.")
                return true
            }
            lastTriggerTime = now
            Log.d(TAG, "Wake word detected: '$text'")

            // Pause recognizer immediately to avoid listening to our own TTS response
            cleanupRecognizer()

            try {
                onWakeWordDetected()
            } catch (e: Exception) {
                Log.e(TAG, "Error in wake word callback", e)
            }

            // Resume listening after acknowledgment
            scheduleRestart(2500L)
            return true
        }
        return false
    }

    private fun scheduleRestart(delayMs: Long) {
        if (!isListening) return
        cancelPendingRestart()
        val runnable = Runnable {
            if (isListening) {
                initAndStartRecognizer()
            }
        }
        restartRunnable = runnable
        mainHandler.postDelayed(runnable, delayMs)
    }

    private fun cancelPendingRestart() {
        restartRunnable?.let {
            mainHandler.removeCallbacks(it)
            restartRunnable = null
        }
    }

    private fun cleanupRecognizer() {
        try {
            speechRecognizer?.cancel()
            speechRecognizer?.destroy()
        } catch (e: Exception) {
            Log.w(TAG, "Error destroying speech recognizer", e)
        }
        speechRecognizer = null
    }

    fun stopListening() {
        mainHandler.post {
            isListening = false
            cancelPendingRestart()
            cleanupRecognizer()
            Log.d(TAG, "Wake word listener stopped")
        }
    }
}
