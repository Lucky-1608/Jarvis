package com.jarvis.app

import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.GestureDescription
import android.graphics.Path
import android.graphics.Rect
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo
import android.util.Log
import org.json.JSONArray
import org.json.JSONObject

class JarvisAccessibilityService : AccessibilityService() {
    
    companion object {
        var instance: JarvisAccessibilityService? = null
    }

    override fun onServiceConnected() {
        super.onServiceConnected()
        instance = this
        Log.d("JarvisDeviceHands", "Accessibility Service Connected")
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        // Track screen changes if necessary
    }

    override fun onInterrupt() {
        Log.d("JarvisDeviceHands", "Accessibility Service Interrupted")
        instance = null
    }
    
    override fun onDestroy() {
        super.onDestroy()
        instance = null
    }

    // Exposed for Capacitor bridge
    fun performAction(action: String, target: String, x: Float = 0f, y: Float = 0f): Boolean {
        val root = rootInActiveWindow ?: return false
        
        when(action) {
            "tap" -> {
                // robust tap matching text or content description
                val nodes = root.findAccessibilityNodeInfosByText(target)
                if (nodes.isNotEmpty()) {
                    var node: AccessibilityNodeInfo? = nodes[0]
                    while (node != null) {
                        if (node.isClickable) {
                            node.performAction(AccessibilityNodeInfo.ACTION_CLICK)
                            return true
                        }
                        node = node.parent
                    }
                    nodes[0].performAction(AccessibilityNodeInfo.ACTION_CLICK)
                    return true
                }
            }
            "tapXY" -> {
                val path = Path()
                path.moveTo(x, y)
                val gestureBuilder = GestureDescription.Builder()
                gestureBuilder.addStroke(GestureDescription.StrokeDescription(path, 0, 100))
                return dispatchGesture(gestureBuilder.build(), null, null)
            }
            "scroll" -> {
                root.performAction(AccessibilityNodeInfo.ACTION_SCROLL_FORWARD)
                return true
            }
        }
        return false
    }

    fun readScreen(): String {
        val root = rootInActiveWindow ?: return "[]"
        val elements = JSONArray()
        traverseNode(root, elements)
        return elements.toString()
    }

    private fun traverseNode(node: AccessibilityNodeInfo?, elements: JSONArray) {
        if (node == null) return
        
        val text = node.text?.toString()
        val desc = node.contentDescription?.toString()
        
        if (!text.isNullOrEmpty() || !desc.isNullOrEmpty() || node.isClickable) {
            val rect = Rect()
            node.getBoundsInScreen(rect)
            
            val obj = JSONObject()
            if (!text.isNullOrEmpty()) obj.put("text", text)
            if (!desc.isNullOrEmpty()) obj.put("contentDescription", desc)
            obj.put("bounds", "${rect.left},${rect.top},${rect.right},${rect.bottom}")
            obj.put("clickable", node.isClickable)
            
            elements.put(obj)
        }

        for (i in 0 until node.childCount) {
            traverseNode(node.getChild(i), elements)
        }
    }
}
