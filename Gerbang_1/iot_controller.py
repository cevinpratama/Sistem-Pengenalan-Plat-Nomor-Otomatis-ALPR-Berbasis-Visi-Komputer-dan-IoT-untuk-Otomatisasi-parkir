import serial
import time
import config

class ArduinoController:
    def __init__(self):
        """Inisialisasi dan coba hubungkan ke Arduino."""
        self.arduino = None
        try:
            self.arduino = serial.Serial(
                port=config.PORT_ARDUINO,
                baudrate=config.BAUDRATE,
                timeout=1
            )
            print(f"✅ Berhasil terhubung ke Arduino di port {config.PORT_ARDUINO}.")
            time.sleep(2)  
        except Exception as e:
            print(f"❌ Gagal terhubung ke Arduino: {e}")
            print("ℹ️ Program akan berjalan tanpa fungsionalitas Arduino.")

    def is_connected(self):
        """Mengecek apakah Arduino terhubung."""
        return self.arduino is not None and self.arduino.is_open

    def send_command(self, command):
        """Mengirim perintah 'BUKA' atau 'TUTUP' ke Arduino."""
        if not self.is_connected():
            print(f"⚠️ Peringatan: Arduino tidak terhubung. Perintah '{command}' tidak dikirim.")
            return

        try:
            if command == "BUKA":
                self.arduino.write(b'B')
                print("✅ [PYTHON] Perintah BUKA dikirim ke Arduino.")
            elif command == "TUTUP":
                self.arduino.write(b'T')
                print("✅ [PYTHON] Perintah TUTUP dikirim ke Arduino.")
        except Exception as e:
            print(f"❌ Gagal mengirim perintah ke Arduino: {e}")

    def read_line(self):
        """Membaca data baris dari Arduino jika tersedia."""
        if self.is_connected() and self.arduino.in_waiting > 0:
            try:
                return self.arduino.readline().decode('utf-8').strip()
            except Exception as e:
                print(f"❌ Gagal membaca dari Arduino: {e}")
        return None

    def close(self):
        """Menutup koneksi serial."""
        if self.is_connected():
            self.arduino.close()
            print("✅ Koneksi Arduino ditutup.")
