import cv2
import serial
import time
import datetime
import re
import mysql.connector
from mysql.connector import Error
from ultralytics import YOLO
import supervision as sv
import easyocr


PORT_ARDUINO = 'COM5' 
BAUDRATE = 9600

MODEL_PATH = 'plat.pt'
SOURCE_PATH = 0

DB_HOST = 'localhost'
DB_USER = 'root'
DB_PASSWORD = ''
DB_NAME = 'mesin_parkir'
DB_TABLE = 'data_mobil'

CONFIRMATION_COUNT = 5     
DURASI_PENGUMPULAN = 4     

print("🚀 Memulai Sistem Parkir Cerdas (Versi IoT + Akurasi Tinggi)...")

try:
    arduino = serial.Serial(port=PORT_ARDUINO, baudrate=BAUDRATE, timeout=1)
    print(f"✅ Berhasil terhubung ke Arduino di port {PORT_ARDUINO}.")
    time.sleep(2) 
except Exception as e:
    print(f"❌ Gagal terhubung ke Arduino: {e}")
    print("ℹ️ Program akan berjalan tanpa fungsionalitas Arduino.")
    arduino = None

try:
    model = YOLO(MODEL_PATH)
    reader = easyocr.Reader(['en'], gpu=False)
    print("✅ Model YOLO dan EasyOCR berhasil dimuat.")
except Exception as e:
    print(f"❌ Gagal memuat model AI: {e}")
    exit()

try:
    db_connection = mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME)
    db_cursor = db_connection.cursor()
    print(f"✅ Berhasil terhubung ke database MySQL '{DB_NAME}'")
except Error as e:
    print(f"❌ Error saat menghubungkan ke MySQL: {e}")
    exit()

cap = cv2.VideoCapture(SOURCE_PATH)
if not cap.isOpened():
    print(f"❌ Gagal membuka sumber video di path: {SOURCE_PATH}")
    exit()
print("✅ Kamera berhasil diakses.")


TARGET_OCR_HEIGHT = 100

def preprocess_for_ocr(image):
    if image.shape[0] == 0 or image.shape[1] == 0: return None
    scale_ratio = TARGET_OCR_HEIGHT / image.shape[0]
    width = int(image.shape[1] * scale_ratio)
    resized = cv2.resize(image, (width, TARGET_OCR_HEIGHT), interpolation=cv2.INTER_LANCZOS4)
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    binary_image = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    return binary_image

def plat_sudah_ada(nomor_plat):
    try:
        query = f"SELECT 1 FROM {DB_TABLE} WHERE nomor_plat = %s AND waktu_keluar IS NULL LIMIT 1"
        db_cursor.execute(query, (nomor_plat,))
        return db_cursor.fetchone() is not None
    except Error as e:
        print(f"❌ Error saat mengecek plat: {e}")
        return False

def simpan_plat(waktu_masuk, nomor_plat):
    try:
        query = f"INSERT INTO {DB_TABLE} (waktu_masuk, nomor_plat) VALUES (%s, %s)"
        db_cursor.execute(query, (waktu_masuk, nomor_plat))
        db_connection.commit()
    except Error as e:
        print(f"❌ Error saat menyimpan plat: {e}")

def kirim_perintah_arduino(perintah):
    if not arduino:
        print(f"⚠️ Peringatan: Arduino tidak terhubung. Perintah '{perintah}' tidak dikirim.")
        return
    try:
        if perintah == "BUKA":
            arduino.write(b'B')
            print("✅ [PYTHON] Perintah BUKA dikirim ke Arduino.")
        elif perintah == "TUTUP":
            arduino.write(b'T')
            print("✅ [PYTHON] Perintah TUTUP dikirim ke Arduino.")
    except Exception as e:
        print(f"❌ Gagal mengirim perintah ke Arduino: {e}")

def ekstrak_plat_dari_frame(frame):
    extraction_pattern = re.compile(r'([A-Z]{1,2}\d{1,4}[A-Z]{1,3})')
    results = model(frame, stream=True, conf=0.25, verbose=False)
    for res in results:
        detections = sv.Detections.from_ultralytics(res)
        if len(detections) == 0: continue
        
        best_detection_index = detections.confidence.argmax()
        detections = detections[best_detection_index:best_detection_index+1]
        
        bbox = detections.xyxy[0]
        x1, y1, x2, y2 = map(int, bbox)
        plate_crop = frame[y1:y2, x1:x2]
        
        if plate_crop.size > 0:
            processed_crop = preprocess_for_ocr(plate_crop)
            if processed_crop is None: continue
            
            ocr_result = reader.readtext(processed_crop, detail=0, allowlist='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
            if ocr_result:
                raw_plate_text = "".join(ocr_result).upper().replace(" ", "")
                match = extraction_pattern.search(raw_plate_text)
                if match:
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(frame, match.group(1), (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
                    return match.group(1)
    return None

sistem_status = "MENUNGGU"
kandidat_plat = {}
waktu_mulai_pengumpulan = 0
plat_terbaik = None

print(f"\n✅ Sistem siap. Menunggu sinyal dari Sensor 1...")

try:
    while True:
        success, frame = cap.read()
        if not success: break
        if cv2.waitKey(1) & 0xFF == ord('q'): break

        if arduino and arduino.in_waiting > 0:
            data_dari_arduino = arduino.readline().decode('utf-8').strip()
            print(f"ℹ️ Menerima sinyal dari Arduino: '{data_dari_arduino}'")
            
            if data_dari_arduino == "SENSOR1_AKTIF" and sistem_status == "MENUNGGU":
                print("🔥 SENSOR 1 AKTIF! Memulai fase pengumpulan data plat...")
                sistem_status = "MENGUMPULKAN"
                kandidat_plat = {}
                plat_terbaik = None
                waktu_mulai_pengumpulan = time.time()
            
            elif data_dari_arduino == "SENSOR2_AKTIF":
                kirim_perintah_arduino("TUTUP")

        if sistem_status == "MENGUMPULKAN":
            plat_terbaca = ekstrak_plat_dari_frame(frame)
            if plat_terbaca:
                kandidat_plat[plat_terbaca] = kandidat_plat.get(plat_terbaca, 0) + 1
                print(f"INFO: Kandidat -> {kandidat_plat}")

                if kandidat_plat[plat_terbaca] >= CONFIRMATION_COUNT:
                    print(f"🎉 KONFIRMASI DITEMUKAN! Plat paling stabil adalah: {plat_terbaca}")
                    plat_terbaik = plat_terbaca
                    sistem_status = "ANALISIS"
            
            if time.time() - waktu_mulai_pengumpulan > DURASI_PENGUMPULAN and sistem_status == "MENGUMPULKAN":
                print("⌛ Waktu pengumpulan habis. Menganalisis data yang terkumpul...")
                if kandidat_plat:
                    plat_terbaik = max(kandidat_plat, key=kandidat_plat.get)
                else:
                    plat_terbaik = None
                sistem_status = "ANALISIS"

        elif sistem_status == "ANALISIS":
            if plat_terbaik:
                print(f"📈 Analisis Selesai. Plat terpilih adalah: {plat_terbaik}")
                if not plat_sudah_ada(plat_terbaik):
                    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    simpan_plat(timestamp, plat_terbaik)
                    print(f"✅ PLAT BARU! Menyimpan {plat_terbaik} dan membuka gerbang.")
                    kirim_perintah_arduino("BUKA")
                else:
                    print(f"⚠️ PLAT DUPLIKAT! {plat_terbaik} sudah ada di dalam. Gerbang tidak dibuka.")
            else:
                print("❌ Tidak ada kandidat plat yang valid terdeteksi.")

            print("\n✅ Sistem kembali ke mode menunggu...")
            sistem_status = "MENUNGGU"

        cv2.putText(frame, f"STATUS: {sistem_status}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2, cv2.LINE_AA)
        cv2.imshow("Sistem Gerbang Parkir Cerdas (IoT + Akurasi Tinggi)", frame)

finally:
    print("\n👋 Membersihkan dan menutup program...")
    cap.release()
    cv2.destroyAllWindows()
    if arduino and arduino.is_open:
        arduino.close()
        print("✅ Koneksi Arduino ditutup.")
    if 'db_connection' in locals() and db_connection.is_connected():
        db_connection.close()
        print("✅ Koneksi database ditutup.")
