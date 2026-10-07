package com.jarvis.app

import android.content.Context
import android.speech.tts.TextToSpeech
import android.util.Log
import java.util.Locale

class JarvisTTS(context: Context) : TextToSpeech.OnInitListener {
    private var tts: TextToSpeech? = null
    private var isInitialized = false

    private val pendingQueue = mutableListOf<String>()

    init {
        tts = TextToSpeech(context, this)
    }

    override fun onInit(status: Int) {
        if (status == TextToSpeech.SUCCESS) {
            val result = tts?.setLanguage(Locale.US)
            if (result == TextToSpeech.LANG_MISSING_DATA || result == TextToSpeech.LANG_NOT_SUPPORTED) {
                Log.e("JarvisTTS", "Language not supported")
            } else {
                isInitialized = true
                Log.d("JarvisTTS", "TTS Initialized Successfully")
                for (queuedText in pendingQueue) {
                    tts?.speak(queuedText, TextToSpeech.QUEUE_ADD, null, "jarvis_tts_id")
                }
                pendingQueue.clear()
            }
        } else {
            Log.e("JarvisTTS", "Initialization failed")
        }
    }

    fun speak(text: String) {
        if (isInitialized) {
            tts?.speak(text, TextToSpeech.QUEUE_FLUSH, null, "jarvis_tts_id")
        } else {
            Log.d("JarvisTTS", "TTS not initialized yet, queueing text: $text")
            pendingQueue.add(text)
        }
    }

    fun stop() {
        if (isInitialized) {
            tts?.stop()
        }
    }

    fun destroy() {
        tts?.stop()
        tts?.shutdown()
    }
}
