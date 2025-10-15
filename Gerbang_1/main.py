import cv2
import time
import datetime
import config

from iot_controller import ArduinoController
from db_controller import DatabaseManager
from vision_processor import VisionProcessor

def main():
    """Fungsi utama untuk menjalankan seluruh aplikasi."""
    print("🚀 Memulai Sistem Parkir Cerdas (Versi Modular)...")
    
    arduino = ArduinoController()
    db = DatabaseManager()
    vision = VisionProcessor()

    cap = cv2.VideoCapture(config.SOURCE_PATH)
    if not cap.isOpened():
        print(f"❌ Gagal membuka kamera di path: {config.SOURCE_PATH}")
        return

    print(f"\n✅ Sistem siap. Menunggu sinyal dari Sensor 1...")

    sistem_status = "MENUNGGU"
    kandidat_plat = {}
    waktu_mulai_pengumpulan = 0

    try:
        while True:
            success, frame = cap.read()
            if not success: break
            if cv2.waitKey(1) & 0xFF == ord('q'): break

            signal = arduino.read_line()
            if signal:
                print(f"ℹ️ Menerima sinyal dari Arduino: '{signal}'")
                if signal == "SENSOR1_AKTIF" and sistem_status == "MENUNGGU":
                    print("🔥 SENSOR 1 AKTIF! Memulai fase pengumpulan data plat...")
                    sistem_status = "MENGUMPULKAN"
                    kandidat_plat.clear()
                    waktu_mulai_pengumpulan = time.time()
                elif signal == "SENSOR2_AKTIF":
                    arduino.send_command("TUTUP")

            if sistem_status == "MENGUMPULKAN":
                plat_terbaca = vision.extract_plate_from_frame(frame)
                if plat_terbaca:
                    kandidat_plat[plat_terbaca] = kandidat_plat.get(plat_terbaca, 0) + 1
                    print(f"INFO: Kandidat -> {kandidat_plat}")

                    if kandidat_plat[plat_terbaca] >= config.CONFIRMATION_COUNT:
                        plat_terbaik = plat_terbaca
                        sistem_status = "ANALISIS"

                if time.time() - waktu_mulai_pengumpulan > config.DURASI_PENGUMPULAN and sistem_status == "MENGUMPULKAN":
                    if kandidat_plat:
                        plat_terbaik = max(kandidat_plat, key=kandidat_plat.get)
                    else:
                        plat_terbaik = None
                    sistem_status = "ANALISIS"

            elif sistem_status == "ANALISIS":
                if plat_terbaik:
                    print(f"📈 Analisis Selesai. Plat terpilih: {plat_terbaik}")
                    if not db.is_plate_exist(plat_terbaik):
                        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        db.save_plate(timestamp, plat_terbaik)
                        arduino.send_command("BUKA")
                    else:
                        print(f"⚠️ PLAT DUPLIKAT! {plat_terbaik} sudah ada di dalam.")
                else:
                    print("❌ Tidak ada plat yang valid terdeteksi.")
                
                print("\n✅ Sistem kembali ke mode menunggu...")
                sistem_status = "MENUNGGU"

            cv2.putText(frame, f"STATUS: {sistem_status}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2, cv2.LINE_AA)
            cv2.imshow("Sistem Gerbang Parkir Cerdas", frame)

    finally:
        print("\n👋 Membersihkan dan menutup program...")
        cap.release()
        cv2.destroyAllWindows()
        arduino.close()
        db.close()

if __name__ == "__main__":
    main()
