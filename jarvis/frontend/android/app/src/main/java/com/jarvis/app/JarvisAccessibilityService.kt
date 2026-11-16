package com.jarvis.app

import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.GestureDescription
import android.graphics.Bitmap
import android.graphics.Path
import android.graphics.Rect
import android.os.Build
import android.util.Base64
import android.util.Log
import android.view.Display
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo
import androidx.core.content.ContextCompat
import org.json.JSONArray
import org.json.JSONObject
import java.io.ByteArrayOutputStream

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

    fun captureScreen(callback: (success: Boolean, base64: String?, width: Int, height: Int, error: String?) -> Unit) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            val executor = ContextCompat.getMainExecutor(this)
            takeScreenshot(
                Display.DEFAULT_DISPLAY,
                executor,
                object : TakeScreenshotCallback {
                    override fun onSuccess(screenshotResult: ScreenshotResult) {
                        try {
                            val hardwareBuffer = screenshotResult.hardwareBuffer
                            val colorSpace = screenshotResult.colorSpace
                            val bitmap = Bitmap.wrapHardwareBuffer(hardwareBuffer, colorSpace)
                            if (bitmap != null) {
                                val softwareBitmap = bitmap.copy(Bitmap.Config.ARGB_8888, false)
                                hardwareBuffer.close()

                                val stream = ByteArrayOutputStream()
                                softwareBitmap.compress(Bitmap.CompressFormat.JPEG, 80, stream)
                                val byteArray = stream.toByteArray()
                                val base64 = Base64.encodeToString(byteArray, Base64.NO_WRAP)
                                val width = softwareBitmap.width
                                val height = softwareBitmap.height
                                softwareBitmap.recycle()
                                bitmap.recycle()
                                callback(true, base64, width, height, null)
                            } else {
                                hardwareBuffer.close()
                                callback(false, null, 0, 0, "Failed to create bitmap from hardware buffer")
                            }
                        } catch (e: Exception) {
                            Log.e("JarvisAccessibility", "Failed to process screenshot", e)
                            callback(false, null, 0, 0, e.message ?: "Screenshot processing error")
                        }
                    }

                    override fun onFailure(errorCode: Int) {
                        val errMsg = when (errorCode) {
                            ERROR_TAKE_SCREENSHOT_INTERNAL_ERROR -> "Internal screenshot error"
                            ERROR_TAKE_SCREENSHOT_NO_END_OF_FRAME -> "No end of frame"
                            ERROR_TAKE_SCREENSHOT_INVALID_DISPLAY -> "Invalid display"
                            ERROR_TAKE_SCREENSHOT_INTERVAL_TIME_SHORT -> "Interval time too short"
                            else -> "Screenshot failed with error code $errorCode"
                        }
                        Log.e("JarvisAccessibility", errMsg)
                        callback(false, null, 0, 0, errMsg)
                    }
                }
            )
        } else {
            callback(false, null, 0, 0, "Native screen capture requires Android 11+ (API 30+)")
        }
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
