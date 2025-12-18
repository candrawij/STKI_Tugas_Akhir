import csv
import time
import os
import re
import shutil
import random 
from datetime import datetime
from playwright.sync_api import sync_playwright

# ================= KONFIGURASI =================
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_OUTPUT_DIR = os.path.join(os.path.dirname(CURRENT_DIR), "Data_Mentah")
USER_DATA_DIR = os.path.join(CURRENT_DIR, "chrome_session") 
DEFAULT_MAX = 3000 
AUTOSAVE_INTERVAL = 100

SCROLL_BATCH_SIZE = 6   
SCROLL_PIXEL = 800      
USE_HEADLESS_MODE = True # Mode Gaib Aktif

OWNER_KEYWORDS = [
    "terimakasih", "terima kasih", "makasih", "trimakasih", "trims", "tq", "thanks", "thank you",
    "matur nuwun", "suwun", "hatur nuhun",
    "mohon maaf", "maaf", "sorry", "apologize", 
    "respon dari pemilik", "response from the owner",
    "atas ulasannya", "atas masukannya", "atas kunjungan", "atas review", "atas bintang",
    "ditunggu kedatangannya", "maaf atas ketidaknyamanan", "sehat selalu", "sukses selalu",
    "kak", "sis", "gan", "bund", "bapak", "ibu", "om", "tante" 
]

def clean_session_junk():
    print("🧹 Membersihkan sampah cache Chrome...")
    junk_paths = [
        os.path.join(USER_DATA_DIR, "Default", "Cache"),
        os.path.join(USER_DATA_DIR, "Default", "Code Cache"),
        os.path.join(USER_DATA_DIR, "Default", "Service Worker"),
    ]
    for path in junk_paths:
        if os.path.exists(path):
            try: shutil.rmtree(path)
            except: pass
    print("✨ Session bersih & siap.")

def sanitize_filename(name):
    clean_name = re.sub(r'[\\/*?:"<>|]', "", name).strip()
    return clean_name.title()

def validate_url(url):
    url = url.strip()
    if "googleusercontent" in url:
        return None, "Link Salah! Jangan pakai link gambar."
    if " " in url and "." not in url:
        return None, "Sepertinya Anda memasukkan NAMA tempat, bukan URL."
    if url.startswith("httpsmaps"): url = url.replace("httpsmaps", "https://maps")
    if url.startswith("httpmaps"): url = url.replace("httpmaps", "http://maps")
    if not url.startswith("http"): url = "https://" + url
    if "hl=" not in url:
        symbol = "&" if "?" in url else "?"
        url += f"{symbol}hl=id"
    return url, None

def extract_rating_flexible(card):
    try:
        star_el = card.locator('span[aria-label*="stars"], span[aria-label*="bintang"]').first
        if star_el.count() > 0:
            return star_el.get_attribute('aria-label').split(' ')[0].strip()
        text_el = card.locator('span:has-text("/5")').first
        if text_el.count() > 0:
            text = text_el.inner_text().strip()
            if '/' in text: return text.split('/')[0].strip()
    except: pass
    return "0"

def extract_time_flexible(card):
    try:
        time_el = card.locator('span').filter(has_text=re.compile(r'(lalu|ago|week|month|year|day|jam|menit|detik|bulan|tahun|hari)')).first
        if time_el.count() > 0: return time_el.inner_text().strip()
    except: pass
    return ""

def is_text_likely_owner(text):
    text_lower = text.lower()
    if len(text) < 5 and not re.search('[aeiou]', text_lower):
        return True 

    for keyword in OWNER_KEYWORDS:
        if keyword in text_lower:
            user_pronouns = ['saya', 'aku', 'gue', 'kami merasa', 'kita', 'keluarga saya']
            if not any(p in text_lower for p in user_pronouns):
                return True 
    return False

def apply_sorting_newest(page):
    print("⚡ Mencoba mengurutkan 'Terbaru'...")
    try:
        # Tunggu sebentar memastikan elemen load sempurna di headless
        time.sleep(2)
        sort_btn = page.locator('button[aria-label*="Sort"], button[aria-label*="Urutkan"]').first
        if sort_btn.count() > 0:
            sort_btn.click()
            time.sleep(1.5)
            newest_opt = page.locator('div[role="menuitemradio"]').filter(has_text=re.compile(r'(Terbaru|Newest)', re.IGNORECASE)).first
            if newest_opt.count() > 0:
                newest_opt.click()
                print("✅ Berhasil diurutkan: Terbaru")
                time.sleep(3)
                return True
    except: pass
    print("⚠️ Gagal sorting (Mungkin layout beda karena Headless).")
    return False

def scrape_reviews():
    clean_session_junk()
    
    print("--- 🚀 GMAPS SCRAPER V9.2 (Headless Fix) ---")
    
    nama_file = input("1. Nama Tempat: ").strip()
    if not nama_file: return
    folder_lokasi = input("2. Nama Folder Lokasi (misal: Sleman): ").strip() or "General"

    while True:
        raw_url = input("3. Masukkan URL Google Maps: ").strip()
        target_url, error = validate_url(raw_url)
        if error: print(f"❌ {error}")
        elif not target_url: return 
        else: break 

    nama_file_clean = sanitize_filename(nama_file)
    full_dir = os.path.join(BASE_OUTPUT_DIR, folder_lokasi)
    os.makedirs(full_dir, exist_ok=True)
    output_csv = os.path.join(full_dir, f"{nama_file_clean}.csv")
    
    if not os.path.exists(output_csv):
        with open(output_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Rating', 'Waktu', 'Teks_Mentah', 'Tanggal_Scrap']) 
    
    print("-" * 40)
    print(f"🚀 Target: {nama_file_clean}") 
    print(f"👻 Mode Gaib: {'ON' if USE_HEADLESS_MODE else 'OFF'}")

    current_date_scrap = datetime.now().strftime('%Y-%m-%d')

    with sync_playwright() as p:
        # [UPDATE PENTING DI SINI] 
        # Menambahkan User Agent agar dianggap browser Windows Asli, bukan Bot Headless
        browser = p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR, 
            headless=USE_HEADLESS_MODE, 
            viewport={"width": 1280, "height": 720}, 
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-gpu"]
        )
        page = browser.pages[0]

        page.route("**/*.{png,jpg,jpeg,svg,webp,gif,woff,woff2,ttf,otf}", lambda route: route.abort())
        
        unique_reviews_hashes = set()
        unsaved_buffer = [] 
        total_collected = 0

        try:
            print("⏳ Membuka halaman...")
            page.goto(target_url, timeout=60000)
            time.sleep(3)

            print("👀 Mencari tombol Ulasan...")
            time.sleep(2) 
            
            btn_ulasan = page.locator('button, div[role="tab"]').filter(has_text=re.compile(r'^(Ulasan|Reviews)$', re.IGNORECASE)).first
            if btn_ulasan.count() > 0:
                btn_ulasan.click()
                time.sleep(3)
            else:
                btn_link = page.locator('button').filter(has_text=re.compile(r'(Lihat semua ulasan|See all reviews)', re.IGNORECASE)).first
                if btn_link.count() > 0:
                    btn_link.click()
                    time.sleep(3)

            # Sorting sekarang harusnya berhasil karena User Agent sudah dipalsukan
            apply_sorting_newest(page)

            scrollable_div = page.locator('div.m6QErb[aria-label*="Ulasan"], div.m6QErb[aria-label*="Reviews"]').first
            if scrollable_div.count() == 0:
                scrollable_div = page.locator('div[role="main"] > div > div:nth-child(2)').first

            try:
                if scrollable_div.count() > 0: scrollable_div.hover()
                else: page.mouse.move(400, 400)
            except: pass

            last_count = 0
            stuck_count = 0
            
            print("⚡ Mulai mengambil data...")

            while True:
                for _ in range(SCROLL_BATCH_SIZE):
                    page.mouse.wheel(0, SCROLL_PIXEL)
                    time.sleep(random.uniform(0.05, 0.15)) 
                time.sleep(random.uniform(0.5, 0.8)) 

                try:
                    expand_btns = page.locator('button').filter(has_text=re.compile(r'^(Lainnya|More|Selengkapnya|See more)$', re.IGNORECASE)).all()
                    for btn in expand_btns:
                        if btn.is_visible():
                            try: btn.dispatch_event('click')
                            except: btn.click(force=True, timeout=50)
                except: pass

                visible_cards = page.locator('div.jftiEf').all()
                for card in visible_cards:
                    try:
                        text_els = card.locator('.wiI7pd').all()
                        full_text_list = []
                        
                        for t in text_els:
                            is_labeled_owner = t.evaluate("""el => {
                                let parent = el.closest('div');
                                if (!parent) return false;
                                return parent.innerText.includes('Respon dari pemilik') || parent.innerText.includes('Response from the owner');
                            }""")
                            if is_labeled_owner: continue 

                            content = t.inner_text().strip()
                            if is_text_likely_owner(content): continue
                            
                            if content: full_text_list.append(content)
                        
                        text_full = " ".join(full_text_list)

                        if text_full:
                            rating = extract_rating_flexible(card)
                            time_str = extract_time_flexible(card)
                            text_clean = text_full.replace('\n', ' ').replace('\r', ' ')
                            
                            review_signature = (rating, time_str, text_clean)
                            
                            if review_signature not in unique_reviews_hashes:
                                unique_reviews_hashes.add(review_signature)
                                unsaved_buffer.append([rating, time_str, text_clean, current_date_scrap]) 
                                total_collected += 1
                    except: continue

                if len(unsaved_buffer) >= AUTOSAVE_INTERVAL:
                    try:
                        with open(output_csv, 'a', newline='', encoding='utf-8') as f:
                            writer = csv.writer(f)
                            writer.writerows(unsaved_buffer)
                        print(f"   💾 Saved: {len(unsaved_buffer)} item. Total: {total_collected}")
                        unsaved_buffer = [] 
                    except Exception as e: print(f"⚠️ Gagal Save: {e}")

                print(f"   🌾 Terkumpul: {total_collected}...", end="\r")

                if total_collected >= DEFAULT_MAX:
                    print("\n✅ Target tercapai!")
                    break

                review_cards = page.locator('div.jftiEf')
                current_dom_count = review_cards.count()

                if current_dom_count == last_count:
                    stuck_count += 1
                    if current_dom_count > 0:
                        try:
                            review_cards.last.scroll_into_view_if_needed(timeout=1000)
                        except: pass
                    
                    if stuck_count > 25: 
                        print(f"\n⚠️ Tidak ada ulasan baru (Mentok). Berhenti.")
                        break
                else:
                    stuck_count = 0
                    if scrollable_div.count() > 0: 
                        try: scrollable_div.hover()
                        except: pass

                last_count = current_dom_count

        except KeyboardInterrupt:
            print("\n\n🛑 DETEKSI CTRL+C. Menghentikan loop...")
        
        except Exception as e:
            print(f"\n⚠️ INTERUPSI: {e}")

        finally:
            print("\n🧹 FINALISASI...")
            if unsaved_buffer:
                try:
                    with open(output_csv, 'a', newline='', encoding='utf-8') as f:
                        writer = csv.writer(f)
                        writer.writerows(unsaved_buffer)
                    print(f"✅ Sisa data tersimpan.")
                except Exception as e:
                    print(f"❌ Gagal simpan sisa: {e}")

            print(f"📊 Total: {total_collected}. Lokasi: {output_csv}")
            try: browser.close()
            except: pass 
            print("🏁 Selesai.")

if __name__ == "__main__":
    scrape_reviews()