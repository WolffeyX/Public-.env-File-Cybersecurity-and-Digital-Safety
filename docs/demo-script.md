# Semak Dulu: Demo Script (3 minutes)

Scenes: S1 (bank + personal QR) → S5 (relative) → S9 (already paid) → S8 (escalation payoff).
S8 is the 180-second timer, so S1 is sent first and S8 plays out at the end.

## Phones and people

| Phone | Role | Who holds it |
|---|---|---|
| Phone 1 | **Mak** (parent) | Owner A |
| Phone 2 | **Anak** (primary contact) | Owner B |
| Phone 3 | **Adik** (second contact) | Owner C (also narrates) |

Before going on stage:
- All three phones messaged the bot in the last 24 hours (WhatsApp window, CO-5).
- Setup is done: Anak and Mak linked, Adik added with TAMBAH. Mak already did the practice check.
- QR images saved in Mak's gallery: `personal` (static personal DuitNow) and `business`.
- Phone 2 and Phone 3 are screen-mirrored or held up so the judges can see them.
- Backup video is ready (NFR-RO-02).

## Timeline

| Time | Scene | What happens | Narration (BM) |
|---|---|---|---|
| 0:00 | Problem | Slides only | "Penipu telefon Mak, mengaku pegawai bank, dan hantar kod QR. Mak percaya, sebab dia bukan orang asing pada Mak." |
| 0:20 | **S1** | Phone 1: forward the personal QR to Semak Dulu. The question appears with 3 buttons. Tap **Bank/Polis/Mahkamah**. Result: 🛑 JANGAN BAYAR. | "Mak cuma forward gambar tu dan tekan satu butang. Bot tak cakap 'selamat', dia cakap 'jangan bayar'." |
| 0:50 | S1 alert | Phone 2 (Anak) buzzes: ⚠️ AMARAN with **Saya uruskan**. **Do not tap it yet.** | "Serentak, anak Mak dapat amaran. Pemasa 3 minit sudah mula." |
| 1:10 | **S5** | Phone 1: forward the same QR, tap **Saudara/Kawan/Kedai**. Result: 🟡 Tunggu dulu, with the payee name and "tanya kod rahsia keluarga". No alert on Phone 2. | "Kalau Mak kata saudara yang minta, bot tak tuduh. Dia minta Mak telefon semula guna nombor yang Mak dah simpan." |
| 1:40 | **S9** | Phone 1: tap **Saya sudah bayar**. Mak gets the 4 steps (bank, 997, 999, police report). Phone 2 gets the urgent PAID alert. | "Kalau Mak dah terbayar, bot terus beritahu apa nak buat, ikut urutan. Anak dapat amaran segera." |
| 2:10 | Trust | Slide: never "safe", no AI deciding, image never stored, reports never cause a STOP. | "Keputusan ikut peraturan tetap, bukan AI. Gambar QR tak disimpan." |
| 3:00 | **S8** | The S1 timer ends. Phone 3 (Adik) buzzes with the same alert. Adik taps **Saya uruskan**. Phone 2 receives "ahli keluarga lain sedang menguruskan". | "Anak tak jawab dalam 3 minit, jadi ahli keluarga kedua dimaklumkan. Bila seorang tekan, yang lain tahu." |
| 3:20 | Close | Slide: roadmap and the ask. | |

If the S8 payoff comes too late, put it first: send S1 *before* the pitch starts, and the buzz lands at about 3 minutes in.

## If something fails

| Problem | What to do |
|---|---|
| WhatsApp is not delivering | Switch to Telegram (NFR-RO-03). Same flow, same messages. Owner B confirms the bot answers "Daftar" on Telegram first. |
| Both channels fail | Play the backup video (S1, S2, S5, S8, S9), or run `python scripts\chat_sim.py` on the laptop. |
| A button says "semakan ini sudah tamat" | The check is older than 10 minutes. Forward the QR again. |
| The alert does not reach Phone 2 | Message the bot from that phone to reopen the 24-hour window, then repeat the scene. |
| The QR will not read | Use the `noqr` fallback story: with **Bank/Polis/Mahkamah** the bot still says STOP (S2). Say so out loud. |

## Never say on stage
- "Selamat" or "safe" about any QR. The bot never says it.
- "Penipu" about a named person or account.