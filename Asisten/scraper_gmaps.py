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

# [BARU] Konfigurasi Scroll
SCROLL_BATCH_SIZE = 4  # Berapa kali scroll sebelum berhenti untuk ambil data
SCROLL_PIXEL = 600     # Jarak pixel sekali scroll (jangan terlalu besar biar gak loncat)

OWNER_KEYWORDS = [
    "terimakasih", "terima kasih", "thank you", "thanks", 
    "mohon maaf", "sorry", "apologize", 
    "respon dari pemilik", "response from the owner",
    "atas ulasannya", "atas masukannya", "atas kunjungan",
    "ditunggu kedatangannya", "maaf atas ketidaknyamanan"
]

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
    for keyword in OWNER_KEYWORDS:
        if keyword in text_lower:
            user_pronouns = ['saya', 'aku', 'gue', 'kami merasa', 'kita']
            if not any(p in text_lower for p in user_pronouns):
                return True 
    return False

def apply_sorting_newest(page):
    print("⚡ Mencoba mengurutkan 'Terbaru'...")
    try:
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
    print("⚠️ Gagal sorting / sudah default.")
    return False

def scrape_reviews():
    print("--- 🕵️‍♂️ GMAPS SCRAPER V8.2 (Batch Scroll + Precise Click) ---")
    
    nama_file = input("1. Nama Tempat: ").strip()
    if not nama_file: return
    folder_lokasi = input("2. Nama Folder Lokasi (misal: Sleman): ").strip() or "General"

    while True:
        raw_url = input("3. Masukkan URL Google Maps: ").strip()
        target_url, error = validate_url(raw_url)
        if error: print(f"❌ {error}")
        elif not target_url: return 
        else: break 

    # Persiapan File
    nama_file_clean = sanitize_filename(nama_file)
    full_dir = os.path.join(BASE_OUTPUT_DIR, folder_lokasi)
    os.makedirs(full_dir, exist_ok=True)
    output_csv = os.path.join(full_dir, f"{nama_file_clean}.csv")
    
    # Header CSV
    if not os.path.exists(output_csv):
        with open(output_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Rating', 'Waktu', 'Teks_Mentah', 'Tanggal_Scrap']) 
    
    print("-" * 40)
    print(f"🚀 Target: {nama_file_clean}") 
    print(f"💾 Auto-Save: ON (Tiap {AUTOSAVE_INTERVAL} data)")

    current_date_scrap = datetime.now().strftime('%Y-%m-%d')
    print(f"📅 Tanggal Scraping: {current_date_scrap}")

    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR, 
            headless=False,
            viewport={"width": 1280, "height": 720}, 
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        page = browser.pages[0]
        
        unique_reviews_hashes = set()
        unsaved_buffer = [] 
        total_collected = 0

        try:
            print("⏳ Membuka halaman...")
            page.goto(target_url, timeout=60000)
            time.sleep(3)

            # Navigasi & Sort
            print("👀 Mencari tombol Ulasan...")
            btn_ulasan = page.locator('button, div[role="tab"]').filter(has_text=re.compile(r'^(Ulasan|Reviews)$', re.IGNORECASE)).first
            if btn_ulasan.count() > 0:
                btn_ulasan.click()
                time.sleep(3)
            else:
                btn_link = page.locator('button').filter(has_text=re.compile(r'(Lihat semua ulasan|See all reviews)', re.IGNORECASE)).first
                if btn_link.count() > 0:
                    btn_link.click()
                    time.sleep(3)

            apply_sorting_newest(page)

            print("📜 Persiapan scrolling...")
            scrollable_div = page.locator('div.m6QErb[aria-label*="Ulasan"], div.m6QErb[aria-label*="Reviews"]').first
            if scrollable_div.count() == 0:
                scrollable_div = page.locator('div[role="main"] > div > div:nth-child(2)').first

            if scrollable_div.count() > 0: 
                scrollable_div.hover()
            else: 
                page.mouse.move(400, 400)

            last_count = 0
            stuck_count = 0
            
            print("⚡ Mulai mengambil data...")

            # --- LOOP UTAMA (PERBAIKAN STRATEGI) ---
            while True:
                
                # [UPDATE 1: BATCH SCROLLING]
                # Kita scroll beberapa kali DULU, baru ambil data.
                # Ini lebih cepat dan tidak patah-patah.
                for _ in range(SCROLL_BATCH_SIZE):
                    page.mouse.wheel(0, SCROLL_PIXEL)
                    # Jeda sangat pendek antar scroll (efek inertia mouse)
                    time.sleep(random.uniform(0.1, 0.25)) 
                
                # Jeda agak lama setelah batch scroll selesai (biar loading tuntas)
                time.sleep(random.uniform(0.8, 1.2))

                # [UPDATE 2: PERBAIKAN TOMBOL EXPAND (BIAR GAK KLIK USER)]
                try:
                    # Kita cari tombol yang teksnya BENAR-BENAR "Lainnya" atau "More"
                    # Dan pastikan tombol itu terlihat (visible)
                    expand_btns = page.locator('button').filter(has_text=re.compile(r'^(Lainnya|More|Selengkapnya|See more)$', re.IGNORECASE)).all()
                    for btn in expand_btns:
                        if btn.is_visible():
                            # Gunakan dispatchEvent click (bukan mouse click) agar akurat ke elemen
                            # Ini mencegah salah klik jika layout bergeser (user profile)
                            try:
                                btn.dispatch_event('click')
                            except:
                                # Fallback jika dispatch gagal, pakai click biasa tapi hati-hati
                                btn.click(force=True, timeout=100)
                            time.sleep(0.05) 
                except: pass

                # [EKSTRAKSI DATA (SAMA SEPERTI SEBELUMNYA)]
                visible_cards = page.locator('div.jftiEf').all()
                for card in visible_cards:
                    try:
                        text_els = card.locator('.wiI7pd').all()
                        full_text_list = []
                        
                        for t in text_els:
                            is_owner_box = t.evaluate("el => el.closest('.C69kGc') !== null")
                            content = t.inner_text().strip()
                            likely_owner = is_text_likely_owner(content)

                            if not is_owner_box and not likely_owner:
                                if content: full_text_list.append(content)
                        
                        text_full = " | ".join(full_text_list)

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

                # Auto Save
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

                # Stuck Check (Logika Elemen Terakhir)
                review_cards = page.locator('div.jftiEf')
                current_dom_count = review_cards.count()

                if current_dom_count == last_count:
                    stuck_count += 1
                    if current_dom_count > 0:
                        try:
                            # Scroll perlahan ke elemen terakhir
                            review_cards.last.scroll_into_view_if_needed(timeout=2000)
                            time.sleep(1)
                        except: pass
                    
                    if stuck_count > 20: 
                        print(f"\n⚠️ Tidak ada ulasan baru (Mentok). Berhenti.")
                        break
                else:
                    stuck_count = 0
                    if scrollable_div.count() > 0: scrollable_div.hover()

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