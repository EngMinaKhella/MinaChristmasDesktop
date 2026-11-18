# Mina Christmas Desktop v1.1.0

Mina Christmas Desktop v1.1.0 is a Windows desktop winter overlay with falling snow, screen-edge frost, animated Santa fly-bys, a snow-clearing taskbar tractor, festive lights, optional music, and independent click / typing / delete sound effects.

The companion Chrome / Microsoft Edge extension adds gentle snow, page-edge frost, Santa fly-bys, a snowman hover animation, a seasonal cursor, and optional input sounds inside web pages.

**The app runs from the Windows notification area (system tray), beside the clock/network/volume icons.** Its transparent desktop overlay is click-through, so normal mouse interaction with your apps continues to work.

## v1.1.0 development status\n\nThis version is being prepared on the feature branch `feature/desktop-winter-experience-v1.1.0`. It has not been published as a permanent GitHub Release yet. Do not create the `v1.1.0` tag until the desktop and browser features have been tested on Windows.\n\n## Browser extension (Chrome and Edge)\n\nSee [`browser_extension/README_AR.md`](browser_extension/README_AR.md) for installation. Open `chrome://extensions` or `edge://extensions`, enable Developer mode, choose **Load unpacked**, and select the `browser_extension` folder. The overlay is pointer-transparent, hides for hidden tabs and full-screen content, and only runs on ordinary HTTP / HTTPS pages. It does not modify browser toolbar, tabs, or address bar.\n\n## Download for Windows

1. Open the repository's **Releases** page.
2. Download `MinaChristmasDesktop.exe` from the latest release.
3. Run the EXE. No Python installation is required for the packaged build.
4. The app icon appears in the notification area. Right-click it for **Open settings**, **Pause / Resume**, or **Exit**. Double-click/activate the default tray item to open settings.

Windows may place new tray icons inside the hidden-icons menu (`^`). To keep it visible, open **Settings → Personalization → Taskbar → Other system tray icons** and enable Mina Christmas Desktop.

## Build locally

Requirements: Windows 10/11, Python 3.10 or later.

```powershell
python -m pip install -r requirements.txt pyinstaller
python MinaChristmasDesktop.py
```

Or double-click `build.bat`. The standalone EXE is written to `dist/MinaChristmasDesktop.exe`.

## Build on GitHub

- Push the source to a GitHub repository.
- Open **Actions → Build Windows EXE → Run workflow** to create a downloadable build artifact.
- To publish a permanent download, create and push a version tag:

```bash
git tag v1.0.0
git push origin v1.0.0
```

The workflow builds the Windows x64 EXE, packages the browser extension ZIP, and attaches the EXE to the GitHub Release for a version tag. The development branch also runs the build and uploads both files as temporary workflow artifacts.

## Desktop, lock screen, and system tray

- The tray icon is the app's control point; the animated layer is shown on the signed-in Windows desktop, not as a lock-screen application.
- Windows lock/sign-in screens use a separate protected desktop. A normal desktop application cannot draw over that secure screen.
- Closing the settings window hides it; it does not exit the app. Use **Exit** from the tray menu to close the app.

## Background image and 4K displays

- Use **Choose image…** in settings to select a JPG, JPEG, PNG, or BMP image as your Windows wallpaper. The app keeps a copy in `%APPDATA%\MinaChristmasDesktop` so the selected file remains available.
- **Use built-in** selects the bundled background again.
- The overlay adapts to the current display dimensions and DPI. A 4K monitor is supported, but true crisp 4K wallpaper quality depends on using an original 3840×2160 image. The bundled image is lower resolution and may look soft when enlarged.

## Settings and local data

Settings are saved in `%APPDATA%\MinaChristmasDesktop\settings.json`. The app can optionally start with Windows. Wallpaper restoration is enabled by default; disable **Restore my wallpaper on exit** only if you intentionally want the selected wallpaper to remain.

## Assets and permissions

The `assets` folder includes the background image, music, and hover sound supplied with this project. Before making this repository public or distributing the EXE, make sure you own these assets or have permission to redistribute them. The Python source and included artwork/music do not automatically have an open-source license; add a license only if you have the rights and want to grant reuse.

## Platform note

`MinaChristmasDesktop.exe` is for Windows 10/11 PCs. It cannot run natively on Android or iPhone. A phone release would need a separate Android app (APK/AAB) and/or iOS app (IPA), with a different implementation.
