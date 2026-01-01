import os
import sys
import subprocess
import time
import shutil

# ================= KONFIGURASI PINTAR =================
# Mencari Python di .venv agar tidak perlu aktivasi manual
venv_python = os.path.join(os.getcwd(), ".venv", "Scripts", "python.exe")
if os.path.exists(venv_python):
    PYTHON_EXE = venv_python
else:
    PYTHON_EXE = sys.executable

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    clear_screen()
    print("="*50)
    print("   🏕️  CAMPGROUND AI - MISSION CONTROL (V3.1)")
    print("   (Fixed Pipeline: Merge & Training)")
    print("="*50)

def run_script(script_name, folder="", description=""):
    """
    Menjalankan script python lain dengan path yang benar.
    """
    # Tentukan lokasi script
    if folder:
        script_path = os.path.join(folder, script_name)
    else:
        script_path = script_name

    # Cek keberadaan file
    if not os.path.exists(script_path):
        print(f"❌ Error: File '{script_path}' tidak ditemukan!")
        return False

    if description:
        print(f"\n[⏳] {description}...")
        print(f"     File: {script_path}")
    else:
        print(f"\n🚀 Menjalankan: {script_name}...")
    
    print("-" * 40)
    
    try:
        # Menjalankan script sebagai subprocess
        result = subprocess.run([PYTHON_EXE, script_path], check=True)
        if result.returncode == 0:
            print(f"✅ SUKSES.")
            return True
        else:
            print(f"❌ GAGAL (Return Code: {result.returncode}).")
            return False
    except subprocess.CalledProcessError as e:
        print(f"❌ Error eksekusi: {e}")
        return False
    except KeyboardInterrupt:
        print("\n⚠️ Dibatalkan oleh user.")
        return False

# ================= MENU 1: HUNTING DATA =================
def menu_hunting():
    while True:
        print_header()
        print("🕵️‍♂️ MODE PEMBURU DATA (SCRAPING)")
        print("-" * 30)
        print("1. Scrape Ulasan Gmaps (Utama)")
        print("2. Scrape Metadata/Foto (Opsional)")
        print("0. Kembali ke Menu Utama")
        
        pilihan = input("\nPilih menu (0-2): ").strip()
        
        if pilihan == '1':
            run_script('scraper_gmaps.py', folder='Asisten', description="Scraping Ulasan")
            input("\nTekan Enter untuk lanjut...")
        elif pilihan == '2':
            run_script('scraper_metadata.py', folder='Asisten', description="Scraping Metadata")
            input("\nTekan Enter untuk lanjut...")
        elif pilihan == '0':
            break

# ================= MENU 2: UPDATE OTAK AI =================
def menu_update_ai():
    print_header()
    print("🧠 MODE UPDATE OTAK AI (PIPELINE OTOMATIS)")
    print("⚠️  Pastikan Anda sudah selesai scraping data baru.")
    print("-" * 30)
    confirm = input("Mulai proses update? (y/n): ").lower()
    
    if confirm != 'y': return

    start_time = time.time()
    
    # 1. CLEANING DATA (Output: corpus_staging.csv)
    # Lokasi: Root (clean_data.py biasanya di root agar mudah akses folder Data_Mentah)
    if not run_script('clean_data.py', folder='', description="1. Membersihkan & Filter Data Mentah"): return

    # 2. MERGING (Staging -> Master) [BAGIAN INI DIPERBAIKI]
    # Lokasi: Asisten/merge_corpus.py (Sesuai perbaikan sebelumnya)
    if not run_script('merge_corpus.py', folder='Asisten', description="2. Menggabungkan Data (Merge & Deduplicate)"): return

    # 3. KONVERSI METADATA (Harga/Foto)
    # Lokasi: Asisten/konversi_data.py
    if not run_script('konversi_data.py', folder='Asisten', description="3. Integrasi Harga & Fasilitas"): return

    # 4. TRAINING AI (Word2Vec)
    # Lokasi: Root
    if not run_script('train_w2v.py', folder='', description="4. Melatih Model AI (Word2Vec)"): return

    # 5. GENERATE SCORECARD (Analisis Aspek)
    # Lokasi: Asisten/scorecard_generator.py
    if not run_script('scorecard_generator.py', folder='Asisten', description="5. Membuat Rapor & Insight"): return

    total_time = time.time() - start_time
    print("\n" + "="*50)
    print(f"🎉 SEMUA PROSES SELESAI dalam {total_time:.2f} detik!")
    print("   AI sekarang sudah lebih pintar dan data master aman.")
    print("="*50)
    input("\nTekan Enter untuk kembali...")

# ================= MENU UTAMA =================
def main_menu():
    while True:
        print_header()
        print("MENU UTAMA:")
        print("1. 🕵️‍♂️  Tambah Data Baru (Scraping)")
        print("2. 🧠  Update Otak AI (Pipeline Otomatis)")
        print("3. 🧪  Tes Kepintaran AI (Cek Otak)")
        print("4. 📊  Audit Kualitas Data (Cek Jumlah)")
        print("5. 🌐  Jalankan Website (Streamlit)")
        print("0. Keluar")
        
        pilihan = input("\nPilih menu (0-5): ").strip()
        
        if pilihan == '1':
            menu_hunting()
            
        elif pilihan == '2':
            menu_update_ai()
            
        elif pilihan == '3':
            # File ada di folder Tools
            run_script('cek_otak_ai.py', folder='Tools', description="Tes Asosiasi Kata")
            input("\nTekan Enter untuk kembali...")

        elif pilihan == '4':
            # File ada di folder Tools
            run_script('cek_data_corpus.py', folder='Tools', description="Audit Jumlah Data per Tempat")
            input("\nTekan Enter untuk kembali...")
            
        elif pilihan == '5':
            print("\n[🌐] Menjalankan Server Web...")
            print("     (Tekan Ctrl+C di terminal ini untuk berhenti/kembali)")
            try:
                # Menjalankan Streamlit
                subprocess.run([PYTHON_EXE, "-m", "streamlit", "run", "streamlit_app.py"])
            except KeyboardInterrupt:
                print("\n\n✅ Web Server dimatikan. Kembali ke menu...")
                time.sleep(1)
                
        elif pilihan == '0':
            print("👋 Sampai jumpa!")
            sys.exit()
        else:
            print("❌ Pilihan tidak valid.")
            time.sleep(1)

if __name__ == "__main__":
    main_menu()