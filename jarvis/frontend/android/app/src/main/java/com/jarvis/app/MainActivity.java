package com.jarvis.app;

import android.Manifest;
import android.app.AlertDialog;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.PowerManager;
import android.provider.Settings;
import android.util.Log;
import androidx.annotation.NonNull;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;
import android.accessibilityservice.AccessibilityServiceInfo;
import android.view.accessibility.AccessibilityManager;
import com.getcapacitor.BridgeActivity;
import java.util.ArrayList;
import java.util.List;

public class MainActivity extends BridgeActivity {

    private static final String TAG = "JarvisMainActivity";
    private static final int RC_STANDARD_PERMISSIONS = 101;
    public static MainActivity instance = null;

    @Override
    public void onCreate(Bundle savedInstanceState) {
        instance = this;
        registerPlugin(DeviceHandsPlugin.class);
        super.onCreate(savedInstanceState);

        // Initiate permissions setup flow
        requestAppPermissionsFlow();

        // Start Foreground Service
        startJarvisService();
    }

    @Override
    public void onDestroy() {
        super.onDestroy();
        if (instance == this) {
            instance = null;
        }
    }

    /**
     * Handle physical/gesture Back button so user can exit/minimize the app cleanly.
     * If the webview has internal navigation history, go back;
     * otherwise gracefully minimize to background (home screen).
     */
    @Override
    public void onBackPressed() {
        if (getBridge() != null && getBridge().getWebView() != null && getBridge().getWebView().canGoBack()) {
            getBridge().getWebView().goBack();
        } else {
            moveTaskToBack(true);
        }
    }

    @Override
    public void onResume() {
        super.onResume();
        // Ensure background service is running when returning from Settings
        startJarvisService();
    }

    private void startJarvisService() {
        try {
            Intent serviceIntent = new Intent(this, JarvisBackgroundService.class);
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                ContextCompat.startForegroundService(this, serviceIntent);
            } else {
                startService(serviceIntent);
            }
        } catch (Exception e) {
            Log.e(TAG, "Error starting JarvisBackgroundService", e);
        }
    }

    /**
     * 1. Requests standard runtime permissions (Microphone, Notifications) via native OS popups.
     * 2. Proceeds to battery optimization and special permissions.
     */
    private void requestAppPermissionsFlow() {
        List<String> neededPermissions = new ArrayList<>();

        // Audio recording for wake word and voice commands
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            neededPermissions.add(Manifest.permission.RECORD_AUDIO);
        }

        // Notification permission for Android 13+ (API 33+)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
                neededPermissions.add(Manifest.permission.POST_NOTIFICATIONS);
            }
        }

        if (!neededPermissions.isEmpty()) {
            ActivityCompat.requestPermissions(
                this,
                neededPermissions.toArray(new String[0]),
                RC_STANDARD_PERMISSIONS
            );
        } else {
            // Standard permissions already granted, proceed with background & accessibility prompts
            checkBackgroundAndSpecialPermissions();
        }
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, @NonNull String[] permissions, @NonNull int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == RC_STANDARD_PERMISSIONS) {
            // Once user answers the standard dialogs, prompt for background execution & accessibility
            checkBackgroundAndSpecialPermissions();
            startJarvisService();
        }
    }

    /**
     * Prompts system dialogs and direct settings redirects for background & accessibility.
     */
    private void checkBackgroundAndSpecialPermissions() {
        requestIgnoreBatteryOptimization();
    }

    /**
     * Pops up the native Android system dialog:
     * "Let app always run in background? [Cancel] [Allow]"
     */
    private void requestIgnoreBatteryOptimization() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            PowerManager pm = (PowerManager) getSystemService(Context.POWER_SERVICE);
            if (pm != null && !pm.isIgnoringBatteryOptimizations(getPackageName())) {
                try {
                    Intent intent = new Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS);
                    intent.setData(Uri.parse("package:" + getPackageName()));
                    startActivity(intent);
                } catch (Exception e) {
                    try {
                        Intent intent = new Intent(Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS);
                        startActivity(intent);
                    } catch (Exception ignored) {}
                }
            }
        }

        // Prompt for Accessibility service next
        promptAccessibilityPermission();
    }

    /**
     * Checks if JarvisAccessibilityService is enabled. If not, displays an explanatory popup
     * with a one-tap button that redirects directly to Accessibility Settings.
     */
    private void promptAccessibilityPermission() {
        if (!isAccessibilityServiceEnabled()) {
            new AlertDialog.Builder(this)
                .setTitle("Enable Assistant Controls")
                .setMessage("To allow Jarvis to tap screen elements, navigate apps, and execute commands hands-free, please enable 'Jarvis' in Accessibility Settings.")
                .setPositiveButton("Open Settings", (dialog, which) -> {
                    try {
                        Intent intent = new Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS);
                        startActivity(intent);
                    } catch (Exception e) {
                        Log.e(TAG, "Failed opening Accessibility Settings", e);
                    }
                })
                .setNegativeButton("Later", (dialog, which) -> {
                    dialog.dismiss();
                    promptNotificationAccess();
                })
                .show();
        } else {
            promptNotificationAccess();
        }
    }

    /**
     * Checks if Notification Listener is enabled. If not, displays a popup redirecting
     * directly to Notification Listener Settings.
     */
    private void promptNotificationAccess() {
        if (!isNotificationListenerEnabled()) {
            new AlertDialog.Builder(this)
                .setTitle("Notification Announcements")
                .setMessage("To allow Jarvis to read and announce incoming WhatsApp and Telegram messages, enable Notification Access for Jarvis.")
                .setPositiveButton("Open Settings", (dialog, which) -> {
                    try {
                        Intent intent = new Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS);
                        startActivity(intent);
                    } catch (Exception e) {
                        Log.e(TAG, "Failed opening Notification Settings", e);
                    }
                })
                .setNegativeButton("Later", (dialog, which) -> dialog.dismiss())
                .show();
        }
    }

    private boolean isAccessibilityServiceEnabled() {
        if (JarvisAccessibilityService.Companion.getInstance() != null) {
            return true;
        }

        // 1. Official Android AccessibilityManager API
        try {
            AccessibilityManager am = (AccessibilityManager) getSystemService(Context.ACCESSIBILITY_SERVICE);
            if (am != null) {
                List<AccessibilityServiceInfo> enabledServices =
                    am.getEnabledAccessibilityServiceList(AccessibilityServiceInfo.FEEDBACK_ALL_MASK);
                if (enabledServices != null) {
                    for (AccessibilityServiceInfo service : enabledServices) {
                        if (service.getId() != null && service.getId().toLowerCase().contains(getPackageName().toLowerCase())) {
                            return true;
                        }
                    }
                }
            }
        } catch (Exception e) {
            Log.w(TAG, "Error checking AccessibilityManager status", e);
        }

        // 2. Direct Settings.Secure check without strict int gating
        try {
            String settingValue = Settings.Secure.getString(
                getContentResolver(),
                Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES
            );
            if (settingValue != null && settingValue.toLowerCase().contains(getPackageName().toLowerCase())) {
                return true;
            }
        } catch (Exception e) {
            Log.w(TAG, "Error checking Settings.Secure accessibility status", e);
        }

        return false;
    }

    private boolean isNotificationListenerEnabled() {
        try {
            String flat = Settings.Secure.getString(getContentResolver(), "enabled_notification_listeners");
            return flat != null && flat.contains(getPackageName());
        } catch (Exception e) {
            Log.w(TAG, "Error checking notification listener status", e);
            return false;
        }
    }
}
