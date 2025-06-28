import streamlit as st
import pandas as pd
from datetime import datetime, date, time
import re
from supabase import create_client, Client
import bcrypt

# Konfigurasi halaman
st.set_page_config(
    page_title="Meeting Room Booking",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="collapsed"
)

def load_css():
    st.markdown("""
    <style>
    /* Reset dan base styling */
    .stApp {
        background-color: #ffffff;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }
    /* Header kecil dan sejajar dengan button */
    .header-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1.5rem;
        padding: 0 1rem;
    }
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 0.4rem 0.8rem;
        border-radius: 25px;
        font-size: 14px;
        font-weight: 500;
        height: 42px;
        display: flex;
        align-items: center;
        cursor: pointer;
        color: white;
        transition: all 0.2s ease;
        min-width: 200px;
        margin: 0;
    }
    .main-header:hover {
        background: linear-gradient(135deg, #5a6fd8 0%, #6a4190 100%);
        box-shadow: 0 4px 12px rgba(102,126,234,0.3);
    }
    /* Button kanan atas */
    .nav-buttons {
        display: flex;
        gap: 0.75rem;
    }
    .nav-button {
        border-radius: 25px;
        font-size: 14px;
        padding: 0.6rem 1.2rem;
        min-width: 140px;
        height: 42px;
        background: #007AFF;
        color: white;
        border: none;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s ease;
    }
    .nav-button:hover {
        background: #0056CC;
        box-shadow: 0 4px 12px rgba(0,122,255,0.3);
        transform: translateY(-1px);
    }
    /* Sembunyikan button secondary (tanpa label) */
    button[kind="secondary"] {
        display: none !important;
    }
    /* Link admin di bawah */
    .admin-link {
        text-align: center;
        margin-top: 3rem;
        padding: 2rem 0;
        border-top: 1px solid #f0f0f0;
    }
    .admin-link a {
        color: #007AFF;
        font-size: 14px;
        opacity: 0.7;
        text-decoration: none;
        cursor: pointer;
        transition: opacity 0.2s ease;
    }
    .admin-link a:hover {
        opacity: 1;
        text-decoration: underline;
    }
    /* Form styling */
    .stForm {
        background: #f8f9fa;
        padding: 2rem;
        border-radius: 12px;
        border: 1px solid #e9ecef;
        box-shadow: 0 2px 12px rgba(0,0,0,0.08);
    }
    /* Button form */
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
        box-shadow: 0 4px 12px rgba(0,122,255,0.3);
        transform: translateY(-1px);
    }
    /* Input styles */
    .stTextInput > div > div > input,
    .stSelectbox > div > div > select,
    .stDateInput > div > div > input,
    .stTimeInput > div > div > input {
        border: 1px solid #d1d5db;
        border-radius: 8px;
        padding: 0.75rem;
        font-size: 16px;
        transition: border-color 0.2s ease;
    }
    .stTextInput > div > div > input:focus,
    .stSelectbox > div > div > select:focus {
        border-color: #007AFF;
        box-shadow: 0 0 0 3px rgba(0,122,255,0.1);
    }
    /* Data table */
    .stDataFrame {
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        overflow: hidden;
    }
    /* Messages */
    .stSuccess, .stError, .stWarning {
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
    /* Hide Streamlit menu/footer */
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
            st.error("⚠️ Konfigurasi API Key/URL tidak valid")
            return None
        supabase = create_client(url, key)
        # Tes koneksi
        supabase.table('bookings').select('id').limit(1).execute()
        return supabase
    except Exception as e:
        st.error(f"Error init supabase: {e}")
        return None

# Validasi input
def validate_name(nama):
    if not nama or len(nama.strip()) < 2:
        return False, "Nama minimal 2 karakter"
    if not re.match(r'^[A-Za-z\s]+$', nama.strip()):
        return False, "Nama hanya huruf dan spasi"
    return True, ""

def validate_phone(no_hp):
    if not no_hp:
        return False, "No HP harus diisi"
    no_hp_clean = re.sub(r'[^\d]', '', no_hp)
    if len(no_hp_clean) < 10 or len(no_hp_clean) > 15:
        return False, "No HP tidak valid (10-15 digit)"
    return True, ""

def validate_time_range(start, end):
    if start >= end:
        return False, "Waktu selesai harus lebih besar dari waktu mulai"
    return True, ""

def validate_booking_conflict(supabase, date_b, start, end, room, exclude_id=None):
    try:
        query = supabase.table('bookings').select('*').eq('tanggal_booking', str(date_b)).eq('ruang_meeting', room)
        if exclude_id:
            query = query.neq('id', exclude_id)
        result = query.execute()
        for b in result.data:
            existing_start = datetime.strptime(b['waktu_mulai'], '%H:%M:%S').time()
            existing_end = datetime.strptime(b['waktu_selesai'], '%H:%M:%S').time()
            if (start < existing_end and end > existing_start):
                return False, f"Jadwal bentrok dengan {b['nama']} ({existing_start}-{existing_end})"
        return True, ""
    except Exception as e:
        return False, str(e)

def check_admin_auth():
    return st.session_state.get('admin_authenticated', False)

def admin_login():
    st.subheader("🔐 Admin Login")
    with st.form("admin_login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            try:
                correct_user = st.secrets.get("admin", {}).get("username", "admin")
                correct_hash = st.secrets.get("admin", {}).get("password_hash", "")
                if username == correct_user and bcrypt.checkpw(password.encode(), correct_hash.encode()):
                    st.session_state['admin_authenticated'] = True
                    st.success("Login berhasil")
                    st.rerun()
                else:
                    st.error("Username atau password salah")
            except:
                st.error("Hash admin rusak, perbarui secrets")
                
def booking_form_page():
    # Layout header dan button
    st.markdown("""
    <div class="header-container">
        <div class="main-header" onclick="window.location.reload()">
            <h1>Meeting Room Booking System</h1>
        </div>
        <div class="nav-buttons">
            <!-- Button "Lihat Daftar Booking" di kanan -->
            <button class="nav-button" id="btn_list">📋 Lihat Daftar Booking</button>
        </div>
    </div>
    <script>
    document.getElementById('btn_list').onclick = function() {
        window.location.href='?page=list';
    }
    </script>
    """, unsafe_allow_html=True)
    
    # Jika di halaman form, sembunyikan button "Booking Room Meeting 19"
    if st.session_state.get('page') != 'form':
        # Tampilkan button "Booking Room Meeting 19" di kanan atas
        st.markdown("""
        <div style="display:flex; justify-content:flex-end; margin-top:1rem;">
            <button class="nav-button" id="btn_home">Booking Room Meeting 19</button>
        </div>
        <script>
        document.getElementById('btn_home').onclick = function() {
            window.location.href='?page=form';
        }
        </script>
        """, unsafe_allow_html=True)
    
    # Header utama sebagai hyperlink
    st.markdown("""
    <a href="?page=form" style="text-decoration:none;">
        <div class="main-header" style="margin-top:0;">
            <h1 style="font-size:14px; margin:0;">Meeting Room Booking System</h1>
        </div>
    </a>
    """, unsafe_allow_html=True)
    
    # Form booking
    with st.form("booking_form"):
        st.subheader("📝 Form Booking Meeting Room")
        col1, col2 = st.columns(2)
        with col1:
            nama = st.text_input("Nama *")
            subdir = st.text_input("Sub Direktorat")
            no_hp = st.text_input("No. HP *")
        with col2:
            ruang_meeting = st.selectbox("Ruang Meeting *", ["", "Breakout Traction", "Cozy 19.2"])
            tanggal_booking = st.date_input("Tanggal Booking *", min_value=date.today())
            col_time1, col_time2 = st.columns(2)
            with col_time1:
                waktu_mulai = st.time_input("Waktu Mulai *", value=time(9,0))
            with col_time2:
                waktu_selesai = st.time_input("Waktu Selesai *", value=time(10,0))
        keterangan = st.text_area("Keterangan Meeting")
        if st.form_submit_button("📅 Submit Booking"):
            # Validasi dan insert ke database
            # (kode validasi sama seperti sebelumnya)
            pass
    
    # Link admin di bawah
    st.markdown("""
    <div class="admin-link">
        <a href="?page=admin">Admin Panel</a>
    </div>
    """, unsafe_allow_html=True)

def booking_list_page():
    # Header dan button di kanan atas
    st.markdown("""
    <div class="header-container">
        <div class="main-header" onclick="window.location.href='?page=list'">
            <h1>Meeting Room Booking System</h1>
        </div>
        <div class="nav-buttons">
            <!-- Button "Booking Room Meeting 19" di kanan -->
            <button class="nav-button" id="btn_home_list">Booking Room Meeting 19</button>
        </div>
    </div>
    <script>
    document.getElementById('btn_home_list').onclick = function() {
        window.location.href='?page=form';
    }
    </script>
    """, unsafe_allow_html=True)
    # Tampilkan data dan filter seperti sebelumnya
    # (kode sama seperti sebelumnya)
    # Link admin di bawah
    st.markdown("""
    <div class="admin-link">
        <a href="?page=admin">Admin Panel</a>
    </div>
    """, unsafe_allow_html=True)

def main():
    load_css()
    
    # Initialize session state
    if 'page' not in st.session_state:
        st.session_state.page = "form"
    
    # Route to pages
    if st.session_state.page == "form":
        booking_form_page()
    elif st.session_state.page == "list":
        booking_list_page()
    elif st.session_state.page == "admin":
        admin_page()

if __name__ == "__main__":
    main()
