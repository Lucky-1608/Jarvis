package com.jarvis.app

import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.net.Uri
import android.os.BatteryManager
import android.os.Build
import android.os.PowerManager
import android.provider.Settings
import androidx.core.app.NotificationCompat
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
    fun closeApp(call: PluginCall) {
        val name = call.getString("name") ?: call.getString("target") ?: call.getString("app_name") ?: "current"
        val success = AppLauncher.closeApp(context, name)
        val ret = JSObject()
        ret.put("success", success)
        if (success) {
            ret.put("message", "Successfully closed $name")
            call.resolve(ret)
        } else {
            ret.put("error", "Failed to close app: $name")
            call.reject("Failed to close app: $name")
        }
    }

    @PluginMethod
    fun minimizeApp(call: PluginCall) {
        MainActivity.instance?.runOnUiThread {
            MainActivity.instance?.moveTaskToBack(true)
        }
        val ret = JSObject().apply { put("success", true) }
        call.resolve(ret)
    }

    @PluginMethod
    fun performAction(call: PluginCall) {
        val action = call.getString("action") ?: ""
        val target = call.getString("target") ?: call.getString("name") ?: call.getString("app_name") ?: ""
        val text = call.getString("text") ?: ""

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
            "close_app", "close" -> {
                val success = AppLauncher.closeApp(context, target.ifBlank { "current" })
                val ret = JSObject()
                ret.put("success", success)
                if (success) {
                    ret.put("message", "Successfully closed app")
                    call.resolve(ret)
                } else {
                    call.reject("Failed to close app")
                }
            }
            "tap", "tapXY", "scroll", "type_text", "type", "back", "home", "recents", "notifications" -> {
                val x = call.getDouble("x", 0.0)?.toFloat() ?: 0f
                val y = call.getDouble("y", 0.0)?.toFloat() ?: 0f
                val success = JarvisAccessibilityService.instance?.performAction(action, target, x, y, text) ?: false
                val ret = JSObject()
                ret.put("success", success)
                if (success) {
                    call.resolve(ret)
                } else {
                    call.reject("Failed to perform accessibility action: $action")
                }
            }
            else -> {
                call.reject("Unknown action: $action")
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

    @PluginMethod
    fun sendSMS(call: PluginCall) {
        val number = call.getString("number") ?: ""
        val message = call.getString("message") ?: ""
        if (number.isBlank()) {
            call.reject("Missing destination number")
            return
        }
        try {
            val intent = Intent(Intent.ACTION_SENDTO).apply {
                data = Uri.parse("smsto:$number")
                putExtra("sms_body", message)
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            context.startActivity(intent)
            val ret = JSObject().apply {
                put("success", true)
                put("message", "SMS composer opened for $number")
            }
            call.resolve(ret)
        } catch (e: Exception) {
            call.reject("Failed to send SMS: ${e.message}")
        }
    }

    @PluginMethod
    fun makeCall(call: PluginCall) {
        val number = call.getString("number") ?: ""
        if (number.isBlank()) {
            call.reject("Missing phone number")
            return
        }
        try {
            val intent = Intent(Intent.ACTION_DIAL).apply {
                data = Uri.parse("tel:$number")
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            context.startActivity(intent)
            val ret = JSObject().apply {
                put("success", true)
                put("message", "Call initiated to $number")
            }
            call.resolve(ret)
        } catch (e: Exception) {
            call.reject("Failed to make call: ${e.message}")
        }
    }

    @PluginMethod
    fun getBattery(call: PluginCall) {
        try {
            val ifilter = IntentFilter(Intent.ACTION_BATTERY_CHANGED)
            val batteryStatus: Intent? = context.registerReceiver(null, ifilter)
            val level: Int = batteryStatus?.getIntExtra(BatteryManager.EXTRA_LEVEL, -1) ?: -1
            val scale: Int = batteryStatus?.getIntExtra(BatteryManager.EXTRA_SCALE, -1) ?: -1
            val batteryPct = if (level >= 0 && scale > 0) (level * 100 / scale) else 0
            val status: Int = batteryStatus?.getIntExtra(BatteryManager.EXTRA_STATUS, -1) ?: -1
            val isCharging = status == BatteryManager.BATTERY_STATUS_CHARGING || status == BatteryManager.BATTERY_STATUS_FULL

            val ret = JSObject().apply {
                put("level", batteryPct)
                put("charging", isCharging)
                put("output", "Battery level: $batteryPct%, Charging: $isCharging")
            }
            call.resolve(ret)
        } catch (e: Exception) {
            call.reject("Failed to read battery: ${e.message}")
        }
    }

    @PluginMethod
    fun showNotification(call: PluginCall) {
        val title = call.getString("title") ?: "Jarvis"
        val message = call.getString("message") ?: ""
        try {
            val nm = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            val channelId = "JarvisAlertsChannel"
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                val channel = NotificationChannel(channelId, "Jarvis Alerts", NotificationManager.IMPORTANCE_HIGH)
                nm.createNotificationChannel(channel)
            }
            val notif = NotificationCompat.Builder(context, channelId)
                .setContentTitle(title)
                .setContentText(message)
                .setSmallIcon(android.R.drawable.ic_dialog_info)
                .setAutoCancel(true)
                .build()
            nm.notify(System.currentTimeMillis().toInt(), notif)
            val ret = JSObject().apply { put("success", true) }
            call.resolve(ret)
        } catch (e: Exception) {
            call.reject("Failed to show notification: ${e.message}")
        }
    }

    @PluginMethod
    fun openAccessibilitySettings(call: PluginCall) {
        try {
            val intent = Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS)
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            context.startActivity(intent)
            call.resolve(JSObject().apply { put("success", true) })
        } catch (e: Exception) {
            call.reject("Failed to open accessibility settings: ${e.message}")
        }
    }

    @PluginMethod
    fun openNotificationSettings(call: PluginCall) {
        try {
            val intent = Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS)
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            context.startActivity(intent)
            call.resolve(JSObject().apply { put("success", true) })
        } catch (e: Exception) {
            call.reject("Failed to open notification settings: ${e.message}")
        }
    }

    @PluginMethod
    fun requestBatteryOptimization(call: PluginCall) {
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                val intent = Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS)
                intent.data = Uri.parse("package:${context.packageName}")
                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                context.startActivity(intent)
            }
            call.resolve(JSObject().apply { put("success", true) })
        } catch (e: Exception) {
            call.reject("Failed to request battery optimization: ${e.message}")
        }
    }

    @PluginMethod
    fun getPermissionsStatus(call: PluginCall) {
        val ret = JSObject()
        var isAccessibility = JarvisAccessibilityService.instance != null
        if (!isAccessibility) {
            try {
                val am = context.getSystemService(Context.ACCESSIBILITY_SERVICE) as? android.view.accessibility.AccessibilityManager
                val enabledServices = am?.getEnabledAccessibilityServiceList(android.accessibilityservice.AccessibilityServiceInfo.FEEDBACK_ALL_MASK)
                isAccessibility = enabledServices?.any { it.id?.contains(context.packageName, ignoreCase = true) == true } ?: false
            } catch (ignored: Exception) {}
        }
        if (!isAccessibility) {
            try {
                val settingValue = Settings.Secure.getString(context.contentResolver, Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES)
                isAccessibility = settingValue?.contains(context.packageName, ignoreCase = true) == true
            } catch (ignored: Exception) {}
        }

        val pm = context.getSystemService(Context.POWER_SERVICE) as? PowerManager
        val isBatteryIgnored = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            pm?.isIgnoringBatteryOptimizations(context.packageName) ?: false
        } else {
            true
        }

        val flat = Settings.Secure.getString(
            context.contentResolver,
            "enabled_notification_listeners"
        )
        val isNotificationEnabled = flat != null && flat.contains(context.packageName)

        ret.put("accessibilityEnabled", isAccessibility)
        ret.put("batteryOptimizationIgnored", isBatteryIgnored)
        ret.put("notificationAccessEnabled", isNotificationEnabled)
        call.resolve(ret)
    }
}
