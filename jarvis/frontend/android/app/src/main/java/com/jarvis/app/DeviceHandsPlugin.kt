package com.jarvis.app

import com.getcapacitor.JSObject
import com.getcapacitor.Plugin
import com.getcapacitor.PluginCall
import com.getcapacitor.PluginMethod
import com.getcapacitor.annotation.CapacitorPlugin

@CapacitorPlugin(name = "DeviceHands")
class DeviceHandsPlugin : Plugin() {

    @PluginMethod
    fun performAction(call: PluginCall) {
        val action = call.getString("action")
        val target = call.getString("target")

        if (action == "open_app" && target != null) {
            val success = AppLauncher.openApp(context, target)
            val ret = JSObject()
            ret.put("success", success)
            if (success) {
                call.resolve(ret)
            } else {
                call.reject("Failed to open app: $target")
            }
        } else {
            call.reject("Unknown action or missing target")
        }
    }
}
