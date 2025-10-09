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
from collections import Counter

PORT_ARDUINO = 'COM5'
BAUDRATE = 9600
MODEL_PATH = 'plat.pt'
SOURCE_PATH = 0
DB_HOST = 'localhost'
DB_USER = 'root'
DB_PASSWORD = ''
DB_NAME = 'mesin_parkir'
DB_TABLE = 'data_mobil'

try:
    arduino = serial.Serial(port=PORT_ARDUINO, baudrate=BAUDRATE, timeout=1)
    print(f"✅ Berhasil terhubung ke Arduino di port {PORT_ARDUINO}.")
    time.sleep(2)
except Exception as e:
    print(f"❌ Gagal terhubung ke Arduino: {e}")
    exit()

model = YOLO(MODEL_PATH)
reader = easyocr.Reader(['en'], gpu=False)

try:
    db_connection = mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME)
    db_cursor = db_connection.cursor()
    print(f"✅ Berhasil terhubung ke database MySQL '{DB_NAME}'")
except Error as e:
    print(f"❌ Error saat menghubungkan ke MySQL: {e}")
    exit()

cap = cv2.VideoCapture(SOURCE_PATH)

def preprocess_for_ocr(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    enhanced_gray = clahe.apply(gray)
    return enhanced_gray

def plat_sudah_ada(nomor_plat):
    try:
        query = f"SELECT 1 FROM {DB_TABLE} WHERE nomor_plat = %s LIMIT 1"
        db_cursor.execute(query, (nomor_plat,))
        return db_cursor.fetchone() is not None
    except Error as e:
        print(f"❌ Error saat mengecek plat: {e}")
        return False

def simpan_plat(waktu_masuk, nomor_plat):
    try:
        query = f"INSERT INTO {DB_TABLE} (waktu_masuk, nomor_plat) VALUES (%s, %s)"
        values = (waktu_masuk, nomor_plat)
        db_cursor.execute(query, values)
        db_connection.commit()
    except Error as e:
        print(f"❌ Error saat menyimpan plat: {e}")

def kirim_perintah_arduino(perintah):
    if perintah == "BUKA":
        arduino.write(b'B')
    elif perintah == "TUTUP":
        arduino.write(b'T')

def ekstrak_plat_dari_frame(frame):
    extraction_pattern = re.compile(r'([A-Z]{1,2}\d{1,4}[A-Z]{1,3})')
    results = model(frame, stream=True, conf=0.25, verbose=False)
    
    for res in results:
        detections = sv.Detections.from_ultralytics(res)
        if len(detections) == 0:
            continue
        
        best_detection_index = detections.confidence.argmax()
        detections = detections[best_detection_index:best_detection_index+1]
        
        bbox = detections.xyxy[0]
        x1, y1, x2, y2 = map(int, bbox)
        plate_crop = frame[y1:y2, x1:x2]
        
        if plate_crop.size > 0:
            processed_crop = preprocess_for_ocr(plate_crop)
            ocr_result = reader.readtext(processed_crop, detail=0, allowlist='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
            if ocr_result:
                raw_plate_text = "".join(ocr_result).upper().replace(" ", "")
                match = extraction_pattern.search(raw_plate_text)
                if match:
                    return match.group(1)
    return None

sistem_status = "MENUNGGU"
kandidat_plat = {}
waktu_mulai_pengumpulan = 0
DURASI_PENGUMPULAN = 3
CONFIRMATION_COUNT = 5

print("\n🚀 Sistem Parkir Cerdas (Versi Stabil) Dimulai. Menunggu sinyal dari Sensor 1...")

try:
    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            break
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

        if arduino.in_waiting > 0:
            data_dari_arduino = arduino.readline().decode('utf-8').strip()
            print(f"ℹ️ Menerima sinyal dari Arduino: '{data_dari_arduino}'")
            if data_dari_arduino == "SENSOR1_AKTIF" and sistem_status == "MENUNGGU":
                print("🔥 SENSOR 1 AKTIF! Memulai fase pengumpulan data plat...")
                sistem_status = "MENGUMPULKAN"
                kandidat_plat = {}
                waktu_mulai_pengumpulan = time.time()
            elif data_dari_arduino == "SENSOR2_AKTIF":
                kirim_perintah_arduino("TUTUP")
                print("✅ [PYTHON] Perintah TUTUP dikirim ke Arduino.")

        if sistem_status == "MENGUMPULKAN":
            plat_terbaca = ekstrak_plat_dari_frame(frame)
            if plat_terbaca:
                kandidat_plat[plat_terbaca] = kandidat_plat.get(plat_terbaca, 0) + 1
                print(f"[INFO] Kandidat: {kandidat_plat}")

                for plat, count in kandidat_plat.items():
                    if count >= CONFIRMATION_COUNT:
                        print(f"🎉 KONFIRMASI DITEMUKAN! Plat paling stabil adalah: {plat}")
                        sistem_status = "ANALISIS"
                        plat_terbaik = plat
                        break
            
            if sistem_status == "MENGUMPULKAN" and time.time() - waktu_mulai_pengumpulan > DURASI_PENGUMPULAN:
                print("⌛ Waktu pengumpulan habis. Memulai analisis dari data yang ada...")
                sistem_status = "ANALISIS"
                if kandidat_plat:
                    plat_terbaik = max(kandidat_plat, key=kandidat_plat.get)
                else:
                    plat_terbaik = None

        elif sistem_status == "ANALISIS":
            if not plat_terbaik:
                print("❌ Tidak ada kandidat plat yang valid. Kembali ke mode menunggu.")
            else:
                print(f"📈 Analisis Selesai. Plat terpilih adalah: {plat_terbaik}")
                if not plat_sudah_ada(plat_terbaik):
                    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    simpan_plat(timestamp, plat_terbaik)
                    print(f"✅ PLAT BARU! Menyimpan {plat_terbaik} ke database dan membuka gerbang.")
                    kirim_perintah_arduino("BUKA")
                    print("✅ [PYTHON] Perintah BUKA dikirim ke Arduino.")
                else:
                    print(f"⚠️  PLAT DUPLIKAT! {plat_terbaik} sudah ada. Gerbang tidak dibuka.")
            
            sistem_status = "MENUNGGU"
            print("\n🚀 Siap untuk kendaraan berikutnya...")

        status_text = f"STATUS: {sistem_status}"
        cv2.putText(frame, status_text, (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)

        if sistem_status == "MENGUMPULKAN":
            collecting_text = f"Mendeteksi... ({len(kandidat_plat)})"
            (text_width, _), _ = cv2.getTextSize(collecting_text, cv2.FONT_HERSHEY_SIMPLEX, 1, 2)
            frame_width = frame.shape[1]
            pos_x = frame_width - text_width - 50
            cv2.putText(frame, collecting_text, (pos_x, 90), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        
        cv2.imshow("Sistem Gerbang Parkir Cerdas", frame)

finally:
    print("\n👋 Membersihkan dan menutup program...")
    cap.release()
    cv2.destroyAllWindows()
    if 'arduino' in locals() and arduino.is_open:
        arduino.close()
    if 'db_connection' in locals() and db_connection.is_connected():
        db_connection.close()