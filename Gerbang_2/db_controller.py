import mysql.connector
from mysql.connector import Error
import config

class DatabaseManager:
    def __init__(self):
        """Inisialisasi dan coba hubungkan ke database."""
        self.connection = None
        self.cursor = None
        try:
            self.connection = mysql.connector.connect(
                host=config.DB_HOST,
                user=config.DB_USER,
                password=config.DB_PASSWORD,
                database=config.DB_NAME
            )
            self.cursor = self.connection.cursor()
            print(f"✅ Berhasil terhubung ke database MySQL '{config.DB_NAME}'")
        except Error as e:
            print(f"❌ Error saat menghubungkan ke MySQL: {e}")
            exit()

    def is_plate_exist(self, nomor_plat):
        """
        Mengecek apakah plat nomor sudah ada di database.
        Ini adalah fungsi yang paling penting untuk diperbaiki.
        """
        if not self.cursor:
            print("❌ (DB) Tidak ada kursor, pengecekan plat gagal.")
            return False
        
        try:
            query = f"SELECT 1 FROM {config.DB_TABLE} WHERE nomor_plat = %s LIMIT 1"
            self.cursor.execute(query, (nomor_plat,))
            result = self.cursor.fetchone()
            
            return result is not None
        
        except Error as e:
            print(f"❌ (DB) Error saat mengecek plat: {e}")
            return False

    def save_plate(self, entry_time, plate_number):
        """Menyimpan data plat baru ke database."""
        try:
            query = f"INSERT INTO {config.DB_TABLE} (waktu_masuk, nomor_plat) VALUES (%s, %s)"
            self.cursor.execute(query, (entry_time, plate_number))
            self.connection.commit()
            print(f"✅ Data plat '{plate_number}' berhasil disimpan.")
        except Error as e:
            print(f"❌ Error saat menyimpan plat: {e}")

    def close(self):
        """Menutup koneksi database."""
        if self.connection and self.connection.is_connected():
            self.cursor.close()
            self.connection.close()
            print("✅ Koneksi database ditutup.")
