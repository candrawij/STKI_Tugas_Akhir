import pandas as pd
import os
import joblib
import multiprocessing
import json
import ast # Library untuk baca string list "[...]" dengan aman
import logging
from gensim.models import Word2Vec
from src.preprocessing import full_preprocessing

# ================= KONFIGURASI =================
logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR = os.path.join(BASE_DIR, 'Documents')
ASSETS_DIR = os.path.join(BASE_DIR, 'Assets')

CORPUS_PATH = os.path.join(DOCS_DIR, 'corpus_master.csv')
INFO_PATH = os.path.join(DOCS_DIR, 'info_tempat.csv') # <--- File Foto/Harga

def parse_price_safe(price_str):
    """Mengubah string "[{'item':...}]" menjadi List Python asli."""
    try:
        if pd.isna(price_str) or price_str == "":
            return []
        # Jika sudah berupa list, kembalikan
        if isinstance(price_str, list):
            return price_str
        # Parsing string menjadi struktur data (list/dict)
        return ast.literal_eval(str(price_str))
    except:
        return []

def train_model():
    print("\n" + "="*60)
    print("🚀 MEMULAI TRAINING MODEL & INTEGRASI DATA")
    print("="*60)

    # 1. LOAD CORPUS (ULASAN)
    if not os.path.exists(CORPUS_PATH):
        print(f"❌ Error: Corpus tidak ditemukan di {CORPUS_PATH}")
        return

    print("📖 Membaca Ulasan (Corpus)...")
    df_corpus = pd.read_csv(CORPUS_PATH)
    df_corpus['Teks_Mentah'] = df_corpus['Teks_Mentah'].fillna('')
    
    # 2. TRAINING AI (Word2Vec)
    print("🧹 Preprocessing Teks...")
    tokenized_sentences = df_corpus['Teks_Mentah'].apply(full_preprocessing).tolist()
    tokenized_sentences = [s for s in tokenized_sentences if len(s) > 0]
    
    print(f"🧠 Melatih AI dengan {len(tokenized_sentences)} kalimat...")
    model = Word2Vec(
        vector_size=10,      # KECILKAN: Dari 100 ke 10. Agar dia fokus ke inti makna saja.
        window=3,            # PERSEMPIT: Dari 5 ke 3. Agar dia fokus ke kata tetangga terdekat.
        min_count=2,         # FILTER: Hanya pelajari kata yang muncul MINIMAL 2 kali (buang typo unik).
        workers=multiprocessing.cpu_count(), 
        sg=1, 
        epochs=200           # TINGKATKAN: Dari 50 ke 200. Suruh dia baca berulang-ulang sampai paham.
    )
    model.build_vocab(tokenized_sentences)
    model.train(tokenized_sentences, total_examples=model.corpus_count, epochs=50)
    
    os.makedirs(ASSETS_DIR, exist_ok=True)
    model.save(os.path.join(ASSETS_DIR, "word2vec.model"))
    print("✅ Model AI disimpan.")

    # ==========================================================
    # 3. MEMBANGUN METADATA (GABUNGAN AI + INFO MANUAL)
    # ==========================================================
    print("\n📦 Menggabungkan Data Foto & Harga...")
    
    # A. Hitung Rating Rata-rata dari Corpus
    avg_ratings = df_corpus.groupby('Nama_Tempat')['Rating'].mean().reset_index()
    avg_ratings.rename(columns={'Rating': 'Avg_Rating'}, inplace=True)
    
    # B. Ambil Lokasi (Baris pertama per tempat)
    df_locations = df_corpus.drop_duplicates(subset='Nama_Tempat')[['Nama_Tempat', 'Lokasi']]
    
    # C. Gabungkan (Base Metadata)
    df_meta_final = df_locations.merge(avg_ratings, on='Nama_Tempat', how='left')
    
    # D. INTEGRASI FILE INFO_TEMPAT.CSV (FOTO & HARGA)
    if os.path.exists(INFO_PATH):
        print("   📂 Ditemukan file 'info_tempat.csv', membaca data...")
        df_info = pd.read_csv(INFO_PATH)
        
        # Pastikan kolom kunci (Nama_Tempat) bertipe string & bersih
        df_info['Nama_Tempat'] = df_info['Nama_Tempat'].str.strip()
        df_meta_final['Nama_Tempat'] = df_meta_final['Nama_Tempat'].str.strip()
        
        # Gabungkan (Merge)
        # Kita gunakan Left Join: Semua tempat di Corpus tetap ada, 
        # kalau di Info ada datanya, kita ambil.
        df_meta_final = df_meta_final.merge(
            df_info[['Nama_Tempat', 'Photo_URL', 'Gmaps_Link', 'Facilities', 'Price_Items', 'Waktu_Buka']], 
            on='Nama_Tempat', 
            how='left'
        )
        
        # E. Parsing Kolom Harga (PENTING!)
        if 'Price_Items' in df_meta_final.columns:
            df_meta_final['Price_Items'] = df_meta_final['Price_Items'].apply(parse_price_safe)
            
        print(f"   ✅ Berhasil menggabungkan info untuk {len(df_info)} tempat.")
        
    else:
        print("⚠️ WARNING: 'info_tempat.csv' tidak ditemukan. Foto/Harga akan kosong.")
        # Isi default jika file tidak ada
        df_meta_final['Photo_URL'] = ""
        df_meta_final['Price_Items'] = [[] for _ in range(len(df_meta_final))]
        df_meta_final['Facilities'] = ""
        df_meta_final['Waktu_Buka'] = "Info belum tersedia"

    # Isi NaN (Kosong) dengan default
    df_meta_final['Photo_URL'] = df_meta_final['Photo_URL'].fillna('https://via.placeholder.com/400x300?text=No+Image')
    df_meta_final['Facilities'] = df_meta_final['Facilities'].fillna('Fasilitas standar')
    df_meta_final['Waktu_Buka'] = df_meta_final['Waktu_Buka'].fillna('Cek Gmaps')
    
    # Simpan
    df_meta_final.set_index('Nama_Tempat', inplace=True)
    joblib.dump(df_meta_final, os.path.join(ASSETS_DIR, "df_metadata.pkl"))
    
    print("🎉 SELESAI! Metadata baru siap digunakan.")

if __name__ == "__main__":
    train_model()