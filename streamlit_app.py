import streamlit as st
import pandas as pd
import base64
import os
import urllib.parse
import time
from datetime import datetime

# --- 1. CONFIG ---
st.set_page_config(layout="wide", page_title="CariKemah.id", page_icon="⛺")

def get_img_as_base64(file):
    try:
        with open(file, "rb") as f: data = f.read()
        return base64.b64encode(data).decode()
    except: return ""

def format_rp(angka): 
    return f"Rp {int(angka):,}".replace(",", ".")

# --- FUNGSI GENERATE E-TICKET (HTML DOWNLOAD) ---
def create_ticket_html(ticket_data, username):
    """Membuat file HTML sederhana untuk E-Ticket"""
    html = f"""
    <div style="border: 2px solid #0984e3; padding: 20px; border-radius: 15px; font-family: sans-serif; max-width: 600px; margin: auto;">
        <div style="text-align: center; border-bottom: 2px dashed #ccc; padding-bottom: 10px; margin-bottom: 20px;">
            <h2 style="color: #0984e3; margin:0;">⛺ CariKemah.id</h2>
            <p style="margin:0; color: #888;">E-Ticket Reservation</p>
        </div>
        <div style="display: flex; justify-content: space-between;">
            <div>
                <p><strong>Nama Tempat:</strong><br>{ticket_data['nama']}</p>
                <p><strong>Pemesan:</strong><br>{username}</p>
                <p><strong>Check-in:</strong><br>{ticket_data['tanggal_checkin']}</p>
            </div>
            <div style="text-align: right;">
                <p><strong>Order ID:</strong><br>#{ticket_data['id']}</p>
                <p><strong>Status:</strong><br><span style="color:green; font-weight:bold;">CONFIRMED</span></p>
                <p><strong>Jumlah:</strong><br>{ticket_data['jumlah_orang']} Unit/Pax</p>
            </div>
        </div>
        <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
        <div style="text-align: center;">
            <h3 style="margin:0;">Total: {format_rp(ticket_data['total_harga'])}</h3>
            <p style="font-size: 12px; color: #aaa;">Harap tunjukkan tiket ini saat kedatangan.</p>
        </div>
    </div>
    """
    return html

# --- 2. LOAD RESOURCES ---
try:
    from Asisten.db_handler import db
    from Asisten.smart_search import SmartSearchEngine
except ImportError: st.stop()

@st.cache_resource
def init_engine(): return SmartSearchEngine()
engine = init_engine()

# --- 3. SESSION STATE ---
if 'user' not in st.session_state: st.session_state.user = None
if 'show_login' not in st.session_state: st.session_state.show_login = False
if 'query_input' not in st.session_state: st.session_state.query_input = ""
if 'page' not in st.session_state: st.session_state.page = "home"

bg_img = get_img_as_base64("tent-night-wide.jpg")
logo_img = get_img_as_base64("logo.png")

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap');
</style>
""", unsafe_allow_html=True)

if os.path.exists('style.css'):
    with open('style.css') as f:
        css_code = f.read()
        css_code += f".hero-wrapper {{ background-image: url('data:image/jpg;base64,{bg_img}'); }}"
        st.markdown(f'<style>{css_code}</style>', unsafe_allow_html=True)

# --- 4. NAVBAR ---
def render_navbar():
    with st.container():
        c_logo, c_space, c_menu = st.columns([2, 5, 4])
        with c_logo:
            if os.path.exists("logo.png"):
                st.image("logo.png", width=120)
            else:
                if st.button("⛺ CariKemah.id", key="nav_logo"):
                    st.session_state.page = "home"; st.rerun()
        with c_menu:
            user = st.session_state.user
            is_admin = user and user['role'] == 'admin'
            if user:
                cols = st.columns([1, 1, 1.5, 1])
                with cols[0]:
                    if st.button("Beranda", key="n_home"): st.session_state.page = "home"; st.rerun()
                with cols[1]:
                    if is_admin:
                        if st.button("Admin", key="n_adm"): st.session_state.page = "admin"; st.rerun()
                    else:
                        if st.button("Tiket", key="n_tik"): st.session_state.page = "tickets"; st.rerun()
                with cols[2]:
                    st.markdown(f"<div style='padding-top:8px; font-size:13px; text-align:center;'>Hi, {user['username']}</div>", unsafe_allow_html=True)
                with cols[3]:
                    if st.button("Keluar", key="n_out"): st.session_state.user = None; st.session_state.page = "home"; st.rerun()
            else:
                cols = st.columns([1, 1, 1])
                with cols[0]:
                    if st.button("Beranda", key="n_home"): st.session_state.page = "home"; st.rerun()
                with cols[1]:
                    if st.button("Masuk", key="n_in"): st.session_state.show_login = True; st.rerun()
                with cols[2]:
                    if st.button("Daftar", key="n_up", type="primary"): st.session_state.show_login = True; st.rerun()

# --- 5. MODAL LOGIC ---
@st.dialog("Akses Akun", width="small")
def show_login_modal():
    tab1, tab2 = st.tabs(["Masuk", "Daftar Baru"])
    with tab1:
        u = st.text_input("Username", key="l_u")
        p = st.text_input("Password", type="password", key="l_p")
        if st.button("Masuk", type="primary", use_container_width=True):
            res = db.verify_login(u, p)
            if res:
                st.session_state.user = res; st.session_state.show_login = False; st.rerun()
            else: st.error("Gagal.")
    with tab2:
        u2 = st.text_input("User Baru", key="r_u")
        p2 = st.text_input("Password Baru", type="password", key="r_p")
        if st.button("Buat Akun", type="primary", use_container_width=True):
            ok, msg = db.register_user(u2, p2)
            if ok: st.success("Berhasil! Silakan Login."); 
        
        else: st.error(msg)

@st.dialog("Detail & Reservasi", width="large")
def show_details(row, detail, sc_data):
    info = detail['info']
    c_img, c_meta = st.columns([1.2, 1])
    with c_img:
        foto = info.get('photo_url') or f"https://placehold.co/600x400/eee/333?text={urllib.parse.quote(row['Nama Tempat'])}"
        st.image(foto, use_container_width=True)
    with c_meta:
        st.markdown(f"## {row['Nama Tempat']}")
        st.markdown(f"📍 **{info.get('lokasi', '-')}**")
        st.markdown(f"### ⭐ {info.get('rating_gmaps', 0)} / 5.0")
        if 'gmaps_link' in info: st.link_button("🗺️ Lihat Peta", info['gmaps_link'], use_container_width=True)
    st.divider()
    t1, t2, t3 = st.tabs(["✨ Info & Review", "💰 Harga", "📅 Booking"])
    with t1:
        st.markdown("#### Fasilitas")
        if detail['fasilitas']:
            chips = "".join([f"<span class='fas-tag'>{f}</span>" for f in detail['fasilitas']])
            st.markdown(chips, unsafe_allow_html=True)
        else: st.info("-")
        st.write("")
        st.markdown("#### Ulasan")
        st.markdown(f"<div class='review-box'>\"{str(row['Isi Ulasan'])[:400]}...\"</div>", unsafe_allow_html=True)
    with t2:
        if detail['harga']:
            df_h = pd.DataFrame(detail['harga'])[['item', 'harga']]
            df_h['Biaya'] = df_h['harga'].apply(format_rp)
            st.dataframe(df_h[['item', 'Biaya']], hide_index=True, use_container_width=True)
        else: st.warning("Harga tidak tersedia.")
    with t3:
        if not st.session_state.user: st.warning("Silakan Login dulu.")
        else:
            price_list = detail['harga']
            if price_list:
                opts = [f"{p['item']} - {format_rp(p['harga'])}" for p in price_list]
                sel = st.selectbox("Pilih Paket", opts)
                p_val = int(price_list[opts.index(sel)]['harga'])
            else:
                sel = "Tiket Masuk"; p_val = 15000
                st.write(f"Harga: {format_rp(p_val)}")
            c_d, c_q = st.columns(2)
            with c_d: dt = st.date_input("Check-in", min_value=datetime.today())
            with c_q: qt = st.number_input("Jumlah", 1, 100, 1)
            tot = p_val * qt
            st.markdown(f"<div style='background:#f9f9f9; padding:15px; border-radius:10px; text-align:right;'><span style='color:#555'>Total Estimasi</span><br><span style='font-size:1.5rem; font-weight:bold; color:#0984e3'>{format_rp(tot)}</span></div><br>", unsafe_allow_html=True)
            if st.button("Konfirmasi Booking", type="primary", use_container_width=True):
                if db.add_booking(st.session_state.user['id'], detail['info'].get('id') or db.get_place_by_name(row['Nama Tempat']), str(dt), qt, tot):
                    st.success("Berhasil! Cek Tiket Saya."); time.sleep(2); st.rerun()

render_navbar()
if st.session_state.show_login: show_login_modal()

# === PAGE: HOME ===
if st.session_state.page == "home":
    st.markdown("""
    <div class="hero-wrapper">
        <div class="hero-overlay"></div>
        <div class="hero-content">
            <div class="hero-title">Explore, Camp, Connect!</div>
            <div class="hero-subtitle">Temukan tempat camping impianmu dengan teknologi AI</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 6, 1])
    with c2:
        with st.container(border=True):
            st.markdown("##### 🔍 Mau kemah di mana?")
            r1, r2, r3 = st.columns([3, 2, 1.5])
            with r1: q = st.text_input("Destinasi", placeholder="Cth: Pantai Jogja, Kaliurang...", label_visibility="collapsed")
            with r2: cat = st.selectbox("Tipe", ["Semua", "Gunung", "Pantai"], label_visibility="collapsed")
            with r3: 
                if st.button("Cari", type="primary", use_container_width=True):
                    st.session_state.query_input = q; st.session_state.filter_cat = cat; st.rerun()
    query = st.session_state.get('query_input')
    if query:
        st.write(""); st.markdown(f"### 🔎 Hasil: '{query}'")
        with st.spinner("AI sedang mencari..."):
            fq = f"{query} {st.session_state.get('filter_cat','Semua')}" if st.session_state.get('filter_cat') != 'Semua' else query
            res = engine.search(fq, top_k=20)
        if res.empty: st.warning("Tidak ditemukan.")
        else:
            for i, row in res.iterrows():
                pid = db.get_place_by_name(row['Nama Tempat'])
                det = db.get_place_details(pid)
                inf = det['info']
                with st.container(border=True):
                    c_img, c_inf, c_act = st.columns([2, 4, 2])
                    with c_img: st.image(inf.get('photo_url') or f"https://placehold.co/300x200/eee/333?text={urllib.parse.quote(row['Nama Tempat'][:10])}", use_container_width=True)
                    with c_inf:
                        st.markdown(f"<div class='card-title'>{row['Nama Tempat']}</div>", unsafe_allow_html=True)
                        st.markdown(f"<div class='card-location'>📍 {inf.get('lokasi','-')}</div>", unsafe_allow_html=True)
                        st.markdown(f"<span class='card-rating'>⭐ {inf.get('rating_gmaps',0)}</span>", unsafe_allow_html=True)
                        st.markdown(f"<div style='margin-top:8px; font-size:13px; color:#555'>\"{str(row['Isi Ulasan'])[:100]}...\"</div>", unsafe_allow_html=True)
                    with c_act:
                        st.write("")
                        mp = 15000
                        if det['harga']: mp = min([int(x['harga']) for x in det['harga']])
                        st.markdown(f"<div class='card-price-label'>Mulai</div><div class='card-price-value'>{format_rp(mp)}</div>", unsafe_allow_html=True)
                        st.write("")
                        if st.button("Pilih", key=f"b_{i}", type="primary", use_container_width=True): show_details(row, det, {})
    else:
        st.markdown("<br><br>", unsafe_allow_html=True)
        col_icon = st.columns(4)
        icons = [("🏔️","Gunung"),("🏖️","Pantai"),("⛺","Glamping"),("🔥","Campervan")]
        for idx, (ic, tx) in enumerate(icons):
            with col_icon[idx]: st.markdown(f"<div class='cat-box'><span style='font-size:30px'>{ic}</span><span style='font-size:12px; font-weight:bold; color:#555'>{tx}</span></div>", unsafe_allow_html=True)
        st.write(""); st.subheader("🔥 Destinasi Terpopuler")
        conn = db.get_connection()
        df_top = pd.read_sql_query("SELECT * FROM tempat ORDER BY rating_gmaps DESC LIMIT 4", conn); conn.close()
        cols = st.columns(4)
        for i, row in df_top.iterrows():
            with cols[i]:
                with st.container(border=True):
                    st.image(row['photo_url'] or f"https://placehold.co/400x300/2ecc71/ffffff?text={urllib.parse.quote(row['nama'][:10])}", use_container_width=True)
                    st.markdown(f"**{row['nama']}**")
                    st.caption(f"📍 {row['lokasi']}")
                    st.markdown(f"⭐ {row['rating_gmaps']}")
                    sp = "Rp 15.000"
                    try: 
                        import json
                        hl = json.loads(row['harga_json'])
                        if hl: sp = f"Rp {min([int(x['harga']) for x in hl]):,}".replace(",", ".")
                    except: pass
                    st.markdown(f"<div style='color:#e67e22; font-weight:bold'>{sp}</div>", unsafe_allow_html=True)
                    if st.button("Detail", key=f"d_{row['id']}", use_container_width=True):
                        det = db.get_place_details(row['id'])
                        show_details({'Nama Tempat': row['nama'], 'Isi Ulasan': "Populer.", 'Lokasi': row['lokasi']}, det, {})

# === PAGE: TIKET SAYA (UPDATE: CETAK & UI) ===
elif st.session_state.page == "tickets":
    st.markdown("## 🎫 Tiket & Pesanan Saya")
    if not st.session_state.user: st.warning("Silakan Login terlebih dahulu.")
    else:
        df = db.get_user_bookings(st.session_state.user['id'])
        if df.empty: st.info("Belum ada riwayat pemesanan.")
        else:
            for index, row in df.iterrows():
                status = row['status']
                s_class = "status-pending"
                if status == 'CONFIRMED': s_class = "status-confirmed"
                elif status == 'REJECTED': s_class = "status-rejected"
                
                with st.container(border=True):
                    st.markdown(f"<div class='ticket-header'><span style='font-weight:bold; color:#888;'>Order ID: #{row['id']}</span><span class='status-badge {s_class}'>{status}</span></div>", unsafe_allow_html=True)
                    c_qr, c_inf, c_prc = st.columns([1, 3, 1.5])
                    with c_qr:
                        qr_text = f"TIKET-{row['id']}-{st.session_state.user['username']}"
                        st.image(f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={qr_text}", width=100)
                    with c_inf:
                        st.markdown(f"### {row['nama']}")
                        c_i1, c_i2 = st.columns(2)
                        with c_i1: st.markdown(f"<div class='ticket-label'>Check-in Date</div><div class='ticket-value'>📅 {row['tanggal_checkin']}</div>", unsafe_allow_html=True)
                        with c_i2: st.markdown(f"<div class='ticket-label'>Pax</div><div class='ticket-value'>👥 {row['jumlah_orang']} Unit</div>", unsafe_allow_html=True)
                    with c_prc:
                        st.markdown(f"<div class='ticket-label' style='text-align:right'>Total</div><div class='ticket-total' style='text-align:right'>{format_rp(row['total_harga'])}</div>", unsafe_allow_html=True)
                        st.write("")
                        if status == 'CONFIRMED':
                            # FITUR DOWNLOAD HTML
                            ticket_html = create_ticket_html(row, st.session_state.user['username'])
                            st.download_button(
                                label="🖨️ Cetak E-Ticket",
                                data=ticket_html,
                                file_name=f"E-Ticket_{row['id']}.html",
                                mime="text/html",
                                key=f"dl_{row['id']}",
                                type="primary",
                                use_container_width=True
                            )
                        elif status == 'PENDING':
                            st.button("Menunggu Konfirmasi", key=f"wait_{row['id']}", disabled=True, use_container_width=True)
                        else:
                            st.button("Dibatalkan", key=f"canc_{row['id']}", disabled=True, use_container_width=True)

# === PAGE: ADMIN (UPDATE: TOMBOL TOLAK) ===
elif st.session_state.page == "admin":
    st.title("Admin Panel")
    if st.session_state.user and st.session_state.user['role']=='admin':
        df = db.get_all_bookings_admin()
        c1, c2, c3 = st.columns(3)
        with c1: st.metric("Total Pesanan", len(df))
        with c2: st.metric("Pendapatan", format_rp(df[df['status']=='CONFIRMED']['total_harga'].sum()))
        with c3: st.metric("Perlu Konfirmasi", len(df[df['status']=='PENDING']))
        st.divider()
        st.subheader("Daftar Pesanan Masuk")
        for i, r in df.iterrows():
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([0.5, 2, 1, 1.5])
                with c1: st.write(f"#{r['id']}")
                with c2: 
                    st.write(f"**{r['nama']}**")
                    st.caption(f"User: {r['username']} | Tgl: {r['tanggal_checkin']}")
                with c3: st.write(format_rp(r['total_harga']))
                with c4:
                    if r['status'] == 'PENDING':
                        ca, cb = st.columns(2)
                        with ca:
                            if st.button("✅", key=f"acc_{i}", type="primary"): 
                                db.update_booking_status(r['id'], 'CONFIRMED'); st.rerun()
                        with cb:
                            if st.button("❌", key=f"rej_{i}"): 
                                db.update_booking_status(r['id'], 'REJECTED'); st.rerun()
                    else:
                        color = "green" if r['status']=='CONFIRMED' else "red"
                        st.markdown(f"<span style='color:{color}; font-weight:bold'>{r['status']}</span>", unsafe_allow_html=True)
    else:
        st.error("Akses Ditolak."); st.button("Kembali", on_click=lambda: st.session_state.update(page="home"))

st.markdown("<br><hr><center style='color:#aaa; font-size:12px'>© 2025 CariKemah.id</center>", unsafe_allow_html=True)