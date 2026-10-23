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
    fun performAction(action: String, target: String, x: Float = 0f, y: Float = 0f, text: String = ""): Boolean {
        // 1. Global Navigation Actions (do not require active window root)
        when (action) {
            "back", "go_back" -> {
                return performGlobalAction(GLOBAL_ACTION_BACK)
            }
            "home", "go_home" -> {
                return performGlobalAction(GLOBAL_ACTION_HOME)
            }
            "recents", "overview" -> {
                return performGlobalAction(GLOBAL_ACTION_RECENTS)
            }
            "notifications" -> {
                return performGlobalAction(GLOBAL_ACTION_NOTIFICATIONS)
            }
            "close_app", "close" -> {
                return performGlobalAction(GLOBAL_ACTION_HOME)
            }
        }

        // 2. Window / Node Actions
        val root = rootInActiveWindow ?: return false
        
        when (action) {
            "type_text", "type" -> {
                val inputNode = root.findFocus(AccessibilityNodeInfo.FOCUS_INPUT)
                    ?: root.findFocus(AccessibilityNodeInfo.FOCUS_ACCESSIBILITY)
                if (inputNode != null) {
                    val contentToType = if (text.isNotBlank()) text else target
                    val arguments = android.os.Bundle().apply {
                        putCharSequence(
                            AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE,
                            contentToType
                        )
                    }
                    return inputNode.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, arguments)
                }
                return false
            }
            "tap" -> {
                if (x > 0f && y > 0f) {
                    val path = Path()
                    path.moveTo(x, y)
                    val gestureBuilder = GestureDescription.Builder()
                    gestureBuilder.addStroke(GestureDescription.StrokeDescription(path, 0, 100))
                    return dispatchGesture(gestureBuilder.build(), null, null)
                }
                // Robust tap matching text or content description
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
                val dir = target.lowercase().trim()
                if (dir == "up" || dir == "backward") {
                    return root.performAction(AccessibilityNodeInfo.ACTION_SCROLL_BACKWARD)
                } else if (dir == "down" || dir == "forward" || dir.isEmpty()) {
                    return root.performAction(AccessibilityNodeInfo.ACTION_SCROLL_FORWARD)
                } else {
                    // Gesture swipe fallback for horizontal scrolling
                    val displayMetrics = resources.displayMetrics
                    val width = displayMetrics.widthPixels.toFloat()
                    val height = displayMetrics.heightPixels.toFloat()
                    val path = Path()
                    if (dir == "left") {
                        path.moveTo(width * 0.8f, height * 0.5f)
                        path.lineTo(width * 0.2f, height * 0.5f)
                    } else {
                        path.moveTo(width * 0.2f, height * 0.5f)
                        path.lineTo(width * 0.8f, height * 0.5f)
                    }
                    val gestureBuilder = GestureDescription.Builder()
                    gestureBuilder.addStroke(GestureDescription.StrokeDescription(path, 0, 300))
                    return dispatchGesture(gestureBuilder.build(), null, null)
                }
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
