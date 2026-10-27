// Prevents additional console window on Windows in release
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use serde_json::json;
use std::process::Command;
use tauri::{
    menu::{Menu, MenuItem},
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
    Manager, WindowEvent,
};
use tauri_plugin_notification::NotificationExt;

#[tauri::command]
fn run_command(command: String, cwd: Option<String>) -> Result<serde_json::Value, String> {
    #[cfg(target_os = "windows")]
    let mut cmd = Command::new("cmd");
    #[cfg(target_os = "windows")]
    cmd.args(["/C", &command]);

    #[cfg(not(target_os = "windows"))]
    let mut cmd = Command::new("sh");
    #[cfg(not(target_os = "windows"))]
    cmd.args(["-c", &command]);

    if let Some(dir) = cwd {
        if !dir.trim().is_empty() {
            cmd.current_dir(dir);
        }
    }

    match cmd.output() {
        Ok(output) => {
            let stdout = String::from_utf8_lossy(&output.stdout).to_string();
            let stderr = String::from_utf8_lossy(&output.stderr).to_string();
            Ok(json!({
                "status": "success",
                "output": {
                    "stdout": stdout,
                    "stderr": stderr
                }
            }))
        }
        Err(e) => Ok(json!({
            "status": "error",
            "error": e.to_string()
        })),
    }
}

#[tauri::command]
fn open_app(app_name: String, url: Option<String>) -> Result<serde_json::Value, String> {
    #[cfg(target_os = "windows")]
    {
        let full_cmd = if let Some(target_url) = url {
            format!("start \"\" \"{}\" \"{}\"", app_name, target_url)
        } else {
            format!("start \"\" \"{}\"", app_name)
        };
        let _ = Command::new("cmd").args(["/C", &full_cmd]).spawn();
        Ok(json!({ "status": "success" }))
    }

    #[cfg(target_os = "macos")]
    {
        let mut cmd = Command::new("open");
        cmd.args(["-a", &app_name]);
        if let Some(target_url) = url {
            cmd.arg(&target_url);
        }
        let _ = cmd.spawn();
        Ok(json!({ "status": "success" }))
    }

    #[cfg(all(not(target_os = "windows"), not(target_os = "macos")))]
    {
        let mut cmd = Command::new(&app_name);
        if let Some(target_url) = url {
            cmd.arg(&target_url);
        }
        let _ = cmd.spawn();
        Ok(json!({ "status": "success" }))
    }
}

#[tauri::command]
fn close_app(app_name: String) -> Result<serde_json::Value, String> {
    #[cfg(target_os = "windows")]
    {
        let exe = if app_name.to_lowercase().ends_with(".exe") {
            app_name
        } else {
            format!("{}.exe", app_name)
        };
        let _ = Command::new("taskkill").args(["/IM", &exe, "/F"]).output();
        Ok(json!({ "status": "success" }))
    }

    #[cfg(target_os = "macos")]
    {
        let _ = Command::new("killall").arg(&app_name).output();
        Ok(json!({ "status": "success" }))
    }

    #[cfg(all(not(target_os = "windows"), not(target_os = "macos")))]
    {
        let _ = Command::new("pkill").args(["-f", &app_name]).output();
        Ok(json!({ "status": "success" }))
    }
}

#[tauri::command]
fn show_notification(
    app: tauri::AppHandle,
    title: String,
    message: String,
) -> Result<serde_json::Value, String> {
    let _ = app
        .notification()
        .builder()
        .title(title)
        .body(message)
        .show();
    Ok(json!({ "status": "success" }))
}

#[tauri::command]
fn capture_screen() -> Result<serde_json::Value, String> {
    // Screen capture fallback on desktop
    Ok(json!({
        "status": "error",
        "error": "Screen capture via Tauri native is handled through OS display stream."
    }))
}

#[tauri::command]
fn show_window(app: tauri::AppHandle) -> Result<serde_json::Value, String> {
    if let Some(window) = app.get_webview_window("main") {
        let _ = window.show();
        let _ = window.unminimize();
        let _ = window.set_focus();
    }
    Ok(json!({ "status": "success" }))
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_notification::init())
        .plugin(tauri_plugin_single_instance::init(|app, _args, _cwd| {
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.show();
                let _ = window.set_focus();
            }
        }))
        .invoke_handler(tauri::generate_handler![
            run_command,
            open_app,
            close_app,
            show_notification,
            capture_screen,
            show_window
        ])
        .setup(|app| {
            // System Tray Menu Setup
            let open_item = MenuItem::with_id(app, "open", "Open Jarvis", true, None::<&str>)?;
            let hide_item = MenuItem::with_id(app, "hide", "Minimize to Tray", true, None::<&str>)?;
            let shortcut_item = MenuItem::with_id(app, "shortcut", "Shortcut: Ctrl+Shift+J", false, None::<&str>)?;
            let quit_item = MenuItem::with_id(app, "quit", "Quit Jarvis", true, None::<&str>)?;

            let tray_menu = Menu::with_items(
                app,
                &[
                    &open_item,
                    &hide_item,
                    &shortcut_item,
                    &quit_item,
                ],
            )?;

            let icon = app
                .default_window_icon()
                .cloned()
                .unwrap_or_else(|| tauri::include_image!("icons/icon.png"));

            let tray = TrayIconBuilder::new()
                .icon(icon)
                .menu(&tray_menu)
                .show_menu_on_left_click(false)
                .tooltip("Jarvis Companion OS")
                .on_menu_event(|app, event| match event.id.as_ref() {
                    "open" => {
                        if let Some(window) = app.get_webview_window("main") {
                            let _ = window.show();
                            let _ = window.set_focus();
                        }
                    }
                    "hide" => {
                        if let Some(window) = app.get_webview_window("main") {
                            let _ = window.hide();
                        }
                    }
                    "quit" => {
                        app.exit(0);
                    }
                    _ => {}
                })
                .on_tray_icon_event(|tray, event| {
                    if let TrayIconEvent::Click {
                        button: MouseButton::Left,
                        button_state: MouseButtonState::Up,
                        ..
                    } = event
                    {
                        let app = tray.app_handle();
                        if let Some(window) = app.get_webview_window("main") {
                            if window.is_visible().unwrap_or(false) {
                                let _ = window.hide();
                            } else {
                                let _ = window.show();
                                let _ = window.set_focus();
                            }
                        }
                    }
                })
                .build(app)?;

            let _ = tray;

            // Global shortcut plugin (Ctrl+Shift+J)
            let app_handle = app.handle().clone();
            let _ = app.handle().plugin(
                tauri_plugin_global_shortcut::Builder::new()
                    .with_handler(move |_app, shortcut, event| {
                        if event.state() == tauri_plugin_global_shortcut::ShortcutState::Pressed {
                            if shortcut.to_string().to_lowercase().contains("shift")
                                && shortcut.to_string().to_lowercase().contains("j")
                            {
                                if let Some(window) = app_handle.get_webview_window("main") {
                                    if window.is_visible().unwrap_or(false) {
                                        let _ = window.hide();
                                    } else {
                                        let _ = window.show();
                                        let _ = window.set_focus();
                                    }
                                }
                            }
                        }
                    })
                    .build(),
            );

            Ok(())
        })
        .on_window_event(|window, event| {
            // Minimize to system tray on window close
            if let WindowEvent::CloseRequested { api, .. } = event {
                api.prevent_close();
                let _ = window.hide();
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running Jarvis Tauri application");
}
