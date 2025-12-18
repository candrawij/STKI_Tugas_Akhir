import pandas as pd
import os
import re
from datetime import datetime, timedelta
import dateutil.relativedelta

# ================= KONFIGURASI =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(BASE_DIR, 'Data_Mentah')
DOCS_DIR = os.path.join(BASE_DIR, 'Documents')
OUTPUT_FILE = os.path.join(DOCS_DIR, 'corpus_master.csv') 

STOPWORDS = set([
    'dan', 'di', 'ke', 'dari', 'yang', 'ini', 'itu', 'untuk', 'pada', 
    'adalah', 'dengan', 'saya', 'aku', 'kami', 'kita', 'karena', 'yg', 
    'tdk', 'gak', 'ga', 'aja', 'saja', 'bgt', 'banget', 'dah', 'nih', 
    'tuh', 'dong', 'sih', 'kok', 'dgn', 'dr', 'utk'
])

# [REVISI V-FINAL] KAMUS PERBAIKAN NAMA (HANYA UNTUK TYPO & KAPITALISASI)
# Kita HAPUS penyatuan Sikunir agar mereka tetap menjadi entitas terpisah.
NAME_MAPPING = {
    # Kasus Kapitalisasi (Tetap Wajib disatukan)
    "Caub (Camp Area Umbul Bengkok)": "Caub (Camp Area Umbul Bengkok)",
    "CAUB (Camp Area Umbul Bengkok)": "Caub (Camp Area Umbul Bengkok)",
    "Glamping menoreh": "Glamping Menoreh",
    "GLAMPING MENOREH": "Glamping Menoreh",
    "Biosfer 2 camping ground": "Biosfer 2 Camping Ground",

    # Kasus Typo Jelas (Boleh disatukan)
    "Watu gendong camping hills outbond center adventure": "Watu Gendong Camping Hills",
    "Watu Gendong Camping Hills Outbond Center Adventure": "Watu Gendong Camping Hills",
    
    # [DIHAPUS] Bagian penyatuan Sikunir dihapus. 
    # Sikunir A dan Sikunir B akan tetap terpisah.
}

def standardize_name(name):
    """
    Membersihkan nama tempat:
    1. Title Case (Otomatis)
    2. Cek Kamus Mapping (Manual)
    """
    # 1. Standarisasi awal: Title Case & Strip
    clean = str(name).strip().title()
    
    # 2. Cek Mapping Khusus (Prioritas Tinggi)
    if clean in NAME_MAPPING:
        return NAME_MAPPING[clean]
    if name in NAME_MAPPING:
        return NAME_MAPPING[name]
        
    return clean

def convert_relative_time(row):
    relative_time = row.get('Waktu')
    scrap_date_str = row.get('Tanggal_Scrap')
    
    if pd.isna(relative_time): return None
    
    anchor_date = datetime.now()
    if pd.notna(scrap_date_str):
        try: anchor_date = datetime.strptime(str(scrap_date_str), '%Y-%m-%d')
        except: pass
    
    text = str(relative_time).lower().strip()
    try:
        match = re.search(r'(\d+)\s+(tahun|bulan|minggu|hari|jam|menit|detik)', text)
        if match:
            value = int(match.group(1))
            unit = match.group(2)
            if unit == 'tahun': date_obj = anchor_date - dateutil.relativedelta.relativedelta(years=value)
            elif unit == 'bulan': date_obj = anchor_date - dateutil.relativedelta.relativedelta(months=value)
            elif unit == 'minggu': date_obj = anchor_date - timedelta(weeks=value)
            elif unit == 'hari': date_obj = anchor_date - timedelta(days=value)
            else: date_obj = anchor_date
            return date_obj.strftime('%Y-%m-%d')

        if 'setahun' in text: return (anchor_date - dateutil.relativedelta.relativedelta(years=1)).strftime('%Y-%m-%d')
        elif 'sebulan' in text: return (anchor_date - dateutil.relativedelta.relativedelta(months=1)).strftime('%Y-%m-%d')
        elif 'seminggu' in text: return (anchor_date - timedelta(weeks=1)).strftime('%Y-%m-%d')
        elif 'sehari' in text or 'kemarin' in text: return (anchor_date - timedelta(days=1)).strftime('%Y-%m-%d')
        elif 'baru saja' in text or 'menit' in text or 'jam' in text: return anchor_date.strftime('%Y-%m-%d')
    except Exception: return anchor_date.strftime('%Y-%m-%d')
    return anchor_date.strftime('%Y-%m-%d')

def clean_text(text):
    if pd.isna(text): return ""
    text = str(text).lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\d+', '', text)
    words = text.split()
    words = [w for w in words if w not in STOPWORDS and len(w) > 2]
    return " ".join(words)

def run_cleaning_pipeline():
    print("--- 🧹 CLEANING DATA V3 (NON-AGGRESSIVE MAPPING) ---")
    
    all_data = []
    
    # 1. BACA DATA BARU (MENTAH)
    if os.path.exists(RAW_DIR):
        for root, dirs, files in os.walk(RAW_DIR):
            for file in files:
                if file.endswith(".csv"):
                    filepath = os.path.join(root, file)
                    try:
                        df = pd.read_csv(filepath)
                        folder_name = os.path.basename(root)
                        file_name = os.path.splitext(file)[0]
                        
                        # Standarisasi Nama
                        clean_name = standardize_name(file_name)
                        
                        df['Nama_Tempat'] = clean_name
                        df['Lokasi'] = folder_name
                        all_data.append(df)
                        print(f"   📄 Mentah: {clean_name} ({len(df)})")
                    except Exception as e: print(f"   ⚠️ Error {file}: {e}")

    # 2. BACA DATA LAMA (CORPUS MASTER)
    if os.path.exists(OUTPUT_FILE):
        try:
            df_old = pd.read_csv(OUTPUT_FILE)
            # FIX DATA LAMA JUGA
            df_old['Nama_Tempat'] = df_old['Nama_Tempat'].apply(standardize_name)
            
            all_data.append(df_old)
            print(f"   📂 Corpus Lama: {len(df_old)} baris (Nama diperbaiki)")
        except: pass

    if not all_data:
        print("❌ Tidak ada data.")
        return False

    # Gabung
    df_master = pd.concat(all_data, ignore_index=True)
    if 'Tanggal_Scrap' not in df_master.columns: df_master['Tanggal_Scrap'] = None

    print(f"📊 Total Gabungan: {len(df_master)} baris")

    # Konversi Waktu
    print("⏳ Konversi Waktu...")
    df_master['Waktu'] = df_master.apply(convert_relative_time, axis=1)

    # Cleaning Teks
    print("🧼 Cleaning Teks...")
    df_master['Teks_Bersih'] = df_master['Teks_Mentah'].apply(clean_text)
    
    # Filter Sampah
    df_master.dropna(subset=['Teks_Bersih'], inplace=True)
    df_master = df_master[df_master['Teks_Bersih'].str.len() > 5]
    
    # DEDUPLIKASI FINAL 
    print("🔗 Menghapus Duplikat...")
    df_master.drop_duplicates(subset=['Nama_Tempat', 'Teks_Mentah'], inplace=True)

    # Simpan
    final_cols = ['Nama_Tempat', 'Lokasi', 'Rating', 'Teks_Mentah', 'Waktu']
    df_staging = df_master[final_cols]
    
    os.makedirs(DOCS_DIR, exist_ok=True)
    df_staging.to_csv(OUTPUT_FILE, index=False)
    
    print(f"✅ SUKSES! Corpus Master Diperbarui: {OUTPUT_FILE}")
    print(f"📊 Total Data Bersih: {len(df_staging)} baris")
    return True

if __name__ == "__main__":
    run_cleaning_pipeline()