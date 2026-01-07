import pandas as pd
import sqlite3
import os
import ast
import csv
import sys

# --- SETUP PATH ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CURRENT_DIR)
sys.path.append(ROOT_DIR)

# CONFIG
DOCS_DIR = os.path.join(ROOT_DIR, 'Documents')
RIWAYAT_DIR = os.path.join(ROOT_DIR, 'Riwayat')
DB_PATH = os.path.join(ROOT_DIR, 'camping.db')

FILE_INFO_TEMPAT = os.path.join(DOCS_DIR, 'info_tempat.csv')
FILE_CORPUS_MASTER = os.path.join(DOCS_DIR, 'corpus_master.csv')
FILE_INPUT_HARGA = os.path.join(DOCS_DIR, 'input_harga.csv')
FILE_INPUT_FASILITAS = os.path.join(DOCS_DIR, 'input_fasilitas.csv')
FILE_RIWAYAT = os.path.join(RIWAYAT_DIR, 'riwayat_pencarian.csv') 

NAME_TO_ID_MAP = {}

def get_db_connection(): return sqlite3.connect(DB_PATH)
def standardize_name(name): return str(name).strip().title()

def upsert_place(cursor, nama, lokasi="-", rating=0.0, gmaps="", photo="", buka=""):
    nama_clean = standardize_name(nama)
    if "Kaliurip Mount" in nama_clean: nama_clean = "Gunung Cilik Kaliurip"
    if "Gunung Cilik Kaliurip Wonosobo" in nama_clean: nama_clean = "Gunung Cilik Kaliurip"

    cursor.execute("SELECT id, lokasi, rating_gmaps FROM tempat WHERE nama = ?", (nama_clean,))
    res = cursor.fetchone()
    
    if res:
        place_id, db_lokasi, db_rating = res
        update_query, update_vals = [], []
        if (db_lokasi=="-" or db_lokasi=="") and (lokasi!="-" and lokasi!=""): update_query.append("lokasi = ?"); update_vals.append(lokasi)
        if (db_rating==0.0) and (rating>0.0): update_query.append("rating_gmaps = ?"); update_vals.append(rating)
        if gmaps: update_query.append("gmaps_link = ?"); update_vals.append(gmaps)
        if photo: update_query.append("photo_url = ?"); update_vals.append(photo)
        if buka: update_query.append("waktu_buka = ?"); update_vals.append(buka)

        if update_query:
            sql = f"UPDATE tempat SET {', '.join(update_query)} WHERE id = ?"
            update_vals.append(place_id)
            cursor.execute(sql, tuple(update_vals))
        NAME_TO_ID_MAP[nama_clean] = place_id
        return place_id
    else:
        try:
            cursor.execute('INSERT INTO tempat (nama, lokasi, rating_gmaps, gmaps_link, photo_url, waktu_buka) VALUES (?, ?, ?, ?, ?, ?)', (nama_clean, lokasi, rating, gmaps, photo, buka))
            place_id = cursor.lastrowid
            NAME_TO_ID_MAP[nama_clean] = place_id
            return place_id
        except sqlite3.IntegrityError: return None

def migrate_data():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA synchronous = OFF")

    print("\n🚀 TAHAP 1: Migrasi Data TEMPAT (Master)...")
    if os.path.exists(FILE_INFO_TEMPAT):
        df = pd.read_csv(FILE_INFO_TEMPAT).fillna("")
        for _, row in df.iterrows():
            upsert_place(cursor, row.get('Nama_Tempat'), gmaps=row.get('Gmaps_Link', ''), photo=row.get('Photo_URL', ''), buka=row.get('Waktu_Buka', ''))
            p_id = NAME_TO_ID_MAP.get(standardize_name(row.get('Nama_Tempat')))
            if p_id and row.get('Price_Items'):
                try:
                    items = ast.literal_eval(row['Price_Items'])
                    if isinstance(items, list):
                        if cursor.execute("SELECT COUNT(*) FROM harga WHERE tempat_id=?", (p_id,)).fetchone()[0] == 0:
                            for it in items: cursor.execute("INSERT INTO harga (tempat_id, item, harga, kategori) VALUES (?, ?, ?, ?)", (p_id, it.get('item',''), it.get('harga',0), 'Umum'))
                except: pass

    print("\n🚀 TAHAP 2: Migrasi ULASAN...")
    if os.path.exists(FILE_CORPUS_MASTER):
        df = pd.read_csv(FILE_CORPUS_MASTER).fillna("")
        count = 0
        for _, row in df.iterrows():
            p_id = upsert_place(cursor, row.get('Nama_Tempat'), lokasi=row.get('Lokasi', '-'), rating=row.get('Rating', 0.0))
            if p_id:
                raw = row.get('Teks_Mentah', '')
                try: ur = int(float(row.get('Rating', 0)))
                except: ur = 0
                cursor.execute('INSERT INTO ulasan (tempat_id, rating_user, teks_mentah, teks_bersih, waktu_ulasan, tanggal_scrap) VALUES (?, ?, ?, ?, ?, ?)', (p_id, ur, raw, str(raw).lower(), row.get('Waktu'), row.get('Tanggal_Scrap', None)))
                count += 1
                if count % 2000 == 0: print(f"      ⏳ {count}...")

    print("\n🚀 TAHAP 3: Data Harga & Fasilitas Manual...")
    if os.path.exists(FILE_INPUT_HARGA):
        df_hrg = pd.read_csv(FILE_INPUT_HARGA).fillna("")
        p_ids = set()
        for _, row in df_hrg.iterrows():
            p_id = upsert_place(cursor, row.get('Nama_Tempat'))
            if p_id:
                if p_id not in p_ids: cursor.execute("DELETE FROM harga WHERE tempat_id = ?", (p_id,)); p_ids.add(p_id)
                cursor.execute("INSERT INTO harga (tempat_id, item, harga, kategori) VALUES (?, ?, ?, ?)", (p_id, row.get('item'), row.get('harga', 0), row.get('kategori', '')))

    if os.path.exists(FILE_INPUT_FASILITAS):
        df_fas = pd.read_csv(FILE_INPUT_FASILITAS).fillna("")
        for _, row in df_fas.iterrows():
            p_id = upsert_place(cursor, row.get('Nama_Tempat'))
            if p_id: cursor.execute("INSERT INTO fasilitas (tempat_id, nama_fasilitas) VALUES (?, ?)", (p_id, row.get('Fasilitas')))

    # --- TAHAP 4: RIWAYAT (MAPPING BENAR) ---
    print("\n🚀 TAHAP 4: Migrasi Riwayat Pencarian...")
    if os.path.exists(FILE_RIWAYAT):
        try:
            with open(FILE_RIWAYAT, 'r', encoding='utf-8', errors='replace') as f:
                reader = csv.DictReader(f)
                count_riwayat = 0
                for row in reader:
                    # Mapping CSV -> DB
                    waktu = row.get('timestamp')
                    q_user = row.get('query_mentah')
                    intent = row.get('intent_terdeteksi')
                    region = row.get('region_terdeteksi')
                    
                    # Bersihkan 'None' string
                    if str(intent).lower() == 'none': intent = None
                    if str(region).lower() == 'none': region = None
                    
                    if waktu and q_user:
                        # query_bersih bisa kita isi dengan query user yang sudah di-lowercase jika intent kosong
                        q_clean = q_user.lower()
                        
                        cursor.execute("""
                            INSERT INTO riwayat (waktu, query_user, query_bersih, intent, region, jumlah_hasil) 
                            VALUES (?, ?, ?, ?, ?, 0)
                        """, (waktu, q_user, q_clean, intent, region))
                        count_riwayat += 1
            print(f"   📜 Berhasil: {count_riwayat} log pencarian.")
        except Exception as e: print(f"   ⚠️ Gagal baca riwayat: {e}")
    else: print("   ⚠️ File riwayat_pencarian.csv tidak ditemukan.")

    conn.commit(); conn.close()
    print("\n✅ SEMUA MIGRASI SELESAI.")

if __name__ == "__main__":
    try:
        from Asisten.db_handler import db
        db.init_tables()
    except: pass
    migrate_data()