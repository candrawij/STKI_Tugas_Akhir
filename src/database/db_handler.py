import sqlite3
import pandas as pd
import os
import json
import hashlib # Library keamanan untuk mengacak password
from datetime import datetime

# Path Database
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'camping.db')

class DBHandler:
    def __init__(self):
        self.db_path = DB_PATH
        self.init_tables() # Jalankan pembuatan tabel setiap kali handler dipanggil

    def get_connection(self):
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def init_tables(self):
        """Membuat tabel jika belum ada (Upgrade Schema)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 1. Tabel Users (BARU)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT DEFAULT 'user',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 2. Tabel Bookings (BARU)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                tempat_id INTEGER,
                tanggal_checkin TEXT,
                jumlah_orang INTEGER,
                total_harga INTEGER,
                status TEXT DEFAULT 'CONFIRMED',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(tempat_id) REFERENCES tempat(id)
            )
        ''')
        
        # 3. Tabel Riwayat Pencarian (LAMA - TETAP ADA)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS riwayat (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                waktu TEXT,
                query TEXT,
                jumlah_hasil INTEGER
            )
        ''')
        
        conn.commit()
        conn.close()

    # ================= BAGIAN 1: FITUR PENCARIAN (LAMA) =================
    
    def log_search(self, query, count):
        conn = self.get_connection()
        conn.execute("INSERT INTO riwayat (waktu, query, jumlah_hasil) VALUES (?, ?, ?)", 
                     (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), query, count))
        conn.commit()
        conn.close()

    def get_search_history(self, limit=50):
        conn = self.get_connection()
        df = pd.read_sql_query(f"SELECT waktu, query, jumlah_hasil FROM riwayat ORDER BY id DESC LIMIT {limit}", conn)
        conn.close()
        return df

    def get_place_by_name(self, name):
        conn = self.get_connection()
        res = conn.execute("SELECT id FROM tempat WHERE nama = ? COLLATE NOCASE LIMIT 1", (name,)).fetchone()
        conn.close()
        return res[0] if res else None

    def get_place_details(self, place_id):
        conn = self.get_connection()
        cur = conn.cursor()
        
        # Info Utama
        place = cur.execute("SELECT * FROM tempat WHERE id = ?", (place_id,)).fetchone()
        cols = [description[0] for description in cur.description]
        info = dict(zip(cols, place)) if place else {}
        
        # Harga
        prices = cur.execute("SELECT item, harga, kategori FROM harga WHERE tempat_id = ?", (place_id,)).fetchall()
        price_list = [{"item": p[0], "harga": p[1], "kategori": p[2]} for p in prices]
        
        # Fasilitas
        # Ganti 'fasilitas' menjadi 'item' (atau nama kolom yang muncul di cek_db.py)
        facs = cur.execute("SELECT nama_fasilitas FROM fasilitas WHERE tempat_id = ?", (place_id,)).fetchall()
        fac_list = [f[0] for f in facs]
        
        conn.close()
        return {"info": info, "harga": price_list, "fasilitas": fac_list}

    # ================= BAGIAN 2: FITUR USER & BOOKING (BARU) =================

    def _hash_password(self, password):
        """Mengacak password agar tidak terbaca manusia (Security)"""
        return hashlib.sha256(password.encode()).hexdigest()

    def register_user(self, username, password):
        """Mendaftarkan user baru"""
        conn = self.get_connection()
        try:
            hashed_pw = self._hash_password(password)
            conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_pw))
            conn.commit()
            return True, "Registrasi berhasil! Silakan login."
        except sqlite3.IntegrityError:
            return False, "Username sudah dipakai, coba yang lain."
        except Exception as e:
            return False, f"Error: {e}"
        finally:
            conn.close()

    def verify_login(self, username, password):
        """Cek apakah username dan password cocok"""
        conn = self.get_connection()
        hashed_pw = self._hash_password(password)
        
        user = conn.execute("SELECT id, username, role FROM users WHERE username = ? AND password = ?", 
                            (username, hashed_pw)).fetchone()
        conn.close()
        
        if user:
            return {"id": user[0], "username": user[1], "role": user[2]} # Return data user
        return None # Login gagal

    def add_booking(self, user_id, tempat_id, tanggal, jum_orang, total_harga):
        conn = self.get_connection()
        try:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO bookings (user_id, tempat_id, tanggal_checkin, jumlah_orang, total_harga, status)
                VALUES (?, ?, ?, ?, ?, 'PENDING')
            """, (user_id, tempat_id, tanggal, jum_orang, total_harga))
            
            conn.commit()
            return True
        except Exception as e:
            print(f"Error add_booking: {e}")
            return False
        finally:
            conn.close()
            
    def get_user_bookings(self, user_id):
        """Ambil riwayat pesanan user tertentu"""
        conn = self.get_connection()
        query = """
            SELECT b.id, t.nama, b.tanggal_checkin, b.jumlah_orang, b.total_harga, b.status
            FROM bookings b
            JOIN tempat t ON b.tempat_id = t.id
            WHERE b.user_id = ?
            ORDER BY b.created_at DESC
        """
        df = pd.read_sql_query(query, conn, params=(user_id,))
        conn.close()
        return df

    # [BARU] Mengambil semua booking untuk Admin
    def get_all_bookings_admin(self):
        conn = self.get_connection()
        query = """
            SELECT b.id, u.username, t.nama, b.tanggal_checkin, b.jumlah_orang, b.total_harga, b.status, b.created_at
            FROM bookings b
            JOIN users u ON b.user_id = u.id
            JOIN tempat t ON b.tempat_id = t.id
            ORDER BY b.created_at DESC
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df

    # [BARU] Update status booking (Terima/Tolak)
    def update_booking_status(self, booking_id, new_status):
        conn = self.get_connection()
        try:
            conn.execute("UPDATE bookings SET status = ? WHERE id = ?", (new_status, booking_id))
            conn.commit()
            return True
        except Exception as e:
            print(f"Update Error: {e}")
            return False
        finally:
            conn.close()

# Instance Global
db = DBHandler()