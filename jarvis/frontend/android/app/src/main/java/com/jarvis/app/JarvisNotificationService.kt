package com.jarvis.app

import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import android.util.Log

class JarvisNotificationService : NotificationListenerService() {

    override fun onNotificationPosted(sbn: StatusBarNotification?) {
        super.onNotificationPosted(sbn)
        sbn?.let {
            val packageName = it.packageName
            val extras = it.notification.extras
            val title = extras.getString("android.title")
            val text = extras.getCharSequence("android.text")?.toString()
            
            Log.d("JarvisNotification", "New Notification from $packageName: Title: $title, Text: $text")
            
            // Here you can send this data back to the Capacitor bridge or backend websocket
            // Example: sendEventToFrontend("notification", mapOf("app" to packageName, "title" to title, "text" to text))
        }
    }

    override fun onNotificationRemoved(sbn: StatusBarNotification?) {
        super.onNotificationRemoved(sbn)
        // Handle notification dismissed
    }
}
