import pandas as pd
import numpy as np
import os
import re
from datetime import datetime
from gensim.models import Word2Vec
from sklearn.metrics.pairwise import cosine_similarity

# DATABASE HANDLER
try:
    from Asisten.db_handler import db
except ImportError:
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from Asisten.db_handler import db

# PATH
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, 'Assets', 'word2vec.model')

# FILE CONFIG CSV (KAMUS)
PHRASE_MAP_PATH = os.path.join(BASE_DIR, 'config_phrase_map.csv')
REGION_MAP_PATH = os.path.join(BASE_DIR, 'config_region_map.csv')
INTENT_MAP_PATH = os.path.join(BASE_DIR, 'config_special_intent.csv')

WEIGHT_SEMANTIC = 0.7
WEIGHT_RECENCY = 0.3

class SmartSearchEngine:
    def __init__(self):
        self.model = None
        self.df = None
        self.doc_vectors = None
        self.is_ready = False
        
        # Data Kamus
        self.phrase_dict = {}
        self.region_dict = {}
        self.intent_dict = {}
        
        self.load_configs()
        self.load_resources()

    def load_configs(self):
        """Membaca file CSV Kamus"""
        try:
            # 1. Load Phrase Map (Untuk perbaikan kata)
            if os.path.exists(PHRASE_MAP_PATH):
                df_ph = pd.read_csv(PHRASE_MAP_PATH)
                # Urutkan berdasarkan panjang frase (descending) agar frase panjang diganti duluan
                # misal: "kamar mandi" dulu baru "mandi"
                df_ph['len'] = df_ph['Phrase'].str.len()
                df_ph = df_ph.sort_values('len', ascending=False)
                self.phrase_dict = dict(zip(df_ph['Phrase'], df_ph['Token']))
                print(f"✅ Loaded Phrase Map: {len(self.phrase_dict)} entries")

            # 2. Load Region Map (Untuk filter lokasi)
            if os.path.exists(REGION_MAP_PATH):
                df_rg = pd.read_csv(REGION_MAP_PATH)
                # Group by region_code untuk mendapatkan list sinonim
                # misal: diy -> [jogja, yogyakarta, sleman, ...]
                for _, row in df_rg.iterrows():
                    code = row['region_code'].lower()
                    term = row['location_term'].lower()
                    if code not in self.region_dict: self.region_dict[code] = []
                    self.region_dict[code].append(term)
                print(f"✅ Loaded Region Map: {len(self.region_dict)} regions")

            # 3. Load Intent Map (Untuk ALL / Rating)
            if os.path.exists(INTENT_MAP_PATH):
                df_in = pd.read_csv(INTENT_MAP_PATH)
                self.intent_dict = dict(zip(df_in['intent_phrase'], df_in['intent_code']))
                print(f"✅ Loaded Intent Map: {len(self.intent_dict)} intents")

        except Exception as e:
            print(f"⚠️ Warning loading configs: {e}")

    def load_resources(self):
        try:
            conn = db.get_connection()
            query = """
                SELECT u.teks_bersih, u.teks_mentah, u.waktu_ulasan, t.nama, t.lokasi, t.rating_gmaps
                FROM ulasan u JOIN tempat t ON u.tempat_id = t.id
                WHERE u.teks_bersih IS NOT NULL AND u.teks_bersih != ''
            """
            self.df = pd.read_sql_query(query, conn)
            conn.close()
            
            self.df['waktu_ulasan'] = pd.to_datetime(self.df['waktu_ulasan'], errors='coerce')
            self.df['teks_mentah'] = self.df['teks_mentah'].fillna("").astype(str)
            self.df['teks_bersih'] = self.df['teks_bersih'].fillna("").astype(str)
            self.df['lokasi_lower'] = self.df['lokasi'].astype(str).str.lower()
            
        except Exception as e:
            print(f"❌ Gagal load database: {e}")
            return

        if os.path.exists(MODEL_PATH):
            try: self.model = Word2Vec.load(MODEL_PATH)
            except: return
        else: return

        if not self.df.empty and self.model:
            self.doc_vectors = np.array([self.get_vector(text) for text in self.df['teks_bersih']])
            self.is_ready = True
        else:
            print("❌ Search Engine GAGAL inisialisasi.")

    def get_vector(self, text):
        if not self.model: return np.zeros(100)
        words = str(text).split()
        word_vecs = [self.model.wv[w] for w in words if w in self.model.wv]
        if len(word_vecs) == 0: return np.zeros(self.model.vector_size)
        return np.mean(word_vecs, axis=0)

    def preprocess_query(self, query):
        """Membersihkan dan mengganti kata berdasarkan Phrase Map"""
        q = query.lower().strip()
        
        # 1. Cek Intent Khusus dulu (ALL / TOP)
        if q in self.intent_dict:
            return q, self.intent_dict[q]
            
        # 2. Ganti Frase (Phrase Map)
        for phrase, token in self.phrase_dict.items():
            if phrase in q:
                q = q.replace(phrase, token)
        
        return q, None

    def detect_region_filter(self, query):
        """Mendeteksi apakah user menyebut nama daerah"""
        q_lower = query.lower()
        detected = []
        
        # Cek dari Region Map yang diload dari CSV
        for region_code, terms in self.region_dict.items():
            for term in terms:
                # Cek exact match atau boundary agar 'tengah' tidak kena 'jawa tengah'
                if term in q_lower:
                    detected.extend(terms) # Tambahkan semua sinonim wilayah itu
                    break # Cukup 1 term per region code
        return list(set(detected))

    def search(self, query, top_k=50):
        if not self.is_ready: return pd.DataFrame()

        # 1. Preprocess (Gunakan Kamus)
        clean_query, intent = self.preprocess_query(query)
        
        # 2. Handle Intent Khusus
        if intent == "ALL":
            # Kembalikan 1 per tempat
            return self.df.drop_duplicates(subset=['nama']).assign(**{"Skor Relevansi": 100.0}).head(100)
            
        # 3. Hitung Skor Semantik
        query_vec = self.get_vector(clean_query).reshape(1, -1)
        semantic_scores = cosine_similarity(query_vec, self.doc_vectors)[0]
        semantic_scores = (semantic_scores + 1) / 2 
        
        recency_scores = self.calculate_recency_score(self.df['waktu_ulasan'])
        final_scores = (semantic_scores * WEIGHT_SEMANTIC) + (recency_scores * WEIGHT_RECENCY)

        # 4. Filter Lokasi
        target_regions = self.detect_region_filter(query)
        if target_regions:
            # Penalti bagi tempat yang TIDAK mengandung lokasi yg dimaksud
            mask = self.df['lokasi_lower'].apply(lambda x: any(r in x for r in target_regions))
            final_scores = final_scores * np.where(mask, 1.0, 0.0)

        # 5. Result
        top_indices = final_scores.argsort()[::-1][:top_k]
        results = []
        for idx in top_indices:
            if final_scores[idx] <= 0: continue
            row = self.df.iloc[idx]
            results.append({
                "Nama Tempat": row['nama'],
                "Lokasi": row['lokasi'],
                "Isi Ulasan": row['teks_mentah'],
                "Skor Relevansi": round(final_scores[idx] * 100, 1)
            })
            
        return pd.DataFrame(results)
    
    def calculate_recency_score(self, date_series):
        today = datetime.now()
        days_diff = (today - date_series).dt.days.fillna(1825)
        return np.exp(-0.001 * np.maximum(days_diff, 0))