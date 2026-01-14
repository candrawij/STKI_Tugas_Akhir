# 🏕️ CariKemah.id - Intelligent Camping Search Engine

Sistem rekomendasi tempat kemah cerdas berbasis **Hybrid AI (Word2Vec + Keyword)** untuk wilayah Yogyakarta & Jawa Tengah.

---

## 🚀 CARA MENJALANKAN

Pilih salah satu cara di bawah ini untuk memulai sistem:

### ✅ OPSI 1: WEB MODERN (UTAMA)
Tampilan antarmuka grafis yang modern dengan fitur lengkap (Search, Booking, Admin).

Web bisa diakses melalui URL berikut: `https://stki-tugas-akhir.streamlit.app/`

Atau bisa menggunakan cara lain yaitu:

1.  **Buka Terminal** di folder proyek.
2.  **Jalankan Perintah:**
    ```bash
    streamlit run streamlit_app.py
    ```
3.  Web otomatis terbuka di browser: `http://localhost:8501`

---

### ⚠️ OPSI 2: TERMINAL / CLI (CADANGAN)
Gunakan opsi ini jika Web/Browser mengalami kendala (Error/Lag). Fitur tetap 100% sama.

1.  **Pastikan Library Terinstall:**
    ```bash
    pip install -r requirements.txt
    ```
2.  **Jalankan Sistem:**
    ```bash
    python main_system.py
    ```

---

### 🛠️ TROUBLESHOOTING (RESET DATA)
Jika data pencarian atau database berantakan, reset ulang sistem dengan cara:

1.  Jalankan: `python pipeline.py`
2.  Pilih Menu **3** (Database Manager) -> Menu **1** (Reset Total).

---

## 🔑 AKUN DEMO

| Role | Username | Password |
| :--- | :--- | :--- |
| **Admin** | `admin` | `admin123` |
| **User** | `test` | `123` |

---


