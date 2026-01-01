import sqlite3
import pandas as pd
import os
import json
import hashlib
from datetime import datetime

# Path Database
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'camping.db')

class DBHandler:
    def __init__(self):
        self.db_path = DB_PATH
        self.init_tables()

    def get_connection(self):
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def init_tables(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 1. Tabel Users
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT DEFAULT 'user',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 2. Tabel Bookings
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                tempat_id INTEGER,
                tanggal_checkin TEXT,
                jumlah_orang INTEGER,
                total_harga REAL,
                status TEXT DEFAULT 'PENDING',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(tempat_id) REFERENCES tempat(id)
            )
        ''')
        
        # 3. Tabel Riwayat (SESUAI REQUEST ANDA)
        # Kolom: id, waktu, query_user, jumlah_hasil, durasi_detik
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS riwayat (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                waktu TEXT,
                query_user TEXT,
                jumlah_hasil INTEGER,
                durasi_detik REAL DEFAULT 0.0
            )
        ''')
        
        # Seed Admin jika belum ada
        try:
            cursor.execute("SELECT * FROM users WHERE username='admin'")
            if not cursor.fetchone():
                h_pw = hashlib.sha256("admin123".encode()).hexdigest()
                cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", 
                               ('admin', h_pw, 'admin'))
        except: pass
        
        conn.commit()
        conn.close()

    # ================= LOGGING PENCARIAN (PERBAIKAN UTAMA) =================
    
    def log_search(self, query, count, duration=0.0):
        """Mencatat history pencarian ke database"""
        conn = self.get_connection()
        try:
            # Gunakan kolom 'query_user' dan 'durasi_detik'
            conn.execute(
                "INSERT INTO riwayat (waktu, query_user, jumlah_hasil, durasi_detik) VALUES (?, ?, ?, ?)", 
                (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), query, count, duration)
            )
            conn.commit()
        except Exception as e:
            print(f"❌ Gagal Log Search: {e}")
        finally:
            conn.close()

    def get_search_history(self, limit=50):
        conn = self.get_connection()
        try:
            # Select kolom yang benar
            df = pd.read_sql_query(f"SELECT waktu, query_user as query, jumlah_hasil, durasi_detik FROM riwayat ORDER BY id DESC LIMIT {limit}", conn)
            return df
        except:
            return pd.DataFrame()
        finally:
            conn.close()

    # ================= TEMPAT & DETAIL =================
    def get_place_by_name(self, name):
        conn = self.get_connection()
        res = conn.execute("SELECT id FROM tempat WHERE nama LIKE ? LIMIT 1", (f"%{name}%",)).fetchone()
        conn.close()
        return res[0] if res else None

    def get_place_details(self, place_id):
        conn = self.get_connection()
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        info = c.execute("SELECT * FROM tempat WHERE id = ?", (place_id,)).fetchone()
        info = dict(info) if info else {}
        
        # Ambil detail harga (Coba parsing JSON jika tabel harga kosong/error)
        harga = []
        try:
            if info.get('harga_json'): harga = json.loads(info['harga_json'])
        except: pass
        
        # Ambil detail fasilitas
        fasilitas = []
        if info.get('fasilitas'): fasilitas = [f.strip() for f in info['fasilitas'].split(',')]
        
        conn.close()
        return {"info": info, "harga": harga, "fasilitas": fasilitas}

    # ================= USER & BOOKING =================
    def register_user(self, username, password):
        conn = self.get_connection()
        try:
            h_pw = hashlib.sha256(password.encode()).hexdigest()
            conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, h_pw))
            conn.commit()
            return True, "Sukses"
        except: return False, "Username sudah ada"
        finally: conn.close()

    def verify_login(self, username, password):
        conn = self.get_connection()
        h_pw = hashlib.sha256(password.encode()).hexdigest()
        user = conn.execute("SELECT id, username, role FROM users WHERE username=? AND password=?", (username, h_pw)).fetchone()
        conn.close()
        if user: return {"id": user[0], "username": user[1], "role": user[2]}
        return None

    def add_booking(self, uid, pid, tgl, qty, tot):
        conn = self.get_connection()
        try:
            conn.execute("INSERT INTO bookings (user_id, tempat_id, tanggal_checkin, jumlah_orang, total_harga) VALUES (?, ?, ?, ?, ?)", 
                         (uid, pid, tgl, qty, tot))
            conn.commit()
            return True
        except: return False
        finally: conn.close()

    def get_user_bookings(self, uid):
        conn = self.get_connection()
        q = "SELECT b.id, t.nama, b.tanggal_checkin, b.total_harga, b.status, b.jumlah_orang FROM bookings b JOIN tempat t ON b.tempat_id = t.id WHERE b.user_id = ? ORDER BY b.id DESC"
        df = pd.read_sql_query(q, conn, params=(uid,))
        conn.close()
        return df

    def get_all_bookings_admin(self):
        conn = self.get_connection()
        q = "SELECT b.id, u.username, t.nama, b.tanggal_checkin, b.total_harga, b.status FROM bookings b JOIN users u ON b.user_id = u.id JOIN tempat t ON b.tempat_id = t.id ORDER BY b.id DESC"
        df = pd.read_sql_query(q, conn)
        conn.close()
        return df

    def update_booking_status(self, bid, status):
        conn = self.get_connection()
        conn.execute("UPDATE bookings SET status = ? WHERE id = ?", (status, bid))
        conn.commit()
        conn.close()

db = DBHandler()