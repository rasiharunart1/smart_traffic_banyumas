# Catatan Rilis — Smart Traffic Counter v3.3

Tanggal rilis: 2025-08-12

## Fitur Baru
- Mode RAW Counting:
  - Menampilkan kotak RAW YOLO (seperti skrip asli).
  - Counting tetap aktif via tracker di belakang layar.
- Mode RAW-only:
  - Hanya render RAW tanpa counting — untuk inspeksi visual.
- Opsi `raw_draw_ids`:
  - Menampilkan Track ID di label bbox RAW (pemetaan via IoU ke track aktif).
- Performa:
  - Screen capture via mss (fallback PIL).
  - Otomatis `detection_stride=1` di RAW/RAW+Count untuk presisi.
- UI:
  - Antarmuka modern, statistik live per kelas kendaraan, Data Viewer & operasi DB.
- Konfigurasi:
  - `runtime.raw_conf`, `raw_iou`, `raw_force_full_region`, `raw_show_all_classes`, `raw_draw_ids`.

## Perbaikan
- Stabilitas screen capture dan DPI awareness Windows.
- Clamp bbox agar tidak keluar frame.
- Penanganan ROI di sekitar counting line pada mode non-RAW.

## Catatan Upgrade
- `settings.json` kini memuat key runtime tambahan (raw_*).
- `TRACKING_CONFIG` dapat disesuaikan di `config.py` untuk stabilitas ID.

## Diketahui (Known Issues)
- Onefile build memerlukan penanganan path khusus untuk resource (model). Direkomendasikan onedir build.
- Pada adegan sangat padat, ID dapat sesekali tertukar — kurangi `max_match_distance` dan naikkan `raw_iou`.

## Kontributor
- Pemelihara: rasiharunart1