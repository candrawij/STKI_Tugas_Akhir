import pandas as pd
import numpy as np
import os
import re
import sys
from gensim.models import Word2Vec
from sklearn.metrics.pairwise import cosine_similarity

# --- 1. SETUP PATH ABSOLUT ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(CURRENT_DIR)
MODEL_PATH = os.path.join(BASE_DIR, 'Assets', 'word2vec.model')

# Import DB
try:
    from Asisten.db_handler import db
except ImportError:
    sys.path.append(BASE_DIR)
    from Asisten.db_handler import db

# Konstanta
WEIGHT_SEMANTIC = 0.3
WEIGHT_KEYWORD = 0.7

class SmartSearchEngine:
    def __init__(self):
        self.model = None
        self.df = None
        self.doc_vectors = None
        self.is_ready = False
        self.vector_size = 100 # Default jika model gagal load
        
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

        # 2. Load Model & Cek Dimensi
        if os.path.exists(MODEL_PATH):
            try: 
                self.model = Word2Vec.load(MODEL_PATH)
                self.vector_size = self.model.vector_size # AMBIL UKURAN ASLI MODEL
                print(f"✅ Model Loaded. Vector Size: {self.vector_size}")
            except Exception as e: 
                print(f"❌ Model Corrupt: {e}")
        else:
            print(f"❌ Model tidak ditemukan di: {MODEL_PATH}")
        
        # 3. Vectorization
        if not self.df.empty and self.model:
            # Gunakan list comprehension dengan np.stack agar lebih aman
            vectors = [self.get_vector(t) for t in self.df['teks_bersih']]
            self.doc_vectors = np.vstack(vectors) # vstack lebih aman untuk array list
            self.is_ready = True

    def get_vector(self, text):
        # Gunakan ukuran dinamis (self.vector_size), JANGAN hardcode 100
        if not self.model: return np.zeros(self.vector_size)
        
        words = str(text).split()
        # Ambil vektor kata yang dikenal
        valid_vectors = [self.model.wv[w] for w in words if w in self.model.wv]
        
        if not valid_vectors: 
            return np.zeros(self.vector_size) # Return vector nol dengan ukuran yg benar
        
        return np.mean(valid_vectors, axis=0)

    def search(self, query, top_k=20):
        if not self.is_ready: return pd.DataFrame()

        clean_query = query.lower()
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
        
        # Result Formatting
        top_indices = final_scores.argsort()[::-1][:top_k*2]
        results = []
        seen = set()
        
        for idx in top_indices:
            if final_scores[idx] > 0.01:
                nama = self.df.iloc[idx]['nama']
                if nama in seen: continue # Deduplikasi manual
                seen.add(nama)
                
                results.append({
                    "Nama Tempat": nama,
                    "Lokasi": self.df.iloc[idx]['lokasi'],
                    "Isi Ulasan": self.df.iloc[idx]['teks_mentah'],
                    "Skor Relevansi": round(final_scores[idx] * 100, 1)
                })
                if len(results) >= top_k: break
        
        return pd.DataFrame(results)