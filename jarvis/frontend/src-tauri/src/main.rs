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
        let lower = app_name.trim().to_lowercase();
        let target_arg = url.unwrap_or_default();
        let has_arg = !target_arg.trim().is_empty();

        let full_cmd = match lower.as_str() {
            "terminal" | "windows terminal" | "wt" | "wt.exe" => {
                if has_arg {
                    format!("wt.exe cmd.exe /K \"{}\"", target_arg)
                } else {
                    "start wt.exe".to_string()
                }
            }
            "cmd" | "cmd.exe" | "command prompt" => {
                if has_arg {
                    format!("start cmd.exe /K \"{}\"", target_arg)
                } else {
                    "start cmd.exe".to_string()
                }
            }
            "powershell" | "powershell.exe" => {
                if has_arg {
                    format!("start powershell.exe -NoExit -Command \"{}\"", target_arg)
                } else {
                    "start powershell.exe".to_string()
                }
            }
            "code" | "vscode" | "vs code" => {
                if has_arg {
                    format!("start code \"{}\"", target_arg)
                } else {
                    "start code".to_string()
                }
            }
            _ => {
                if has_arg {
                    format!("start \"\" \"{}\" \"{}\"", app_name, target_arg)
                } else {
                    format!("start \"\" \"{}\"", app_name)
                }
            }
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
    #[cfg(target_os = "windows")]
    {
        use std::os::windows::process::CommandExt;

        let ps_script = r#"
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$b = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$bmp = New-Object System.Drawing.Bitmap $b.Width, $b.Height
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($b.Location, [System.Drawing.Point]::Empty, $b.Size)
$ms = New-Object System.IO.MemoryStream
$bmp.Save($ms, [System.Drawing.Imaging.ImageFormat]::Png)
$b64 = [Convert]::ToBase64String($ms.ToArray())
$ms.Dispose()
$g.Dispose()
$bmp.Dispose()
Write-Output "$($b.Width)|$($b.Height)|$b64"
"#;

        let output = Command::new("powershell")
            .args(["-NoProfile", "-NonInteractive", "-Command", ps_script])
            .creation_flags(0x08000000) // CREATE_NO_WINDOW
            .output();

        match output {
            Ok(out) => {
                if !out.status.success() {
                    let err = String::from_utf8_lossy(&out.stderr).to_string();
                    return Ok(json!({
                        "status": "error",
                        "error": format!("PowerShell screen capture failed: {}", err)
                    }));
                }

                let text = String::from_utf8_lossy(&out.stdout).trim().to_string();
                let parts: Vec<&str> = text.splitn(3, '|').collect();
                if parts.len() == 3 {
                    let width: u32 = parts[0].trim().parse().unwrap_or(1920);
                    let height: u32 = parts[1].trim().parse().unwrap_or(1080);
                    let b64 = parts[2].trim().to_string();
                    Ok(json!({
                        "status": "success",
                        "image_base64": b64,
                        "width": width,
                        "height": height
                    }))
                } else if !text.is_empty() {
                    Ok(json!({
                        "status": "success",
                        "image_base64": text,
                        "width": 1920,
                        "height": 1080
                    }))
                } else {
                    Ok(json!({
                        "status": "error",
                        "error": "Empty screen capture received from PowerShell."
                    }))
                }
            }
            Err(e) => Ok(json!({
                "status": "error",
                "error": format!("Failed to spawn PowerShell: {}", e)
            })),
        }
    }

    #[cfg(target_os = "macos")]
    {
        let script = "screencapture -x -C /tmp/jarvis_capture.png && base64 -i /tmp/jarvis_capture.png && rm -f /tmp/jarvis_capture.png";
        let output = Command::new("sh").args(["-c", script]).output();

        match output {
            Ok(out) if out.status.success() => {
                let b64 = String::from_utf8_lossy(&out.stdout).trim().to_string();
                Ok(json!({
                    "status": "success",
                    "image_base64": b64,
                    "width": 1920,
                    "height": 1080
                }))
            }
            Ok(out) => {
                let err = String::from_utf8_lossy(&out.stderr).to_string();
                Ok(json!({
                    "status": "error",
                    "error": format!("screencapture failed: {}", err)
                }))
            }
            Err(e) => Ok(json!({
                "status": "error",
                "error": format!("Failed to execute screencapture: {}", e)
            })),
        }
    }

    #[cfg(all(not(target_os = "windows"), not(target_os = "macos")))]
    {
        let script = "import -window root /tmp/jarvis_capture.png && base64 -w 0 /tmp/jarvis_capture.png && rm -f /tmp/jarvis_capture.png";
        let output = Command::new("sh").args(["-c", script]).output();

        match output {
            Ok(out) if out.status.success() => {
                let b64 = String::from_utf8_lossy(&out.stdout).trim().to_string();
                Ok(json!({
                    "status": "success",
                    "image_base64": b64,
                    "width": 1920,
                    "height": 1080
                }))
            }
            _ => Ok(json!({
                "status": "error",
                "error": "Screen capture on Linux requires an active X11 display and 'import' (ImageMagick)."
            })),
        }
    }
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

#[tauri::command]
fn get_app_version(app: tauri::AppHandle) -> Result<serde_json::Value, String> {
    let version = app.package_info().version.to_string();
    Ok(json!({
        "status": "success",
        "version": version
    }))
}

#[tauri::command]
fn exit_app(app: tauri::AppHandle) -> Result<serde_json::Value, String> {
    app.exit(0);
    Ok(json!({ "status": "success" }))
}

#[tauri::command]
fn install_update_and_restart(app: tauri::AppHandle, download_url: String) -> Result<serde_json::Value, String> {
    #[cfg(target_os = "windows")]
    {
        let temp_dir = std::env::temp_dir();
        let target_installer = temp_dir.join("Jarvis-Setup-Update.exe");
        let target_path_str = target_installer.to_string_lossy().to_string();
        let clean_url = download_url.trim().to_string();

        let script = format!(
            "$wc = New-Object System.Net.WebClient; $wc.DownloadFile('{url}', '{dest}'); Start-Process -FilePath '{dest}'",
            url = clean_url,
            dest = target_path_str.replace('\\', "\\\\")
        );

        let _ = Command::new("powershell")
            .args(["-NoProfile", "-WindowStyle", "Hidden", "-Command", &script])
            .spawn();

        let app_clone = app.clone();
        std::thread::spawn(move || {
            std::thread::sleep(std::time::Duration::from_millis(1500));
            app_clone.exit(0);
        });

        Ok(json!({
            "status": "success",
            "message": "Update process initiated"
        }))
    }

    #[cfg(not(target_os = "windows"))]
    {
        let _ = open_app(download_url, None);
        Ok(json!({
            "status": "success",
            "message": "Update URL opened in browser"
        }))
    }
}

#[tauri::command]
fn sync_latest_frontend(app: tauri::AppHandle, target_url: Option<String>) -> Result<serde_json::Value, String> {
    if let Some(window) = app.get_webview_window("main") {
        let url_str = target_url.unwrap_or_else(|| {
            "https://jarvisos-gdhfgnc4gscqecav.centralindia-01.azurewebsites.net".to_string()
        });
        if let Ok(parsed) = tauri::Url::parse(&url_str) {
            let _ = window.navigate(parsed);
            let _ = window.show();
            let _ = window.set_focus();
            return Ok(json!({ "status": "success", "url": url_str }));
        }
    }
    Err("Failed to parse URL or find main window".to_string())
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
            show_window,
            get_app_version,
            exit_app,
            install_update_and_restart,
            sync_latest_frontend
        ])
        .setup(|app| {
            // System Tray Menu Setup
            let sync_item = MenuItem::with_id(app, "sync_frontend", "⚡ Sync Latest Frontend (Live)", true, None::<&str>)?;
            let open_item = MenuItem::with_id(app, "open", "Open Jarvis", true, None::<&str>)?;
            let hide_item = MenuItem::with_id(app, "hide", "Minimize to Tray", true, None::<&str>)?;
            let shortcut_item = MenuItem::with_id(app, "shortcut", "Shortcut: Ctrl+Shift+J", false, None::<&str>)?;
            let quit_item = MenuItem::with_id(app, "quit", "Quit Jarvis", true, None::<&str>)?;

            let tray_menu = Menu::with_items(
                app,
                &[
                    &sync_item,
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
                    "sync_frontend" => {
                        if let Some(window) = app.get_webview_window("main") {
                            let target = "https://jarvisos-gdhfgnc4gscqecav.centralindia-01.azurewebsites.net";
                            if let Ok(parsed) = tauri::Url::parse(target) {
                                let _ = window.navigate(parsed);
                                let _ = window.show();
                                let _ = window.set_focus();
                            }
                        }
                    }
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
