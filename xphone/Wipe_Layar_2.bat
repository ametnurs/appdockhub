@echo off
title XPhone - Reset Pabrik Layar 2
echo ====================================================
echo        MEMBERSIHKAN TOTAL DATA LAYAR #2
echo ====================================================
echo.
echo Menghentikan proses emulator jika masih berjalan...
taskkill /F /FI "WINDOWTITLE eq Android Emulator - XPhone_2:5556" >nul 2>&1
timeout /t 2 >nul
echo Menghapus file database akun dan sesi login lama...
del /f /q "%USERPROFILE%\.android\avd\XPhone_2.avd\userdata-qemu.img*" >nul 2>&1
del /f /q "%USERPROFILE%\.android\avd\XPhone_2.avd\cache.img*" >nul 2>&1
rd /s /q "%USERPROFILE%\.android\avd\XPhone_2.avd\snapshots" >nul 2>&1
echo.
echo Menjalankan proses format wipe-data resmi QEMU...
start "" "%USERPROFILE%\AppData\Local\Android\Sdk\emulator\emulator.exe" -avd XPhone_2 -port 5556 -gpu swiftshader -feature -Vulkan -feature -GLDirectMem -no-snapshot-load -no-boot-anim -camera-back none -camera-front none -cores 2 -memory 1536 -wipe-data
echo.
echo [SUKSES] Layar #2 berhasil di-reset total ke setelan pabrik!
echo Seluruh akun Gmail lama telah dihapus dan layar siap digunakan.
echo.
pause
