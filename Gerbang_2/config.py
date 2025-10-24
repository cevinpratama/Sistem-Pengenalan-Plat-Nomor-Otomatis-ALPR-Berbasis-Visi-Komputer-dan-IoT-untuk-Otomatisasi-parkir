import os
import sys


# Konfigurasi Arduino
PORT_ARDUINO = 'COM5'
BAUDRATE = 9600

# Konfigurasi Model & Kamera
MODEL_PATH = 'plat.pt'
SOURCE_PATH = 0
TARGET_OCR_HEIGHT = 100

# Konfigurasi Database
DB_HOST = 'localhost'
DB_USER = 'root'
DB_PASSWORD = ''
DB_NAME = 'mesin_parkir'
DB_TABLE = 'data_mobil'

# Konfigurasi Logika Deteksi
CONFIRMATION_COUNT = 5
DURASI_PENGUMPULAN = 4

MIDTRANS_SERVER_KEY = os.environ.get('MIDTRANS_SERVER_KEY')

if MIDTRANS_SERVER_KEY is None:
    print("❌ ERROR: Kunci MIDTRANS_SERVER_KEY tidak ditemukan di environment variable.")
    print("Silakan atur variabel lingkungan sebelum menjalankan aplikasi.")
    sys.exit(1)
