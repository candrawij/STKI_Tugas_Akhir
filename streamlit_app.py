import streamlit as st
import pandas as pd
import os
import json
import csv
import ast
import urllib.parse
from datetime import datetime

st.set_page_config(page_title="Cari Kemah AI", page_icon="🏕️", layout="wide")

# --- LOAD MODUL ---
try:
    from Asisten.smart_search import SmartSearchEngine
except ImportError:
    st.error("Modul Asisten/smart_search.py tidak ditemukan.")
    st.stop()

# --- PATH ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "Documents", "info_tempat.csv") 
SCORECARD_PATH = os.path.join(BASE_DIR, "Documents", "scorecards.json")
LOG_FOLDER = os.path.join(BASE_DIR, "Riwayat")
LOG_PATH = os.path.join(LOG_FOLDER, "riwayat_pencarian.csv")

# --- HELPER ---
def load_css():
    st.markdown("""
    <style>
        .sub-judul { font-size: 1.2em; color: #555; margin-bottom: 20px; }
        .badge { padding: 4px 8px; border-radius: 4px; color: white; font-size: 0.8em; margin-right: 5px; }
        .snippet-text { color: #666; font-style: italic; font-size: 0.9em; }
    </style>
    """, unsafe_allow_html=True)

def parse_metadata_column(val):
    try:
        if pd.isna(val) or val == "": return []
        if isinstance(val, (list, dict)): return val
        # Bersihkan string dan coba eval
        s = str(val).strip()
        if s.startswith("[") or s.startswith("{"):
            return ast.literal_eval(s)
        return []
    except: return []

def save_log(query, count):
    if not os.path.exists(LOG_FOLDER): os.makedirs(LOG_FOLDER)
    if not os.path.exists(LOG_PATH):
        with open(LOG_PATH, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(["waktu", "query", "hasil"])
    try:
        with open(LOG_PATH, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), query, count])
    except: pass

load_css()

# --- INIT ---
@st.cache_resource
def init_engine(): return SmartSearchEngine()

@st.cache_data
def load_db():
    sc = {}
    if os.path.exists(SCORECARD_PATH):
        try:
            with open(SCORECARD_PATH, "r") as f: sc = json.load(f)
        except: pass

    df = pd.DataFrame()
    if os.path.exists(DATA_PATH):
        try:
            df = pd.read_csv(DATA_PATH).fillna("")
            # Parsing Harga & Fasilitas
            col_hrg = next((c for c in df.columns if 'price' in c.lower() or 'harga' in c.lower()), None)
            col_fas = next((c for c in df.columns if 'facilit' in c.lower() or 'fasilitas' in c.lower()), None)
            
            if col_hrg: df['parsed_harga'] = df[col_hrg].apply(parse_metadata_column)
            else: df['parsed_harga'] = [[] for _ in range(len(df))]

            if col_fas: df['parsed_fasilitas'] = df[col_fas].apply(parse_metadata_column)
            else: df['parsed_fasilitas'] = [[] for _ in range(len(df))]
        except: pass
    return sc, df

engine = init_engine()
scorecards, df_info = load_db()

# --- SEARCH LOGIC ---
def run_search(query):
    if not query: return pd.DataFrame()
    
    if engine.is_ready:
        raw = engine.search(query, top_k=100) # Ambil banyak
        if raw.empty: return pd.DataFrame()
        
        # Deduplikasi (Ambil 1 per tempat)
        seen, unique = set(), []
        for _, r in raw.iterrows():
            if r['Nama Tempat'] not in seen:
                unique.append(r)
                seen.add(r['Nama Tempat'])
            if len(unique) >= 10: break
        return pd.DataFrame(unique)
    return pd.DataFrame()

# --- MATCHING LOGIC (FUZZY) ---
def find_info_row(name_query, df_db):
    if df_db.empty: return pd.Series()
    q = str(name_query).lower().strip()
    
    # 1. Coba Exact Match
    match = df_db[df_db['Nama_Tempat'].astype(str).str.lower().str.strip() == q]
    if not match.empty: return match.iloc[0]
    
    # 2. Coba Containment (Misal: "Ledok Sambi" in "Ledok Sambi Ecopark")
    # Cari baris dimana nama di DB mengandung query user ATAU sebaliknya
    for idx, row in df_db.iterrows():
        db_name = str(row['Nama_Tempat']).lower().strip()
        if q in db_name or db_name in q:
            return row
            
    return pd.Series()

# --- ADMIN ---
with st.sidebar:
    st.header("⚙️ Admin")
    if st.checkbox("Dashboard"):
        if st.text_input("Password", type="password") == "1234":
            st.success("Login Sukses")
            st.metric("Total Info", len(df_info))
            
            # BACA LOG DENGAN AMAN
            if os.path.exists(LOG_PATH):
                try:
                    # on_bad_lines='skip' akan melewati baris error (misal beda kolom)
                    df_log = pd.read_csv(LOG_PATH, on_bad_lines='skip')
                    st.dataframe(df_log.tail(10))
                except Exception as e:
                    st.error(f"Error baca log: {e}")

# --- UI ---
st.title("🏕️ Cari Kemah AI")
st.markdown('<p class="sub-judul">Temukan Hidden Gems di Jogja & Jateng</p>', unsafe_allow_html=True)

if 'last_df' not in st.session_state: st.session_state.last_df = pd.DataFrame()

c1, c2 = st.columns([3, 1])
with c1:
    with st.form("search"):
        q = st.text_input("Cari", placeholder="Misal: pinggir sungai jogja...")
        go = st.form_submit_button("Cari")
with c2:
    sort = st.selectbox("Urutkan", ["Relevansi AI", "Rating"], label_visibility="collapsed")

if go:
    res = run_search(q)
    st.session_state.last_df = res
    if q: save_log(q, len(res))

final_df = st.session_state.last_df
if sort == "Rating" and not final_df.empty:
    final_df = final_df.sort_values(by='Rating', ascending=False)

# --- RENDER ---
if final_df.empty and go: st.warning("Tidak ditemukan.")
elif not final_df.empty:
    if q: st.caption(f"Hasil untuk: **{q}**")
    
    for _, row in final_df.iterrows():
        nama = row['Nama Tempat']
        lokasi = row['Lokasi']
        ulasan = row['Isi Ulasan']
        
        # CARI METADATA (DENGAN LOGIKA BARU)
        meta = find_info_row(nama, df_info)
        
        alamat = lokasi
        foto = ""
        maps = "#"
        parsed_hrg, parsed_fas = [], []
        
        if not meta.empty:
            alamat = meta.get("Alamat") or meta.get("Lokasi") or alamat
            foto = meta.get("Photo_URL") or ""
            maps = meta.get("Gmaps_Link") or "#"
            parsed_hrg = meta.get("parsed_harga", [])
            parsed_fas = meta.get("parsed_fasilitas", [])

        sc = scorecards.get(nama)
        
        with st.container():
            c1, c2, c3 = st.columns([1.5, 2.5, 2])
            with c1:
                if str(foto).startswith("http"): st.image(foto, use_container_width=True)
                else: st.image(f"https://placehold.co/400x300/2E8B57/FFFFFF?text={urllib.parse.quote(nama)}", use_container_width=True)
                st.link_button("📍 Maps", maps, use_container_width=True)
            
            with c2:
                st.subheader(nama)
                st.caption(f"📍 {alamat}")
                
                # Snippet
                if len(ulasan) > 5:
                    snip = ulasan[:150] + "..." if len(ulasan) > 150 else ulasan
                    st.markdown(f"<div style='background:#f0f2f6;padding:8px;border-radius:4px;font-size:0.9em'><i>\"{snip}\"</i><br><small>📅 {row['Tanggal Ulasan']}</small></div>", unsafe_allow_html=True)
                
                # POPUP HARGA
                if st.button("💰 Cek Harga", key=f"btn_{nama}"):
                    @st.dialog(f"Info: {nama}")
                    def pop():
                        if not parsed_hrg: st.warning("Data harga belum tersedia.")
                        else:
                            st.write("**Daftar Harga:**")
                            for p in parsed_hrg:
                                if isinstance(p, dict):
                                    st.write(f"- {p.get('Item','Item')}: Rp {p.get('Harga','0')}")
                        
                        st.divider()
                        st.write("**Fasilitas:**")
                        if parsed_fas and isinstance(parsed_fas, list):
                            for f in parsed_fas:
                                val = list(f.values())[0] if isinstance(f, dict) else f
                                st.write(f"• {val}")
                        else: st.caption("-")
                    pop()

            with c3:
                if sc:
                    st.markdown("##### 📊 Rapor")
                    for asp in sc.get('aspects', {}).values():
                        if asp.get('mentions', 0) > 0:
                            ca, cb = st.columns([1,1])
                            ca.write(f"{asp['icon']} {asp['label']}")
                            st.progress(asp['score']/5)
                else: st.caption("Belum ada rapor.")
        st.divider()