# Smart Traffic Counter v3.3 — Panduan Pengguna

Dokumen ini menjelaskan cara menggunakan aplikasi Smart Traffic Counter v3.3 untuk deteksi dan penghitungan kendaraan secara real-time.

Versi aplikasi: v3.3  
Platform: Windows (exe onedir)  
Model: YOLO (default yolo11n.pt)  
Antarmuka: GUI (Tkinter)

## 1. Ringkasan Fitur
- Deteksi kendaraan real-time dari 3 sumber:
  - Screen capture (region pilihan atau fullscreen)
  - Webcam
  - Network stream (RTSP/HTTP)
- Mode RAW + Counting:
  - Menampilkan kotak deteksi "mentah" (RAW) dari YOLO persis seperti skrip standar.
  - Penghitungan tetap aktif (tracker berjalan di belakang layar).
  - Opsional menampilkan Track ID di label bbox RAW.
- Mode RAW-only:
  - Hanya menampilkan kotak RAW tanpa counting.
- Mode Tracking (non-RAW):
  - Menampilkan kotak hasil tracker + ID + jalur gerak (path).
- Penghitungan arah (UP/DOWN) berbasis garis hitung (counting line) yang Anda gambar.
- Database (SQLite atau MySQL) untuk menyimpan hasil hitung, backup/restore, dan Data Viewer bawaan.
- Pengaturan tersimpan otomatis di settings.json.

## 2. Persyaratan Sistem
- OS: Windows 10/11 64-bit.
- CPU: Intel/AMD modern. GPU NVIDIA (opsional) untuk percepatan via CUDA.
- RAM: 8 GB (minimum), 16 GB disarankan.
- Storage: ≥ 2 GB kosong (Torch/OpenCV cukup besar).
- Kamera/Stream: Opsional (jika tidak pakai screen).
- Jika GPU:
  - Driver NVIDIA terbaru.
  - Torch CUDA build sesuai versi CUDA (opsional jika paket exe dibangun khusus GPU).

## 3. Instalasi & Menjalankan Aplikasi
### 3.1. Menjalankan dari .exe
- Buka folder:
  - `dist/SmartTrafficCounter/`
- Jalankan:
  - `SmartTrafficCounter.exe`
- Catatan:
  - Jika Windows Defender SmartScreen muncul, pilih "More info" → "Run anyway".
  - File `settings.json` akan dibuat otomatis di folder kerja saat pertama jalan.
  - Pastikan `yolo11n.pt` tersedia (biasanya dibundel di folder yang sama dengan exe).

### 3.2. Menjalankan dari source (opsional)
- Khusus pengembang. Lihat `build_windows.bat` atau panduan PyInstaller jika diperlukan.

## 4. Antarmuka Pengguna (UI Tour)
- Header:
  - Model Settings: ganti model, confidence, IoU, device.
  - DB Settings: atur koneksi database (SQLite/MySQL).
  - Data Viewer: lihat laporan data tersimpan.
  - Status koneksi DB.
- Sidebar Kiri:
  - Input Source:
    - Type: screen/webcam/network.
    - Test Source: uji sumber video.
  - Screen Capture:
    - Select Region atau Full Screen.
    - Start/Stop Preview.
  - Counting Line Setup:
    - Line Settings: warna, ketebalan, band_px, invert direction.
    - Draw Line: gambar 1 garis hitung.
    - Clear Line: hapus garis.
  - Detection Control:
    - Start/Stop Detection.
    - Reset Counts.
  - System Status:
    - Info region/source, status line, status preview.
- Pusat (Video):
  - Kanvas video (live).
  - FPS dan jumlah deteksi/teks info.
  - Petunjuk penggunaan singkat.
- Sidebar Kanan:
  - Live Statistics:
    - Total UP/DOWN
    - Per jenis kendaraan: car, motorcycle, bus, truck (UP/DOWN)
  - Database Operations:
    - Save to Database, Data Viewer, Settings, Backup, Restore
  - System Info:
    - Model, nilai conf/IoU, device
    - Tips performa
  - Legend arah dan status.

## 5. Alur Kerja Cepat (Mulai Cepat)
- Pilih sumber input:
  - Screen: klik Select Region atau Full Screen.
  - Webcam: set index kamera (0/1/…).
  - Network: isi Stream URL (mis. rtsp://…).
- Klik Start Preview untuk melihat feed live.
- Gambar Counting Line:
  - Klik tombol "Draw Line", lalu drag di video untuk membuat satu garis.
  - Pastikan garis melintasi jalur kendaraan.
  - Jika arah kebalik, aktifkan "invert_direction" di Line Settings.
- Mulai Deteksi:
  - Klik "Start Detection".
  - Mode default: RAW + Counting aktif (kotak RAW tampil, perhitungan berjalan).
- Simpan Hasil:
  - Klik "Save to Database".
  - Lihat di "Data Viewer".

## 6. Mode Operasi
### 6.1. RAW + Counting (default)
- Menampilkan bbox RAW (langsung dari model YOLO) seperti skrip.
- Tracker tetap berjalan di belakang layar untuk counting (tanpa menggambar bbox tracker).
- Opsional tampilkan Track ID di label bbox RAW (`runtime.raw_draw_ids = true`).
- Cocok jika Anda menginginkan visual RAW yang konsisten dengan counting akurat.

### 6.2. RAW-only (tanpa counting)
- Menampilkan bbox RAW saja, tidak ada ID/track, counting dimatikan.
- Gunakan untuk inspeksi visual murni atau evaluasi model.

### 6.3. Tracking (non-RAW)
- Menampilkan bbox hasil tracker + ID + jalur gerak.
- Counting tetap berjalan.
- Cocok jika ingin melihat ID stabil dan lintasan kendaraan.

## 7. Menggambar Garis Hitung (Counting Line)
- Klik "Draw Line", lalu drag di video untuk membuat 1 garis.
- Gunakan `band_px` untuk toleransi jarak crossing (default 12 px).
- Label "UP" dan "DOWN" akan muncul. Arah ini ditentukan oleh normal garis.
- Jika arah terbalik dari yang diinginkan, ubah `invert_direction` di Line Settings.

## 8. Pengaturan (settings.json)
Lokasi: dibuat otomatis di folder kerja. Edit saat aplikasi tidak berjalan.

Bagian penting:
- model:
  - `model_path`: path model YOLO (default "yolo11n.pt").
  - `confidence_threshold`, `iou_threshold`: dipakai saat non-RAW mode.
  - `detection_confidence`: ambang untuk diteruskan ke tracker (filter).
  - `device`: "auto"/"cpu"/"cuda".
- input:
  - `type`: "screen"/"webcam"/"network"
  - `webcam_index`: 0/1/…
  - `stream_url`: RTSP/HTTP URL
  - `screen_region`: [left, top, right, bottom]
- line_settings:
  - `line_color`: warna hex, mis. "#00d4ff"
  - `line_thickness`: ketebalan garis
  - `show_label`: true/false
  - `label_text`: teks label di garis
  - `band_px`: lebar pita toleransi crossing
  - `invert_direction`: true/false
- runtime:
  - `imgsz`: resolusi inference (mis. 576)
  - `use_half`: true (FP16 di GPU)
  - `use_roi_around_line`: gunakan ROI sekitar garis (non-RAW)
  - `roi_margin_px`, `roi_gate_length_px`, `roi_safe_pad_px`: parameter ROI
  - `detection_stride`: jalankan deteksi setiap n frame (non-RAW)
  - `predict_missing`, `max_prediction_frames`: prediksi track yang hilang sementara
  - `use_class_filter`: filter kelas kendaraan saat non-RAW
  - `draw_paths`, `max_path_points_drawn`: gambar jalur (non-RAW)
  - `flush_frames`: jumlah grab frame kamera untuk kurangi lag
  - `use_mss_screen_capture`: gunakan mss untuk screen capture
  - `win_force_dpi_awareness`: DPI aware (Windows)
  - `raw_detections_mode`: true → RAW-only (counting OFF)
  - `raw_counting_mode`: true → RAW visual + counting ON
  - `raw_force_full_region`: true → deteksi full frame agar mirip skrip
  - `raw_show_all_classes`: true/false (tampilkan semua kelas atau hanya kendaraan)
  - `raw_conf`: 0.25 (threshold RAW)
  - `raw_iou`: 0.70 (IoU RAW/NMS)
  - `raw_draw_ids`: true/false (tampilkan Track ID di atas bbox RAW saat raw_counting_mode)

## 9. Tips Akurasi & Performa
- Tiga kendaraan berdampingan tetap dihitung 3 jika:
  - Deteksi menghasilkan 3 bbox terpisah (atur `raw_iou` lebih tinggi 0,65–0,75 agar NMS tidak menggabung).
  - Tracker menjaga 3 ID berbeda (turunkan `max_match_distance` jika perlu).
- RAW(+Count) memaksa `detection_stride = 1` untuk presisi crossing.
- Jika FPS turun:
  - Turunkan `imgsz` ke 512/448.
  - Nonaktifkan `raw_draw_ids` (sedikit penghematan).
  - Gunakan GPU (Torch CUDA).
- ROI:
  - Untuk non-RAW, nyalakan `use_roi_around_line` agar hemat komputasi.
  - Jika RAW+Count, `raw_force_full_region=true` untuk hasil mirip skrip.

## 10. Database & Pelaporan
- Save to Database: menyimpan ringkasan hitungan (UP/DOWN total dan per kelas).
- Data Viewer: melihat riwayat data tersimpan (filter tanggal, export CSV opsional).
- Backup/Restore:
  - Backup database file.
  - Restore dari backup (hati-hati menimpa data).

## 11. Pemecahan Masalah (lihat juga dokumen Pemecahan Masalah)
- Kotak tidak muncul di RAW+Count:
  - Pastikan `runtime.raw_counting_mode=true` dan `raw_detections_mode=false`.
  - Periksa `raw_conf/raw_iou` sesuai (0.25/0.70 rekomendasi awal).
- Counting tidak bertambah:
  - Pastikan garis sudah tergambar dan melintasi jalur kendaraan.
  - Perbesar `band_px` (12–18).
  - Invert direction jika arah terbalik.
- Kamera/Stream tidak tampil:
  - Uji di "Test Source".
  - Atur `flush_frames` (2–4) untuk mengurangi lag.
- FPS lambat:
  - Gunakan GPU/CUDA, atau turunkan `imgsz`.

## 12. Keamanan & Privasi
- Aplikasi memproses video lokal dan tidak mengirimkan ke cloud.
- Data yang disimpan hanyalah angka hitungan ke database (tanpa video).
- Pastikan Anda memiliki izin untuk merekam/menangkap sumber video.

## 13. Lisensi dan Pihak Ketiga
- Menggunakan Ultralytics YOLO, PyTorch, OpenCV, dan pustaka terkait.
- Lisensi masing-masing mengikuti ketentuan asalnya.

## 14. Kontak & Dukungan
- Pemelihara: rasiharunart1
- Laporkan bug/permintaan fitur disertai langkah reproduksi dan screenshot.

### Lampiran A — Rekomendasi Nilai Awal
- runtime:
  - `imgsz`: 576
  - `raw_counting_mode`: true
  - `raw_detections_mode`: false
  - `raw_conf`: 0.25
  - `raw_iou`: 0.70
  - `raw_force_full_region`: true
  - `band_px`: 12
- `TRACKING_CONFIG`:
  - `max_match_distance`: 80 (turunkan ke 50–60 jika ID mudah bercampur saat padat)

### Lampiran B — Alur Ideal
1) Pilih input → 2) Preview → 3) Draw Line → 4) Start Detection → 5) Save to DB → 6) Data Viewer.