import pandas as pd
from Asisten.smart_search import SmartSearchEngine
from Asisten.classic_search import ClassicSearchEngine

def calculate_advanced_metrics():
    print("\n🚀 MEMULAI EVALUASI TINGKAT LANJUT (PRECISION/RECALL)")
    print("="*80)

    ai = SmartSearchEngine()
    classic = ClassicSearchEngine()

    if not ai.is_ready or not classic.is_ready: return

    # Ground Truth: Daftar keyword yang WAJIB muncul di nama tempat untuk query tertentu
    ground_truth = {
        "pantai": ["Pantai", "Ngrumput", "Wohkudu"],
        "gunung": ["Gunung", "Merapi", "Sumbing"],
        "pinus": ["Pinus", "Hutan"],
        "kamar mandi": ["Camp", "Bumi Perkemahan"], # Asumsi tempat kemah resmi punya WC
    }

    def evaluate(engine, label):
        print(f"\n📊 Evaluasi: {label}")
        total_p, total_r, total_f1 = 0, 0, 0
        
        print(f"{'Query':<15} | {'P':<5} | {'R':<5} | {'F1':<5}")
        print("-" * 40)

        for q, keywords in ground_truth.items():
            res = engine.search(q, top_k=5)
            retrieved = res['Nama Tempat'].tolist() if not res.empty else []
            
            # Hitung True Positive (Tempat yang namanya mengandung keyword)
            tp = sum(1 for r in retrieved if any(k.lower() in r.lower() for k in keywords))
            
            # Hitung Metrics
            precision = tp / len(retrieved) if retrieved else 0
            # Kita anggap total relevant docs di DB minimal 3
            recall = tp / 3 
            f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
            
            total_p += precision
            total_r += recall
            total_f1 += f1
            
            print(f"{q:<15} | {precision:.2f}  | {recall:.2f}  | {f1:.2f}")

        n = len(ground_truth)
        print("-" * 40)
        print(f"🏆 RATA-RATA: F1-Score = {total_f1/n:.2f}")

    evaluate(ai, "Word2Vec")
    evaluate(classic, "TF-IDF")

if __name__ == "__main__":
    calculate_advanced_metrics()