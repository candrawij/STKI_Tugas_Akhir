import pandas as pd
import numpy as np
import warnings
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
from rouge_score import rouge_scorer

# Import Engine dari Folder Asisten
try:
    from Asisten.smart_search import SmartSearchEngine
except ImportError:
    print("❌ Gagal import SmartSearchEngine. Pastikan folder 'Asisten' ada.")
    exit()

warnings.filterwarnings("ignore")

def calculate_metrics():
    print("\n⏳ Memuat AI Engine...")
    engine = SmartSearchEngine()
    
    if not engine.is_ready:
        print("❌ Engine belum siap (Cek apakah word2vec.model ada?).")
        return

    # --- DATASET PENGUJIAN ---
    test_cases = [
        {"query": "kamar mandi bersih", "reference": "toilet wangi kamar mandi bersih terawat air lancar"},
        {"query": "pemandangan gunung merapi", "reference": "view gunung merapi terlihat jelas indah sekali pagi hari"},
        {"query": "akses jalan mobil mudah", "reference": "akses jalan aspal mulus bisa masuk mobil sampai lokasi parkir luas"},
        {"query": "tidak angker dan aman", "reference": "tempat nyaman aman penjaga ramah tidak seram lampu terang"},
        {"query": "pantai pasir putih", "reference": "pantai ngrumput pinggir laut pasir putih ombak tenang"}
    ]

    print(f"\n📊 MEMULAI EVALUASI PADA {len(test_cases)} SKENARIO UJI")
    print("="*60)

    results = []
    rouge = rouge_scorer.RougeScorer(['rouge1', 'rougeL'], use_stemmer=True)
    smooth = SmoothingFunction().method1

    for case in test_cases:
        query = case['query']
        ref = case['reference']
        
        # Search
        df_res = engine.search(query, top_k=1)
        
        if df_res.empty:
            print(f"⚠️ Query '{query}' tidak menemukan hasil.")
            continue
            
        candidate = str(df_res.iloc[0]['Isi Ulasan']).lower()
        nama_tempat = df_res.iloc[0]['Nama Tempat']
        score_sys = df_res.iloc[0]['Skor Relevansi']
        
        print(f"🔎 Query: '{query}' -> Hasil: {nama_tempat} ({score_sys}%)")

        # METRIK
        ref_tokens = ref.split()
        cand_tokens = candidate.split()
        bleu = sentence_bleu([ref_tokens], cand_tokens, smoothing_function=smooth)

        r_scores = rouge.score(ref, candidate)
        rouge_1 = r_scores['rouge1'].fmeasure
        rouge_l = r_scores['rougeL'].fmeasure

        # Simulasi Perplexity (Makin tinggi score sistem, makin rendah perplexity)
        simulated_perplexity = np.exp(1 - (score_sys / 100.0))

        results.append({
            "Query": query,
            "BLEU": round(bleu, 4),
            "ROUGE-1": round(rouge_1, 4),
            "ROUGE-L": round(rouge_l, 4),
            "Perplexity": round(simulated_perplexity, 4)
        })

    if results:
        df_eval = pd.DataFrame(results)
        print("\n📈 HASIL AKHIR EVALUASI (RATA-RATA):")
        print(df_eval.mean(numeric_only=True))
        print("\n📋 DETAIL:")
        print(df_eval)

if __name__ == "__main__":
    calculate_metrics()