import time
import pandas as pd
from Asisten.smart_search import SmartSearchEngine
from Asisten.classic_search import ClassicSearchEngine

def run_battle():
    print("\n" + "="*60)
    print("🥊 BATTLE ROYAL: WORD2VEC (AI) vs TF-IDF (Classic)")
    print("="*60)

    # 1. Inisialisasi
    print("⏳ Memuat Word2Vec Engine...")
    w2v_engine = SmartSearchEngine()
    
    print("⏳ Memuat TF-IDF Engine...")
    tfidf_engine = ClassicSearchEngine()

    if not w2v_engine.is_ready:
        print("❌ Word2Vec Engine gagal dimuat.")
    if not tfidf_engine.is_ready:
        print("❌ TF-IDF Engine gagal dimuat.")
    
    if not w2v_engine.is_ready or not tfidf_engine.is_ready: return

    # 2. Skenario
    test_scenarios = [
        {"query": "pantai pasir putih", "type": "Keyword Spesifik"},
        {"query": "toilet bersih", "type": "Fasilitas"},
        {"query": "view bagus", "type": "Semantik (View=Pemandangan)"}, 
        {"query": "tempat adem", "type": "Bahasa Informal"}, 
        {"query": "tidak angker", "type": "Negasi"},
        {"query": "karimun jawa", "type": "Lokasi"}
    ]

    print(f"\n🚀 Memulai Pengujian...\n")
    header = f"{'QUERY':<20} | {'METODE':<10} | {'WAKTU':<8} | {'SKOR':<6} | {'TOP RESULT':<30}"
    print("-" * 100)
    print(header)
    print("-" * 100)

    results = []

    for case in test_scenarios:
        q = case['query']
        
        # W2V
        start = time.time()
        res_w2v = w2v_engine.search(q, top_k=1)
        dur_w2v = time.time() - start
        
        top_w2v = res_w2v.iloc[0]['Nama Tempat'] if not res_w2v.empty else "-"
        scr_w2v = res_w2v.iloc[0]['Skor Relevansi'] if not res_w2v.empty else 0

        # TF-IDF
        start = time.time()
        res_tf = tfidf_engine.search(q, top_k=1)
        dur_tf = time.time() - start
        
        top_tf = res_tf.iloc[0]['Nama Tempat'] if not res_tf.empty else "-"
        scr_tf = res_tf.iloc[0]['Skor Relevansi'] if not res_tf.empty else 0

        # Print
        print(f"{q:<20} | Word2Vec | {dur_w2v:.4f}s | {scr_w2v:<6} | {top_w2v[:30]}")
        print(f"{'':<20} | TF-IDF   | {dur_tf:.4f}s | {scr_tf:<6} | {top_tf[:30]}")
        print("-" * 100)

        results.append({
            "Query": q,
            "Winner": "W2V" if scr_w2v > scr_tf else "TF-IDF" if scr_tf > scr_w2v else "Draw"
        })

    # Kesimpulan
    w_wins = len([r for r in results if r['Winner'] == 'W2V'])
    t_wins = len([r for r in results if r['Winner'] == 'TF-IDF'])
    print(f"\n🏆 SKOR AKHIR: W2V ({w_wins}) - TF-IDF ({t_wins})")

if __name__ == "__main__":
    run_battle()