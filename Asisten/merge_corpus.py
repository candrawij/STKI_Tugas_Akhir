import pandas as pd
import os
import shutil
from datetime import datetime

# ================= KONFIGURASI =================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS_DIR = os.path.join(BASE_DIR, 'Documents')

FILE_MASTER = os.path.join(DOCS_DIR, 'corpus_master.csv')
FILE_STAGING = os.path.join(DOCS_DIR, 'corpus_staging.csv')
BACKUP_DIR = os.path.join(DOCS_DIR, 'Backup_Master')

def merge_staging_to_master():
    print("--- 🔄 MEMULAI PROSES MERGE (STAGING -> MASTER) ---")

    # 1. Cek Staging
    if not os.path.exists(FILE_STAGING):
        print("❌ Tidak ada file 'corpus_staging.csv'. Jalankan 'clean_data.py' dulu.")
        return

    print("📖 Membaca data Staging (Data Baru)...")
    df_staging = pd.read_csv(FILE_STAGING)
    
    if df_staging.empty:
        print("⚠️ File Staging kosong.")
        return

    # Bersihkan spasi di nama tempat agar pencocokan akurat
    df_staging['Nama_Tempat'] = df_staging['Nama_Tempat'].str.strip()
    print(f"   👉 Ditemukan {len(df_staging)} ulasan calon masuk.")

    # 2. Cek Master
    if os.path.exists(FILE_MASTER):
        print("📖 Membaca data Master (Data Lama)...")
        df_master = pd.read_csv(FILE_MASTER)
        df_master['Nama_Tempat'] = df_master['Nama_Tempat'].str.strip()
        
        jumlah_awal_master = len(df_master)
        print(f"   👉 Master saat ini berisi {jumlah_awal_master} ulasan.")

        # --- BACKUP DULU ---
        os.makedirs(BACKUP_DIR, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = os.path.join(BACKUP_DIR, f'corpus_master_backup_{timestamp}.csv')
        shutil.copy(FILE_MASTER, backup_path)
        print(f"   🛡️ Backup aman di: {backup_path}")

    else:
        print("🆕 Membuat Master baru.")
        df_master = pd.DataFrame(columns=df_staging.columns)
        jumlah_awal_master = 0

    # 3. PROSES PENGGABUNGAN CERDAS
    print("⚙️ Menggabungkan data...")
    
    # Gabungkan Master + Staging
    df_combined = pd.concat([df_master, df_staging], ignore_index=True)

    # 4. PENGHAPUSAN DUPLIKAT (LOGIKA BARU)
    # Kita anggap duplikat HANYA JIKA 'Nama_Tempat' DAN 'Teks_Mentah' sama persis.
    # keep='first' artinya data lama di Master dipertahankan, data Staging yang sama dibuang.
    
    df_combined.drop_duplicates(subset=['Nama_Tempat', 'Teks_Mentah'], keep='first', inplace=True)
    
    jumlah_akhir = len(df_combined)
    data_baru_masuk = jumlah_akhir - jumlah_awal_master
    
    if data_baru_masuk > 0:
        print(f"   ✅ Berhasil menambahkan {data_baru_masuk} ulasan BARU ke Master.")
    else:
        print("   ℹ️ Tidak ada data baru (semua data di Staging sudah ada di Master).")

    # 5. RAPIKAN URUTAN DOC_ID
    # Reset index agar urut 1, 2, 3...
    df_combined.reset_index(drop=True, inplace=True)
    df_combined['Doc_ID'] = range(1, len(df_combined) + 1)
    
    # Pastikan urutan kolom rapi
    cols = ['Doc_ID', 'Nama_Tempat', 'Lokasi', 'Rating', 'Teks_Mentah', 'Waktu']
    # Filter hanya kolom yang ada (jaga-jaga kalau ada kolom ekstra)
    cols = [c for c in cols if c in df_combined.columns]
    df_combined = df_combined[cols]

    # 6. SIMPAN
    df_combined.to_csv(FILE_MASTER, index=False)
    
    print("\n" + "="*50)
    print(f"🎉 SUKSES! Master sekarang berisi {len(df_combined)} ulasan.")
    print("👉 Langkah selanjutnya: Jalankan 'python train_w2v.py' untuk update otak AI.")
    print("="*50)

if __name__ == "__main__":
    merge_staging_to_master()