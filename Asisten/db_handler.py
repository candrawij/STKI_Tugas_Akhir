import sqlite3
import pandas as pd
import os
import json
import hashlib
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'camping.db')

class DBHandler:
    def __init__(self):
        self.db_path = DB_PATH
        self.init_tables()

    def get_connection(self):
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def init_tables(self):
        try:
            import sys
            sys.path.append(os.path.join(BASE_DIR, 'scripts'))
            import setup_db
            setup_db.create_tables()
        except:
            pass # Fallback handled by setup_db if available

    # ================= LOGGING PENCARIAN =================
    def log_search(self, query, query_clean, count, top_result, duration=0.0, intent=None, region=None):
        conn = self.get_connection()
        try:
            conn.execute(
                """INSERT INTO riwayat 
                   (waktu, query_user, query_bersih, intent, region, jumlah_hasil, hasil_teratas, durasi_detik) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", 
                (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), query, query_clean, intent, region, count, top_result, duration)
            )
            conn.commit()
        except Exception as e: print(f"❌ Log Error: {e}")
        finally: conn.close()

    def get_search_history(self, limit=50):
        conn = self.get_connection()
        try:
            return pd.read_sql_query(f"SELECT waktu, query_user, intent, region, jumlah_hasil, hasil_teratas FROM riwayat ORDER BY id DESC LIMIT {limit}", conn)
        except: return pd.DataFrame()
        finally: conn.close()

    # ================= TEMPAT & DETAIL (PERBAIKAN UTAMA DI SINI) =================
    def get_place_by_name(self, name):
        conn = self.get_connection()
        res = conn.execute("SELECT id FROM tempat WHERE nama LIKE ? LIMIT 1", (f"%{name}%",)).fetchone()
        conn.close()
        return res[0] if res else None

    def get_place_details(self, place_id):
        conn = self.get_connection()
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        # 1. Info Utama
        info = c.execute("SELECT * FROM tempat WHERE id = ?", (place_id,)).fetchone()
        info = dict(info) if info else {}
        
        # 2. Ambil Harga dari Tabel 'harga' (PRIORITAS UTAMA)
        db_harga = c.execute("SELECT item, harga, kategori FROM harga WHERE tempat_id = ?", (place_id,)).fetchall()
        
        # Format ke List of Dict
        harga_list = [{"item": h['item'], "harga": h['harga'], "kategori": h['kategori']} for h in db_harga]
        
        # Fallback ke JSON hanya jika tabel kosong
        if not harga_list and info.get('harga_json'):
            try: harga_list = json.loads(info['harga_json'])
            except: pass
        
        # 3. Ambil Fasilitas dari Tabel 'fasilitas' (PRIORITAS UTAMA)
        db_fas = c.execute("SELECT nama_fasilitas FROM fasilitas WHERE tempat_id = ?", (place_id,)).fetchall()
        
        fasilitas_list = [f['nama_fasilitas'] for f in db_fas]
        
        # Fallback ke string fasilitas di tabel tempat
        if not fasilitas_list and info.get('fasilitas'):
            fasilitas_list = [f.strip() for f in info['fasilitas'].split(',')]
        
        conn.close()
        return {"info": info, "harga": harga_list, "fasilitas": fasilitas_list}

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
        df = pd.read_sql_query("SELECT b.id, t.nama, b.tanggal_checkin, b.total_harga, b.status, b.jumlah_orang FROM bookings b JOIN tempat t ON b.tempat_id = t.id WHERE b.user_id = ? ORDER BY b.id DESC", conn, params=(uid,))
        conn.close()
        return df

    def get_all_bookings_admin(self):
        conn = self.get_connection()
        df = pd.read_sql_query("SELECT b.id, u.username, t.nama, b.tanggal_checkin, b.total_harga, b.status FROM bookings b JOIN users u ON b.user_id = u.id JOIN tempat t ON b.tempat_id = t.id ORDER BY b.id DESC", conn)
        conn.close()
        return df

    def update_booking_status(self, bid, status):
        conn = self.get_connection()
        conn.execute("UPDATE bookings SET status = ? WHERE id = ?", (status, bid))
        conn.commit()
        conn.close()

db = DBHandler()