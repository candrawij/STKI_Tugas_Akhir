import pandas as pd
import os
import sys

# Pastikan Python bisa menemukan folder Asisten
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from Asisten.smart_search import SmartSearchEngine
except ImportError as e:
    print(f"❌ Error Import: {e}")
    sys.exit()

def run_test():
    print("⏳ Sedang memuat AI Engine (Tunggu sebentar)...")
    engine = SmartSearchEngine()
    
    if not engine.is_ready:
        print("❌ Engine gagal dimuat. Cek database atau model Word2Vec.")
        return

    print("✅ Engine SIAP! Memulai pengujian...\n")

    # DAFTAR QUERY YANG AKAN DIUJI
    # Kita uji kasus-kasus yang kemarin bermasalah
    test_queries = [
        "kamar mandi bersih",  # Uji: Apakah review "kotor" masih muncul?
        "tempat angker",       # Uji: Apakah tempat biasa (non-seram) masih dapat skor tinggi?
        "pemandangan bagus",   # Uji: Kualitas umum
        "jogja",               # Uji: Filter wilayah (Harusnya tidak ada Semarang/Jateng)
        "jawa tengah",         # Uji: Filter wilayah (Harusnya tidak ada Jogja/Sleman)
        "tidak rekomen",       # Uji: Sentimen negatif
        "semua tempat"         # Uji: Intent ALL
    ]

    for query in test_queries:
        print("="*60)
        print(f"🔎 QUERY: '{query}'")
        print("="*60)
        
        # Cari Top 5 saja biar tidak kepanjangan
        df = engine.search(query, top_k=5)
        
        if df.empty:
            print("⚠️ Tidak ditemukan hasil (DataFrame Kosong).")
        else:
            for i, row in df.iterrows():
                nama = row['Nama Tempat']
                skor = row['Skor Relevansi']
                lokasi = row['Lokasi']
                # Ambil 150 karakter pertama ulasan
                ulasan = str(row['Isi Ulasan']).replace('\n', ' ')[:150] + "..."
                
                print(f"[{i+1}] {nama}")
                print(f"    ⭐ Skor AI : {skor}%")
                print(f"    📍 Lokasi  : {lokasi}")
                print(f"    💬 Ulasan  : \"{ulasan}\"")
                print("-" * 40)
        
        print("\n")

if __name__ == "__main__":
    run_test()