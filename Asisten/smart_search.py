import pandas as pd
import numpy as np
import os
import re
from datetime import datetime
from gensim.models import Word2Vec
from sklearn.metrics.pairwise import cosine_similarity

# ================= KONFIGURASI PATH =================
# Mengambil folder Root project (Naik satu level dari folder Asisten)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Lokasi Model (Sesuai info Anda: di folder Assets)
MODEL_PATH = os.path.join(BASE_DIR, 'Assets', 'word2vec.model')

# Lokasi Database Utama
CORPUS_PATH = os.path.join(BASE_DIR, 'Documents', 'corpus_master.csv')

# ================= KONFIGURASI BOBOT =================
# Anda bisa mainkan angka ini sesuai selera
WEIGHT_SEMANTIC = 0.7  # 70% ditentukan oleh kecocokan kata (Relevansi)
WEIGHT_RECENCY = 0.3   # 30% ditentukan oleh seberapa baru ulasannya (Freshness)

class SmartSearchEngine:
    def __init__(self):
        self.model = None
        self.df = None
        self.doc_vectors = None
        self.is_ready = False
        
        self.load_resources()

    def load_resources(self):
        """Memuat Model AI dan Database"""
        print(f"⚙️ Memuat Smart Search Engine...")
        print(f"   📂 Model: {MODEL_PATH}")
        print(f"   📂 Data : {CORPUS_PATH}")
        
        # 1. Load Data CSV
        if os.path.exists(CORPUS_PATH):
            self.df = pd.read_csv(CORPUS_PATH)
            
            # Konversi kolom 'Waktu' jadi datetime agar bisa dihitung umurnya
            # Jika kolom Waktu belum ada (data lama), akan jadi NaT (Not a Time)
            if 'Waktu' in self.df.columns:
                self.df['Waktu'] = pd.to_datetime(self.df['Waktu'], errors='coerce')
            else:
                print("⚠️ Peringatan: Kolom 'Waktu' tidak ditemukan. Fitur recency akan mati.")
                self.df['Waktu'] = pd.NaT
                
            # Pastikan Teks_Mentah string
            self.df['Teks_Mentah'] = self.df['Teks_Mentah'].fillna("").astype(str)
            
        else:
            print(f"❌ Error: File {CORPUS_PATH} tidak ditemukan.")
            return

        # 2. Load Model Word2Vec
        if os.path.exists(MODEL_PATH):
            try:
                self.model = Word2Vec.load(MODEL_PATH)
                print("   ✅ Model Word2Vec berhasil dimuat.")
            except Exception as e:
                print(f"❌ Error memuat model: {e}")
                return
        else:
            print(f"❌ Error: Model tidak ditemukan di {MODEL_PATH}")
            return

        # 3. Pre-calculate Vectors (Agar pencarian ngebut)
        print("   ↳ Menghitung vektor dokumen (Caching)...")
        # Kita ubah semua ulasan menjadi vektor angka saat inisialisasi
        self.doc_vectors = np.array([self.get_vector(text) for text in self.df['Teks_Mentah']])
        
        self.is_ready = True
        print("🚀 Search Engine SIAP DIGUNAKAN!")

    def get_vector(self, text):
        """Mengubah kalimat menjadi rata-rata vektor kata"""
        if not self.model: return np.zeros(100) # Default size biasanya 100/300
        
        # Preprocessing sederhana agar cocok dengan vocab model
        words = str(text).lower().split()
        
        # Ambil vektor untuk kata yang dikenali model
        # self.model.wv adalah KeyedVectors
        word_vecs = [self.model.wv[w] for w in words if w in self.model.wv]
        
        if len(word_vecs) == 0:
            return np.zeros(self.model.vector_size)
            
        # Rata-rata vektor semua kata dalam kalimat
        return np.mean(word_vecs, axis=0)

    def calculate_recency_score(self, date_series):
        """
        Menghitung skor kebaruan (0.0 - 1.0) menggunakan Exponential Decay.
        Semakin lama tanggalnya, skornya turun perlahan.
        """
        today = datetime.now()
        
        # Hitung selisih hari dari sekarang
        days_diff = (today - date_series).dt.days
        
        # Jika tanggal kosong (NaT), anggap sudah tua sekali (misal 5 tahun/1825 hari)
        days_diff = days_diff.fillna(1825) 
        
        # Pastikan tidak ada nilai negatif (jika ada data masa depan error)
        days_diff = np.maximum(days_diff, 0)

        # Rumus Decay: score = exp(-lambda * days)
        # Lambda 0.001 artinya:
        # - Hari ini (0 hari): Skor 1.0
        # - 1 Tahun (365 hari): Skor 0.69
        # - 2 Tahun (730 hari): Skor 0.48
        decay_rate = 0.001 
        recency_scores = np.exp(-decay_rate * days_diff)
        
        return recency_scores

    def search(self, query, top_k=10):
        if not self.is_ready:
            return pd.DataFrame() # Return kosong jika error

        # 1. Vektorisasi Query User
        query_vec = self.get_vector(query).reshape(1, -1)
        
        # 2. Hitung Kemiripan Semantik (Cosine Similarity)
        # Hasil: -1 s/d 1
        semantic_scores = cosine_similarity(query_vec, self.doc_vectors)[0]
        
        # Normalisasi ke 0 s/d 1 agar bisa dijumlah dengan skor waktu
        semantic_scores = (semantic_scores + 1) / 2 

        # 3. Hitung Skor Kebaruan
        recency_scores = self.calculate_recency_score(self.df['Waktu'])

        # 4. GABUNGKAN SKOR (FINAL SCORE)
        # Final = (Semantik * 0.7) + (Waktu * 0.3)
        final_scores = (semantic_scores * WEIGHT_SEMANTIC) + (recency_scores * WEIGHT_RECENCY)

        # 5. Urutkan & Ambil Top K
        top_indices = final_scores.argsort()[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            row = self.df.iloc[idx]
            
            # Format tanggal agar enak dibaca
            tgl = row.get('Waktu', pd.NaT)
            tgl_str = tgl.strftime('%d %b %Y') if pd.notna(tgl) else "N/A"
            
            results.append({
                "Nama Tempat": row['Nama_Tempat'],
                "Lokasi": row['Lokasi'],
                "Rating": row['Rating'],
                "Tanggal Ulasan": tgl_str,
                "Isi Ulasan": row['Teks_Mentah'],
                "Skor Relevansi": round(final_scores[idx] * 100, 1) # Jadikan persen
            })
            
        return pd.DataFrame(results)

# --- BLOK TESTING ---
if __name__ == "__main__":
    # Ini jalan kalau file ini dijalankan langsung (bukan diimport)
    engine = SmartSearchEngine()
    if engine.is_ready:
        print("\n" + "="*40)
        q = input("🔍 Masukkan kata kunci tes (misal: 'kamar mandi bersih'): ")
        print(f"🔎 Mencari: '{q}' ...")
        
        hasil = engine.search(q)
        
        if not hasil.empty:
            print("\n🏆 HASIL PENCARIAN TERATAS:")
            # Tampilkan kolom tertentu saja biar rapi di terminal
            print(hasil[['Nama Tempat', 'Tanggal Ulasan', 'Skor Relevansi', 'Isi Ulasan']].head(5).to_string())
        else:
            print("❌ Tidak ditemukan hasil.")