from ultralytics import YOLO
import cv2
import supervision as sv
import easyocr
import datetime
import re
import mysql.connector 
from mysql.connector import Error

MODEL_PATH = 'plat.pt'
SOURCE_PATH = 0


DB_HOST = 'localhost'
DB_USER = 'root'     
DB_PASSWORD = '' 
DB_NAME = 'mesin_parkir'
DB_TABLE = 'data_mobil'

model = YOLO(MODEL_PATH)
tracker = sv.ByteTrack(track_activation_threshold=0.25, lost_track_buffer=60, minimum_matching_threshold=0.8, frame_rate=30)
box_annotator = sv.BoxAnnotator(thickness=2)
label_annotator = sv.LabelAnnotator(text_scale=0.5, text_thickness=1, text_position=sv.Position.BOTTOM_CENTER)

print("Memuat model OCR...")
reader = easyocr.Reader(['en'])
print("Model OCR berhasil dimuat.")

db_connection = None
db_cursor = None
try:
    db_connection = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )
    if db_connection.is_connected():
        db_cursor = db_connection.cursor()
        print(f"✅ Berhasil terhubung ke database MySQL '{DB_NAME}'")
except Error as e:
    print(f"❌ Error saat menghubungkan ke MySQL: {e}")
    exit()

def plat_sudah_ada(nomor_plat):
    """Mengecek apakah plat nomor sudah ada di database."""
    try:
        query = f"SELECT 1 FROM {DB_TABLE} WHERE nomor_plat = %s LIMIT 1"
        db_cursor.execute(query, (nomor_plat,))
        return db_cursor.fetchone() is not None
    except Error as e:
        print(f"Error saat mengecek plat: {e}")
        return False 

def simpan_plat(waktu_masuk, nomor_plat):
    """Menyimpan data plat baru ke database."""
    try:
        query = f"INSERT INTO {DB_TABLE} (waktu_masuk, nomor_plat) VALUES (%s, %s)"
        values = (waktu_masuk, nomor_plat)
        db_cursor.execute(query, values)
        db_connection.commit() 
    except Error as e:
        print(f"Error saat menyimpan plat: {e}")

def validate_plate_format(text):
    """Fungsi Validasi Plat Nomor (Regex)."""
    pattern = re.compile(r'^[A-Z]{1,2}\d{1,4}[A-Z]{1,3}$')
    return pattern.match(text) is not None

cap = cv2.VideoCapture(SOURCE_PATH)
print("Memulai deteksi... Tekan 'q' pada jendela yang muncul untuk keluar.")

while cap.isOpened():
    success, frame = cap.read()
    if not success:
        print("Video selesai atau gagal membaca frame.")
        break

    results = model(frame, stream=True, conf=0.4)

    for res in results:
        detections = sv.Detections.from_ultralytics(res)
        tracked_detections = tracker.update_with_detections(detections=detections)

        for i in range(len(tracked_detections)):
            bbox = tracked_detections.xyxy[i]
            x1, y1, x2, y2 = map(int, bbox)
            plate_crop = frame[y1:y2, x1:x2]
            
            if plate_crop.size > 0:
                ocr_result = reader.readtext(plate_crop, detail=0)
                
                if ocr_result:
                    plate_text = "".join(ocr_result).upper().replace(" ", "")
                    
                    if validate_plate_format(plate_text):
                        if not plat_sudah_ada(plate_text):
                            timestamp_dt = datetime.datetime.now()
                            timestamp_str = timestamp_dt.strftime("%Y-%m-%d %H:%M:%S")
                            
                            simpan_plat(timestamp_str, plate_text)
                            print(f"✅ [{timestamp_str}] PLAT BARU TERSIMPAN DI DATABASE: {plate_text}")
        
        labels = [f"ID:{tracker_id}" for tracker_id in tracked_detections.tracker_id]
        annotated_frame = frame.copy()
        annotated_frame = box_annotator.annotate(scene=annotated_frame, detections=tracked_detections)
        annotated_frame = label_annotator.annotate(scene=annotated_frame, detections=tracked_detections, labels=labels)
        cv2.imshow("Deteksi Plat Nomor - Tekan 'q' untuk keluar", annotated_frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
if db_connection and db_connection.is_connected():
    db_cursor.close()
    db_connection.close()
    print("Koneksi MySQL ditutup.")
print("✅ Deteksi selesai.")