import pandas as pd
import numpy as np
import torch
from Asisten.smart_search import SmartSearchEngine
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
from rouge_score import rouge_scorer
from bert_score import score as bert_score_func
import warnings

# Abaikan warning library
warnings.filterwarnings("ignore")

def calculate_metrics():
    print("⏳ Memuat AI Engine...")
    engine = SmartSearchEngine()
    
    if not engine.is_ready:
        print("❌ Engine belum siap (Model/Data missing).")
        return

    # --- 1. DATASET PENGUJIAN (GROUND TRUTH BUATAN) ---
    # Kita buat daftar query dan apa yang "seharusnya" atau "diharapkan" relevan
    # Format: {'query': 'kata kunci', 'reference': 'teks ideal yang kita harapkan muncul'}
    test_cases = [
        {
            "query": "kamar mandi bersih",
            # Kita asumsikan ulasan yang bagus harusnya mengandung kata-kata ini
            "reference": "toilet wangi kamar mandi bersih terawat air lancar" 
        },
        {
            "query": "pemandangan gunung merapi",
            "reference": "view gunung merapi terlihat jelas indah sekali pagi hari"
        },
        {
            "query": "akses jalan mobil mudah",
            "reference": "akses jalan aspal mulus bisa masuk mobil sampai lokasi parkir luas"
        },
        {
            "query": "tidak angker dan aman",
            "reference": "tempat nyaman aman penjaga ramah tidak seram lampu terang"
        },
        {
            "query": "pantai pasir putih",
            "reference": "pantai ngrumput pinggir laut pasir putih ombak tenang"
        }
    ]

    print(f"\n📊 MEMULAI EVALUASI PADA {len(test_cases)} SKENARIO UJI")
    print("="*60)

    results = []
    
    # Inisialisasi Scorer
    rouge = rouge_scorer.RougeScorer(['rouge1', 'rougeL'], use_stemmer=True)
    smooth = SmoothingFunction().method1

    for case in test_cases:
        query = case['query']
        ref = case['reference']
        
        # 1. Jalankan Pencarian
        df_res = engine.search(query, top_k=1) # Ambil 1 hasil teratas saja
        
        if df_res.empty:
            print(f"⚠️ Query '{query}' tidak menemukan hasil.")
            continue
            
        # Ambil teks ulasan dari hasil pencarian teratas (Candidate)
        # Kita ambil ulasan asli dari database yang dikembalikan sistem
        candidate = str(df_res.iloc[0]['Isi Ulasan']).lower()
        nama_tempat = df_res.iloc[0]['Nama Tempat']
        
        print(f"🔎 Query: '{query}'")
        print(f"   📍 Hasil: {nama_tempat}")
        print(f"   📝 Teks Hasil (Candidate): {candidate[:100]}...")
        print(f"   🎯 Teks Acuan (Reference): {ref}")

        # --- HITUNG METRIK ---

        # A. BLEU SCORE (N-Gram Overlap)
        # Mengukur seberapa banyak kata di query/ref muncul di hasil
        ref_tokens = ref.split()
        cand_tokens = candidate.split()
        bleu = sentence_bleu([ref_tokens], cand_tokens, smoothing_function=smooth)

        # B. ROUGE SCORE (Recall Oriented)
        # Mengukur seberapa banyak informasi dari referensi yang terambil
        r_scores = rouge.score(ref, candidate)
        rouge_1 = r_scores['rouge1'].fmeasure
        rouge_l = r_scores['rougeL'].fmeasure

        # C. BERTSCORE (Semantic Similarity) - OPTIONAL (Berat)
        # Menggunakan Pre-trained BERT untuk cek kemiripan makna
        try:
            P, R, F1 = bert_score_func([candidate], [ref], lang="id", verbose=False)
            bert_val = F1.mean().item()
        except Exception as e:
            bert_val = 0.0
            print("   (BERTScore skip - model not loaded)")

        # D. PERPLEXITY (Simulasi Sederhana)
        # Karena kita bukan GenAI, Perplexity dihitung berdasarkan "kebingungan" keyword match
        # Ini pendekatan kasar: Semakin tinggi similarity score sistem kita, semakin rendah perplexity (bingung)
        # Smart Search Score (0-100) kita konversi jadi error rate
        system_score = df_res.iloc[0]['Skor Relevansi'] / 100.0
        # Rumus buatan untuk simulasi: Jika score 100% (1.0), perplexity rendah (mendekati 1)
        # Jika score 0%, perplexity tinggi.
        simulated_perplexity = np.exp(1 - system_score) 

        # Simpan Hasil
        results.append({
            "Query": query,
            "BLEU": round(bleu, 4),
            "ROUGE-1": round(rouge_1, 4),
            "ROUGE-L": round(rouge_l, 4),
            "BERTScore": round(bert_val, 4),
            "Perplexity (Sim)": round(simulated_perplexity, 4),
            "System Confidence": system_score
        })
        print("-" * 60)

    # --- REKAPITULASI ---
    if results:
        df_eval = pd.DataFrame(results)
        print("\n📈 HASIL AKHIR EVALUASI (RATA-RATA):")
        print(f"BLEU Score   : {df_eval['BLEU'].mean():.4f}  (Range 0-1, Tinggi = Bagus)")
        print(f"ROUGE-1      : {df_eval['ROUGE-1'].mean():.4f}  (Range 0-1, Tinggi = Bagus)")
        print(f"BERTScore    : {df_eval['BERTScore'].mean():.4f}  (Range 0-1, Tinggi = Bagus)")
        print(f"Perplexity   : {df_eval['Perplexity (Sim)'].mean():.4f}  (Rendah = Bagus)")
        
        print("\n📋 DETAIL PER QUERY:")
        print(df_eval.to_string(index=False))
        
        # Analisis Jujur Otomatis
        avg_bleu = df_eval['BLEU'].mean()
        print("\n🧐 KESIMPULAN OTOMATIS:")
        if avg_bleu < 0.1:
            print("🔴 BURUK: Hasil pencarian secara tekstual sangat berbeda dengan ekspektasi.")
            print("   Alasan: Mungkin Word2Vec tidak menangkap konteks, atau ulasan di DB terlalu acak.")
        elif avg_bleu < 0.3:
            print("🟡 SEDANG: Ada beberapa kata kunci yang cocok, tapi banyak noise.")
        else:
            print("🟢 BAGUS: Hasil pencarian sangat relevan secara tekstual.")

if __name__ == "__main__":
    calculate_metrics()