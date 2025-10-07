import serial
import time

# --- KONFIGURASI ---
PORT_ARDUINO = 'COM5' # Ganti dengan port COM Anda
BAUDRATE = 9600

# --- KONEKSI ---
try:
    arduino = serial.Serial(port=PORT_ARDUINO, baudrate=BAUDRATE, timeout=1)
    print(f"Berhasil terhubung ke Arduino di port {PORT_ARDUINO}.")
    time.sleep(2)
except Exception as e:
    print(f"Gagal terhubung: {e}")
    exit()

print("Menunggu sinyal dari Arduino...")
try:
    while True:
        # Cek apakah ada data yang masuk dari Arduino
        if arduino.in_waiting > 0:
            # Baca data dan bersihkan
            data = arduino.readline().decode('utf-8').strip()
            print(f"Menerima sinyal dari Arduino: '{data}'")

            if data == "MOBIL_SIAP":
                print("\n==============================================")
                print("MOBIL TERDETEKSI! Silakan berikan perintah.")
                
                perintah_user = input("Ketik 'buka' untuk membuka gerbang: ")

                if perintah_user.lower() == "buka":
                    arduino.write(b'B')
                    print("--> Perintah 'BUKA' dikirim ke Arduino.")
                else:
                    print("--> Perintah tidak dikenali. Gerbang tidak dibuka.")
                print("==============================================\n")
                print("Menunggu sinyal dari Arduino berikutnya...")

except KeyboardInterrupt:
    print("\nProgram dihentikan.")
finally:
    if arduino.is_open:
        arduino.close()
        print("Koneksi ditutup.")