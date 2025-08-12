# Pemecahan Masalah & FAQ — Smart Traffic Counter v3.3

## A. Masalah Umum

### 1) Tidak ada folder `dist/` atau tidak menemukan `.exe`
- Artinya belum build. Ikuti panduan build dengan PyInstaller (lihat dokumentasi build).
- Setelah berhasil build, exe ada di `dist/SmartTrafficCounter/SmartTrafficCounter.exe`.

### 2) Preview hidup, tapi deteksi tidak muncul
- Pastikan model tersedia (`yolo11n.pt` di folder yang sama).
- Cek settings:
  - `runtime.raw_counting_mode=true`
  - `runtime.raw_detections_mode=false`
  - `raw_conf=0.25`, `raw_iou=0.70`
- Pastikan sumber video benar (Test Source).

### 3) Counting tidak bertambah saat kendaraan lewat garis
- Pastikan garis sudah digambar dan melintasi jalur kendaraan.
- Perbesar `line_settings.band_px` (12–18).
- Jika arah kebalik, set `invert_direction=true`.
- `detection_stride` otomatis 1 di RAW(+Count), pastikan tidak dimodifikasi.

### 4) Tiga kendaraan berdampingan dihitung kurang dari 3
- Naikkan `runtime.raw_iou` 0,70 → 0,75 agar NMS tidak menggabungkan.
- Pastikan `runtime.raw_conf` tidak terlalu tinggi.
- Turunkan `TRACKING_CONFIG.max_match_distance` (mis. 50–60) agar ID tidak menyatu.

### 5) FPS rendah
- Turunkan `runtime.imgsz` ke 512/448.
- Nonaktifkan `raw_draw_ids` jika tidak perlu.
- Gunakan GPU (Torch CUDA build).

### 6) Webcam/Stream macet atau lag
- Atur `runtime.flush_frames` ke 2–4.
- Untuk RTSP, pastikan jaringan stabil.

### 7) Garis tidak bisa digambar saat deteksi berjalan
- Hentikan deteksi dulu (Stop Detection), baru "Draw Line".

### 8) Tidak bisa simpan ke database
- Cek koneksi di DB Settings.
- Untuk SQLite, pastikan file tidak dipakai aplikasi lain dan ada izin tulis.

## B. FAQ

### 1) Apakah setiap bbox punya ID?
- RAW-only: tidak (tidak ada tracking).
- RAW+Counting: ya, ID dipertahankan oleh tracker (ID bisa ditampilkan di label RAW).
- Tracking (non-RAW): ya.

### 2) Apakah saya bisa menampilkan ID di bbox RAW?
- Ya, set `runtime.raw_draw_ids=true`.

### 3) Apakah bisa menghitung lebih dari 2 arah?
- Saat ini 1 garis dengan 2 arah (UP/DOWN). Untuk multi-garis memerlukan pengembangan lanjutan.

### 4) Apakah aplikasi perlu internet?
- Tidak, kecuali model harus diunduh pertama kali (jika tidak disertakan).

### 5) Di mana `settings.json`?
- Dibuat otomatis di folder kerja aplikasi. Anda bisa mengeditnya saat aplikasi tidak berjalan.

### 6) Apakah data video disimpan?
- Tidak. Aplikasi hanya menghitung dan menyimpan agregat angka ke database.