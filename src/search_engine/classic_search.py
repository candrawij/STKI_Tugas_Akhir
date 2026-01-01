import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import os
import sys

# Setup Path agar bisa import db_handler
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

try:
    from Asisten.db_handler import db
except ImportError:
    # Fallback manual jika import path bermasalah
    import sqlite3
    class DBHandler:
        def get_connection(self):
            return sqlite3.connect(os.path.join(parent_dir, 'camping.db'))
    db = DBHandler()

class ClassicSearchEngine:
    def __init__(self):
        self.vectorizer = None
        self.tfidf_matrix = None
        self.df = None
        self.is_ready = False
        self.prepare_engine()

    def prepare_engine(self):
        """Memuat data dari DB dan melatih TF-IDF Vectorizer"""
        try:
            conn = db.get_connection()
            # Ambil data yang sama persis dengan yang dipakai Word2Vec
            query = """
            SELECT t.nama, t.lokasi, u.teks_mentah 
            FROM ulasan u 
            JOIN tempat t ON u.tempat_id = t.id
            WHERE u.teks_mentah IS NOT NULL AND u.teks_mentah != ''
            """
            self.df = pd.read_sql_query(query, conn)
            conn.close()

            if not self.df.empty:
                # Preprocessing ringan (lowercase)
                self.df['teks_olah'] = self.df['teks_mentah'].str.lower()
                
                # Inisialisasi TF-IDF (Hapus stop words umum jika perlu)
                # Kita set min_df=1 agar kata unik pun tetap terhitung
                self.vectorizer = TfidfVectorizer()
                
                # Fitting (Melatih) model ke data ulasan
                self.tfidf_matrix = self.vectorizer.fit_transform(self.df['teks_olah'])
                
                self.is_ready = True
                print("✅ [TF-IDF] Engine siap digunakan.")
            else:
                print("❌ [TF-IDF] Data kosong.")
                
        except Exception as e:
            print(f"❌ [TF-IDF] Error init: {e}")

    def search(self, query, top_k=5):
        """Melakukan pencarian berdasarkan kemiripan kosinus TF-IDF"""
        if not self.is_ready: return pd.DataFrame()

        # 1. Transform query menjadi vektor
        query_vec = self.vectorizer.transform([query.lower()])
        
        # 2. Hitung kemiripan (Cosine Similarity)
        # Hasilnya adalah array skor kemiripan antara query dengan SETIAP dokumen
        cosine_scores = cosine_similarity(query_vec, self.tfidf_matrix).flatten()
        
        # 3. Urutkan skor dari yang tertinggi
        # argsort mengembalikan index, [::-1] membalik urutan (descending)
        top_indices = cosine_scores.argsort()[::-1][:top_k*3] # Ambil kandidat lebih banyak utk deduplikasi
        
        results = []
        for idx in top_indices:
            score = cosine_scores[idx]
            
            # Threshold: Abaikan jika kemiripan terlalu kecil (noise)
            if score < 0.01: continue
            
            row = self.df.iloc[idx]
            results.append({
                "Nama Tempat": row['nama'],
                "Lokasi": row['lokasi'],
                "Isi Ulasan": row['teks_mentah'],
                "Skor Relevansi": round(score * 100, 2) # Skala 0-100
            })
            
        # 4. Deduplikasi (Hanya ambil 1 ulasan terbaik per tempat)
        df_res = pd.DataFrame(results)
        if not df_res.empty:
            df_res = df_res.drop_duplicates(subset=['Nama Tempat'], keep='first')
            
        return df_res.head(top_k)