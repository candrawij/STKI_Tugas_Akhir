import sqlite3
import os
import hashlib

# --- SETUP PATH ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CURRENT_DIR)
DB_PATH = os.path.join(ROOT_DIR, 'camping.db')

def create_tables():
    print(f"🔨 Membuat struktur database di: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Tabel TEMPAT (Master Data)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tempat (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nama TEXT UNIQUE NOT NULL,
            lokasi TEXT,
            rating_gmaps REAL DEFAULT 0.0,
            gmaps_link TEXT,
            photo_url TEXT,
            waktu_buka TEXT,
            deskripsi TEXT
        )
    ''')

    # 2. Tabel HARGA (Detail)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS harga (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tempat_id INTEGER,
            item TEXT,
            harga INTEGER,
            kategori TEXT,
            FOREIGN KEY(tempat_id) REFERENCES tempat(id) ON DELETE CASCADE
        )
    ''')

    # 3. Tabel FASILITAS (Detail)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fasilitas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tempat_id INTEGER,
            nama_fasilitas TEXT,
            FOREIGN KEY(tempat_id) REFERENCES tempat(id) ON DELETE CASCADE
        )
    ''')

    # 4. Tabel ULASAN (Corpus AI)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ulasan (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tempat_id INTEGER,
            rating_user INTEGER,
            teks_mentah TEXT,
            teks_bersih TEXT,
            waktu_ulasan TEXT,
            tanggal_scrap TEXT,
            FOREIGN KEY(tempat_id) REFERENCES tempat(id) ON DELETE CASCADE
        )
    ''')

    # 5. Tabel USERS (Auth)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 6. Tabel BOOKINGS (Transaksi)
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

    # 7. Tabel RIWAYAT (Smart Mapping)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS riwayat (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            waktu TEXT,
            query_user TEXT,        
            query_bersih TEXT,      
            intent TEXT,            
            region TEXT,            
            jumlah_hasil INTEGER,
            hasil_teratas TEXT,
            durasi_detik REAL DEFAULT 0.0
        )
    ''')

    # --- SEED DATA (Admin Default) ---
    try:
        cursor.execute("SELECT * FROM users WHERE username='admin'")
        if not cursor.fetchone():
            # Password default: admin123
            h_pw = hashlib.sha256("admin123".encode()).hexdigest()
            cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", 
                           ('admin', h_pw, 'admin'))
            print("👤 User 'admin' dibuat (Pass: admin123)")
    except Exception as e:
        print(f"⚠️ Gagal seed admin: {e}")

    conn.commit()
    conn.close()
    print("✅ Tabel Database Berhasil Dibuat/Diperbarui.")

if __name__ == "__main__":
    create_tables()