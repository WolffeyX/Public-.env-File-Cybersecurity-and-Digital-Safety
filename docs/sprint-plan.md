# Pelan Sprint MVP Semak Dulu — Rabu 14 Okt 2026

Matlamat hari ini: aliran penuh berfungsi di telefon sebenar. Ibu bapa forward QR → bot tanya "Siapa minta bayar?" → keputusan STOP/VERIFY → anak dapat amaran → eskalasi → laporan.

## Jadual hari ini

| Masa | Fasa | Titik semak (semua mesti hadir 10 minit) |
|---|---|---|
| 14:45–15:15 | **Fasa 0** persediaan bersama | `pytest` lulus di 3 komputer |
| 15:15–17:00 | **Milestone 1** | **Sync 1 (17:00):** A: emv + classify lulus ujian · B: Meta "Verify and save" berjaya · C: persediaan & pautan berfungsi dalam `chat_sim` |
| 17:10–19:30 | **Milestone 2** | **Sync 2 (19:30) "Laluan Emas":** telefon sebenar → forward QR → tekan "Bank/Polis/Mahkamah" → 🛑 STOP (S1) |
| 19:30–20:00 | Rehat makan | |
| 20:00–22:00 | **Milestone 3** | **Sync 3 (22:00):** amaran anak, eskalasi, "sudah bayar", laporan (S1–S14 dalam `chat_sim`) |
| 22:00–23:30 | **Milestone 4** integrasi & ujian akhir | `git tag demo-0` · senarai pepijat untuk esok |

**Keutamaan jika masa tidak cukup:** P1 = laluan emas (S1, S2, S3, S5). P2 = amaran, eskalasi, sudah bayar, peringatan (S7–S9, S13). P3 = laporan, Telegram, ahli kedua (S11, S12, FR-03). Apa-apa yang tidak siap malam ini disambung esok, dan kamu masih 5 hari lebih awal daripada pembekuan ciri 19 Okt.

## Fasa 0: Persediaan bersama (30 minit)

Repo permulaan sudah ada struktur Seksyen 13.2, fail kontrak, stub setiap modul dan 110 ujian yang lulus. Kamu tidak perlu menulis fail antara muka dari kosong.

| # | Siapa | Langkah | Selesai bila |
|---|---|---|---|
| 0.1 | B | Cipta repo GitHub peribadi `semak-dulu`. Unzip repo permulaan, kemudian `git init`, `git add .`, `git commit -m "Fasa 0: repo permulaan"`, `git branch -M main`, `git remote add origin <url>`, `git push -u origin main`. Jemput A dan C sebagai collaborator. | A dan C boleh `git clone` |
| 0.2 | Semua | Pasang Python 3.12 dan Git jika belum ada. Ikut README "Fasa 0 setup": clone, venv, `pip install -r requirements-dev.txt`, `pytest`. | `110 passed` di setiap komputer |
| 0.3 | Semua | Baca `src/core/types.py` bersama-sama (10 minit). Ini kontrak: `InboundEvent`, `Button`, `Outbound`, `Task`, `DecodeResult`, `Verdict`, `Channel`, `Store`, `Deps`, dan `handle_event`. Setuju: tiada perubahan tanpa beritahu dalam group. | Semua faham siapa menghasilkan dan siapa menggunakan setiap jenis |
| 0.4 | Semua | Cuba `python scripts/chat_sim.py`, taip `@anak Daftar`, kemudian `quit`. | Simulator berjalan (mesej "not built yet" adalah normal) |
| 0.5 | B (selari) | Mula persediaan akaun (lihat Kad B, M0): Meta developer, AWS CLI, SAM CLI. **Tiada Docker.** | Boleh log masuk Meta dan `aws sts get-caller-identity` berjaya |
| 0.6 | Semua | `git tag fasa-0 && git push --tags` (B sahaja). | Tag wujud |

Peraturan Git untuk pemula: setiap orang hanya ubah fail dalam kad sendiri. Sebelum push: `git pull --rebase`, kemudian `pytest`, kemudian `git push`. Commit setiap 30–60 minit.

## Kad tugasan

Salin kad kamu ke dalam sembang Claude kamu sendiri, bersama kandungan `src/core/types.py` dan fail stub yang sedang kamu kerjakan. Minta Claude bina **satu fungsi pada satu masa, bersama ujiannya**.

### Kad Owner A — Core Engine & Ujian

```text
KAD TUGASAN: OWNER A — CORE ENGINE & UJIAN (Semak Dulu, Rabu 14 Okt)

KONTEKS
- Semak Dulu: bot WhatsApp. Ibu bapa forward gambar QR, jawab "Siapa minta bayar?",
  dapat keputusan STOP atau VERIFY. TIADA keputusan "selamat" (Level hanya STOP/VERIFY).
- Repo: semak-dulu. Python 3.12. Import gaya: `from core.types import ...` (src/ ialah root).
- Kontrak: src/core/types.py (DecodeResult, Verdict, Claim, Level, QrKind). Jangan ubah
  tanpa beritahu B dan C.
- Rujukan: docs/SDD.md 3.4, 3.5, 5.2, 5.3, 11 · docs/SRS.md 2.2.2, 2.2.3.
- core/ TIDAK boleh memanggil rangkaian atau menulis ke cakera.

PUSTAKA: zxing-cpp, Pillow (sudah dalam requirements). Ujian: pytest, segno (jana gambar QR).
TIADA OpenCV/numpy (supaya Lambda tidak perlu Docker). zxing-cpp sudah diuji: membaca
tangkapan skrin JPEG 3-4 px/modul, putaran 12°, kontras rendah.

PENGGUNA KERJA KAMU
- Owner C memanggil verdict.decide() dan verdict.evidence_message_id().
- Worker (Owner B) memanggil classify.decode_and_classify(image_bytes, pepper).

────────────────────────────────────────────────────────
MILESTONE 1 (15:15–17:00): emv.py + fixtures
  1. emv.parse_tlv(payload) -> (list[Field], error|None)
     Pindah dari Colab notebook. Jangan raise; pulangkan error.
  2. emv.compute_crc(data) -> "XXXX"   CRC-16/CCITT-FALSE, poly 0x1021, init 0xFFFF
  3. emv.validate_crc(payload) -> True/False/None
  4. emv.parse_nested(value) -> {sub_tag: value}   untuk tag 26 dan 62
  5. tests/fixtures/payloads.py: 6 payload SINTETIK berdasarkan struktur sampel kamu
     (3 peribadi statik, 1 perniagaan statik, 1 perniagaan dinamik, 1 kod Setel 16 aksara).
     Ganti SEMUA nama dan digit akaun dengan nilai palsu, kemudian kira semula CRC
     dengan compute_crc(). JANGAN commit payload sebenar.
  6. tests/test_emv.py: sah, terpotong, panjang salah, tag bukan digit, nested,
     CRC lulus/gagal, payload tanpa CRC -> None.
  SELESAI BILA: pytest tests/test_emv.py lulus. Push. Lapor di Sync 1.

MILESTONE 2 (17:10–19:30): classify.py + decode.py + verdict.py  ← LALUAN EMAS
  7. classify.classify(payload, pepper) -> DecodeResult  (ikut docstring)
     - Tag 00 = "01" atau "02" (sampel kamu "02"), TLV lulus, tag 26 sub 00 == DUITNOW_ID
       -> PAYMENT_DUITNOW
     - tag 01: "11"=static, "12"=dynamic (notebook asal TERBALIK, sudah dibetulkan)
     - is_personal: tag 52 "0000" -> True, 4 digit lain -> False, tiada -> None
     - report_key: statik sahaja, make_report_key(pepper, network_id, sub01, sub02)
     - JANGAN guna tag 26 sub 03 atau tag 62
  8. tests/test_classify.py: setiap fixture dapat kind, is_personal, static_dynamic,
     report_key yang betul. Dinamik -> report_key None. URL -> QrKind.URL.
  9. decode.decode_qr(image_bytes) -> str|None   (ikut docstring: exif_transpose, "L",
     kecilkan <=2000 px, zxingcpp.read_barcodes, cuba semula besar x2 + autocontrast)
     > 5 MB atau bukan gambar -> raise UnreadableImage
  10. classify.decode_and_classify(image_bytes, pepper) -> DecodeResult
      UnreadableImage -> kind UNREADABLE. Tiada QR -> NO_QR.
  11. tests/test_decode.py: jana QR dengan segno daripada fixture, simpan ke BytesIO
      (bukan cakera), uji: jelas, JPEG q40 kecil, diputar, gambar kosong -> None,
      bait rawak -> UnreadableImage.
  12. verdict.decide(claim, decode) -> Verdict   peraturan V-1..V-5 (SRS 2.2.3)
      verdict.evidence_message_id(n): 0 -> "ev.none", 1-2 -> "ev.few", >=3 -> "ev.many"
  13. tests/test_verdict.py: SETIAP baris jadual V-1..V-5, termasuk OFFICIAL + decode None,
      COURIER + is_personal None (-> VERIFY V-4), notify_child == (level == STOP).
  SELESAI BILA: semua ujian lulus; beritahu B dan C "decode + verdict sudah di main".

MILESTONE 3 (20:00–22:00): ujian e2e aliran (tests/test_flows.py)
  14. Guna tests/fakes.py: Clock, make_deps(), ev(), InMemoryStore, PERSONAL, BUSINESS...
      Dalam make_deps, media_ref "personal"/"business"/"dynamic"/"noqr"/"url" memilih
      DecodeResult palsu, jadi tidak perlu gambar sebenar.
  15. Tulis satu ujian bagi setiap senario yang sudah dibina oleh C:
      S1 bank+peribadi -> STOP + anak dapat amaran
      S2 bank+gambar kabur(noqr) -> STOP + amaran varian "tidak dapat dibaca"
      S3 kurier+peribadi -> STOP     S4 kurier+perniagaan -> VERIFY + nama
      S5 saudara+peribadi -> VERIFY + nama + "kod rahsia"
      S6 url -> mesej e.url, pautan tidak dibuka
      S7 tiada tekan -> Task reminder 120 s, kemudian close_check 600 s
      S8 anak tidak tekan "Saya uruskan" -> clock.advance(180) -> ahli kedua dapat amaran
      S9 "Saya sudah bayar" -> langkah bank/997/999/polis + amaran PAID
      S10 msg_id sama dua kali -> hanya satu balasan
      S11 3 pelapor berbeza -> ev.many, level tidak berubah
      S12 lapor QR dinamik -> r.not_reportable
      S13 tekan butang selepas 10 minit -> q.expired
      S14 BERHENTI + sahkan -> profil dan pautan dipadam
  16. Tambah ke tests/test_messages.py: GABUNGAN mesej keputusan sebenar (keputusan + jumlah
      + nota + bukti + "sudah maklumkan anak") <= 450 aksara dan <= 8 baris (NFR-UI-03).

MILESTONE 4 (22:00–23:30): integrasi & ujian akhir
  17. Set imej ujian NFR-PF-05: 10 tangkapan skrin QR jelas + 10 foto skrin telefon.
      Simpan dalam tests/fixtures/real/ (DI-IGNORE oleh git, jangan commit).
      Skrip kecil: berapa yang dibaca dengan betul? Sasaran >= 9/10 dan >= 6/10.
  18. Bantu B uji di telefon sebenar: S1, S2, S3, S5 dengan QR sebenar kamu.
  19. Senarai pepijat untuk esok.

SYARAT LULUS (SRS) YANG KAMU SAHKAN
  FR-06 klasifikasi · FR-07 medan QR, tiada tekaan · FR-09 STOP tepat 2 kes, tanpa laporan
  FR-10 tiada SAFE + imbasan perkataan · FR-12 kes gagal (sisi decode) · DR-01 tiada gambar
  disimpan · DR-03 kunci laporan HMAC · NFR-PF-05 kadar bacaan · NFR-MT-05 setiap baris
  jadual + setiap kes gagal diuji · NFR-US-04 & NFR-UI-02/03 (lint katalog)

CARA MINTA BANTUAN CLAUDE
  Tampal kad ini + src/core/types.py + fail stub kamu. Contoh: "Bina emv.parse_tlv
  ikut docstring, dengan ujian pytest. Ini kod Colab asal: ..."
```

### Kad Owner B — Platform, Saluran & Video Demo

```text
KAD TUGASAN: OWNER B — PLATFORM, SALURAN & VIDEO DEMO (Semak Dulu, Rabu 14 Okt)

KONTEKS
- Semak Dulu: bot WhatsApp. Aliran: WhatsApp -> API Gateway (HTTP API) -> Ingest Lambda
  -> SQS FIFO -> Worker Lambda -> DynamoDB. Penangguhan (peringatan 120 s, eskalasi 180 s)
  guna SQS standard "timers". Rujukan: docs/SDD.md 2, 4, 6.2, 12.
- SUDAH SIAP & DIUJI dalam repo: template.yaml (sam validate lulus), handlers/ingest.py,
  handlers/worker.py, handlers/config.py (SSM), core/store.py DynamoStore, skrip layer.
  Tugas utama kamu: channels/whatsapp.py, deploy, persediaan Meta, kemudian Telegram.
- Kontrak saluran: kelas Channel dalam src/core/types.py (verify, parse, send, fetch_media).
  user_id SENTIASA "wa:<nombor>". Butang guna Outbound.buttons (maks 3, label maks 20).

PUSTAKA: httpx (HTTP), boto3 (sudah ada dalam Lambda). AWS CLI v2 + SAM CLI. TIADA Docker.

════════════════════════════════════════════════════════
NOTA KHAS: DOCKER / CONTAINER IMAGE — KITA TIDAK PERLUKANNYA
- SDD asal guna container image untuk pustaka QR. Kita tukar ke ZIP + LAMBDA LAYER:
  OpenCV dibuang, hanya zxing-cpp + Pillow. Saya sudah uji: layer 33 MB (had 250 MB),
  import dan baca QR di Python 3.12 x86_64, `sam build` berjaya tanpa Docker
  (setiap fungsi hanya 116 KB).
- Cara ia berfungsi: scripts/build_layer.sh memanggil
    pip install --platform manylinux2014_x86_64 --python-version 3.12 --only-binary=:all:
  yang memuat turun wheel Linux siap-bina, walaupun kamu di Mac atau Windows.
- PERATURAN:
  1. Bina layer:  bash scripts/build_layer.sh   (Windows: scripts\build_layer.ps1)
     Ulang HANYA jika layer/requirements.txt berubah.
  2. Aktifkan venv Python 3.12 SEBELUM `sam build` (SAM semak versi Python tempatan).
  3. JANGAN guna `sam build --use-container`, `sam local invoke` atau `sam local start-api`
     (semuanya perlukan Docker). Uji tempatan dengan pytest (tests/test_handlers.py, moto).
  4. Architectures mesti kekal x86_64 (padan dengan wheel). Mac M1/M2 pun OK.
  5. Ralat "No module named zxingcpp" di Lambda bermaksud folder salah. Mesti
     layer/build/python/zxingcpp...so
- Pelan B jika layer gagal: clone repo dalam AWS CloudShell (Linux) dan jalankan
  build_layer.sh + sam build di sana. Container image ialah pilihan terakhir sahaja.
════════════════════════════════════════════════════════

M0 (serentak dengan Fasa 0, 14:45–15:15): akaun
  1. AWS: pasang AWS CLI v2 + SAM CLI. `aws configure` (region ap-southeast-1 Singapura
     untuk hari ini; ap-southeast-5 Malaysia hanya jika semua servis ada — TBV).
     Semak: `aws sts get-caller-identity`.
  2. Meta (TBV ikut dashboard semasa): developers.facebook.com -> Create App -> jenis
     Business -> tambah produk WhatsApp -> API Setup:
     - catat Phone number ID, salin token akses SEMENTARA (tamat ~24 jam!)
     - "To": tambah nombor telefon A, B, C (setiap satu sahkan dengan kod OTP; had
       penerima nombor ujian kecil, biasanya 5 — TBV)
     - App settings > Basic > App secret
  3. Setiap telefon pasukan hantar "hai" ke nombor ujian (buka tetingkap 24 jam, CO-5).

MILESTONE 1 (15:15–17:00): deploy rangka + jabat tangan webhook
  4. Simpan rahsia SSM (arahan dalam README): wa_token, wa_phone_number_id, wa_app_secret,
     wa_verify_token (teks rawak ciptaan kamu), report_pepper.
  5. whatsapp.WhatsAppChannel.handshake(query): pulangkan query["hub.challenge"] jika
     hub.mode == "subscribe" dan hub.verify_token == self.verify_token, jika tidak None.
     Ujian: tests/test_whatsapp.py.
  6. bash scripts/build_layer.sh && sam build && sam deploy --guided
     - Stack name: semak-dulu-dev · Region: ap-southeast-1 · Parameter Stage: dev
     - "Allow SAM CLI IAM role creation": Y
     - "IngestFunction has no authentication. Is this okay?": y (webhook mesti awam;
       keselamatan dibuat oleh semakan tandatangan dalam kod)
     - Save to samconfig: Y
  7. Salin Output "WebhookWhatsApp" ke Meta > WhatsApp > Configuration > Callback URL,
     Verify token = wa_verify_token, tekan "Verify and save". Kemudian Webhook fields:
     subscribe "messages".
  SELESAI BILA: Meta tunjuk webhook disahkan. CloudWatch log semak-ingest-dev ada GET 200.

MILESTONE 2 (17:10–19:30): WhatsApp penuh  ← LALUAN EMAS (pusat pemeriksaan SDD Khamis,
                                               kita cuba capai hari ini)
  8. verify(): HMAC-SHA256(app_secret, raw_body) bandingkan dengan header
     "x-hub-signature-256" ("sha256=<hex>"), guna hmac.compare_digest. (TBV)
  9. parse(): entry[].changes[].value.messages[] -> InboundEvent
     text -> kind "text", image -> kind "image" (media_ref = image.id),
     interactive.button_reply.id -> kind "button". statuses[] -> abaikan.
     msg_id = msg["id"], user_id = make_user_id("wa", msg["from"]).
     Ujian dengan contoh JSON webhook (dari docs Meta) dalam tests/test_whatsapp.py.
  10. send(): teks biasa jika tiada butang; mesej "interactive" jenis "button" jika ada.
      httpx.post(..., timeout=10), raise jika status >= 400 (log status sahaja, bukan isi).
  11. fetch_media(): 2 langkah (GET media id -> url, GET url dengan token) -> bytes.
  12. Deploy. Uji dengan telefon sebenar menggunakan aliran persediaan C (sudah siap pada
      Sync 1): hantar "Daftar" -> butang bahasa muncul -> tekan -> mesej seterusnya.
  13. Sync 2: forward QR -> 3 butang -> tekan Bank/Polis/Mahkamah -> 🛑 STOP.
  SELESAI BILA: S1 berjaya di telefon sebenar.

MILESTONE 3 (20:00–22:00): kebolehpercayaan + Telegram
  14. Token kekal: Business Settings > System users > jana token dengan kebenaran
      whatsapp_business_messaging (TBV). Kemas kini SSM wa_token --overwrite.
      (Token sementara akan tamat sebelum demo!)
  15. Uji pemasa sebenar: forward QR, jangan tekan -> peringatan selepas ~120 s (S7).
      Anak tidak tekan "Saya uruskan" -> ahli kedua dapat amaran ~180 s (S8).
  16. Ukur masa (NFR-PF-01..04): baca medan "ms" dalam log worker.done untuk 20 semakan.
  17. Uji amaran CloudWatch: semak-worker-errors-dev wujud. Pilihan: tambah SNS e-mel.
  18. telegram.TelegramChannel (fallback): verify (header secret token), parse (message.text,
      message.photo[-1].file_id, callback_query.data), send (inline_keyboard), fetch_media,
      answerCallbackQuery. setWebhook dengan secret_token. Simpan tg_token, tg_secret.
  SELESAI BILA: S7, S8 berjaya di telefon; bot Telegram balas "Daftar".

MILESTONE 4 (22:00–23:30): integrasi & demo
  19. Jalankan S1, S2, S3, S5, S9 di telefon sebenar bersama A dan C.
  20. S10: hantar semula webhook yang sama (Meta kadang-kadang hantar dua kali) -> satu balasan.
  21. Rakam video demo kasar (S1, S2, S5, S8, S9) sebagai sandaran. Video akhir pada 20 Okt.
  22. git tag demo-0 && git push --tags

SYARAT LULUS (SRS) YANG KAMU SAHKAN
  NFR-SE-01 HTTPS (URL API Gateway) · NFR-SE-02 tandatangan salah -> 401, tiada balasan
  NFR-SE-03 kebenaran minimum (template) · NFR-SE-04 tiada rahsia dalam Git/log
  NFR-PF-01..04 masa · DR-09 log tanpa nama/nombor penuh (guna short_hash)
  NFR-RO-01..03 (Telegram jika WhatsApp gagal) · NFR-SU-02 amaran ralat
  Sahkan fakta TBV: had 3 butang/20 aksara, tetingkap 24 jam, had penerima nombor ujian.

CARA MINTA BANTUAN CLAUDE
  Tampal kad ini + src/core/types.py + src/channels/whatsapp.py (docstring ada format API).
  Contoh: "Bina WhatsAppChannel.parse ikut docstring dan tulis ujian dengan contoh webhook."
```

### Kad Owner C — Aliran, Kandungan & Skrip Demo

```text
KAD TUGASAN: OWNER C — ALIRAN, KANDUNGAN & SKRIP DEMO (Semak Dulu, Rabu 14 Okt)

KONTEKS
- Semak Dulu: bot WhatsApp. Kamu bina "otak" perbualan: core/flows.py.
  handle_event(event, store, deps) -> list[Outbound | Task]. Tiada panggilan rangkaian.
  Outbound = mesej untuk dihantar. Task = kerja tertunda (delay_s 0 = segera, >0 = pemasa).
- Rujukan: docs/SRS.md 2.2 (FR-01..FR-27) & 2.2.3 (jadual keputusan), docs/SDD.md 5.4-5.6, 6.
- SUDAH SIAP: InMemoryStore + DynamoStore (core/store.py, diuji), messages.py (render, label),
  katalog src/messages/ms.yaml + en.yaml (draf penuh), scripts/chat_sim.py, tests/fakes.py.
  Kamu TIDAK perlu bina store. Guna store melalui kaedah dalam kelas Store (types.py).
- Butang: id "<tindakan>:<nilai>:<ref>" (senarai dalam types.py). Label dari katalog btn.*.
- Uji setiap langkah dengan: python scripts/chat_sim.py
  (contoh: @anak Daftar · @anak Mak · @mak <KOD> · @mak tap 1 · @mak img personal · timers)

PUSTAKA: tiada baharu. Guna secrets.choice untuk kod pasangan.

────────────────────────────────────────────────────────
MILESTONE 1 (15:15–17:00): persediaan & pautan   (FR-01..FR-04, FR-21..FR-23)
  1. Pembantu: get_or_create_user(user_id) · lang_of(user) · addr(user) (address_as atau
     render("s.default_address")) · send(to, msg_id, lang, buttons=None, **params)
  2. Mesej pertama pengguna baharu -> s.choose_lang + [btn.lang_ms, btn.lang_en]
     (butang lang:ms:- / lang:en:-), kemudian s.welcome. BM jika tidak memilih (FR-04).
  3. route_text: arahan (COMMANDS, tidak peka huruf besar/kecil):
     DAFTAR -> role PRIMARY, s.ask_address. Teks seterusnya daripada PRIMARY yang belum ada
              address_as -> simpan address_as, jana kod 6 aksara dari
              "ABCDEFGHJKLMNPQRSTUVWXYZ23456789" (NFR-SE-06), put_pair_code(target PARENT,
              24 jam), hantar s.pair_code.
     Teks yang padan ^[A-Za-z2-9]{6}$ -> peek_pair_code:
       target PARENT -> s.consent + [btn.agree] (consent:yes:<kod>)
       target SECOND -> s.second_invite + [btn.accept] (accept2:yes:<kod>)
       tiada/tamat -> s.code_invalid
     BAHASA/LANGUAGE -> butang bahasa semula · BANTUAN/HELP -> h.help
     BERHENTI -> h.stop_confirm + [btn.stop_confirm] (stop:confirm:-)
     teks lain -> h.help (FR-23)
  4. route_button:
     consent:yes:<kod> -> consume_pair_code; parent: role PARENT, address_as dari kod,
       consent_at = now; put_link(PRIMARY); s.linked_parent ke ibu bapa, s.linked_child ke
       anak; kemudian s.practice_invite + tandakan semakan seterusnya is_practice (FR-21).
     stop:confirm:- -> delete_user_everything; h.stopped; h.contact_left kepada yang lain.
     TAMBAH (route_text) hanya PRIMARY yang ada pautan -> kod target SECOND dengan
       parent_id; jika get_links ada SECOND -> s.second_exists (FR-03).
     accept2:yes:<kod> -> put_link(SECOND), s.second_linked + s.second_linked_primary.
  SELESAI BILA: dalam chat_sim: anak DAFTAR -> Mak -> kod -> mak hantar kod -> Setuju ->
  kedua-dua dapat pengesahan. Tulis tests/test_flows_setup.py. Push. Lapor di Sync 1.

MILESTONE 2 (17:10–19:30): aliran semakan QR  ← LALUAN EMAS  (FR-05..FR-13, FR-24..FR-26)
  5. on_image:
     - had kadar: count_recent_checks(10 min) >= 10 -> h.rate_limited (NFR-SE-05)
     - get_open_check -> jika ada, status CLOSED (FR-26)
     - Check baharu (DECODING, expires = now + 15 min, media_ref, is_practice jika perlu)
     - pulangkan: q.who_asked + 3 butang claim:OFFICIAL|COURIER|KNOWN_PERSON:<check_id>
       (label btn.claim_official/courier/known), Task("decode", user, check_id, 0),
       Task("reminder", ..., 120), Task("close_check", ..., 600)
  6. route_task "decode": get_check; data = deps.fetch_media(user, media_ref);
     check.decode = deps.decode_image(data); status DECODED; media_ref = None (DR-01).
     Sehingga A siap, chat_sim guna `img personal` dll.
  7. Tekan claim:<X>:<check_id>:
     - check tiada/tamat/CLOSED/ANSWERED -> q.expired (FR-25)
     - v = verdict.decide(claim, check.decode)   (Owner A; sebelum siap, buat fungsi
       sementara mengikut jadual V-1..V-5)
     - Susun teks (satu Outbound, <= 450 aksara):
         [v.practice_prefix jika latihan] + render(v.message_id, payee_name atau
         v.unknown_name, address_as) + [v.amount jika ada] + [nota e.* jika kind NO_QR/
         UNREADABLE/URL/OTHER_TEXT/PAYMENT_OTHER_EMV] + [baris bukti ev.* jika report_key]
         + [v.told_contact jika STOP dan ada pautan dan bukan latihan] + [v.semak_mule
         jika VERIFY]
     - butang: [btn.paid -> paid:yes:<check_id>] [btn.report -> report:open:<check_id>]
     - status ANSWERED, simpan claim dan verdict_level
     - STOP dan ada pautan dan bukan latihan -> escalation.start_alert(...) (M3; buat stub
       kosong dahulu)
  8. route_task "reminder": check masih DECODING/DECODED dan belum diingatkan ->
     q.reminder + 3 butang yang sama (FR-24). "close_check": jika belum ANSWERED -> CLOSED.
  9. paid:yes:<check_id> -> p.paid kepada ibu bapa + start_alert(PAID) (FR-13).
  SELESAI BILA: chat_sim: @mak img personal -> tap 1 -> 🛑 STOP. Sync 2 di telefon sebenar.

MILESTONE 3 (20:00–22:00): amaran keluarga & laporan  (FR-14..FR-20, FR-27)
  10. escalation.start_alert: Alert(PRIMARY_SENT, expires 7 hari, notified=[primary]);
      a.child.stop (claim_label = c.<CLAIM>, qr_desc = a.qr_personal/business/unreadable)
      atau a.child.paid; butang btn.ack -> ack:handle:<alert_id>;
      Task("escalate", parent, alert_id, 180). Mesej dalam bahasa PENERIMA.
  11. on_ack: transition_alert(stage semasa -> ACKED, acked_by). Berjaya -> a.ack_done
      kepada penekan + a.ack_other kepada contact lain yang sudah dimaklumkan. Gagal
      (sudah ACKED) -> a.ack_done sahaja (FR-27, tekan dua kali = satu pengesahan).
  12. on_escalate: PRIMARY_SENT + ada SECOND -> SECONDARY_SENT, amaran yang sama ke SECOND,
      Task escalate 180 lagi. PRIMARY_SENT tanpa SECOND, atau SECONDARY_SENT ->
      UNACKED + a.parent.unacked kepada ibu bapa. ACKED -> tiada apa-apa.
  13. reports: open_report (report_key None -> r.not_reportable; jika tidak r.choose_reason +
      3 butang report:<scam_pattern|dispute|other>:<check_id>); submit_report
      (reporter_hash, add_report -> r.thanks / r.already_reported).
  SELESAI BILA: S8, S9, S11, S12 berjaya dalam chat_sim (guna `timers`).

MILESTONE 4 (22:00–23:30): kandungan, skrip demo, integrasi
  14. docs/demo-script.md: babak demo 3 minit (S1 -> S8 -> S5 -> S9), siapa pegang telefon
      mana, ayat naratif, apa dibuat jika WhatsApp gagal (beralih ke Telegram).
  15. Semak semula ms.yaml: hantar ke penutur asli BM (NFR-US-07). Selepas setiap edit:
      pytest tests/test_messages.py.
  16. Bersama A dan B: jalankan S1–S14 di telefon/chat_sim, catat pepijat.

SYARAT LULUS (SRS) YANG KAMU SAHKAN
  FR-01..FR-05, FR-08, FR-11, FR-13..FR-27 (tingkah laku aliran) · NFR-UI-03 <= 450 aksara
  NFR-UI-05 panggil "Mak"/"Ayah" · NFR-US-01 1 forward + 1 tekan · NFR-US-05 setiap mesej
  berakhir dengan butang atau tindakan · NFR-US-06 kod rahsia keluarga · NFR-SE-05 had
  kadar · NFR-SE-06 kod pasangan · NFR-SE-07 notis privasi dalam s.consent
  NFR-LE-01 penafian dalam s.welcome · NFR-LE-02 tiada "penipu"

CARA MINTA BANTUAN CLAUDE
  Tampal kad ini + src/core/types.py + src/core/flows.py + bahagian ms.yaml yang berkaitan.
  Contoh: "Bina route_text untuk DAFTAR dan nama alamat ikut langkah 3, dengan ujian
  pytest guna tests/fakes.py."
```
