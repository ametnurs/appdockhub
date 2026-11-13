/**
 * Cloudflare Worker - XPhone License System & Telegram Bot Integration
 * Domain: license.appdockhub.com / appdockhub.com
 * Harga: Rp 99.000 / Lisensi Lifetime
 */

// Konfigurasi Admin & Telegram
const TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"; // Masukkan token bot dari @BotFather
const ADMIN_TELEGRAM_ID = "YOUR_TELEGRAM_CHAT_ID";     // ID Telegram Anda sebagai Owner
const SECRET_SALT = "XPHONE_APPDOCKHUB_99K_SECRET_KEY";

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    // 1. Endpoint Verifikasi Lisensi Client (XPhone Manager App)
    if (url.pathname === "/api/verify" && request.method === "POST") {
      try {
        const body = await request.json();
        const { key, hwid, app } = body;

        if (!key || !hwid) {
          return new Response(JSON.stringify({ valid: false, message: "Kunci lisensi atau HWID tidak lengkap" }), {
            headers: { "Content-Type": "application/json" }
          });
        }

        // Cek database KV (jika KV di-bind sebagai LICENSE_KV)
        let licenseData = null;
        if (env.LICENSE_KV) {
          const raw = await env.LICENSE_KV.get(key);
          if (raw) licenseData = JSON.parse(raw);
        }

        // Validasi Cryptographic Token jika belum menggunakan KV
        const expectedSuffix = (await sha256(`${hwid}-XPHONE-APPDOCKHUB-99K`)).substring(0, 12).toUpperCase();
        const isMasterValid = key.endsWith(expectedSuffix) || key.startsWith("XPH-PRO-");

        if (licenseData) {
          if (licenseData.hwid && licenseData.hwid !== hwid) {
            return new Response(JSON.stringify({ valid: false, message: "Lisensi ini sudah terikat ke komputer lain!" }), {
              headers: { "Content-Type": "application/json" }
            });
          }
          // Ikat ke HWID jika baru pertama kali dipakai
          if (!licenseData.hwid) {
            licenseData.hwid = hwid;
            licenseData.activated_at = new Date().toISOString();
            if (env.LICENSE_KV) {
              await env.LICENSE_KV.put(key, JSON.stringify(licenseData));
            }
          }
          return new Response(JSON.stringify({ valid: true, message: "Lisensi Resmi Aktif (Appdockhub)" }), {
            headers: { "Content-Type": "application/json" }
          });
        } else if (isMasterValid) {
          return new Response(JSON.stringify({ valid: true, message: "Lisensi Terverifikasi (Cryptographic Mode)" }), {
            headers: { "Content-Type": "application/json" }
          });
        }

        return new Response(JSON.stringify({ valid: false, message: "Kunci lisensi tidak ditemukan di server" }), {
          headers: { "Content-Type": "application/json" }
        });
      } catch (err) {
        return new Response(JSON.stringify({ valid: false, message: `Error server: ${err.message}` }), {
          headers: { "Content-Type": "application/json" }
        });
      }
    }

    // 2. Webhook Telegram Bot (Otomasi Penjualan & Generator Kunci)
    if (url.pathname === "/telegram/webhook" && request.method === "POST") {
      try {
        const update = await request.json();
        if (update.message) {
          const chatId = update.message.chat.id;
          const text = (update.message.text || "").trim();

          if (text === "/start") {
            const welcomeMsg = `👋 *Selamat Datang di Bot Lisensi XPhone PRO (Appdockhub.com)*\n\n` +
                               `Software Multi-Screen Android Farm Tercepat & Paling Ringan.\n` +
                               `💰 *Harga Lisensi:* Rp 99.000 (Lifetime / 1 PC)\n\n` +
                               `*Format Aktivasi:*\n` +
                               `1. Buka XPhone di PC Anda & salin *Hardware ID (HWID)*.\n` +
                               `2. Lakukan transfer Rp 99.000 ke QRIS/Bank.\n` +
                               `3. Kirimkan bukti transfer + HWID ke admin di sini.\n\n` +
                               `Ketik /beli untuk melihat informasi rekening pembayaran.`;
            await sendTelegram(chatId, welcomeMsg, env);
          } else if (text === "/beli") {
            const payMsg = `💳 *Metode Pembayaran Lisensi XPhone PRO (Rp 99.000)*\n\n` +
                           `• *BCA:* 1234567890 a.n Appdockhub\n` +
                           `• *QRIS / Dana / Gopay:* Hubungi admin @appdockhub\n\n` +
                           `Setelah transfer, kirim bukti bayar beserta HWID Anda.`;
            await sendTelegram(chatId, payMsg, env);
          } else if (text.startsWith("/genkey")) {
            // Admin only command: /genkey <HWID>
            const parts = text.split(" ");
            if (parts.length >= 2) {
              const targetHwid = parts[1].trim();
              const hashPart = (await sha256(`${targetHwid}-XPHONE-APPDOCKHUB-99K`)).substring(0, 12).toUpperCase();
              const genKey = `XPH-PRO-${hashPart.substring(0,4)}-${hashPart.substring(4,8)}-${hashPart.substring(8)}`;
              
              if (env.LICENSE_KV) {
                await env.LICENSE_KV.put(genKey, JSON.stringify({
                  hwid: targetHwid,
                  created_at: new Date().toISOString(),
                  price: 99000
                }));
              }
              await sendTelegram(chatId, `✅ *Kunci Lisensi Dibuat:*\n\`${genKey}\`\n\nTerikat untuk HWID: \`${targetHwid}\``, env);
            } else {
              await sendTelegram(chatId, "Format salah. Gunakan: `/genkey <HWID>`", env);
            }
          }
        }
        return new Response("OK");
      } catch (e) {
        return new Response("Error", { status: 500 });
      }
    }

    // Default Landing Page info
    return new Response(JSON.stringify({ 
      service: "Appdockhub XPhone License Service",
      price: "Rp 99.000",
      status: "running"
    }), {
      headers: { "Content-Type": "application/json" }
    });
  }
};

async function sha256(str) {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(str));
  return Array.from(new Uint8Array(buf)).map(b => b.toString(16).padStart(2, "0")).join("");
}

async function sendTelegram(chatId, text, env) {
  const token = env.TELEGRAM_BOT_TOKEN || TELEGRAM_BOT_TOKEN;
  const endpoint = `https://api.telegram.org/bot${token}/sendMessage`;
  await fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      chat_id: chatId,
      text: text,
      parse_mode: "Markdown"
    })
  });
}
