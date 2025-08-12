# Mulai Cepat — Smart Traffic Counter v3.3

Tujuan: mulai hitung kendaraan dalam 2 menit.

## 1) Jalankan Aplikasi
- Buka `dist/SmartTrafficCounter/`
- Jalankan `SmartTrafficCounter.exe`

## 2) Pilih Sumber Video
- Screen:
  - Klik "Select Region" atau "Full Screen"
  - Klik "Start Preview"
- Webcam:
  - Pilih Type: webcam, set index = 0
  - Klik "Start Preview"
- Network:
  - Isi Stream URL (rtsp/http)
  - Klik "Start Preview"

## 3) Gambar Garis Hitung (1 garis)
- Klik "Draw Line" → drag di video → lepas.
- Jika arah terbalik, atur `invert_direction` di Line Settings.

## 4) Mulai Deteksi
- Klik "Start Detection".
- Default: RAW + Counting aktif (tampil bbox RAW + counting jalan).

## 5) Simpan Hasil
- Klik "Save to Database".
- Lihat "Data Viewer" untuk laporan.

### Nilai Rekomendasi
- `runtime.raw_conf`: 0.25
- `runtime.raw_iou`: 0.70 (naikkan 0.75 jika objek rapat agar tidak digabung)
- `band_px`: 12–18
- `imgsz`: 576 (turunkan jika FPS rendah)

### Masalah Umum
- Kotak tidak muncul: pastikan `raw_counting_mode=true` dan `raw_detections_mode=false`.
- Tidak menghitung: garis belum digambar atau `band_px` terlalu kecil.
- FPS lambat: turunkan `imgsz` atau gunakan GPU.