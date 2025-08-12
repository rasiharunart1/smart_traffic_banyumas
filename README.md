# Smart Traffic Counter v3.3

Deteksi kendaraan real-time dan penghitungan arah (UP/DOWN) dengan antarmuka GUI modern (Tkinter), menggunakan Ultralytics YOLO. Mendukung input Screen capture, Webcam, dan Network stream (RTSP/HTTP). Menyediakan mode visualisasi RAW dengan counting aktif, penyimpanan ke database, penampil data (Data Viewer), dan paket .exe untuk Windows.

- Nama aplikasi: SmartTrafficCounter
- Model default: yolo11n.pt
- Output (exe): dist/SmartTrafficCounter/SmartTrafficCounter.exe


<img width="1920" height="1080" alt="image" src="https://github.com/user-attachments/assets/c51caad7-a9d9-4a93-ab4a-b76c4fb0d705" />


## Daftar Isi
- [Fitur](#fitur)
- [Persyaratan Sistem](#persyaratan-sistem)
- [Mulai Cepat (Jalankan .exe)](#mulai-cepat-jalankan-exe)
- [Bangun .exe (Windows, PyInstaller)](#bangun-exe-windows-pyinstaller)
- [Panduan Penggunaan](#panduan-penggunaan)
- [Mode](#mode)
- [Pengaturan Utama](#pengaturan-utama)
- [Database](#database)
- [Pemecahan Masalah](#pemecahan-masalah)
- [Dokumentasi](#dokumentasi)
- [Lisensi](#lisensi)

## Fitur
- Multi-input:
  - Screen capture (pilih region atau fullscreen)
  - Webcam
  - Network stream (RTSP/HTTP)
- Mode RAW + Counting:
  - Menampilkan bounding box RAW dari YOLO persis seperti skrip dasar
  - Counting tetap aktif melalui tracker di belakang layar
  - Opsi menampilkan Track ID pada bbox RAW
- Mode RAW-only (tanpa counting) dan Mode Tracking (non-RAW) dengan ID/path
- Penghitungan arah (UP/DOWN) menggunakan satu garis hitung yang digambar pengguna
- Optimisasi ROI (non-RAW), kontrol FPS, screen capture via mss
- Integrasi database (SQLite/MySQL), Data Viewer, backup/restore
- Pengaturan tersimpan di settings.json

## Persyaratan Sistem
- Windows 10/11 64-bit
- CPU: Intel/AMD modern; GPU NVIDIA opsional untuk akselerasi CUDA
- RAM: minimal 8 GB (disarankan 16 GB)
- Penyimpanan: ≥ 2 GB kosong (Torch/OpenCV berukuran besar)
- Jika memakai GPU: driver NVIDIA + Torch CUDA yang sesuai dengan sistem

## Mulai Cepat (Jalankan .exe)
- Setelah proses build (lihat bagian di bawah), buka:
  - `dist/SmartTrafficCounter/`
- Klik ganda:
  - `SmartTrafficCounter.exe`
- Catatan:
  - Jika SmartScreen muncul, klik "More info" → "Run anyway"
  - `settings.json` dibuat otomatis di folder kerja saat pertama kali jalan
  - `yolo11n.pt` sebaiknya berada di samping exe (sudah dibundel jika memakai spec yang disediakan)

## Bangun .exe (Windows, PyInstaller)
Prasyarat:
- Python 3.9–3.11 (disarankan)
- Virtual environment (.venv) di repo (opsional namun disarankan)

Langkah cepat (dari root repositori):
1) Buat dan aktifkan venv
- `python -m venv .venv`
- `.venv\\Scripts\\activate`
- `python -m pip install --upgrade pip`

2) Pasang tool dan dependensi minimal untuk build
- `pip install pyinstaller ultralytics torch torchvision opencv-python numpy Pillow mss pyautogui`

3) Build dengan spec yang disediakan (mode onedir direkomendasikan)
- `python -m PyInstaller --noconfirm --clean SmartTrafficCounter.spec`

4) Jalankan
- `explorer dist\\SmartTrafficCounter`
- Klik ganda `SmartTrafficCounter.exe`

Onefile (opsional):
- Mode onefile butuh penanganan path khusus untuk model/resource (tidak dibahas di sini). Mode onedir direkomendasikan karena lebih sederhana dan andal.

Lokasi exe:
- `dist/SmartTrafficCounter/SmartTrafficCounter.exe`

## Panduan Penggunaan
1) Pilih Sumber Input:
- Screen: "Select Region" atau "Full Screen", lalu "Start Preview"
- Webcam: pilih index (0/1/…), lalu "Start Preview"
- Network: tempel URL Stream, lalu "Start Preview"

2) Gambar Garis Hitung (satu garis):
- Klik "Draw Line", klik-dan-drag pada video, lepas untuk menetapkan
- Jika arah UP/DOWN terbalik dari ekspektasi, aktifkan "invert_direction" di Line Settings

3) Mulai Deteksi:
- Klik "Start Detection"
- Mode default adalah RAW + Counting (bbox RAW dirender; counting aktif)

4) Simpan Hasil:
- Klik "Save to Database" dan lihat data di "Data Viewer"

## Mode
- RAW + Counting (default)
  - Merender deteksi RAW dari YOLO
  - Tracker berjalan di latar untuk counting
  - Opsional: tampilkan Track ID di label RAW (`runtime.raw_draw_ids=true`)
- RAW-only
  - Hanya menampilkan bbox RAW (tanpa tracker, tanpa counting)
- Tracking (non-RAW)
  - Merender bbox tracker + ID + path; counting aktif

Tips: Untuk adegan padat (kendaraan berdampingan), naikkan `runtime.raw_iou` (mis. 0,70 → 0,75) agar NMS tidak menggabungkan bbox berdekatan.

## Pengaturan Utama
Semua pengaturan tersimpan di `settings.json`.

- model
  - `model_path`: "yolo11n.pt"
  - `confidence_threshold`, `iou_threshold`: untuk mode non-RAW
  - `detection_confidence`: filter yang diteruskan ke tracker
  - `device`: "auto" | "cpu" | "cuda"
- input
  - `type`: "screen" | "webcam" | "network"
  - `webcam_index`, `stream_url`, `screen_region`
- line_settings
  - `band_px`: rekomendasi 12–18
  - `invert_direction`: membalik interpretasi UP/DOWN bila perlu
- runtime
  - `imgsz`: 576 (tune untuk FPS/akurasi)
  - `use_half`: true pada CUDA (FP16)
  - `use_roi_around_line`: optimasi non-RAW
  - RAW:
    - `raw_detections_mode`: RAW-only
    - `raw_counting_mode`: RAW visual + counting (default true)
    - `raw_force_full_region`: true untuk perilaku mirip skrip
    - `raw_show_all_classes`: false → hanya kendaraan saat render
    - `raw_conf`: 0,25
    - `raw_iou`: 0,70 (naikkan jika bbox sering tergabung)
    - `raw_draw_ids`: true untuk menampilkan Track ID pada label RAW

Tuning tracking (di `config.py` → `TRACKING_CONFIG`):
- `max_match_distance`: turunkan (50–60) jika ID sering menyatu pada kondisi padat
- `max_track_lost_frames`: ketahanan track

## Database
- Mendukung SQLite (default) atau MySQL
- Atur di "DB Settings" pada aplikasi
- "Save to Database" menyimpan total UP/DOWN per kelas dan agregat
- "Data Viewer" menampilkan riwayat; tersedia Backup/Restore

## Pemecahan Masalah
- Tidak ada `dist/` atau exe:
  - Belum dilakukan build. Jalankan PyInstaller dengan spec di atas.
- Bbox RAW tidak muncul:
  - Pastikan `runtime.raw_counting_mode=true`
  - Pastikan `raw_detections_mode=false`
  - Periksa `raw_conf=0,25`, `raw_iou=0,70`
- Tidak menghitung saat melintas:
  - Pastikan garis hitung melintasi jalur kendaraan
  - Perbesar `band_px` (12–18)
  - Aktifkan `invert_direction` bila perlu
- Tiga kendaraan berdampingan dihitung kurang dari 3:
  - Naikkan `runtime.raw_iou` ke 0,75; pertimbangkan menurunkan `max_match_distance`
- FPS rendah:
  - Turunkan `imgsz` ke 512/448
  - Nonaktifkan `raw_draw_ids`
  - Gunakan Torch CUDA

## Dokumentasi
- Panduan Pengguna: [docs/User_Manual_SmartTrafficCounter.md](docs/User_Manual_SmartTrafficCounter.md)
- Mulai Cepat: [docs/Quick_Start_CheatSheet.md](docs/Quick_Start_CheatSheet.md)
- Pemecahan Masalah & FAQ: [docs/Troubleshooting_FAQ.md](docs/Troubleshooting_FAQ.md)
- Referensi Pengaturan: [docs/Settings_Reference.md](docs/Settings_Reference.md)
- Catatan Rilis v3.3: [docs/Release_Notes_v3.3.md](docs/Release_Notes_v3.3.md)

## Lisensi
Tentukan lisensi proyek Anda di sini (misalnya MIT). Jika belum ada, tambahkan file LICENSE ke repo.
