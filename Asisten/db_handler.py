import sqlite3
import pandas as pd
import os
import json
import hashlib
from datetime import datetime

# Path: Root Project/camping.db
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
        
        # Tabel Users
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT DEFAULT 'user',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabel Bookings
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                tempat_id INTEGER,
                tanggal_booking DATETIME DEFAULT CURRENT_TIMESTAMP,
                tanggal_checkin DATE,
                jumlah_orang INTEGER,
                total_harga REAL,
                status TEXT DEFAULT 'PENDING',
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(tempat_id) REFERENCES tempat(id)
            )
        ''')
        
        # Seed Admin (Jika belum ada)
        cursor.execute("SELECT * FROM users WHERE username='admin'")
        if not cursor.fetchone():
            h_pw = hashlib.sha256("admin123".encode()).hexdigest()
            cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", 
                           ('admin', h_pw, 'admin'))
        
        conn.commit()
        conn.close()

    # --- AUTHENTICATION ---
    def _hash(self, password):
        return hashlib.sha256(password.encode()).hexdigest()

    def register_user(self, username, password):
        conn = self.get_connection()
        try:
            conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", 
                         (username, self._hash(password)))
            conn.commit()
            return True, "Registrasi berhasil!"
        except sqlite3.IntegrityError:
            return False, "Username sudah digunakan."
        finally:
            conn.close()

    def verify_login(self, username, password):
        conn = self.get_connection()
        user = conn.execute("SELECT id, username, role FROM users WHERE username=? AND password=?", 
                            (username, self._hash(password))).fetchone()
        conn.close()
        if user:
            return {"id": user[0], "username": user[1], "role": user[2]}
        return None

    # --- DATA TEMPAT (HYBRID FETCH) ---
    def get_place_by_name(self, name):
        conn = self.get_connection()
        # COLLATE NOCASE agar pencarian tidak sensitif huruf besar/kecil
        res = conn.execute("SELECT id FROM tempat WHERE nama = ? COLLATE NOCASE LIMIT 1", (name,)).fetchone()
        conn.close()
        return res[0] if res else None

    def get_place_details(self, place_id):
        conn = self.get_connection()
        conn.row_factory = sqlite3.Row # Agar bisa akses kolom pakai nama
        c = conn.cursor()
        
        # 1. Ambil Info Dasar
        place = c.execute("SELECT * FROM tempat WHERE id = ?", (place_id,)).fetchone()
        if not place: 
            conn.close()
            return None
            
        info = dict(place)
        
        # 2. Ambil Harga (Coba Tabel Relasional dulu, kalau kosong coba JSON)
        prices = c.execute("SELECT item, harga, kategori FROM harga WHERE tempat_id = ?", (place_id,)).fetchall()
        price_list = [{"item": p['item'], "harga": p['harga'], "kategori": p['kategori']} for p in prices]
        
        if not price_list and info.get('harga_json'):
            try: price_list = json.loads(info['harga_json'])
            except: pass

        # 3. Ambil Fasilitas (Coba Tabel Relasional dulu, kalau kosong coba String)
        facs = c.execute("SELECT nama_fasilitas FROM fasilitas WHERE tempat_id = ?", (place_id,)).fetchall()
        fac_list = [f['nama_fasilitas'] for f in facs]
        
        if not fac_list and info.get('fasilitas'):
            fac_list = [f.strip() for f in info['fasilitas'].split(',')]

        conn.close()
        return {"info": info, "harga": price_list, "fasilitas": fac_list}

    # --- BOOKING SYSTEM ---
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
        q = """SELECT b.id, t.nama, b.tanggal_checkin, b.total_harga, b.status, b.jumlah_orang 
               FROM bookings b JOIN tempat t ON b.tempat_id = t.id 
               WHERE b.user_id = ? ORDER BY b.id DESC"""
        df = pd.read_sql_query(q, conn, params=(uid,))
        conn.close()
        return df

    def get_all_bookings_admin(self):
        conn = self.get_connection()
        q = """SELECT b.id, u.username, t.nama, b.tanggal_checkin, b.total_harga, b.status, b.created_at
               FROM bookings b 
               JOIN users u ON b.user_id = u.id 
               JOIN tempat t ON b.tempat_id = t.id 
               ORDER BY b.id DESC"""
        df = pd.read_sql_query(q, conn)
        conn.close()
        return df

    def update_booking_status(self, bid, status):
        conn = self.get_connection()
        conn.execute("UPDATE bookings SET status = ? WHERE id = ?", (status, bid))
        conn.commit()
        conn.close()

db = DBHandler()