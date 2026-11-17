@echo off
setlocal
cd /d "%~dp0"
echo Building MinaChristmasDesktop.exe ...
python -m pip install --upgrade pip
if errorlevel 1 goto fail
python -m pip install -r requirements.txt pyinstaller
if errorlevel 1 goto fail
python -m PyInstaller --noconfirm --clean --onefile --windowed --collect-all pystray --collect-all PIL --collect-all imageio_ffmpeg --icon "assets\app_icon.ico" --add-data "assets;assets" --name MinaChristmasDesktop MinaChristmasDesktop.py
if errorlevel 1 goto fail
echo.
echo Build complete: %~dp0dist\MinaChristmasDesktop.exe
echo This is a Windows x64 executable.
pause
exit /b 0
:fail
echo.
echo BUILD FAILED - see the messages above.
pause
exit /b 1
