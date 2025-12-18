import pandas as pd
import numpy as np
import os
import re
from datetime import datetime
from gensim.models import Word2Vec
from sklearn.metrics.pairwise import cosine_similarity

# ================= KONFIGURASI PATH =================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, 'Assets', 'word2vec.model')
CORPUS_PATH = os.path.join(BASE_DIR, 'Documents', 'corpus_master.csv')

# Bobot Skor
WEIGHT_SEMANTIC = 0.7
WEIGHT_RECENCY = 0.3

# Kamus Sinonim Lokasi (Agar AI paham Jogja = Sleman/Bantul/dll)
REGION_MAP = {
    "jogja": ["yogyakarta", "jogja", "sleman", "bantul", "kulon progo", "gunung kidul", "kaliurang"],
    "yogya": ["yogyakarta", "jogja", "sleman", "bantul", "kulon progo", "gunung kidul"],
    "sleman": ["sleman", "kaliurang"],
    "semarang": ["semarang", "ungaran", "bandungan"],
    "magelang": ["magelang"],
    "wonosobo": ["wonosobo", "dieng"],
    "dieng": ["dieng", "wonosobo", "banjarnegara"],
    "kendal": ["kendal"]
}

class SmartSearchEngine:
    def __init__(self):
        self.model = None
        self.df = None
        self.doc_vectors = None
        self.is_ready = False
        self.load_resources()

    def load_resources(self):
        print(f"⚙️ Memuat Smart Search Engine...")
        if os.path.exists(CORPUS_PATH):
            self.df = pd.read_csv(CORPUS_PATH)
            if 'Waktu' in self.df.columns:
                self.df['Waktu'] = pd.to_datetime(self.df['Waktu'], errors='coerce')
            else:
                self.df['Waktu'] = pd.NaT
            self.df['Teks_Mentah'] = self.df['Teks_Mentah'].fillna("").astype(str)
            # Pastikan kolom Lokasi lowercase agar mudah difilter
            self.df['Lokasi_Lower'] = self.df['Lokasi'].astype(str).str.lower()
        else:
            return

        if os.path.exists(MODEL_PATH):
            try:
                self.model = Word2Vec.load(MODEL_PATH)
            except: return
        else: return

        self.doc_vectors = np.array([self.get_vector(text) for text in self.df['Teks_Mentah']])
        self.is_ready = True
        print("✅ Search Engine Siap.")

    def get_vector(self, text):
        if not self.model: return np.zeros(100)
        words = str(text).lower().split()
        word_vecs = [self.model.wv[w] for w in words if w in self.model.wv]
        if len(word_vecs) == 0: return np.zeros(self.model.vector_size)
        return np.mean(word_vecs, axis=0)

    def calculate_recency_score(self, date_series):
        today = datetime.now()
        days_diff = (today - date_series).dt.days
        days_diff = days_diff.fillna(1825) 
        days_diff = np.maximum(days_diff, 0)
        decay_rate = 0.001 
        return np.exp(-decay_rate * days_diff)

    def detect_region_filter(self, query):
        """Mendeteksi apakah user menyebut nama daerah"""
        q_lower = query.lower()
        detected_regions = []
        
        for key, synonyms in REGION_MAP.items():
            if key in q_lower: # Jika user ketik "Jogja"
                detected_regions.extend(synonyms)
        
        return detected_regions

    def search(self, query, top_k=50):
        if not self.is_ready: return pd.DataFrame()

        # 1. Hitung Skor Normal (AI + Waktu)
        query_vec = self.get_vector(query).reshape(1, -1)
        semantic_scores = cosine_similarity(query_vec, self.doc_vectors)[0]
        semantic_scores = (semantic_scores + 1) / 2 
        recency_scores = self.calculate_recency_score(self.df['Waktu'])
        final_scores = (semantic_scores * WEIGHT_SEMANTIC) + (recency_scores * WEIGHT_RECENCY)

        # 2. FILTER LOKASI (HARD FILTER)
        # Jika user minta "Jogja", kita kurangi skor tempat lain drastis atau nol-kan
        target_regions = self.detect_region_filter(query)
        
        if target_regions:
            print(f"📍 Filter Wilayah Aktif: {target_regions}")
            # Buat masker boolean: True jika lokasi tempat ada di target regions
            # Cek apakah string 'Lokasi' mengandung salah satu target
            # Contoh: Lokasi "Sleman" cocok dengan target ["sleman", "jogja"...]
            mask = self.df['Lokasi_Lower'].apply(lambda x: any(r in x for r in target_regions))
            
            # Yang TIDAK cocok, skornya dikali 0 (Dibuang)
            # Atau dikali 0.1 (Dipendam ke bawah)
            final_scores = final_scores * np.where(mask, 1.0, 0.0)

        # 3. Urutkan
        top_indices = final_scores.argsort()[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            # Skip jika skor 0 (kena filter lokasi)
            if final_scores[idx] <= 0: continue
            
            row = self.df.iloc[idx]
            tgl = row.get('Waktu', pd.NaT)
            tgl_str = tgl.strftime('%d %b %Y') if pd.notna(tgl) else "N/A"
            
            results.append({
                "Nama Tempat": row['Nama_Tempat'],
                "Lokasi": row['Lokasi'],
                "Rating": row['Rating'],
                "Tanggal Ulasan": tgl_str,
                "Isi Ulasan": row['Teks_Mentah'],
                "Skor Relevansi": round(final_scores[idx] * 100, 1)
            })
            
        return pd.DataFrame(results)