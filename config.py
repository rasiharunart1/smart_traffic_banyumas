"""
Configuration file untuk Vehicle Counter Application
Berisi semua pengaturan yang digunakan oleh aplikasi, termasuk database, model YOLO, tracking, dan tampilan GUI.
"""

# Konfigurasi koneksi ke database PostgreSQL
DATABASE_CONFIG = {
    'dbname': "person_counter",         # Nama database
    'user': "magang",                   # Username database
    'password': "magang123#",           # Password database
    'host': "10.98.33.122",             # Alamat IP server database
    'port': "5433"                      # Port koneksi database
}

# Konfigurasi model YOLO
MODEL_CONFIG = {
    'model_path': 'yolo11n.pt',         # Path ke file model YOLO
    'confidence_threshold': 0.05,       # Threshold minimum confidence untuk menampilkan deteksi
    'iou_threshold': 0.5,               # Threshold IoU untuk NMS (Non-Maximum Suppression)
    'detection_confidence': 0.15        # Confidence minimum agar deteksi dianggap valid
}

# Daftar class kendaraan berdasarkan COCO dataset
VEHICLE_CLASSES = [2, 3, 5, 7]          # Class ID: 2=car, 3=motorcycle, 5=bus, 7=truck
CLASS_NAMES = {
    2: 'car',
    3: 'motorcycle',
    5: 'bus',
    7: 'truck'
}

# Konfigurasi tampilan GUI aplikasi
GUI_CONFIG = {
    'window_title': "YOLO Vehicle Counter - Screen Capture v2.3 DIRECTIONAL",  # Judul jendela aplikasi
    'window_size': "1400x900",              # Ukuran jendela GUI
    'fps_target': 30                        # Target frame per second untuk video
}

# Pengaturan default untuk garis perhitungan (counting line)
DEFAULT_LINE_SETTINGS = {
    'line_color': '#FF0000',                # Warna garis (merah)
    'line_thickness': 3,                    # Ketebalan garis
    'line_style': 'solid',                  # Gaya garis: solid, dashed, dll
    'show_label': True,                     # Tampilkan label pada garis
    'label_text': 'COUNTING LINE',          # Teks label
    'detection_threshold': 50,             # Ambang jarak deteksi ke garis (dalam piksel)
    'line_type': 'manual'                   # Jenis garis: manual atau otomatis
}

# Konfigurasi untuk sistem pelacakan (tracking)
TRACKING_CONFIG = {
    'max_distance': 50,                    # Jarak maksimum antar frame untuk menganggap objek sama
    'path_history_length': 10,              # Panjang riwayat jalur pergerakan kendaraan
    'track_timeout': 3.5,                   # Waktu dalam detik sebelum sebuah track dianggap hilang
    'min_detection_size': 20                # Ukuran minimum deteksi (lebar/tinggi) agar diproses
}

# Konfigurasi warna untuk bounding box dan elemen visual lainnya
COLOR_CONFIG = {
    'active_vehicle': (0, 255, 0),          # Warna hijau untuk kendaraan yang sedang aktif terdeteksi
    'counted_vehicle': (128, 128, 128),     # Abu-abu untuk kendaraan yang sudah dihitung
    'center_dot_active': (0, 0, 255),       # Titik tengah merah untuk kendaraan aktif
    'center_dot_counted': (64, 64, 64),     # Titik tengah abu-abu gelap untuk kendaraan yang dihitung
    'tracking_path': (255, 0, 0),           # Jalur pelacakan berwarna biru
    'tracking_path_counted': (64, 64, 64)   # Jalur pelacakan abu-abu untuk kendaraan yang sudah dihitung
}
