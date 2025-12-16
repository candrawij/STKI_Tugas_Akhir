# 🏕️ Smart Camp Advisor (Jateng & DIY)

**Sistem Rekomendasi Tempat Camping Cerdas Berbasis Hybrid AI (Word2Vec + Scorecard)**

Project ini adalah platform pencarian tempat camping yang menggabungkan kecerdasan buatan (**NLP Word2Vec**) dengan analisis data terstruktur (**Scorecard System**). Sistem ini dirancang untuk memahami konteks pencarian pengguna (bukan sekadar kata kunci) dan memberikan wawasan mendalam mengenai kualitas fasilitas berdasarkan ulasan nyata di Google Maps.

---

## 🚀 Fitur Unggulan (Key Features)

### 1. 🧠 Hybrid Search Engine (Semantic + Context)
* **Pencarian Semantik:** Menggunakan model **Word2Vec** untuk memahami makna kata. Jika pengguna mencari *"tempat sejuk"*, sistem akan merekomendasikan tempat dengan ulasan *"dingin"*, *"berkabut"*, atau *"asri"*.
* **Intent & Region Detection:** Otomatis mendeteksi niat pengguna (misal: "untuk keluarga", "adventure") dan memfilter wilayah (misal: "di Sleman", "di Semarang").

### 2. 📊 Smart Scorecard & Insight
* **Rapor Kualitas:** Menganalisis sentimen ulasan untuk memberikan skor (1-5) pada aspek krusial: **Toilet, Akses Jalan, Pemandangan, dan Pelayanan**.
* **AI Insight:** Memberikan ringkasan singkat satu kalimat mengenai keunikan tempat tersebut.
* **Badges:** Label otomatis seperti *"Ramah Anak"*, *"Cocok untuk Pemula"*, dll.

### 3. 💰 Estimasi Biaya Cerdas (Smart Costing)
* **Kategorisasi Harga:** Membaca data harga mentah dan memilahnya menjadi 4 kategori: **Biaya Wajib (Tiket/Parkir), Sewa Pokok (Tenda), Sewa Mewah, dan Layanan**.
* **Kalkulator Dasar:** Otomatis menghitung estimasi biaya minimal (Tiket Termurah + Parkir) untuk membantu perencanaan budget pengguna.

### 4. ⚙️ Automation Pipeline
* **Pusat Kendali Otomatis:** Script `pipeline.py` menangani seluruh siklus hidup data: dari Scraping -> Cleaning -> Training AI -> hingga Deployment.
* **Single Source Data:** Data terpusat di `info_tempat.csv` dan `corpus_master.csv` untuk menjaga konsistensi informasi.

### 5. 💻 Modern Admin Dashboard
* **Analitik Pencarian:** Memantau kata kunci yang paling sering dicari dan wilayah favorit pengguna secara *real-time*.
* **Manajemen Data:** Melihat total database tempat yang terdaftar.

---

## 🛠️ Teknologi (Tech Stack)

* **Bahasa:** Python 3.10+
* **Frontend:** Streamlit (dengan Custom CSS Glassmorphism)
* **Machine Learning:** Gensim (Word2Vec), Scikit-Learn (Cosine Similarity)
* **NLP Preprocessing:** Sastrawi (Stemming Bahasa Indonesia), NLTK
* **Data Scraper:** Playwright (Google Maps Reviews & Metadata)
* **Data Processing:** Pandas, NumPy

---

## 📂 Struktur Project

Berikut adalah anatomi file dalam project ini:

```plaintext
📦 Root/
├── 📜 pipeline.py             # [COMMANDER] Pusat kendali otomatisasi (Jalankan ini!)
├── 📜 streamlit_app.py        # [FRONTEND] Website utama (UI)
├── 📜 clean_data.py           # [CLEANER] Modul pembersih teks ulasan
├── 📜 train_w2v.py            # [TEACHER] Modul pelatih model AI
│
├── 📂 Asisten/                # [WORKERS] Skrip pendukung (Backend Workers)
│   ├── scraper_gmaps.py       # Robot scraping ulasan
│   ├── scraper_metadata.py    # Robot scraping foto & info
│   ├── konversi_data.py       # Integrator data harga & fasilitas
│   └── scorecard_generator.py # Analis sentimen & pembuat rapor
│
├── 📂 src/                    # [BRAIN] Logika Inti
│   ├── mesin_pencari.py       # Logika search engine & ranking
│   ├── preprocessing.py       # Pembersih teks & deteksi intent
│   └── utils.py               # Fungsi bantuan (Logging, Parsing)
│
├── 📂 Documents/              # [DATABASE] Penyimpanan Data
│   ├── corpus_master.csv      # Dataset ulasan bersih
│   ├── info_tempat.csv        # Database utama (Single Source of Truth)
│   ├── scorecards.json        # Hasil analisis rapor AI
│   └── input_harga.csv        # (Input Manual) Data harga mentah
│
└── 📂 Assets/                 # [MEMORY] Model Biner
    └── word2vec.model         # Otak AI yang sudah dilatih
```

🚀 Cara Menjalankan (Installation)
1. Persiapan Environment
Pastikan Python sudah terinstall. Gunakan Virtual Environment agar lebih rapi.

```
# Clone repository
git clone [https://github.com/username/project-kemah.git](https://github.com/username/project-kemah.git)
cd project-kemah

# Buat Virtual Environment
python -m venv .venv

# Aktifkan (Windows)
.venv\Scripts\activate
# Aktifkan (Mac/Linux)
source .venv/bin/activate
```

2. Install Library

```
pip install -r requirements.txt
playwright install  # Wajib untuk scraper berjalan
```

3. Jalankan Aplikasi
Gunakan pipeline.py sebagai pintu masuk utama untuk kemudahan manajemen.

```
python pipeline.py
```
Akan muncul menu interaktif:

Menu 1: Tambah data baru (Scraping).

Menu 2: Update Otak AI (Cleaning -> Training -> Scoring).

Menu 4: Jalankan Website.

Jika ingin menjalankan website langsung tanpa pipeline:

```
streamlit run streamlit_app.py
```

🔐 Akses Admin
Fitur dashboard admin terletak di Sidebar (sebelah kiri) pada aplikasi web.

Password Default: 1234

📝 Catatan Penting
Model AI: File model (Assets/word2vec.model) di-ignore oleh git untuk mencegah konflik versi library. Silakan jalankan Menu 2 (Update Otak AI) di pipeline.py saat pertama kali clone repo ini.

Browser Session: Folder cache browser (hasil scraping) otomatis diabaikan agar repo tetap ringan.
