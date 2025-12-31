import streamlit as st
import pandas as pd
import base64
import os
import urllib.parse
import time
from datetime import datetime

# --- 1. CONFIG & CSS ---
st.set_page_config(layout="wide", page_title="CariKemah.id", page_icon="⛺")

# Fungsi Convert Gambar Lokal ke Base64 (Wajib untuk CSS Background)
def get_img_as_base64(file):
    try:
        with open(file, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except: return ""

def format_rp(angka): 
    return f"Rp {int(angka):,}".replace(",", ".")

# Load Database Handler
try:
    from Asisten.db_handler import db
    from Asisten.smart_search import SmartSearchEngine
except ImportError: st.stop()

# Session State Init
if 'user' not in st.session_state: st.session_state.user = None
if 'show_login' not in st.session_state: st.session_state.show_login = False
if 'query_input' not in st.session_state: st.session_state.query_input = ""

# Load CSS & Inject Background Image
bg_img = get_img_as_base64("tent-night-wide.jpg") if os.path.exists("tent-night-wide.jpg") else ""
logo_img = get_img_as_base64("logo.png") if os.path.exists("logo.png") else ""

# CSS Injection dengan Variabel Python
st.markdown(f"""
<style>
    /* Import Style Eksternal */
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');
</style>
""", unsafe_allow_html=True)

# Baca file style.css untuk layouting
if os.path.exists('style.css'):
    with open('style.css') as f:
        css_code = f.read()
        # Inject Background Image URL ke dalam CSS Class .hero-wrapper
        css_code += f"""
        .hero-wrapper {{
            background-image: url("data:image/jpg;base64,{bg_img}");
        }}
        """
        st.markdown(f'<style>{css_code}</style>', unsafe_allow_html=True)

# --- 2. ENGINE LOAD ---
@st.cache_resource
def init_engine(): return SmartSearchEngine()

engine = init_engine()

# --- 3. NAVBAR COMPONENT (HYBRID HTML + STREAMLIT) ---
def render_navbar():
    # Container Navbar (Kita pakai columns agar tombol Login bisa interaktif)
    with st.container():
        c_logo, c_space, c_menu = st.columns([1, 6, 2])
        
        with c_logo:
            # Tampilkan Logo atau Teks
            if os.path.exists("logo.png"):
                st.image("logo.png", width=120)
            else:
                st.markdown("### ⛺ CariKemah")
        
        with c_menu:
            # Logic Tombol Login/User
            if st.session_state.user:
                u = st.session_state.user
                st.write(f"👤 **{u['username']}**")
                if st.button("Keluar", key="logout_btn"):
                    st.session_state.user = None
                    st.rerun()
            else:
                # Tombol Masuk & Daftar
                col_login, col_reg = st.columns(2)
                with col_login:
                    if st.button("Masuk"):
                        st.session_state.show_login = True
                        st.rerun()
                with col_reg:
                    # Tombol daftar dummy
                    st.button("Daftar", type="primary")

# --- 4. MODAL LOGIN (Overlay) ---
@st.dialog("Login ke CariKemah")
def show_login_modal():
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")
    if st.button("Masuk Sekarang", type="primary", use_container_width=True):
        res = db.verify_login(u, p)
        if res:
            st.session_state.user = res
            st.session_state.show_login = False
            st.rerun()
        else:
            st.error("Username/Password salah!")

# --- 5. MODAL DETAIL & BOOKING (FUNGSI PENTING YANG HILANG TADI) ---
@st.dialog("Detail & Reservasi", width="large")
def show_details(row, detail, sc_data):
    info = detail['info']
    
    # Header: Nama & Lokasi
    st.markdown(f"## {row['Nama Tempat']}")
    st.markdown(f"📍 {info.get('lokasi', '-')}")
    
    # Foto Utama
    foto_url = info.get('photo_url')
    if not foto_url: 
        safe_name = urllib.parse.quote(row['Nama Tempat'])
        foto_url = f"https://placehold.co/800x400/222/FFF?text={safe_name}"
    
    st.image(foto_url, use_container_width=True)

    # Tabs Info
    tab1, tab2, tab3 = st.tabs(["ℹ️ Info & Fasilitas", "💰 Harga", "📝 Booking"])
    
    with tab1:
        c1, c2 = st.columns([2, 1])
        with c1:
            st.markdown("### Fasilitas")
            if detail['fasilitas']:
                # Render chips fasilitas
                st.write(", ".join(detail['fasilitas']))
            else:
                st.info("Data fasilitas belum tersedia.")
        
        with c2:
            st.markdown("### Rating")
            rate = info.get('rating_gmaps', 0)
            st.markdown(f"**⭐ {rate} / 5.0**")
            st.caption("Sumber: Google Maps")
            
            if 'gmaps_link' in info and info['gmaps_link']:
                st.link_button("🗺️ Buka Peta", info['gmaps_link'], use_container_width=True)

        st.divider()
        st.markdown("### Ulasan Relevan")
        st.info(f"\"{str(row['Isi Ulasan'])[:300]}...\"")

    with tab2:
        if detail['harga']:
            # Tampilkan Tabel Harga Rapi
            df_h = pd.DataFrame(detail['harga'])[['item', 'harga']]
            df_h['harga_fmt'] = df_h['harga'].apply(format_rp)
            st.dataframe(df_h[['item', 'harga_fmt']], column_config={"item": "Jenis", "harga_fmt": "Biaya"}, hide_index=True, use_container_width=True)
        else:
            st.warning("Informasi harga belum tersedia.")

    # FORM BOOKING LOGIS (SEPERTI TERMINAL)
    with tab3:
        if st.session_state.user is None:
            st.warning("🔒 Silakan Login terlebih dahulu untuk memesan.")
        else:
            st.markdown("### Form Pemesanan")
            
            # 1. PILIH PAKET (Dropdown)
            price_list = detail['harga']
            if price_list:
                options = [f"{p['item']} | {format_rp(p['harga'])}" for p in price_list]
                selected_opt = st.selectbox("Pilih Jenis Tiket/Paket:", options)
                
                # Cari harga asli dari pilihan
                idx = options.index(selected_opt)
                selected_item_name = price_list[idx]['item']
                selected_price = int(price_list[idx]['harga'])
            else:
                st.warning("Data harga kosong. Menggunakan default.")
                selected_item_name = "Tiket Masuk (Estimasi)"
                selected_price = 15000
                st.write(f"**Harga:** {format_rp(selected_price)}")

            # 2. INPUT DATA
            c_date, c_qty = st.columns(2)
            with c_date:
                tgl = st.date_input("Tanggal Check-in", min_value=datetime.today())
            with c_qty:
                qty = st.number_input("Jumlah (Orang/Unit)", min_value=1, value=1)

            # 3. KALKULASI & SUBMIT
            total = selected_price * qty
            st.divider()
            
            st.markdown(f"**Total Estimasi: {format_rp(total)}**")
            
            if st.button("✅ Ajukan Booking Sekarang", type="primary", use_container_width=True):
                user_id = st.session_state.user['id']
                tempat_id = detail['info'].get('id')
                if not tempat_id: tempat_id = db.get_place_by_name(row['Nama Tempat'])
                
                ok = db.add_booking(user_id, tempat_id, str(tgl), qty, total)
                
                if ok:
                    st.success("🎉 Berhasil! Status Pesanan: PENDING.")
                    time.sleep(2)
                    st.rerun()
                else:
                    st.error("Gagal menyimpan pesanan.")

# --- 6. HERO SECTION & SEARCH LOGIC ---
def render_hero():
    # HTML Wrapper
    st.markdown("""
    <div class="hero-wrapper">
        <div class="hero-overlay"></div>
        <div class="hero-content">
            <div class="hero-title">Explore, Camp, Connect!</div>
            <div class="hero-subtitle">Temukan ribuan tempat camping terbaik di Jawa Tengah & DIY</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # SEARCH WIDGET
    c1, c2, c3 = st.columns([1, 6, 1])
    with c2:
        with st.container(border=True):
            st.markdown("##### 🔍 Mau kemah di mana?")
            
            row_in1, row_in2, row_btn = st.columns([3, 2, 1.5])
            with row_in1:
                query = st.text_input("Destinasi", placeholder="Cth: Pantai Jogja, Kaliurang...", label_visibility="collapsed", key="search_box")
            with row_in2:
                kategori = st.selectbox("Kategori", ["Semua", "Gunung", "Pantai", "Hutan", "Glamping"], label_visibility="collapsed")
            with row_btn:
                if st.button("Cari Tempat", type="primary", use_container_width=True):
                    st.session_state.query_input = query
                    st.session_state.filter_kategori = kategori
                    st.rerun()

# --- 7. RENDER HASIL PENCARIAN (Horizontal Card Style) ---
def render_search_results():
    query = st.session_state.get('query_input', '')
    
    if not query: return

    st.write("")
    st.markdown(f"### 🔎 Hasil pencarian: '{query}'")
    
    # Logic AI Search
    with st.spinner("Mencari tempat terbaik..."):
        final_query = query
        kategori_filter = st.session_state.get('filter_kategori', 'Semua')
        if kategori_filter != 'Semua':
            final_query = f"{query} {kategori_filter}"

        if engine.is_ready:
            df_res = engine.search(final_query, top_k=20)
        else:
            df_res = pd.DataFrame()

    if df_res.empty:
        st.warning(f"Maaf, tidak ditemukan tempat camping yang cocok dengan '{query}'.")
        return

    # Loop hasil dan tampilkan Card Horizontal
    for i, row in df_res.iterrows():
        p_id = db.get_place_by_name(row['Nama Tempat'])
        detail = db.get_place_details(p_id)
        info = detail['info']
        
        with st.container(border=True):
            col_img, col_info, col_price = st.columns([2, 4, 2])
            
            with col_img:
                img_url = info.get('photo_url')
                if not img_url: img_url = f"https://placehold.co/300x200/333/FFF?text={urllib.parse.quote(row['Nama Tempat'][:10])}"
                st.image(img_url, use_container_width=True)
            
            with col_info:
                st.markdown(f"<div class='card-title'>{row['Nama Tempat']}</div>", unsafe_allow_html=True)
                st.markdown(f"📍 {info.get('lokasi', row['Lokasi'])}")
                
                rate = info.get('rating_gmaps', 0)
                st.markdown(f"<div class='card-rating'>{rate} / 5.0</div> <span style='color:#777; font-size:12px'>(Google Reviews)</span>", unsafe_allow_html=True)
                
                st.markdown(f"<div style='margin-top:10px; font-style:italic; font-size:13px; color:#555'>\"{str(row['Isi Ulasan'])[:120]}...\"</div>", unsafe_allow_html=True)
                
                fas = detail['fasilitas'][:3]
                if fas: st.write(f"✨ {', '.join(fas)}")

            with col_price:
                st.write("") 
                st.markdown("<div class='card-price-label'>Mulai dari</div>", unsafe_allow_html=True)
                
                min_price = 15000
                if detail['harga']:
                     min_price = min([int(x['harga']) for x in detail['harga']])
                
                st.markdown(f"<div class='card-price-value'>{format_rp(min_price)}</div>", unsafe_allow_html=True)
                st.markdown("<div class='card-price-label'>/ malam</div>", unsafe_allow_html=True)
                
                st.write("")
                if st.button("Pilih Kamar", key=f"btn_res_{i}", type="primary", use_container_width=True):
                    show_details(row, detail, {})

# --- 8. CATEGORY ICONS ---
def render_categories():
    st.markdown("""
    <div class="cat-container">
        <div class="cat-box"><span style="font-size:30px">🏔️</span><span style="font-size:12px; font-weight:bold; color:#555">Gunung</span></div>
        <div class="cat-box"><span style="font-size:30px">🏖️</span><span style="font-size:12px; font-weight:bold; color:#555">Pantai</span></div>
        <div class="cat-box"><span style="font-size:30px">⛺</span><span style="font-size:12px; font-weight:bold; color:#555">Glamping</span></div>
        <div class="cat-box"><span style="font-size:30px">🔥</span><span style="font-size:12px; font-weight:bold; color:#555">Campervan</span></div>
    </div>
    <br><br>
    """, unsafe_allow_html=True)

# --- 9. POPULAR DESTINATIONS ---
def render_recommendations():
    st.subheader("🔥 Destinasi Terpopuler")
    
    conn = db.get_connection()
    df_top = pd.read_sql_query("SELECT * FROM tempat ORDER BY rating_gmaps DESC LIMIT 4", conn)
    conn.close()
    
    cols = st.columns(4)
    for i, row in df_top.iterrows():
        with cols[i]:
            with st.container(border=True):
                img_url = row['photo_url'] if row['photo_url'] else f"https://placehold.co/400x300/2ecc71/ffffff?text={urllib.parse.quote(row['nama'][:10])}"
                
                st.image(img_url, use_container_width=True)
                st.markdown(f"**{row['nama']}**")
                st.caption(f"📍 {row['lokasi']}")
                st.markdown(f"⭐ {row['rating_gmaps']}")
                
                start_price = "Rp 15.000"
                try:
                    import json
                    harga_list = json.loads(row['harga_json'])
                    if harga_list:
                        prices = [int(x['harga']) for x in harga_list]
                        start_price = f"Rp {min(prices):,}".replace(",", ".")
                except: pass
                
                st.markdown(f"<div style='color:#e67e22; font-weight:bold'>{start_price}</div>", unsafe_allow_html=True)
                
                # Kita perlu logic dummy untuk row compatible dengan show_details
                dummy_row = {'Nama Tempat': row['nama'], 'Isi Ulasan': "Destinasi populer dengan rating tinggi.", 'Lokasi': row['lokasi']}
                detail = db.get_place_details(row['id'])
                
                if st.button("Detail", key=f"det_{row['id']}", use_container_width=True):
                    show_details(dummy_row, detail, {})

# --- MAIN EXECUTION ---
# --- UPDATE SESSION STATE UNTUK NAVIGASI ---
if 'page' not in st.session_state: st.session_state.page = "home"

# --- FUNGSI NAVBAR YANG BERFUNGSI ---
def render_navbar():
    # Gunakan container biasa agar styling lebih mudah dikontrol
    with st.container():
        # Layout: [Logo (2)] --- [Spacer (4)] --- [Menu (4)]
        c_logo, c_space, c_menu = st.columns([2, 4, 4])
        
        with c_logo:
            if os.path.exists("logo.png"):
                st.image("logo.png", width=120)
            else:
                if st.button("⛺ CariKemah.id", key="nav_home_logo"):
                    st.session_state.page = "home"
                    st.rerun()

        # MENU KANAN (Navigasi Aktif)
        with c_menu:
            # Gunakan kolom lagi di dalam menu untuk menjejerkan tombol
            # Susunan: Home | Cek Pesanan | (Admin) | User/Login
            
            # Cek User
            user = st.session_state.user
            is_admin = user and user['role'] == 'admin'
            
            # Kolom menu dinamis
            cols_nav = st.columns([1, 1.5, 1.5, 1] if is_admin else [1, 1.5, 1])
            
            # 1. Tombol Home
            with cols_nav[0]:
                if st.button("Beranda", key="nav_home"):
                    st.session_state.page = "home"
                    st.rerun()
            
            # 2. Tombol Cek Pesanan (Hanya jika user login)
            if user and not is_admin:
                with cols_nav[1]:
                    if st.button("Tiket Saya", key="nav_ticket"):
                        st.session_state.page = "tickets"
                        st.rerun()
            
            # 3. Tombol Admin (Hanya jika Admin)
            if is_admin:
                with cols_nav[1]:
                    if st.button("Dashboard", key="nav_admin"):
                        st.session_state.page = "admin"
                        st.rerun()
            
            # 4. Tombol Login/Logout (Paling Kanan)
            with cols_nav[-1]:
                if user:
                    if st.button("Keluar", key="nav_logout", type="primary"):
                        st.session_state.user = None
                        st.session_state.page = "home"
                        st.rerun()
                else:
                    if st.button("Masuk", key="nav_login", type="primary"):
                        st.session_state.show_login = True
                        st.rerun()
    
    st.divider() # Garis pembatas visual

# --- LOGIC UTAMA (MAIN ROUTING) ---

# 1. Render Navbar Global (Selalu muncul)
render_navbar()

# 2. Logic Login Modal (Overlay)
if st.session_state.show_login:
    show_login_modal()

# 3. Routing Halaman Berdasarkan 'st.session_state.page'
if st.session_state.page == "home":
    # --- HALAMAN HOME ---
    render_hero()
    
    # Logic Search vs Landing
    if st.session_state.get('query_input'):
        render_search_results()
    else:
        render_categories()
        render_recommendations()

elif st.session_state.page == "tickets":
    # --- HALAMAN TIKET SAYA ---
    if st.session_state.user:
        st.markdown("## 🎫 Tiket & Pesanan Saya")
        # Panggil fungsi render tiket (Nanti kita percantik di Checkpoint 3)
        df = db.get_user_bookings(st.session_state.user['id'])
        if df.empty:
            st.info("Belum ada riwayat pemesanan.")
        else:
            st.dataframe(df) # Placeholder sementara
    else:
        st.warning("Silakan login dulu.")

elif st.session_state.page == "admin":
    # --- HALAMAN ADMIN ---
    if st.session_state.user and st.session_state.user['role'] == 'admin':
        st.markdown("## 📊 Dashboard Admin")
        # Panggil fungsi render admin (Nanti kita percantik di Checkpoint 4)
        df_adm = db.get_all_bookings_admin()
        st.dataframe(df_adm) # Placeholder sementara
    else:
        st.error("Akses Ditolak.")
        if st.button("Kembali"):
            st.session_state.page = "home"
            st.rerun()

# Footer
st.markdown("<br><hr><center style='color:#aaa; font-size:12px'>© 2025 CariKemah.id</center>", unsafe_allow_html=True)