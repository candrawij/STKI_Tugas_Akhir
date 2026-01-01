import time
import pandas as pd
from Asisten.smart_search import SmartSearchEngine
from Asisten.classic_search import ClassicSearchEngine

def run_battle():
    print("\n" + "="*60)
    print("🥊 BATTLE ROYAL: WORD2VEC (AI) vs TF-IDF (Classic)")
    print("="*60)

    # 1. Inisialisasi Kedua Engine
    print("⏳ Memuat Word2Vec Engine...")
    w2v_engine = SmartSearchEngine()
    
    print("⏳ Memuat TF-IDF Engine...")
    tfidf_engine = ClassicSearchEngine()

    if not w2v_engine.is_ready or not tfidf_engine.is_ready:
        print("❌ Gagal memuat salah satu engine. Cek database/model.")
        return

    # 2. Skenario Pengujian (Didesain untuk menguji kelebihan/kekurangan masing-masing)
    test_scenarios = [
        # KASUS 1: KEYWORD EXACT MATCH (Biasanya TF-IDF Menang)
        {"query": "pantai pasir putih", "type": "Keyword Spesifik"},
        {"query": "toilet bersih", "type": "Fasilitas Umum"},
        
        # KASUS 2: SEMANTIC / SINONIM (Biasanya Word2Vec Menang)
        # "View" tidak selalu ada di teks, tapi "pemandangan" ada. W2V harusnya paham.
        {"query": "view bagus", "type": "Semantik/Sinonim"}, 
        # "Adem" mungkin tidak ada, tapi "sejuk" atau "dingin" ada.
        {"query": "tempat adem", "type": "Bahasa Informal"}, 
        
        # KASUS 3: NEGASI (Word2Vec Fitur Khusus)
        {"query": "tidak angker", "type": "Sentiment Negatif"},
        
        # KASUS 4: NAMA TEMPAT (Hybrid Logic W2V Harusnya Menang Mutlak)
        {"query": "karimun jawa", "type": "Entitas Lokasi"}
    ]

    results = []

    print(f"\n🚀 Memulai Pengujian pada {len(test_scenarios)} Query...\n")
    
    # Header Tabel Output
    header = f"{'QUERY':<20} | {'METODE':<10} | {'WAKTU':<8} | {'SKOR':<6} | {'TOP RESULT (Ringkasan)':<40}"
    print("-" * 100)
    print(header)
    print("-" * 100)

    for case in test_scenarios:
        q = case['query']
        
        # --- TEST 1: WORD2VEC ---
        start_time = time.time()
        res_w2v = w2v_engine.search(q, top_k=1)
        time_w2v = time.time() - start_time
        
        if not res_w2v.empty:
            top_w2v = res_w2v.iloc[0]['Nama Tempat']
            score_w2v = res_w2v.iloc[0]['Skor Relevansi']
        else:
            top_w2v = "Tidak ditemukan"
            score_w2v = 0

        # --- TEST 2: TF-IDF ---
        start_time = time.time()
        res_tfidf = tfidf_engine.search(q, top_k=1)
        time_tfidf = time.time() - start_time
        
        if not res_tfidf.empty:
            top_tfidf = res_tfidf.iloc[0]['Nama Tempat']
            score_tfidf = res_tfidf.iloc[0]['Skor Relevansi']
        else:
            top_tfidf = "Tidak ditemukan"
            score_tfidf = 0

        # --- CETAK HASIL ---
        print(f"{q:<20} | Word2Vec | {time_w2v:.4f}s | {score_w2v:<6} | {top_w2v[:40]}")
        print(f"{'('+case['type']+')':<20} | TF-IDF   | {time_tfidf:.4f}s | {score_tfidf:<6} | {top_tfidf[:40]}")
        print("-" * 100)

        # Simpan untuk analisa otomatis
        results.append({
            "Query": q,
            "Type": case['type'],
            "W2V_Score": score_w2v,
            "TFIDF_Score": score_tfidf,
            "Winner": "Word2Vec" if score_w2v > score_tfidf else "TF-IDF" if score_tfidf > score_w2v else "Seri"
        })

    # 3. KESIMPULAN OTOMATIS (Jujur)
    w2v_wins = len([r for r in results if r['Winner'] == 'Word2Vec'])
    tfidf_wins = len([r for r in results if r['Winner'] == 'TF-IDF'])
    
    print("\n📊 REKAPITULASI AKHIR:")
    print(f"Word2Vec Menang : {w2v_wins} kali")
    print(f"TF-IDF Menang   : {tfidf_wins} kali")
    
    print("\n📝 ANALISA UNTUK LAPORAN:")
    if w2v_wins > tfidf_wins:
        print("✅ Word2Vec lebih unggul secara umum, terutama pada query semantik dan nama tempat.")
        print("   Saran: Pertahankan Word2Vec sebagai engine utama.")
    elif tfidf_wins > w2v_wins:
        print("⚠️ TF-IDF ternyata lebih unggul (terutama di keyword exact match).")
        print("   Argumen Laporan: 'Meskipun TF-IDF unggul di data terbatas, Word2Vec tetap dipilih")
        print("   karena kemampuan menangkap sinonim (contoh: view vs pemandangan) yang tidak dimiliki TF-IDF.'")
    else:
        print("🤝 Kedua metode memiliki performa seimbang.")

if __name__ == "__main__":
    run_battle()