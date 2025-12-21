import sqlite3
import os

DB_PATH = 'camping.db'

def reset_log():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("🧹 Membersihkan tabel riwayat yang error...")
    try:
        # Hapus semua isi tabel riwayat
        cursor.execute("DELETE FROM riwayat")

        # Reset counter ID kembali ke 1
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='riwayat'")

        conn.commit()
        print("✅ Tabel Riwayat sudah BERSIH. Error 'pyarrow' harusnya hilang.")
    except Exception as e:
        print(f"❌ Gagal: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    reset_log()