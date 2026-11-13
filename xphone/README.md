# 📱 XPhone - Emulator Android Sendiri (Super Ringan + GUI Manager)

Emulator Android **buatan sendiri** berbasis engine virtualisasi **Google QEMU (WHPX Hardware Acceleration)** dengan rendering **SwiftShader CPU Engine** (Bebas crash GPU Fermi / NVIDIA GT 610, anti blank screen).

100% Bebas software pihak ketiga (Bukan MuMu, Bukan BlueStacks, Bukan LDPlayer, Bukan Nox).

---

## 🌟 Fitur Utama XPhone

1. **Dedicated UI Launcher & Control Center (`Jalankan_UI_XPhone.bat`):**
   * Tampilan visual grid aplikasi ala smartphone/dashboard kontrol.
   * Tombol satu-klik untuk Start, Stop, dan Cold Boot.
   * Status koneksi real-time (Online, Booting, Offline) dan port ADB.
   * Satu-klik buka **Google Play Store**, **Cyber Orbit**, dan **Setelan Android**.
   * Integrasi **Pengaturan Proxy** langsung dari UI.
   * Pasang file APK mudah via dialog file.
   * Tombol navigasi virtual (Back, Home, Recent Apps).

2. **Lengkap dengan Google Apps (Official GApps & Google Play Store):**
   * Menggunakan image resmi Google: `android-31\google_apis_playstore\x86_64` (Android 12).
   * Google Play Services dan Google Play Store asli sudah terpasang.
   * Mendukung login akun Google dan unduh game/aplikasi langsung dari Play Store.

3. **Anti-Deteksi (Google Play Integrity & SafetyNet Pass):**
   * Device profile resmi Google Pixel 5 (`redfin`).
   * Lulus verifikasi Play Protect & Play Integrity (Certified Device).
   * Bebas watermark atau identifikasi emulator yang biasanya diblokir oleh game seperti *Cyber Orbit*.

4. **Bebas Masalah Layar Hitam (Anti-Blank Screen Fix):**
   * Dilengkapi engine software rendering Google SwiftShader yang memproses grafis lewat CPU Intel 28-core PC Anda, melewati batas GPU NVIDIA GT 610 yang tidak mendukung Vulkan/OpenGL modern.
   * Menonaktifkan partisi enkripsi bermasalah (`-feature -EncryptUserData`) dan snapshot korup.

5. **Dukungan Proxy Lengkap (HTTP & SOCKS5):**
   * Konfigurasi proxy transparan per-instance untuk bypass jaringan atau masking IP.

---

## 🚀 Cara Menjalankan

Buka folder **[C:\antigravity\xphone](file:///c:/antigravity/xphone)**:

1. **Gunakan Tampilan Grafis (UI Manager - Direkomendasikan):**
   * Klik ganda pada **[`Jalankan_UI_XPhone.bat`](file:///c:/antigravity/xphone/Jalankan_UI_XPhone.bat)**.
   * Klik tombol **▶ Nyalakan HP (Start)** di bagian atas.
   * Setelah status berubah menjadi **● ONLINE**, klik ikon **🛍️ Google Play Store** untuk membuka dan login akun Google.

2. **Jalankan Langsung Lewat Script Cepat:**
   * Klik ganda pada **[`Buka_Emulator_Custom.bat`](file:///c:/antigravity/xphone/Buka_Emulator_Custom.bat)**.
   * Layar HP Android akan langsung muncul di desktop Anda.

3. **Pasang Game / APK:**
   * Melalui UI: Klik card **📦 Pasang File APK** lalu pilih file APK.
   * Melalui Terminal: Klik ganda **[`Install_Cyber_Orbit.bat`](file:///c:/antigravity/xphone/Install_Cyber_Orbit.bat)**.

4. **Atur Proxy:**
   * Melalui UI: Masukkan Host & Port di panel kanan, lalu klik **Pasang Proxy ke HP**.
   * Melalui Terminal: Klik ganda **[`Atur_Proxy.bat`](file:///c:/antigravity/xphone/Atur_Proxy.bat)**.
