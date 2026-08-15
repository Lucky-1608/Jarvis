package com.jarvis.app

import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.util.Log

class AppLauncher {

    companion object {
        fun openApp(context: Context, appName: String): Boolean {
            val pm = context.packageManager
            
            // First, check if the appName provided is already a package name
            var launchIntent = pm.getLaunchIntentForPackage(appName)
            if (launchIntent != null) {
                return launch(context, launchIntent)
            }

            // Otherwise, try to resolve common app names
            val resolvedPackage = resolvePackageName(appName)
            if (resolvedPackage != null) {
                launchIntent = pm.getLaunchIntentForPackage(resolvedPackage)
                if (launchIntent != null) {
                    return launch(context, launchIntent)
                }
            }

            // Fallback: search through all installed apps
            val packages = pm.getInstalledApplications(PackageManager.GET_META_DATA)
            for (packageInfo in packages) {
                val label = pm.getApplicationLabel(packageInfo).toString()
                if (label.equals(appName, ignoreCase = true) || label.contains(appName, ignoreCase = true)) {
                    launchIntent = pm.getLaunchIntentForPackage(packageInfo.packageName)
                    if (launchIntent != null) {
                        return launch(context, launchIntent)
                    }
                }
            }

            Log.e("AppLauncher", "Could not find app: $appName")
            return false
        }

        private fun launch(context: Context, intent: Intent): Boolean {
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            intent.addFlags(Intent.FLAG_ACTIVITY_RESET_TASK_IF_NEEDED)
            // Using FLAG_ACTIVITY_NEW_TASK is crucial for launching from background/service
            try {
                context.startActivity(intent)
                Log.d("AppLauncher", "Successfully launched app")
                return true
            } catch (e: Exception) {
                Log.e("AppLauncher", "Failed to launch app: ${e.message}")
                return false
            }
        }

        private fun resolvePackageName(appName: String): String? {
            return when (appName.lowercase()) {
                "spotify" -> "com.spotify.music"
                "youtube" -> "com.google.android.youtube"
                "youtube music", "yt music" -> "com.google.android.apps.youtube.music"
                "chrome", "google chrome" -> "com.android.chrome"
                "brave" -> "com.brave.browser"
                "whatsapp" -> "com.whatsapp"
                "gmail" -> "com.google.android.gm"
                "maps", "google maps" -> "com.google.android.apps.maps"
                else -> null
            }
        }
    }
}
