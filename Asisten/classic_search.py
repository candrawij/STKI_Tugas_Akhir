import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import os
import sys

# --- SETUP PATH ---
# File ini ada di: Asisten/classic_search.py
# Kita perlu import db dari Asisten.db_handler
try:
    from Asisten.db_handler import db
except ImportError:
    # Fallback jika dijalankan langsung sebagai script
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from Asisten.db_handler import db

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
            query = """
            SELECT t.nama, t.lokasi, u.teks_mentah 
            FROM ulasan u 
            JOIN tempat t ON u.tempat_id = t.id
            WHERE u.teks_mentah IS NOT NULL AND u.teks_mentah != ''
            """
            self.df = pd.read_sql_query(query, conn)
            conn.close()

            if not self.df.empty:
                self.df['teks_olah'] = self.df['teks_mentah'].astype(str).str.lower()
                self.vectorizer = TfidfVectorizer()
                self.tfidf_matrix = self.vectorizer.fit_transform(self.df['teks_olah'])
                self.is_ready = True
                # print("✅ [TF-IDF] Engine siap.")
            else:
                print("❌ [TF-IDF] Data kosong.")
                
        except Exception as e:
            print(f"❌ [TF-IDF] Error init: {e}")

    def search(self, query, top_k=5):
        if not self.is_ready: return pd.DataFrame()

        try:
            query_vec = self.vectorizer.transform([query.lower()])
            cosine_scores = cosine_similarity(query_vec, self.tfidf_matrix).flatten()
            top_indices = cosine_scores.argsort()[::-1][:top_k*5] 
            
            results = []
            for idx in top_indices:
                score = cosine_scores[idx]
                if score < 0.01: continue
                
                row = self.df.iloc[idx]
                results.append({
                    "Nama Tempat": row['nama'],
                    "Lokasi": row['lokasi'],
                    "Isi Ulasan": row['teks_mentah'],
                    "Skor Relevansi": round(score * 100, 2)
                })
                
            df_res = pd.DataFrame(results)
            if not df_res.empty:
                df_res = df_res.drop_duplicates(subset=['Nama Tempat'], keep='first')
                
            return df_res.head(top_k)
        except: return pd.DataFrame()