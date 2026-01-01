import pandas as pd
from Asisten.smart_search import SmartSearchEngine
from Asisten.classic_search import ClassicSearchEngine

def calculate_advanced_metrics():
    print("🚀 MEMULAI EVALUASI TINGKAT LANJUT (METRIK STANDAR)")
    print("="*80)

    # 1. Load Engine
    ai = SmartSearchEngine()      # Word2Vec (Sekarang sudah pakai Kamus!)
    classic = ClassicSearchEngine() # TF-IDF

    if not ai.is_ready or not classic.is_ready:
        print("❌ Engine belum siap.")
        return

    # 2. GROUND TRUTH (KUNCI JAWABAN)
    # Kita definisikan secara manual tempat mana yang WAJIB muncul untuk query tertentu
    # Format: "Query": ["Kata Kunci di Nama Tempat yang Diharapkan"]
    ground_truth = {
        "pantai pasir putih": ["Pantai", "Wohkudu", "Ngrumput", "Gesing"],
        "gunung merapi": ["Merapi", "Klangon", "Kali Talang"],
        "hutan pinus": ["Pinus", "Mangunan", "Becici"],
        "kamar mandi bersih": ["Kali Talang", "Potrobayan", "Watu Mabur"], # Asumsi ulasan bagus ada di sini
        "view bagus": ["Nawang Jagad", "Pinus", "Watu Mabur"] # Uji sinonim "View" -> "Pemandangan"
    }

    # Fungsi Hitung Metrik per Query
    def evaluate_engine(engine, name):
        total_precision = 0
        total_recall = 0
        total_f1 = 0
        
        print(f"\n📊 Evaluasi Metode: {name}")
        print(f"{'Query':<25} | {'TP':<3} | {'FP':<3} | {'FN':<3} | {'Precision':<9} | {'Recall':<9} | {'F1-Score':<9}")
        print("-" * 80)

        for query, expected_keywords in ground_truth.items():
            # Search Top 5
            results = engine.search(query, top_k=5)
            
            retrieved_docs = []
            if not results.empty:
                retrieved_docs = results['Nama Tempat'].tolist()

            # Hitung TP, FP, FN
            # TP (True Positive): Hasil yang mengandung kata kunci yang diharapkan
            tp = 0
            for doc in retrieved_docs:
                # Cek apakah nama tempat mengandung salah satu keyword yang diharapkan
                if any(k.lower() in doc.lower() for k in expected_keywords):
                    tp += 1
            
            fp = len(retrieved_docs) - tp # Yang terambil tapi salah
            # FN (False Negative): Total yg harusnya ada (kita set max 5 agar adil) - yg ketemu
            # Kita asumsikan ada minimal 3 jawaban benar di database
            total_relevant_in_db = 3 
            fn = max(0, total_relevant_in_db - tp) 

            # Rumus
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0
            f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

            # Accumulate
            total_precision += precision
            total_recall += recall
            total_f1 += f1

            print(f"{query:<25} | {tp:<3} | {fp:<3} | {fn:<3} | {precision:.2f}      | {recall:.2f}      | {f1:.2f}")

        # Rata-rata
        n = len(ground_truth)
        avg_p = total_precision / n
        avg_r = total_recall / n
        avg_f1 = total_f1 / n
        
        print("-" * 80)
        print(f"🏆 RATA-RATA {name}: Precision={avg_p:.2f}, Recall={avg_r:.2f}, F1={avg_f1:.2f}")
        return avg_f1

    # Jalankan Evaluasi
    score_ai = evaluate_engine(ai, "Word2Vec (AI)")
    score_classic = evaluate_engine(classic, "TF-IDF (Classic)")

    print("\n📝 KESIMPULAN AKHIR:")
    if score_ai > score_classic:
        print("✅ Metode Word2Vec memiliki F1-Score lebih tinggi.")
    else:
        print("⚠️ Metode TF-IDF memiliki F1-Score lebih tinggi.")
        print("   (Catatan: Ini wajar untuk dataset kecil/spesifik).")

if __name__ == "__main__":
    calculate_advanced_metrics()