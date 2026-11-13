@echo off
title XPhone - Perbaiki Layar 1
echo ====================================================
echo        MEMULIHKAN SENTUHAN & LAYAR #1
echo ====================================================
echo.
set ADB="C:\Users\User\AppData\Local\Android\Sdk\platform-tools\adb.exe"
if not exist %ADB% set ADB="C:\adb\adb.exe"

echo Mereset resolusi dan touch digitizer layar...
%ADB% -s emulator-5554 shell wm size reset
%ADB% -s emulator-5554 shell wm density reset
echo Mengembalikan navigasi standar...
%ADB% -s emulator-5554 shell cmd overlay disable com.android.internal.systemui.navbar.gestural
%ADB% -s emulator-5554 shell settings put secure navigation_mode 0
%ADB% -s emulator-5554 shell input keyevent 3
%ADB% -s emulator-5554 shell monkey -p com.google.android.apps.nexuslauncher -c android.intent.category.LAUNCHER 1
echo.
echo [SUKSES] Layar #1 berhasil dipulihkan! Sentuhan normal kembali.
echo.
pause
