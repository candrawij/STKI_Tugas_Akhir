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
    print("="*60)
    print("   🏕️  CAMPGROUND AI - MISSION CONTROL (V4.0 Hybrid)")
    print("   (Scraping -> CSV Pipeline -> Database -> AI)")
    print("="*60)

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

# ================= MENU 1: HUNTING DATA (LAMA) =================
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

# ================= MENU 2: PREPARE CSV (LAMA) =================
def menu_update_csv():
    print_header()
    print("🧠 MODE UPDATE CSV (DATA MENTAH -> CSV MASTER)")
    print("⚠️  Gunakan ini jika Anda baru selesai Scraping.")
    print("-" * 30)
    confirm = input("Mulai proses update CSV? (y/n): ").lower()
    
    if confirm != 'y': return

    start_time = time.time()
    
    # 1. CLEANING DATA
    if not run_script('clean_data.py', folder='', description="1. Membersihkan & Filter Data Mentah"): return

    # 2. MERGING
    if not run_script('merge_corpus.py', folder='Asisten', description="2. Menggabungkan Data (Merge & Deduplicate)"): return

    # 3. KONVERSI METADATA
    if not run_script('konversi_data.py', folder='Asisten', description="3. Integrasi Harga & Fasilitas"): return

    # 4. GENERATE SCORECARD
    if not run_script('scorecard_generator.py', folder='Asisten', description="4. Membuat Rapor & Insight"): return

    print("\n✅ CSV Master Siap! Sekarang Anda bisa lanjut ke Menu 3 (Database).")
    input("\nTekan Enter untuk kembali...")

# ================= MENU 3: DATABASE & AI MANAGER (BARU) =================
def menu_database_ai():
    while True:
        print_header()
        print("💾 DATABASE & AI MANAGER (SISTEM BARU)")
        print("-" * 30)
        print("1. 🔥 ONE-CLICK RESET (Hapus DB -> Import CSV -> Train AI)")
        print("2. 📥 Import CSV ke Database Saja")
        print("3. 🧠 Train AI (Word2Vec) Saja")
        print("0. Kembali")
        
        pilihan = input("\nPilih menu (0-3): ").strip()
        
        if pilihan == '1':
            confirm = input("⚠️  HAPUS 'camping.db' dan buat ulang dari CSV? (y/n): ").lower()
            if confirm == 'y':
                start = time.time()
                # 1. Hapus DB Lama
                if os.path.exists("camping.db"):
                    os.remove("camping.db")
                    print("\n🗑️  Database lama dihapus.")
                
                # 2. Setup Database (Tabel Baru)
                # Kita panggil scripts/setup_db.py jika ada, atau andalkan db_handler
                if os.path.exists("scripts/setup_db.py"):
                    run_script("scripts/setup_db.py", description="1. Membuat Tabel Database")
                else:
                    print("ℹ️  Mengandalkan inisialisasi otomatis db_handler...")

                # 3. Import CSV ke DB (PENTING)
                # Pastikan file update_db.py ada (script migrasi yang kita buat sebelumnya)
                if run_script("scripts/update_db.py", description="2. Mengimpor Data dari CSV ke SQLite"):
                    # 4. Train AI
                    run_script("train_w2v.py", description="3. Melatih Kecerdasan AI")
                else:
                    print("❌ Gagal Import: Pastikan 'scripts/update_db.py' ada!")

                print(f"\n✨ Selesai dalam {time.time()-start:.2f} detik!")
                input("Tekan Enter...")

        elif pilihan == '2':
            run_script("scripts/update_db.py", description="Update Data Database dari CSV")
            input("Tekan Enter...")

        elif pilihan == '3':
            run_script("train_w2v.py", description="Training Word2Vec dari Database")
            input("Tekan Enter...")

        elif pilihan == '0':
            break

# ================= MENU UTAMA =================
def main_menu():
    while True:
        print_header()
        print("MENU UTAMA:")
        print("1. 🕵️‍♂️  Hunting Data (Scraping)")
        print("2. 🧹  Siapkan Data CSV (Pipeline Lama)")
        print("3. 💾  Kelola Database & AI (Pipeline Baru)")
        print("4. 🧪  Tes Kepintaran AI (Manual)")
        print("5. 📊  Audit Kualitas Data")
        print("6. 🌐  Jalankan Website (Streamlit)")
        print("0. Keluar")
        
        pilihan = input("\nPilih menu (0-6): ").strip()
        
        if pilihan == '1':
            menu_hunting()
            
        elif pilihan == '2':
            menu_update_csv()
            
        elif pilihan == '3':
            menu_database_ai()
            
        elif pilihan == '4':
            run_script('cek_otak_ai.py', folder='Tools', description="Tes Asosiasi Kata")
            input("\nTekan Enter untuk kembali...")

        elif pilihan == '5':
            run_script('cek_data_corpus.py', folder='Tools', description="Audit Jumlah Data per Tempat")
            input("\nTekan Enter untuk kembali...")
            
        elif pilihan == '6':
            print("\n[🌐] Menjalankan Server Web...")
            print("     (Tekan Ctrl+C di terminal ini untuk berhenti/kembali)")
            try:
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