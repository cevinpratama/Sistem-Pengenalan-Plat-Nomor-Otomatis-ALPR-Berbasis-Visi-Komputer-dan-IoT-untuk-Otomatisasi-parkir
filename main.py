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

try:
    arduino = serial.Serial(port=PORT_ARDUINO, baudrate=BAUDRATE, timeout=1)
    print(f"✅ Berhasil terhubung ke Arduino di port {PORT_ARDUINO}.")
    time.sleep(2)
except Exception as e:
    print(f"❌ Gagal terhubung ke Arduino: {e}")
    exit()

model = YOLO(MODEL_PATH)
box_annotator = sv.BoxAnnotator(thickness=2)
label_annotator = sv.LabelAnnotator(text_scale=0.5, text_thickness=1, text_position=sv.Position.TOP_CENTER)

print("Memuat model OCR...")
reader = easyocr.Reader(['en'])
print("✅ Model OCR berhasil dimuat.")

try:
    db_connection = mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME)
    db_cursor = db_connection.cursor()
    print(f"✅ Berhasil terhubung ke database MySQL '{DB_NAME}'")
except Error as e:
    print(f"❌ Error saat menghubungkan ke MySQL: {e}")
    exit()

cap = cv2.VideoCapture(SOURCE_PATH)

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

def validate_plate_format(text):
    pattern = re.compile(r'^[A-Z]{1,2}\d{1,4}[A-Z]{1,3}$')
    return pattern.match(text) is not None

def kirim_perintah_arduino(perintah):
    if perintah == "BUKA":
        arduino.write(b'B')
        print("✅ [PYTHON] Perintah BUKA dikirim ke Arduino.")
    elif perintah == "TUTUP":
        arduino.write(b'T')
        print("✅ [PYTHON] Perintah TUTUP dikirim ke Arduino.")

def deteksi_dan_cek_plat(frame):
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
            ocr_result = reader.readtext(plate_crop, detail=0, allowlist='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
            if ocr_result:
                plate_text = "".join(ocr_result).upper().replace(" ", "")
                print(f"[DEBUG] OCR MENTAH: '{' '.join(ocr_result)}' -> DIPROSES: '{plate_text}'")
                if validate_plate_format(plate_text):
                    if not plat_sudah_ada(plate_text):
                        timestamp_dt = datetime.datetime.now()
                        timestamp_str = timestamp_dt.strftime("%Y-%m-%d %H:%M:%S")
                        simpan_plat(timestamp_str, plate_text)
                        print(f"✅ [{timestamp_str}] PLAT BARU terdeteksi dan disimpan: {plate_text}")
                        return "BARU", detections, plate_text
                    else:
                        print(f"⚠️  PLAT TERDETEKSI DUPLIKASI: {plate_text}")
                        return "DUPLIKAT", detections, plate_text
    return "GAGAL", sv.Detections.empty(), ""

deteksi_aktif = False
waktu_mulai_deteksi = 0
TIMEOUT_DETEKSI = 30

print("\n🚀 Sistem Parkir Otomatis Dimulai. Menunggu sinyal dari Sensor 1...")

try:
    while cap.isOpened():
        success, frame = cap.read()
        if not success: break
        if cv2.waitKey(1) & 0xFF == ord('q'): break

        annotated_frame = frame.copy()

        if arduino.in_waiting > 0:
            data_dari_arduino = arduino.readline().decode('utf-8').strip()
            print(f"ℹ️ Menerima sinyal dari Arduino: '{data_dari_arduino}'")
            if data_dari_arduino == "SENSOR1_AKTIF" and not deteksi_aktif:
                print("🔥 SENSOR 1 AKTIF! Memulai mode deteksi plat...")
                deteksi_aktif = True
                waktu_mulai_deteksi = time.time()
            elif data_dari_arduino == "SENSOR2_AKTIF":
                kirim_perintah_arduino("TUTUP")

        if deteksi_aktif:
            cv2.putText(annotated_frame, "MEMINDAI PLAT...", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            
            status_plat, detections, plate_text = deteksi_dan_cek_plat(frame)
            
            if not detections.is_empty():
                labels = [f"{plate_text} ({detections.confidence[0]:0.2f})"]
                annotated_frame = box_annotator.annotate(scene=annotated_frame, detections=detections)
                annotated_frame = label_annotator.annotate(scene=annotated_frame, detections=detections, labels=labels)

            if status_plat == "BARU":
                kirim_perintah_arduino("BUKA")
                deteksi_aktif = False
            elif status_plat == "DUPLIKAT":
                print("Gerbang tidak dibuka karena plat sudah terdaftar.")
                time.sleep(2)
                deteksi_aktif = False
            
            if time.time() - waktu_mulai_deteksi > TIMEOUT_DETEKSI:
                print("❌ Waktu deteksi habis. Gagal menemukan plat yang valid.")
                deteksi_aktif = False

        cv2.imshow("Sistem Gerbang Parkir Cerdas (Tekan 'q' untuk keluar)", annotated_frame)
finally:
    print("\n👋 Membersihkan dan menutup program...")
    cap.release()
    cv2.destroyAllWindows()
    if 'arduino' in locals() and arduino.is_open:
        arduino.close()
        print("Koneksi Arduino ditutup.")
    if 'db_connection' in locals() and db_connection.is_connected():
        db_cursor.close()
        db_connection.close()
        print("Koneksi MySQL ditutup.")