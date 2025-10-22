import cv2
import time
import datetime
import config
import customtkinter as ctk
from PIL import Image, ImageTk
import threading

from iot_controller import ArduinoController
from db_controller import DatabaseManager
from vision_processor import VisionProcessor

class ParkingSystemApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("🚗 Sistem Parkir Cerdas Gerbang Masuk")
        self.geometry("1400x800")
        
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        self.arduino = ArduinoController()
        self.db = DatabaseManager()
        self.vision = VisionProcessor()
        
        self.sistem_status = "MENUNGGU"
        self.kandidat_plat = {} 
        self.waktu_mulai_pengumpulan = 0
        self.plat_terbaik = None
        
        self.is_running = False
        
        self.setup_ui()
        
        self.cap = None
        
    def setup_ui(self):
        self.grid_columnconfigure(0, weight=2)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        self.left_frame = ctk.CTkFrame(self, corner_radius=15)
        self.left_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.left_frame.grid_rowconfigure(1, weight=1)
        self.left_frame.grid_columnconfigure(0, weight=1)
        
        self.video_header = ctk.CTkLabel(
            self.left_frame, 
            text="📹 Live Camera",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        self.video_header.grid(row=0, column=0, pady=(20, 10), padx=20, sticky="w")
        
        self.video_label = ctk.CTkLabel(self.left_frame, text="")
        self.video_label.grid(row=1, column=0, pady=10, padx=20, sticky="nsew")
        
        self.status_frame = ctk.CTkFrame(self.left_frame, corner_radius=10, fg_color="#1f538d")
        self.status_frame.grid(row=2, column=0, pady=(0, 20), padx=20, sticky="ew")
        
        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text="STATUS: MENUNGGU",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#ffffff"
        )
        self.status_label.pack(pady=15)
        
        self.right_frame = ctk.CTkFrame(self, corner_radius=15)
        self.right_frame.grid(row=0, column=1, padx=(0, 20), pady=20, sticky="nsew")
        self.right_frame.grid_rowconfigure(2, weight=1) # Beri bobot pada log
        
        self.control_header = ctk.CTkLabel(
            self.right_frame,
            text="⚙️ Kontrol & Informasi",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.control_header.pack(pady=(20, 10), padx=20, anchor="w")
        
        self.start_button = ctk.CTkButton(
            self.right_frame,
            text="▶️ START SISTEM",
            command=self.toggle_system,
            font=ctk.CTkFont(size=16, weight="bold"),
            height=50,
            corner_radius=10,
            fg_color="#2fa572",
            hover_color="#1e7f4f"
        )
        self.start_button.pack(pady=10, padx=20, fill="x")
        
        self.info_frame = ctk.CTkFrame(self.right_frame, corner_radius=10)
        self.info_frame.pack(pady=20, padx=20, fill="x")
        
        ctk.CTkLabel(
            self.info_frame,
            text="🚘 Plat Terdeteksi (Hasil Akhir)",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=(15, 5))
        
        self.plat_label = ctk.CTkLabel(
            self.info_frame,
            text="---",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color="#3a7ebf"
        )
        self.plat_label.pack(pady=(5, 15))
        
       
        self.log_frame = ctk.CTkFrame(self.right_frame, corner_radius=10)
        self.log_frame.pack(pady=10, padx=20, fill="both", expand=True)
        
        ctk.CTkLabel(
            self.log_frame,
            text="📝 Log Aktivitas",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=(15, 10))
        
        self.log_text = ctk.CTkTextbox(
            self.log_frame,
            font=ctk.CTkFont(size=11),
            corner_radius=8
        )
        self.log_text.pack(pady=(0, 15), padx=15, fill="both", expand=True)
        
    def log_message(self, message):
        """Menambahkan pesan ke log"""
        try:
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            self.log_text.insert("end", f"[{timestamp}] {message}\n")
            self.log_text.see("end")
        except Exception as e:
            print(f"Error logging: {e}") 

    

    def toggle_system(self):
        """Start/Stop sistem"""
        if not self.is_running:
            self.start_system()
        else:
            self.stop_system()
            
    def start_system(self):
        """Memulai sistem"""
        self.cap = cv2.VideoCapture(config.SOURCE_PATH)
        if not self.cap.isOpened():
            self.log_message(f"❌ Gagal membuka kamera di path: {config.SOURCE_PATH}")
            return
            
        self.is_running = True
        self.start_button.configure(
            text="⏸️ STOP SISTEM",
            fg_color="#d32f2f",
            hover_color="#9a0007"
        )
        self.log_message("🚀 Sistem dimulai!")
        
        self.processing_thread = threading.Thread(target=self.process_video, daemon=True)
        self.processing_thread.start()
        
    def stop_system(self):
        """Menghentikan sistem"""
        self.is_running = False
        if self.cap:
            self.cap.release()
        self.start_button.configure(
            text="▶️ START SISTEM",
            fg_color="#2fa572",
            hover_color="#1e7f4f"
        )
        self.log_message("⏹️ Sistem dihentikan!")
        
    def process_video(self):
        """Proses video dan logika utama (VERSI THREAD-SAFE)"""
        while self.is_running:
            try:
                success, frame = self.cap.read()
                if not success:
                    self.after(0, self.log_message, "❌ Gagal membaca frame. Menghentikan...")
                    break
                    
                signal = self.arduino.read_line()
                if signal:
                    self.after(0, self.log_message, f"ℹ️ Sinyal: {signal}")
                    
                    if signal == "SENSOR1_AKTIF" and self.sistem_status == "MENUNGGU":
                        self.after(0, self.log_message, "🔥 SENSOR 1 AKTIF! Memulai pengumpulan data...")
                        self.sistem_status = "MENGUMPULKAN"
                        self.kandidat_plat.clear()
                        self.waktu_mulai_pengumpulan = time.time()
                        self.after(0, self.status_label.configure, text="STATUS: MENGUMPULKAN DATA")
                        
                    elif signal == "SENSOR2_AKTIF":
                        self.arduino.send_command("TUTUP")
                        self.after(0, self.log_message, "🚪 Gerbang ditutup (Sensor 2 aktif)")
                        
                if self.sistem_status == "MENGUMPULKAN":
                    plat_terbaca = self.vision.extract_plate_from_frame(frame)
                    if plat_terbaca:
                        self.kandidat_plat[plat_terbaca] = self.kandidat_plat.get(plat_terbaca, 0) + 1
                        
                        if self.kandidat_plat[plat_terbaca] >= config.CONFIRMATION_COUNT:
                            self.plat_terbaik = plat_terbaca
                            self.sistem_status = "ANALISIS"
                            
                    if time.time() - self.waktu_mulai_pengumpulan > config.DURASI_PENGUMPULAN and self.sistem_status == "MENGUMPULKAN":
                        if self.kandidat_plat:
                            self.plat_terbaik = max(self.kandidat_plat, key=self.kandidat_plat.get)
                        else:
                            self.plat_terbaik = None
                        self.sistem_status = "ANALISIS"
                        
                elif self.sistem_status == "ANALISIS":
                    self.after(0, self.status_label.configure, text="STATUS: MENGANALISIS")
                    
                    if self.plat_terbaik:
                        self.after(0, self.plat_label.configure, text=self.plat_terbaik)
                        self.after(0, self.log_message, f"📈 Plat terpilih: {self.plat_terbaik}")
                        
                        if not self.db.is_plate_exist(self.plat_terbaik):
                            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            self.db.save_plate(timestamp, self.plat_terbaik)
                            self.arduino.send_command("BUKA")
                            self.after(0, self.log_message, f"✅ Plat {self.plat_terbaik} disimpan. Gerbang dibuka!")
                        else:
                            self.after(0, self.log_message, f"⚠️ DUPLIKAT! {self.plat_terbaik} sudah ada.")
                    else:
                        self.after(0, self.log_message, "❌ Tidak ada plat valid terdeteksi.")
                        
                    self.sistem_status = "MENUNGGU"
                    self.after(0, self.status_label.configure, text="STATUS: MENUNGGU")
                    self.after(0, self.plat_label.configure, text="---")
                    
              
                self.after(0, self.update_frame, frame)
                
                time.sleep(0.03) 
            
            except Exception as e:
                try:
                    self.after(0, self.log_message, f"ERROR di process_video: {e}")
                except:
                    print(f"ERROR di process_video: {e}")
                time.sleep(1)
                
    def update_frame(self, frame):
        """Update tampilan video"""
        try:
            frame_resized = cv2.resize(frame, (800, 600))
            frame_rgb = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)
            
            img = Image.fromarray(frame_rgb)
            imgtk = ImageTk.PhotoImage(image=img)
            
            self.video_label.imgtk = imgtk
            self.video_label.configure(image=imgtk)
        except Exception as e:
            pass
        
    def on_closing(self):
        """Handler saat aplikasi ditutup"""
        self.log_message("👋 Menutup aplikasi...")
        self.stop_system()
        self.arduino.close()
        self.db.close()
        self.destroy()

def main():
    """Fungsi utama untuk menjalankan aplikasi GUI"""
    app = ParkingSystemApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()

if __name__ == "__main__":
    main()