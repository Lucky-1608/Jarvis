package com.jarvis.app

import com.getcapacitor.JSObject
import com.getcapacitor.Plugin
import com.getcapacitor.PluginCall
import com.getcapacitor.PluginMethod
import com.getcapacitor.annotation.CapacitorPlugin

@CapacitorPlugin(name = "DeviceHands")
class DeviceHandsPlugin : Plugin() {

    @PluginMethod
    fun launchApp(call: PluginCall) {
        val name = call.getString("name") ?: call.getString("target") ?: call.getString("app_name")
        if (!name.isNullOrBlank()) {
            val success = AppLauncher.openApp(context, name)
            val ret = JSObject()
            ret.put("success", success)
            if (success) {
                ret.put("message", "Successfully launched $name")
                call.resolve(ret)
            } else {
                ret.put("error", "Failed to launch app: $name")
                call.reject("Failed to launch app: $name")
            }
        } else {
            call.reject("Missing required parameter: name")
        }
    }

    @PluginMethod
    fun performAction(call: PluginCall) {
        val action = call.getString("action")
        val target = call.getString("target") ?: call.getString("name") ?: call.getString("app_name") ?: ""

        when (action) {
            "open_app", "launch_app" -> {
                if (target.isNotBlank()) {
                    val success = AppLauncher.openApp(context, target)
                    val ret = JSObject()
                    ret.put("success", success)
                    if (success) {
                        ret.put("message", "Successfully opened $target")
                        call.resolve(ret)
                    } else {
                        call.reject("Failed to open app: $target")
                    }
                } else {
                    call.reject("Missing target app name")
                }
            }
            "tap", "tapXY", "scroll" -> {
                val x = call.getDouble("x", 0.0)?.toFloat() ?: 0f
                val y = call.getDouble("y", 0.0)?.toFloat() ?: 0f
                val success = JarvisAccessibilityService.instance?.performAction(action, target, x, y) ?: false
                val ret = JSObject()
                ret.put("success", success)
                if (success) {
                    call.resolve(ret)
                } else {
                    call.reject("Failed to perform accessibility action: $action")
                }
            }
            else -> {
                call.reject("Unknown action or missing target: $action")
            }
        }
    }

    @PluginMethod
    fun readScreen(call: PluginCall) {
        val elements = JarvisAccessibilityService.instance?.readScreen() ?: "[]"
        val ret = JSObject()
        ret.put("elements", elements)
        call.resolve(ret)
    }
}
