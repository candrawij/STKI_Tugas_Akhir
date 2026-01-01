import os
import shutil

BASE_DIR = os.getcwd()

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

def move(src, dst):
    if os.path.exists(src):
        ensure_dir(os.path.dirname(dst))
        shutil.move(src, dst)
        print(f"✓ Moved: {src} → {dst}")
    else:
        print(f"- Skipped (not found): {src}")

# =========================
# CREATE TARGET STRUCTURE
# =========================
dirs = [
    "src/search_engine",
    "src/database",
    "src/evaluation",
    "src/training",
    "data/raw",
    "data/processed",
    "data/dictionaries",
    "data/backups",
    "models",
    "assets/images"
]

for d in dirs:
    ensure_dir(d)

# =========================
# MOVE PYTHON LOGIC
# =========================
search_engine_files = [
    "classic_search.py",
    "smart_search.py",
    "preprocessing.py",
    "aspect_definitions.py",
    "utils.py"
]

for f in search_engine_files:
    move(f"Asisten/{f}", f"src/search_engine/{f}")

move("Asisten/db_handler.py", "src/database/db_handler.py")

evaluation_files = [
    "evaluation.py",
    "advanced_evaluation.py",
    "compare_evaluation.py",
    "scorecard_generator.py",
    "cek_akurasi.py"
]

for f in evaluation_files:
    move(f, f"src/evaluation/{f}")

training_files = [
    "train_w2v.py",
    "merge_corpus.py",
    "pipeline.py"
]

for f in training_files:
    move(f, f"src/training/{f}")

# =========================
# MOVE DATA
# =========================
move("Documents", "data/processed")
move("Kamus", "data/dictionaries")
move("Data_Mentah", "data/raw")
move("Documents/Backup_Master", "data/backups")

# =========================
# MOVE MODELS & ASSETS
# =========================
move("Assets/word2vec.model", "models/word2vec.model")
move("logo.png", "assets/images/logo.png")
move("tent-night-wide.jpg", "assets/images/tent-night-wide.jpg")
move("style.css", "assets/style.css")

print("\n✅ Restrukturisasi selesai.")
print("⚠️ Jangan lupa cek ulang import di Python (from src....)")
