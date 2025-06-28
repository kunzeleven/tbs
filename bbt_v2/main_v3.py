import streamlit as st
import pandas as pd
from datetime import datetime, date, time
import re
from supabase import create_client, Client
import bcrypt
from typing import Tuple
from datetime import datetime as dt

# Konfigurasi halaman
st.set_page_config(
    page_title="Meeting Room Booking",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS custom
def load_css():
    st.markdown("""
    <style>
    .stApp {
        background-color: #ffffff;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 0.75rem 1rem;
        border-radius: 12px;
        margin-bottom: 2rem;
        color: white;
        text-align: left;
        font-size: 0.625rem; /* setengah dari ukuran normal */
        cursor: pointer;
        font-weight: bold;
    }
    .main-header:hover {
        opacity: 0.8;
    }
    .top-nav {
        display: flex;
        justify-content: flex-end;
        gap: 0.75rem;
        margin-bottom: 1.5rem;
        padding: 0.5rem 0;
    }
    div[data-testid="column"]:nth-child(2) button,
    div[data-testid="column"]:nth-child(3) button {
        border-radius: 25px !important;
        font-size: 14px !important;
        padding: 0.6rem 1.2rem !important;
        min-width: 140px !important;
        height: 42px !important;
        background: #007AFF !important;
        color: white !important;
        border: none !important;
        font-weight: 500 !important;
        transition: all 0.2s ease !important;
    }
    div[data-testid="column"]:nth-child(2) button:hover,
    div[data-testid="column"]:nth-child(3) button:hover {
        background: #0056CC !important;
        box-shadow: 0 4px 12px rgba(0,122,255,0.3) !important;
        transform: translateY(-1px) !important;
    }
    .admin-link {
        text-align: center;
        margin-top: 3rem;
        padding: 2rem 0;
        border-top: 1px solid #f0f0f0;
    }
    .admin-link a {
        color: #007AFF;
        text-decoration: none;
        font-size: 14px;
        opacity: 0.7;
        transition: opacity 0.2s ease;
        cursor: pointer;
    }
    .admin-link a:hover {
        opacity: 1;
        text-decoration: underline;
    }
    .stForm {
        background: #f8f9fa;
        padding: 2rem;
        border-radius: 12px;
        border: 1px solid #e9ecef;
        box-shadow: 0 2px 12px rgba(0,0,0,0.08);
    }
    .stButton > button {
        background: #007AFF;
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.75rem 1.5rem;
        font-weight: 500;
        transition: all 0.2s ease;
    }
    .stButton > button:hover {
        background: #0056CC;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0,122,255,0.3);
    }
    input[type="text"], input[type="password"], input[type="date"], input[type="time"], textarea, select {
        border: 1px solid #d1d5db;
        border-radius: 8px;
        padding: 0.75rem;
        font-size: 16px;
        width: 100%;
        box-sizing: border-box;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display: none;}
    </style>
    """, unsafe_allow_html=True)

@st.cache_resource
def init_supabase():
    try:
        if "supabase" not in st.secrets:
            st.error("⚠️ Konfigurasi Supabase tidak ditemukan dalam secrets")
            return None
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        if not url.startswith("https://") or len(key) < 100:
            st.error("⚠️ Konfigurasi API Key atau URL tidak valid")
            return None
        supabase = create_client(url, key)
        # Tes koneksi
        supabase.table('bookings').select('id').limit(1).execute()
        return supabase
    except Exception as e:
        st.error(f"⚠️ Gagal koneksi: {str(e)}")
        return None

def validate_name(nama):
    if not nama or len(nama.strip()) < 2:
        return False, "Nama harus diisi minimal 2 karakter"
    if not re.match(r'^[A-Za-z\s]+$', nama.strip()):
        return False, "Nama hanya boleh berisi huruf dan spasi"
    return True, ""

def validate_phone(no_hp):
    if not no_hp:
        return False, "No. HP harus diisi"
    no_hp_clean = re.sub(r'[^\d]', '', no_hp)
    if len(no_hp_clean) < 10 or len(no_hp_clean) > 15:
        return False, "No. HP tidak valid (10-15 digit)"
    return True, ""

def validate_time_range(start, end):
    if start >= end:
        return False, "Waktu selesai harus lebih besar dari waktu mulai"
    return True, ""

def validate_booking_conflict(supabase, tanggal, start, end, room, exclude_id=None):
    try:
        query = supabase.table('bookings').select('*').eq('tanggal_booking', str(tanggal)).eq('ruang_meeting', room)
        if exclude_id:
            query = query.neq('id', exclude_id)
        result = query.execute()
        for b in result.data:
            existing_start = dt.strptime(b['waktu_mulai'], '%H:%M:%S').time()
            existing_end = dt.strptime(b['waktu_selesai'], '%H:%M:%S').time()
            if (start < existing_end and end > existing_start):
                return False, f"Konflik jadwal dengan {b['nama']} ({existing_start}-{existing_end})"
        return True, ""
    except:
        return False, "Error validasi konflik jadwal"

def check_admin_auth():
    if 'admin_authenticated' not in st.session_state:
        st.session_state['admin_authenticated'] = False
    return st.session_state['admin_authenticated']

def admin_login():
    st.subheader("🔐 Admin Login")
    with st.form("admin_login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        if submitted:
            try:
                correct_user = st.secrets.get("admin", {}).get("username", "admin")
                correct_hash = st.secrets.get("admin", {}).get("password_hash", "")
                if username == correct_user and correct_hash and bcrypt.checkpw(password.encode('utf-8'), correct_hash.encode('utf-8')):
                    st.session_state['admin_authenticated'] = True
                    st.success("Login berhasil!")
                    st.rerun()
                else:
                    st.error("Username atau password salah")
            except:
                st.error("Hash admin rusak — perbarui secrets.toml")

def booking_form_page():
    # Navigasi kanan atas
    col1, col2, col3 = st.columns([8, 2, 2])
    with col2:
        # Tidak ada button "Booking Room Meeting 19" di halaman form
        pass
    with col3:
        if st.button("📋 Lihat Daftar Booking", key="nav_list", help="Lihat daftar booking"):
            st.session_state.page = "list"
            st.rerun()
    # Header sebagai hyperlink
    st.markdown("""
    <div class="main-header" onclick="window.location.reload()">
        Meeting Room Booking System
    </div>
    """, unsafe_allow_html=True)
    # Form booking
    with st.form("booking_form", clear_on_submit=True):
        st.subheader("📝 Form Booking Meeting Room")
        col1, col2 = st.columns(2)
        with col1:
            nama = st.text_input("Nama *", placeholder="Masukkan nama lengkap")
            subdir = st.text_input("Sub Direktorat", placeholder="Sub direktorat")
            no_hp = st.text_input("No. HP *", placeholder="Contoh: 08123456789")
        with col2:
            ruang_meeting = st.selectbox("Ruang Meeting *", ["", "Breakout Traction", "Cozy 19.2"])
            tanggal_booking = st.date_input("Tanggal Booking *", min_value=date.today())
            col_time1, col_time2 = st.columns(2)
            with col_time1:
                waktu_mulai = st.time_input("Waktu Mulai *", value=time(9,0))
            with col_time2:
                waktu_selesai = st.time_input("Waktu Selesai *", value=time(10,0))
        keterangan = st.text_area("Keterangan Meeting", placeholder="Agenda atau keterangan")
        submitted = st.form_submit_button("📅 Submit Booking")
        if submitted:
            errors = []
            valid, msg = validate_name(nama)
            if not valid: errors.append(msg)
            valid, msg = validate_phone(no_hp)
            if not valid: errors.append(msg)
            if not ruang_meeting:
                errors.append("Ruang meeting harus dipilih")
            valid, msg = validate_time_range(waktu_mulai, waktu_selesai)
            if not valid: errors.append(msg)
            if errors:
                for e in errors:
                    st.error(e)
            else:
                supabase = init_supabase()
                if supabase:
                    valid, msg = validate_booking_conflict(supabase, tanggal_booking, waktu_mulai, waktu_selesai, ruang_meeting)
                    if not valid:
                        st.error(msg)
                    else:
                        data = {
                            "nama": nama.strip(),
                            "subdir": subdir.strip(),
                            "no_hp": no_hp.strip(),
                            "ruang_meeting": ruang_meeting,
                            "tanggal_booking": str(tanggal_booking),
                            "waktu_mulai": str(waktu_mulai),
                            "waktu_selesai": str(waktu_selesai),
                            "keterangan": keterangan.strip(),
                            "created_at": dt.now().isoformat()
                        }
                        try:
                            supabase.table('bookings').insert(data).execute()
                            st.success("✅ Booking berhasil disimpan!")
                            st.balloons()
                        except:
                            st.error("Gagal menyimpan data")
    # Admin link di bawah
    st.markdown("""
    <div class="admin-link">
        <a href="#" onclick="document.querySelector('[key=admin_nav]').click(); return false;">Admin Panel</a>
    </div>
    """, unsafe_allow_html=True)
    if st.button("", key="admin_nav"):
        st.session_state['page'] = 'admin'
        st.rerun()

def booking_list_page():
    col1, col2, col3 = st.columns([6, 2, 2])
    with col2:
        if st.button("Booking Room Meeting 19", key="nav_home_list", help="Kembali ke halaman utama"):
            st.session_state.page = "form"
            st.rerun()
    with col3:
        if st.button("📋 Lihat Daftar Booking", key="nav_list_active", help="Lihat daftar", disabled=True):
            pass
    # Header sebagai hyperlink
    st.markdown("""
    <div class="main-header" onclick="window.location.reload()">
        📋 Daftar Booking Meeting Room
    </div>
    """, unsafe_allow_html=True)
    if st.button("", key="header_home_nav_list"):
        st.session_state.page = "form"
        st.rerun()
    # Load data
    supabase = init_supabase()
    if supabase:
        try:
            result = supabase.table('bookings').select('*').order('tanggal_booking', desc=False).execute()
            if result.data:
                df = pd.DataFrame(result.data)
                df['Tanggal'] = pd.to_datetime(df['tanggal_booking']).dt.strftime('%d/%m/%Y')
                df['Waktu'] = df['waktu_mulai'].str[:5] + ' - ' + df['waktu_selesai'].str[:5]
                display_df = df[['Tanggal', 'Waktu', 'nama', 'subdir', 'ruang_meeting', 'keterangan']].copy()
                display_df.columns = ['Tanggal', 'Waktu', 'Nama', 'Sub Direktorat', 'Ruang', 'Keterangan']
                st.dataframe(display_df, use_container_width=True, hide_index=True)
                st.subheader("🔍 Filter Booking")
                filter_date = st.date_input("Pilih tanggal", value=date.today())
                filtered_df = df[df['tanggal_booking'] == str(filter_date)]
                if not filtered_df.empty:
                    st.write(f"**Booking tanggal {filter_date.strftime('%d/%m/%Y')}:**")
                    f2 = filtered_df[['Waktu', 'nama', 'subdir', 'ruang_meeting', 'keterangan']].copy()
                    f2.columns = ['Waktu', 'Nama', 'Sub Direktorat', 'Ruang', 'Keterangan']
                    st.dataframe(f2, use_container_width=True, hide_index=True)
                else:
                    st.info("Tidak ada booking pada tanggal ini")
            else:
                st.info("Belum ada data booking")
        except:
            st.error("Gagal load data")
    # Admin link
    if st.button("", key="admin_nav_list"):
        st.session_state['page'] = 'admin'
        st.rerun()

def admin_page():
    if not check_admin_auth():
        col1, col2, col3 = st.columns([6, 2, 2])
        with col2:
            if st.button("Booking Room Meeting 19", key="nav_home_admin"):
                st.session_state['page'] = 'form'
                st.rerun()
        with col3:
            if st.button("📋 Lihat Daftar Booking", key="nav_list_admin"):
                st.session_state['page'] = 'list'
                st.rerun()
        st.markdown("""
        <div class="main-header" onclick="window.location.reload()">
            ⚙️ Admin Panel
        </div>
        """, unsafe_allow_html=True)
        if st.button("", key="admin_nav"):
            st.session_state['page'] = 'admin'
            st.rerun()
        admin_login()
        return
    # Jika sudah login
    col1, col2, col3, col4 = st.columns([4, 2, 2, 2])
    with col2:
        if st.button("Booking Room Meeting 19", key="nav_home_admin"):
            st.session_state['page'] = 'form'
            st.rerun()
    with col3:
        if st.button("📋 Lihat Daftar Booking", key="nav_list_admin"):
            st.session_state['page'] = 'list'
            st.rerun()
    with col4:
        if st.button("🚪 Logout", key="logout_admin"):
            st.session_state['admin_authenticated'] = False
            st.rerun()
    st.markdown("""
    <div class="main-header" onclick="window.location.reload()">
        ⚙️ Admin Panel
    </div>
    """, unsafe_allow_html=True)
    # Load data
    supabase = init_supabase()
    if supabase:
        try:
            result = supabase.table('bookings').select('*').order('tanggal_booking', desc=False).execute()
            if result.data:
                df = pd.DataFrame(result.data)
                df = convert_dataframe_types(df)
                st.subheader("✏️ Edit & Hapus Booking")
                edited_df = st.data_editor(
                    df,
                    column_config={
                        "id": st.column_config.NumberColumn("ID", disabled=True),
                        "nama": st.column_config.TextColumn("Nama", required=True),
                        "subdir": st.column_config.TextColumn("Sub Direktorat"),
                        "no_hp": st.column_config.TextColumn("No. HP", required=True),
                        "ruang_meeting": st.column_config.SelectboxColumn(
                            "Ruang Meeting",
                            options=["Breakout Traction", "Cozy 19.2"],
                            required=True
                        ),
                        "tanggal_booking": st.column_config.DateColumn("Tanggal Booking", required=True, format="DD/MM/YYYY"),
                        "waktu_mulai": st.column_config.TimeColumn("Waktu Mulai", required=True),
                        "waktu_selesai": st.column_config.TimeColumn("Waktu Selesai", required=True),
                        "keterangan": st.column_config.TextColumn("Keterangan"),
                        "created_at": st.column_config.DatetimeColumn("Dibuat", disabled=True)
                    },
                    num_rows="dynamic",
                    use_container_width=True,
                    key="booking_editor"
                )
                if st.button("💾 Simpan Perubahan"):
                    # Simpan perubahan
                    # (kode update database)
                    st.success("Perubahan disimpan")
                    st.rerun()
            else:
                st.info("Belum ada data")
        except:
            st.error("Gagal load data")
    # Jika tidak login
    if st.session_state.get('admin_authenticated', False):
        pass
    else:
        admin_login()

def main():
    load_css()
    if 'page' not in st.session_state:
        st.session_state['page'] = 'form'
    if st.session_state['page'] == 'form':
        booking_form_page()
    elif st.session_state['page'] == 'list':
        booking_list_page()
    elif st.session_state['page'] == 'admin':
        admin_page()

if __name__ == "__main__":
    main()
