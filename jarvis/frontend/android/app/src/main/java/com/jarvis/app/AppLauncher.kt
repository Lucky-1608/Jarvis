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
