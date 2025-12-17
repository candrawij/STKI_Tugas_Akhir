import pandas as pd
import os
import re
from datetime import datetime, timedelta
import dateutil.relativedelta

# ================= KONFIGURASI =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(BASE_DIR, 'Data_Mentah')
DOCS_DIR = os.path.join(BASE_DIR, 'Documents')
OUTPUT_FILE = os.path.join(DOCS_DIR, 'corpus_staging.csv')

STOPWORDS = set([
    'dan', 'di', 'ke', 'dari', 'yang', 'ini', 'itu', 'untuk', 'pada', 
    'adalah', 'dengan', 'saya', 'aku', 'kami', 'kita', 'karena', 'yg', 
    'tdk', 'gak', 'ga', 'aja', 'saja', 'bgt', 'banget', 'dah', 'nih', 
    'tuh', 'dong', 'sih', 'kok'
])

def convert_relative_time(row):
    """
    Mengubah '2 bulan lalu' menjadi 'YYYY-MM-DD'.
    Menggunakan 'Tanggal_Scrap' sebagai patokan jika ada.
    Jika tidak ada, menggunakan hari ini (Fallback).
    """
    relative_time = row.get('Waktu')
    scrap_date_str = row.get('Tanggal_Scrap')
    
    if pd.isna(relative_time):
        return None
    
    # Tentukan Patokan (Anchor Date)
    anchor_date = datetime.now() # Default hari ini
    if pd.notna(scrap_date_str):
        try:
            # Coba parsing tanggal scrap dari CSV
            anchor_date = datetime.strptime(str(scrap_date_str), '%Y-%m-%d')
        except:
            pass # Kalau format salah, tetap pakai hari ini
    
    text = str(relative_time).lower().strip()
    
    try:
        # Pola 1: Angka + Satuan (Contoh: "2 tahun lalu")
        match = re.search(r'(\d+)\s+(tahun|bulan|minggu|hari|jam|menit|detik)', text)
        if match:
            value = int(match.group(1))
            unit = match.group(2)
            
            if unit == 'tahun':
                date_obj = anchor_date - dateutil.relativedelta.relativedelta(years=value)
            elif unit == 'bulan':
                date_obj = anchor_date - dateutil.relativedelta.relativedelta(months=value)
            elif unit == 'minggu':
                date_obj = anchor_date - timedelta(weeks=value)
            elif unit == 'hari':
                date_obj = anchor_date - timedelta(days=value)
            else:
                date_obj = anchor_date
            
            return date_obj.strftime('%Y-%m-%d')

        # Pola 2: Kata Satuan
        if 'setahun' in text:
            return (anchor_date - dateutil.relativedelta.relativedelta(years=1)).strftime('%Y-%m-%d')
        elif 'sebulan' in text:
            return (anchor_date - dateutil.relativedelta.relativedelta(months=1)).strftime('%Y-%m-%d')
        elif 'seminggu' in text:
            return (anchor_date - timedelta(weeks=1)).strftime('%Y-%m-%d')
        elif 'sehari' in text or 'kemarin' in text:
            return (anchor_date - timedelta(days=1)).strftime('%Y-%m-%d')
        elif 'baru saja' in text or 'menit' in text or 'jam' in text:
            return anchor_date.strftime('%Y-%m-%d')
            
    except Exception:
        return anchor_date.strftime('%Y-%m-%d')

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
    print("--- 🧹 MEMULAI PEMBERSIHAN DATA (CLEANING) ---")
    
    all_data = []
    
    if not os.path.exists(RAW_DIR):
        print(f"❌ Folder {RAW_DIR} tidak ditemukan!")
        return False

    for root, dirs, files in os.walk(RAW_DIR):
        for file in files:
            if file.endswith(".csv"):
                filepath = os.path.join(root, file)
                try:
                    df = pd.read_csv(filepath)
                    
                    folder_name = os.path.basename(root)
                    file_name = os.path.splitext(file)[0]
                    
                    df['Nama_Tempat'] = file_name
                    df['Lokasi'] = folder_name
                    
                    all_data.append(df)
                    print(f"   📄 Terbaca: {file_name} ({len(df)} baris)")
                except Exception as e:
                    print(f"   ⚠️ Gagal baca {file}: {e}")

    if not all_data:
        print("❌ Tidak ada data CSV yang ditemukan.")
        return False

    # Gabung Semua
    df_master = pd.concat(all_data, ignore_index=True)
    
    # Pastikan kolom Tanggal_Scrap ada (untuk file lama yg belum punya)
    if 'Tanggal_Scrap' not in df_master.columns:
        df_master['Tanggal_Scrap'] = None

    print(f"📊 Total Data Mentah: {len(df_master)} baris")

    # KONVERSI WAKTU (MENGGUNAKAN JANGKAR TANGGAL SCRAP)
    print("⏳ Mengonversi 'Waktu Relatif' -> 'Tanggal Pasti' (Freeze Time)...")
    
    # Kita kirim SATU BARIS (row) ke fungsi, bukan cuma kolom waktunya
    # Agar fungsi bisa baca kolom 'Waktu' DAN 'Tanggal_Scrap' di baris yg sama
    df_master['Waktu'] = df_master.apply(convert_relative_time, axis=1)

    print("🧼 Membersihkan teks ulasan...")
    df_master['Teks_Bersih'] = df_master['Teks_Mentah'].apply(clean_text)
    
    df_master.dropna(subset=['Teks_Bersih'], inplace=True)
    df_master = df_master[df_master['Teks_Bersih'].str.len() > 5]
    df_master.drop_duplicates(subset=['Nama_Tempat', 'Teks_Mentah'], inplace=True)

    # Simpan
    final_cols = ['Nama_Tempat', 'Lokasi', 'Rating', 'Teks_Mentah', 'Waktu']
    df_staging = df_master[final_cols]
    
    os.makedirs(DOCS_DIR, exist_ok=True)
    df_staging.to_csv(OUTPUT_FILE, index=False)
    
    print(f"✅ Data bersih tersimpan: {OUTPUT_FILE}")
    print(f"📊 Total Data Bersih: {len(df_staging)} baris")
    return True

if __name__ == "__main__":
    run_cleaning_pipeline()