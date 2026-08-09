package com.jarvis.app

import android.accessibilityservice.AccessibilityService
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo
import android.util.Log

class JarvisAccessibilityService : AccessibilityService() {

    override fun onServiceConnected() {
        super.onServiceConnected()
        Log.d("JarvisDeviceHands", "Accessibility Service Connected")
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        // Track screen changes
    }

    override fun onInterrupt() {
        Log.d("JarvisDeviceHands", "Accessibility Service Interrupted")
    }
    
    // Exposed for Capacitor bridge
    fun performAction(action: String, target: String): Boolean {
        val root = rootInActiveWindow ?: return false
        
        when(action) {
            "tap" -> {
                val nodes = root.findAccessibilityNodeInfosByText(target)
                if (nodes.isNotEmpty()) {
                    nodes[0].performAction(AccessibilityNodeInfo.ACTION_CLICK)
                    return true
                }
            }
            "scroll" -> {
                root.performAction(AccessibilityNodeInfo.ACTION_SCROLL_FORWARD)
                return true
            }
        }
        return false
    }
}
