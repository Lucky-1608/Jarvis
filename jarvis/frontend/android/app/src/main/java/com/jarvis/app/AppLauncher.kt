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
            val cleanTarget = appName.lowercase().trim()

            // 1. Exact or substring match
            for (packageInfo in packages) {
                val label = pm.getApplicationLabel(packageInfo).toString()
                if (label.equals(cleanTarget, ignoreCase = true) || label.contains(cleanTarget, ignoreCase = true)) {
                    launchIntent = pm.getLaunchIntentForPackage(packageInfo.packageName)
                    if (launchIntent != null) {
                        return launch(context, launchIntent)
                    }
                }
            }

            // 2. Fuzzy match against app labels (handling typos like 'barve' -> 'Brave')
            var bestPackage: String? = null
            var bestDistance = Int.MAX_VALUE
            for (packageInfo in packages) {
                val label = pm.getApplicationLabel(packageInfo).toString().lowercase().trim()
                if (label.isEmpty()) continue
                val dist = levenshtein(cleanTarget, label)
                if (dist <= 2 && dist < bestDistance) {
                    bestDistance = dist
                    bestPackage = packageInfo.packageName
                }
            }

            if (bestPackage != null) {
                launchIntent = pm.getLaunchIntentForPackage(bestPackage)
                if (launchIntent != null) {
                    return launch(context, launchIntent)
                }
            }

            Log.e("AppLauncher", "Could not find app: $appName")
            return false
        }

        fun closeApp(context: Context, appName: String): Boolean {
            val clean = appName.lowercase().trim()

            // 1. If closing Jarvis itself or self
            if (clean in listOf("jarvis", "jarvis app", "this", "this app", "self", "companion")) {
                MainActivity.instance?.runOnUiThread {
                    MainActivity.instance?.moveTaskToBack(true)
                }
                return true
            }

            // 2. If closing the currently active/foreground app or general window
            if (clean in listOf("current", "active", "active app", "foreground", "window", "the app", "that app", "any", "this")) {
                val acc = JarvisAccessibilityService.instance
                if (acc != null) {
                    return acc.performGlobalAction(android.accessibilityservice.AccessibilityService.GLOBAL_ACTION_BACK) ||
                           acc.performGlobalAction(android.accessibilityservice.AccessibilityService.GLOBAL_ACTION_HOME)
                }
                MainActivity.instance?.runOnUiThread {
                    MainActivity.instance?.moveTaskToBack(true)
                }
                return true
            }

            // 3. Resolve target package name
            val resolvedPkg = resolvePackageName(appName)
            val targetPkg = if (resolvedPkg != null) {
                resolvedPkg
            } else {
                val pm = context.packageManager
                val packages = pm.getInstalledApplications(PackageManager.GET_META_DATA)
                packages.firstOrNull { pkg ->
                    val label = pm.getApplicationLabel(pkg).toString().lowercase().trim()
                    label == clean || label.contains(clean)
                }?.packageName
            }

            if (targetPkg != null) {
                try {
                    val am = context.getSystemService(Context.ACTIVITY_SERVICE) as? android.app.ActivityManager
                    am?.killBackgroundProcesses(targetPkg)
                } catch (e: Exception) {
                    Log.w("AppLauncher", "killBackgroundProcesses failed for $targetPkg", e)
                }

                // If currently visible, use accessibility service to return to home
                val acc = JarvisAccessibilityService.instance
                if (acc != null) {
                    acc.performGlobalAction(android.accessibilityservice.AccessibilityService.GLOBAL_ACTION_HOME)
                }
                return true
            }

            // Fallback: send HOME action to dismiss active window
            val acc = JarvisAccessibilityService.instance
            if (acc != null) {
                return acc.performGlobalAction(android.accessibilityservice.AccessibilityService.GLOBAL_ACTION_HOME)
            }

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
            val clean = appName.lowercase().trim()
            return when {
                clean in listOf("spotify", "spotfy") -> "com.spotify.music"
                clean in listOf("youtube", "yt", "you tube") -> "com.google.android.youtube"
                clean in listOf("youtube music", "yt music", "ytmusic") -> "com.google.android.apps.youtube.music"
                clean in listOf("chrome", "google chrome", "chorme") -> "com.android.chrome"
                clean in listOf("brave", "barve", "brave browser", "brave private web browser") -> "com.brave.browser"
                clean in listOf("whatsapp", "what's app", "wa") -> "com.whatsapp"
                clean in listOf("gmail", "google mail", "email", "mail") -> "com.google.android.gm"
                clean in listOf("maps", "google maps") -> "com.google.android.apps.maps"
                clean in listOf("settings", "setting") -> "com.android.settings"
                clean in listOf("camera") -> "com.google.android.GoogleCamera"
                clean in listOf("calculator", "calc") -> "com.google.android.calculator"
                clean in listOf("telegram") -> "org.telegram.messenger"
                clean in listOf("instagram", "insta") -> "com.instagram.android"
                clean in listOf("twitter", "x") -> "com.twitter.android"
                else -> null
            }
        }

        private fun levenshtein(s1: String, s2: String): Int {
            val dp = Array(s1.length + 1) { IntArray(s2.length + 1) }
            for (i in 0..s1.length) dp[i][0] = i
            for (j in 0..s2.length) dp[0][j] = j
            for (i in 1..s1.length) {
                for (j in 1..s2.length) {
                    val cost = if (s1[i - 1] == s2[j - 1]) 0 else 1
                    dp[i][j] = minOf(
                        dp[i - 1][j] + 1,
                        dp[i][j - 1] + 1,
                        dp[i - 1][j - 1] + cost
                    )
                }
            }
            return dp[s1.length][s2.length]
        }
    }
}
