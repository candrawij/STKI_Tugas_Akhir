import pandas as pd
import numpy as np
import os
import re
import sys
from gensim.models import Word2Vec
from sklearn.metrics.pairwise import cosine_similarity

# --- 1. SETUP PATH ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(CURRENT_DIR)
MODEL_PATH = os.path.join(BASE_DIR, 'Assets', 'word2vec.model')

# Import DB
try:
    from Asisten.db_handler import db
except ImportError:
    sys.path.append(BASE_DIR)
    from Asisten.db_handler import db

class SmartSearchEngine:
    def __init__(self):
        self.model = None
        self.df = None
        self.doc_vectors = None
        self.is_ready = False
        self.vector_size = 100 
        
        self.load_resources()

    def load_resources(self):
        # 1. Load Data
        try:
            conn = db.get_connection()
            query = """SELECT t.id, u.teks_mentah, t.nama, t.lokasi, t.rating_gmaps 
                       FROM ulasan u JOIN tempat t ON u.tempat_id = t.id 
                       WHERE u.teks_mentah IS NOT NULL AND u.teks_mentah != ''"""
            self.df = pd.read_sql_query(query, conn)
            conn.close()
            
            # Cleaning
            self.df['teks_bersih'] = self.df['teks_mentah'].fillna("").astype(str).str.lower()
            self.df['teks_bersih'] = self.df['teks_bersih'].apply(lambda x: re.sub(r'[^a-z0-9\s]', '', x))
            self.df['nama_lower'] = self.df['nama'].astype(str).str.lower()
            self.df['lokasi_lower'] = self.df['lokasi'].astype(str).str.lower()
        except Exception as e:
            print(f"❌ DB Error: {e}")
            return

        # 2. Load Model
        if os.path.exists(MODEL_PATH):
            try: 
                self.model = Word2Vec.load(MODEL_PATH)
                self.vector_size = self.model.vector_size
            except: pass
        
        # 3. Vectorization
        if not self.df.empty and self.model:
            vectors = [self.get_vector(t) for t in self.df['teks_bersih']]
            self.doc_vectors = np.vstack(vectors)
            self.is_ready = True

    def get_vector(self, text):
        if not self.model: return np.zeros(self.vector_size)
        words = str(text).split()
        valid_vectors = [self.model.wv[w] for w in words if w in self.model.wv]
        if not valid_vectors: return np.zeros(self.vector_size)
        return np.mean(valid_vectors, axis=0)

    # --- FUNGSI PENCARIAN (Updated Return Type) ---
    def search(self, query, top_k=20):
        """
        Mengembalikan: (DataFrame Hasil, Debug Dictionary)
        """
        debug_info = {
            "query_original": query,
            "query_clean": "",
            "top_result": "-"
        }

        if not self.is_ready: return pd.DataFrame(), debug_info

        # 1. Cleaning & Debug Data
        clean_query = re.sub(r'[^a-z0-9\s]', '', query.lower())
        debug_info['query_clean'] = clean_query

        # 2. Proses AI
        query_vec = self.get_vector(clean_query).reshape(1, -1)
        
        # A. Semantic Score
        if np.all(query_vec == 0): semantic_scores = np.zeros(len(self.df))
        else: semantic_scores = cosine_similarity(query_vec, self.doc_vectors)[0]
        
        # B. Keyword Score
        keyword_scores = self.df['teks_bersih'].str.contains(clean_query, regex=False).astype(float)
        
        # C. Name Boost
        name_scores = self.df['nama_lower'].str.contains(clean_query, regex=False).astype(float)
        
        # Final Score
        final_scores = (semantic_scores * 0.4) + (keyword_scores * 0.3) + (name_scores * 0.3)
        
        # 3. Formatting
        top_indices = final_scores.argsort()[::-1][:top_k*2]
        results = []
        seen = set()
        
        for idx in top_indices:
            if final_scores[idx] > 0.01:
                nama = self.df.iloc[idx]['nama']
                if nama in seen: continue
                seen.add(nama)
                
                results.append({
                    "Nama Tempat": nama,
                    "Lokasi": self.df.iloc[idx]['lokasi'],
                    "Isi Ulasan": self.df.iloc[idx]['teks_mentah'],
                    "Skor Relevansi": round(final_scores[idx] * 100, 1)
                })
                if len(results) >= top_k: break
        
        df_res = pd.DataFrame(results)
        
        # Update Debug Info
        if not df_res.empty:
            debug_info['top_result'] = df_res.iloc[0]['Nama Tempat']
        else:
            debug_info['top_result'] = "Tidak ditemukan"

        return df_res, debug_info