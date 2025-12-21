import streamlit as st
import pandas as pd
import os
import json
import base64
import urllib.parse

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(
    page_title="CariKemah", 
    page_icon="⛺", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. LOAD MODUL ---
try:
    from Asisten.smart_search import SmartSearchEngine
    from Asisten.db_handler import db 
except ImportError: st.stop()

# --- 3. ASSETS & CSS ---
def get_base64_of_bin_file(bin_file):
    try:
        with open(bin_file, 'rb') as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except: return ""

def set_bg(png_file):
    bin_str = get_base64_of_bin_file(png_file)
    if bin_str:
        st.markdown(f'''
        <style>
        [data-testid="stAppViewContainer"] {{
            /* Overlay Hitam 85% (Lebih Gelap) agar teks mudah dibaca */
            background-image: linear-gradient(rgba(0, 0, 0, 0.85), rgba(0, 0, 0, 0.95)), url("data:image/jpg;base64,{bin_str}");
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }}
        </style>
        ''', unsafe_allow_html=True)

set_bg('tent-night-wide.jpg')

if os.path.exists('style.css'):
    with open('style.css', encoding='utf-8') as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# --- 4. ENGINE & DATA ---
@st.cache_resource
def init_engine(): return SmartSearchEngine()

@st.cache_data
def load_scorecards():
    path = "Documents/scorecards.json"
    if os.path.exists(path):
        try:
            # [FIX] Syntax Multi-line agar tidak error
            with open(path, encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

engine = init_engine()
scorecards = load_scorecards()

# --- 5. LOGIC PENCARIAN ---
if 'search_results' not in st.session_state: st.session_state.search_results = pd.DataFrame()
if 'last_query' not in st.session_state: st.session_state.last_query = ""

def run_search():
    query = st.session_state.query_input
    if query:
        with st.spinner("Sedang mencari..."):
            if engine.is_ready:
                # Engine sekarang otomatis pakai CSV Kamus & Intent
                res = engine.search(query, top_k=60)
                if not res.empty:
                    st.session_state.search_results = res.sort_values('Skor Relevansi', ascending=False).drop_duplicates(subset=['Nama Tempat'], keep='first')
                    st.session_state.last_query = query
                    try: db.log_search(query, len(st.session_state.search_results))
                    except: pass
                else:
                    st.session_state.search_results = pd.DataFrame()
            else: st.error("AI belum siap.")

# Helper Formatter
def format_rp(angka): return f"Rp {int(angka):,}".replace(",", ".")

# Helper Modal
@st.dialog("Informasi Lengkap", width="large")
def show_details(row, detail, sc_data):
    st.markdown(f"<h2 style='text-align:center;'>{row['Nama Tempat']}</h2>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align:center; color:#ccc;'>📍 {detail['info'].get('lokasi', '-')}</p>", unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["ℹ️ Info Umum", "💰 Rincian Biaya", "🤖 Analisis Kualitas"])
    
    with tab1:
        st.markdown("### Fasilitas")
        if detail['fasilitas']:
            st.markdown("".join([f"<span class='fas-tag'>{f}</span>" for f in detail['fasilitas']]), unsafe_allow_html=True)
        else: st.warning("Belum ada data fasilitas.")
        
        st.markdown("### Lokasi")
        link = detail['info'].get('gmaps_link', '#')
        st.link_button("🗺️ Buka Google Maps", link, use_container_width=True)

    with tab2:
        if detail['harga']:
            df_h = pd.DataFrame(detail['harga'])
            if 'kategori' in df_h.columns:
                cats = sorted(df_h['kategori'].unique())
                for cat in cats:
                    st.markdown(f"**{cat.title() if cat else 'Lainnya'}**")
                    items = df_h[df_h['kategori'] == cat]
                    for _, it in items.iterrows():
                        c1, c2 = st.columns([3, 1])
                        c1.write(it['item'])
                        c2.write(f"**{format_rp(it['harga'])}**")
                    st.divider()
            else: st.dataframe(df_h)
        else: st.info("Info harga belum tersedia.")

    with tab3:
        st.info("ℹ️ Skor ini dari analisis sentimen ulasan pengunjung.")
        if sc_data and 'aspects' in sc_data:
            for key, val in sc_data['aspects'].items():
                if val['mentions'] > 0:
                    with st.container(border=True):
                        c1, c2 = st.columns([1, 4])
                        c1.markdown(f"## {val['icon']}")
                        c2.markdown(f"**{val['label']}**")
                        c2.progress(val['score']/5)
                        c2.caption(f"⭐ Skor: {val['score']} / 5.0 (Berdasarkan {val['mentions']} ulasan)")
        else: st.warning("Belum cukup data ulasan.")

# --- 6. UI UTAMA ---
st.markdown("""
<div class="hero-container">
    <h1 class="hero-title">CariKemah</h1>
    <p class="hero-subtitle">Temukan tempat camping terbaik di Jogja & Jateng</p>
</div>
""", unsafe_allow_html=True)

c_spacer1, c_inp, c_spacer2 = st.columns([1, 2, 1])
with c_inp:
    st.text_input("Search", placeholder="Ketik 'Semua', 'Jogja', atau 'Pinggir sungai'...", key="query_input", on_change=run_search, label_visibility="collapsed")
    st.markdown("<p style='text-align:center; font-size:0.9em; color:#ddd;'>Tekan Enter untuk mencari</p>", unsafe_allow_html=True)

# HASIL
df = st.session_state.search_results
if not df.empty:
    st.divider()
    st.markdown(f"### ✨ Hasil Pencarian: {len(df)} Tempat")
    
    for i, (_, row) in enumerate(df.iterrows()):
        nama = row['Nama Tempat']
        p_id = db.get_place_by_name(nama)
        detail = db.get_place_details(p_id) if p_id else {'info':{}, 'harga':[], 'fasilitas':[]}
        info = detail['info']
        sc = scorecards.get(nama, {})
        
        foto = info.get('photo_url') 
        if not foto: foto = f"https://placehold.co/800x450/222/FFF?text={urllib.parse.quote(nama)}"

        with st.container(border=True):
            col_img, col_desc, col_act = st.columns([2, 4, 1.5])
            with col_img:
                st.image(foto, use_container_width=True)
            with col_desc:
                st.subheader(nama)
                st.markdown(f"<span class='match-pill'>{row['Skor Relevansi']}% Sesuai</span>", unsafe_allow_html=True)
                st.caption(f"📍 {info.get('lokasi', row['Lokasi'])}")
                st.markdown(f"<div class='mini-review'>💬 \"{str(row['Isi Ulasan'])[:150]}...\"</div>", unsafe_allow_html=True)
            with col_act:
                st.write("")
                st.write("")
                if st.button("📄 Lihat Detail", key=f"btn_{i}", type="primary", use_container_width=True):
                    show_details(row, detail, sc)

elif st.session_state.last_query:
    st.warning("Tidak ditemukan hasil yang cocok.")