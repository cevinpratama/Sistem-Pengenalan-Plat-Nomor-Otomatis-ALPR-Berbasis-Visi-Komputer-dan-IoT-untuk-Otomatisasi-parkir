import cv2
import re
from ultralytics import YOLO
import supervision as sv
import easyocr
import config

class VisionProcessor:
    def __init__(self):
        """Memuat model AI (YOLO dan EasyOCR)."""
        print("⏳ Memuat model AI, ini mungkin memakan waktu beberapa saat...")
        try:
            self.model = YOLO(config.MODEL_PATH)
            self.reader = easyocr.Reader(['en'], gpu=False)
            self.extraction_pattern = re.compile(r'([A-Z]{1,2}\d{1,4}[A-Z]{1,3})')
            print("✅ Model YOLO dan EasyOCR berhasil dimuat.")
        except Exception as e:
            print(f"❌ Gagal memuat model AI: {e}")
            exit()

    def _preprocess_for_ocr(self, image):
        """Mempersiapkan gambar untuk OCR agar lebih akurat."""
        if image.shape[0] == 0 or image.shape[1] == 0: return None
        scale = config.TARGET_OCR_HEIGHT / image.shape[0]
        width = int(image.shape[1] * scale)
        resized = cv2.resize(image, (width, config.TARGET_OCR_HEIGHT), interpolation=cv2.INTER_LANCZOS4)
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        binary = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        return binary

    def extract_plate_from_frame(self, frame):
        """Mendeteksi, memotong, dan membaca plat dari sebuah frame."""
        results = self.model(frame, stream=True, conf=0.25, verbose=False)
        for res in results:
            detections = sv.Detections.from_ultralytics(res)
            if len(detections) == 0: continue

            best_idx = detections.confidence.argmax()
            bbox = detections.xyxy[best_idx]
            x1, y1, x2, y2 = map(int, bbox)
            
            plate_crop = frame[y1:y2, x1:x2]
            if plate_crop.size <= 0: continue

            processed_crop = self._preprocess_for_ocr(plate_crop)
            if processed_crop is None: continue

            ocr_res = self.reader.readtext(processed_crop, detail=0, allowlist='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
            if ocr_res:
                raw_text = "".join(ocr_res).upper().replace(" ", "")
                match = self.extraction_pattern.search(raw_text)
                if match:
                    plate_text = match.group(1)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(frame, plate_text, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
                    return plate_text
        return None
