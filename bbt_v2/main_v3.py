import streamlit as st
import pandas as pd
from datetime import datetime, date, time
import re
from supabase import create_client, Client
import bcrypt
from typing import Optional, Tuple
import os

# Konfigurasi halaman
st.set_page_config(
    page_title="Meeting Room Booking",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS untuk styling Apple-like dengan perbaikan UI terbaru
def load_css():
    st.markdown("""
    <style>
    /* Reset dan base styling */
    .stApp {
        background-color: #ffffff;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }
    
    /* Header container untuk alignment dengan button */
    .header-nav-container {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 2rem;
        padding: 0.5rem 0;
    }
    
    /* Header styling - sama dengan button size dan sejajar */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 0.6rem 1.2rem; /* Sama dengan button padding */
        border-radius: 25px; /* Sama dengan button border-radius */
        color: white;
        font-size: 14px; /* Sama dengan button font-size */
        font-weight: 500; /* Sama dengan button font-weight */
        height: 42px; /* Sama dengan button height */
        display: flex;
        align-items: center;
        cursor: pointer;
        transition: all 0.2s ease;
        text-decoration: none;
        min-width: 200px;
        box-sizing: border-box;
    }
    
    .main-header:hover {
        background: linear-gradient(135deg, #5a6fd8 0%, #6a4190 100%);
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(102,126,234,0.3);
        color: white;
        text-decoration: none;
    }
    
    .main-header h1 {
        font-size: 14px !important; /* Sama dengan button font-size */
        margin: 0 !important;
        font-weight: 500 !important;
        line-height: 1 !important;
    }
    
    /* Navigation buttons container */
    .nav-buttons {
        display: flex;
        gap: 0.75rem;
        align-items: center;
    }
    
    /* Navigation buttons styling - rounded circle */
    div[data-testid="column"] button {
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
        box-sizing: border-box !important;
    }
    
    div[data-testid="column"] button:hover {
        background: #0056CC !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 12px rgba(0,122,255,0.3) !important;
    }
    
    /* Hide secondary buttons (button biru tanpa label) */
    button[kind="secondary"] {
        display: none !important;
    }
    
    /* Admin link di bawah - diperbaiki menjadi hyperlink yang benar */
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
    
    /* Form styling */
    .stForm {
        background: #f8f9fa;
        padding: 2rem;
        border-radius: 12px;
        border: 1px solid #e9ecef;
        box-shadow: 0 2px 12px rgba(0,0,0,0.08);
    }
    
    /* Button styling untuk form */
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
    
    /* Input styling */
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
    
    /* Table styling */
    .stDataFrame {
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        overflow: hidden;
    }
    
    /* Success/Error messages */
    .stSuccess, .stError, .stWarning {
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
    
    /* Hide Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display: none;}
    </style>
    """, unsafe_allow_html=True)

# Inisialisasi Supabase connection
@st.cache_resource
def init_supabase():
    try:
        if "supabase" not in st.secrets:
            st.error("⚠️ Konfigurasi Supabase tidak ditemukan dalam secrets")
            return None
            
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        
        if not url or not url.startswith("https://"):
            st.error("⚠️ URL Supabase tidak valid")
            return None
            
        if not key or len(key) < 100:
            st.error("⚠️ API Key Supabase tidak valid")
            return None
            
        supabase = create_client(url, key)
        
        try:
            test_result = supabase.table('bookings').select('count').execute()
            return supabase
        except Exception as test_error:
            st.error(f"⚠️ Gagal terhubung ke database: {str(test_error)}")
            return None
            
    except KeyError as e:
        st.error(f"⚠️ Konfigurasi tidak lengkap: {str(e)}")
        return None
    except Exception as e:
        st.error(f"⚠️ Error saat inisialisasi Supabase: {str(e)}")
        return None

# Fungsi validasi
def validate_name(name: str) -> Tuple[bool, str]:
    if not name or len(name.strip()) < 2:
        return False, "Nama harus diisi minimal 2 karakter"
    if not re.match(r'^[A-Za-z\s]+$', name.strip()):
        return False, "Nama hanya boleh berisi huruf dan spasi"
    return True, ""

def validate_phone(phone: str) -> Tuple[bool, str]:
    if not phone:
        return False, "Nomor HP harus diisi"
    phone_clean = re.sub(r'[^\d]', '', phone)
    if len(phone_clean) < 10 or len(phone_clean) > 15:
        return False, "Nomor HP tidak valid (10-15 digit)"
    return True, ""

def validate_time_range(start_time: time, end_time: time) -> Tuple[bool, str]:
    if start_time >= end_time:
        return False, "Waktu selesai harus lebih besar dari waktu mulai"
    return True, ""

def validate_booking_conflict(supabase: Client, booking_date: date, start_time: time, 
                            end_time: time, room: str, booking_id: int = None) -> Tuple[bool, str]:
    try:
        query = supabase.table('bookings').select('*').eq('tanggal_booking', str(booking_date)).eq('ruang_meeting', room)
        if booking_id:
            query = query.neq('id', booking_id)
        
        result = query.execute()
        
        for booking in result.data:
            existing_start = datetime.strptime(booking['waktu_mulai'], '%H:%M:%S').time()
            existing_end = datetime.strptime(booking['waktu_selesai'], '%H:%M:%S').time()
            
            if (start_time < existing_end and end_time > existing_start):
                return False, f"Konflik jadwal dengan booking {booking['nama']} ({existing_start}-{existing_end})"
        
        return True, ""
    except Exception as e:
        return False, "Error validating booking conflict"

# Fungsi autentikasi admin
def check_admin_auth() -> bool:
    if 'admin_authenticated' not in st.session_state:
        st.session_state.admin_authenticated = False
    return st.session_state.admin_authenticated

def admin_login():
    st.subheader("🔐 Admin Login")
    
    with st.form("admin_login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")
        
        if submit:
            try:
                correct_username = st.secrets.get("admin", {}).get("username", "admin")
                correct_password_hash = st.secrets.get("admin", {}).get("password_hash", "")
                
                if (username == correct_username 
                    and correct_password_hash 
                    and bcrypt.checkpw(password.encode('utf-8'), correct_password_hash.encode('utf-8'))):
                    st.session_state.admin_authenticated = True
                    st.success("Login berhasil!")
                    st.rerun()
                else:
                    st.error("Username atau password salah")
            except ValueError:
                st.error("Hash admin rusak — silakan perbarui secrets.toml")
            except Exception as e:
                st.error(f"Error saat login: {str(e)}")

# Halaman Form Booking dengan UI yang diperbaiki
def booking_form_page():
    # Header dan navigation dalam satu container sejajar
    st.markdown("""
    <div class="header-nav-container">
        <div class="main-header" onclick="homeNavigate()">
            <h1>Meeting Room Booking System</h1>
        </div>
        <div class="nav-buttons">
            <!-- Navigation buttons akan ditempatkan di sini oleh Streamlit -->
        </div>
    </div>
    
    <script>
    function homeNavigate() {
        // Sudah di homepage, tidak perlu navigasi
        window.location.reload();
    }
    </script>
    """, unsafe_allow_html=True)
    
    # Navigation button - hanya "Lihat Daftar Booking"
    col1, col2 = st.columns([10, 2])
    
    with col2:
        if st.button("📋 Lihat Daftar Booking", key="nav_list"):
            st.session_state.page = "list"
            st.rerun()
    
    # Form booking
    with st.form("booking_form", clear_on_submit=True):
        st.subheader("📝 Form Booking Meeting Room")
        
        col1, col2 = st.columns(2)
        
        with col1:
            nama = st.text_input("Nama *", placeholder="Masukkan nama lengkap")
            subdir = st.text_input("Sub Direktorat", placeholder="Masukkan sub direktorat")
            no_hp = st.text_input("No. HP *", placeholder="Contoh: 08123456789")
            
        with col2:
            ruang_meeting = st.selectbox("Ruang Meeting *", ["", "Breakout Traction", "Cozy 19.2"])
            tanggal_booking = st.date_input("Tanggal Booking *", min_value=date.today())
            
            col_time1, col_time2 = st.columns(2)
            with col_time1:
                waktu_mulai = st.time_input("Waktu Mulai *", value=time(9, 0))
            with col_time2:
                waktu_selesai = st.time_input("Waktu Selesai *", value=time(10, 0))
        
        keterangan = st.text_area("Keterangan Meeting", placeholder="Agenda atau keterangan tambahan")
        
        submitted = st.form_submit_button("📅 Submit Booking", use_container_width=True)
        
        if submitted:
            # Validasi input
            errors = []
            
            is_valid, error = validate_name(nama)
            if not is_valid:
                errors.append(error)
                
            is_valid, error = validate_phone(no_hp)
            if not is_valid:
                errors.append(error)
                
            if not ruang_meeting:
                errors.append("Ruang meeting harus dipilih")
                
            is_valid, error = validate_time_range(waktu_mulai, waktu_selesai)
            if not is_valid:
                errors.append(error)
            
            if errors:
                for error in errors:
                    st.error(error)
            else:
                # Cek konflik jadwal
                supabase = init_supabase()
                if supabase:
                    is_valid, error = validate_booking_conflict(supabase, tanggal_booking, waktu_mulai, waktu_selesai, ruang_meeting)
                    if not is_valid:
                        st.error(error)
                    else:
                        # Insert ke database
                        try:
                            data = {
                                "nama": nama.strip(),
                                "subdir": subdir.strip(),
                                "no_hp": no_hp.strip(),
                                "ruang_meeting": ruang_meeting,
                                "tanggal_booking": str(tanggal_booking),
                                "waktu_mulai": str(waktu_mulai),
                                "waktu_selesai": str(waktu_selesai),
                                "keterangan": keterangan.strip(),
                                "created_at": datetime.now().isoformat()
                            }
                            
                            result = supabase.table('bookings').insert(data).execute()
                            st.success("✅ Booking berhasil disimpan!")
                            st.balloons()
                            
                        except Exception as e:
                            st.error(f"Error menyimpan data: {str(e)}")
    
    # Admin link di bawah - hyperlink yang benar
    st.markdown("""
    <div class="admin-link">
        <a href="javascript:void(0)" onclick="navigateToAdmin()">Admin Panel</a>
    </div>
    
    <script>
    function navigateToAdmin() {
        // Set session state untuk admin page
        fetch('/admin-navigate', {method: 'POST'}).catch(() => {
            // Fallback: reload page dan set URL parameter
            window.location.href = window.location.href + '?page=admin';
        });
    }
    
    // Check URL parameter for admin navigation
    window.addEventListener('load', function() {
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.get('page') === 'admin') {
            // Trigger admin navigation
            const forms = document.querySelectorAll('form');
            if (forms.length > 0) {
                const adminInput = document.createElement('input');
                adminInput.type = 'hidden';
                adminInput.name = 'admin_nav';
                adminInput.value = 'true';
                forms[0].appendChild(adminInput);
            }
        }
    });
    </script>
    """, unsafe_allow_html=True)
    
    # Check untuk admin navigation
    if st.query_params.get("page") == "admin":
        st.session_state.page = "admin"
        st.query_params.clear()
        st.rerun()

# Halaman List Booking dengan perbaikan
def booking_list_page():
    # Header dan navigation sejajar
    st.markdown("""
    <div class="header-nav-container">
        <div class="main-header" onclick="homeNavigate()">
            <h1>Meeting Room Booking System</h1>
        </div>
        <div class="nav-buttons">
            <!-- Navigation buttons akan ditempatkan di sini -->
        </div>
    </div>
    
    <script>
    function homeNavigate() {
        window.location.href = window.location.pathname;
    }
    </script>
    """, unsafe_allow_html=True)
    
    # Navigation buttons
    col1, col2, col3 = st.columns([8, 2, 2])
    
    with col2:
        if st.button("Booking Room Meeting 19", key="nav_home_list"):
            st.session_state.page = "form"
            st.rerun()
    
    with col3:
        if st.button("📋 Lihat Daftar Booking", key="nav_list_active", disabled=True):
            pass  # Current page
    
    st.markdown("---")
    
    # Load data
    supabase = init_supabase()
    if supabase:
        try:
            result = supabase.table('bookings').select('*').order('tanggal_booking', desc=False).execute()
            
            if result.data:
                df = pd.DataFrame(result.data)
                
                # Format data untuk display
                df['Tanggal'] = pd.to_datetime(df['tanggal_booking']).dt.strftime('%d/%m/%Y')
                df['Waktu'] = df['waktu_mulai'].str[:5] + ' - ' + df['waktu_selesai'].str[:5]
                
                display_df = df[['Tanggal', 'Waktu', 'nama', 'subdir', 'ruang_meeting', 'keterangan']].copy()
                display_df.columns = ['Tanggal', 'Waktu', 'Nama', 'Sub Direktorat', 'Ruang', 'Keterangan']
                
                st.dataframe(display_df, use_container_width=True, hide_index=True)
                
                # Filter berdasarkan tanggal
                st.subheader("🔍 Filter Booking")
                filter_date = st.date_input("Pilih tanggal", value=date.today())
                
                filtered_df = df[df['tanggal_booking'] == str(filter_date)]
                if not filtered_df.empty:
                    st.write(f"**Booking untuk tanggal {filter_date.strftime('%d/%m/%Y')}:**")
                    display_filtered = filtered_df[['Waktu', 'nama', 'subdir', 'ruang_meeting', 'keterangan']].copy()
                    display_filtered.columns = ['Waktu', 'Nama', 'Sub Direktorat', 'Ruang', 'Keterangan']
                    st.dataframe(display_filtered, use_container_width=True, hide_index=True)
                else:
                    st.info("Tidak ada booking pada tanggal tersebut")
                    
            else:
                st.info("Belum ada data booking")
                
        except Exception as e:
            st.error(f"Error loading data: {str(e)}")
    
    # Admin link di bawah - hyperlink yang benar
    st.markdown("""
    <div class="admin-link">
        <a href="?page=admin">Admin Panel</a>
    </div>
    """, unsafe_allow_html=True)
    
    # Check untuk admin navigation
    if st.query_params.get("page") == "admin":
        st.session_state.page = "admin"
        st.query_params.clear()
        st.rerun()

# Fungsi konversi data untuk admin page
def convert_dataframe_types(df):
    """Konversi tipe data DataFrame untuk kompatibilitas dengan st.data_editor"""
    df_converted = df.copy()
    
    try:
        if 'tanggal_booking' in df_converted.columns:
            df_converted['tanggal_booking'] = pd.to_datetime(
                df_converted['tanggal_booking'], 
                errors='coerce'
            ).dt.date
        
        if 'waktu_mulai' in df_converted.columns:
            df_converted['waktu_mulai'] = pd.to_datetime(
                df_converted['waktu_mulai'], 
                format='%H:%M:%S',
                errors='coerce'
            ).dt.time
            
        if 'waktu_selesai' in df_converted.columns:
            df_converted['waktu_selesai'] = pd.to_datetime(
                df_converted['waktu_selesai'], 
                format='%H:%M:%S',
                errors='coerce'
            ).dt.time
        
        if 'created_at' in df_converted.columns:
            df_converted['created_at'] = pd.to_datetime(
                df_converted['created_at'], 
                errors='coerce'
            )
        
        return df_converted
        
    except Exception as e:
        st.error(f"Error konversi data: {str(e)}")
        return df

# Halaman Admin dengan styling yang disesuaikan
def admin_page():
    if not check_admin_auth():
        # Header dan navigation untuk admin login - dengan style yang sama
        st.markdown("""
        <div class="header-nav-container">
            <div class="main-header" onclick="homeNavigate()">
                <h1>Meeting Room Booking System</h1>
            </div>
            <div class="nav-buttons">
                <!-- Navigation buttons akan ditempatkan di sini -->
            </div>
        </div>
        
        <script>
        function homeNavigate() {
            window.location.href = window.location.pathname;
        }
        </script>
        """, unsafe_allow_html=True)
        
        # Navigation buttons dengan style yang sama seperti homepage
        col1, col2, col3 = st.columns([8, 2, 2])
        
        with col2:
            if st.button("Booking Room Meeting 19", key="nav_home_admin"):
                st.session_state.page = "form"
                st.rerun()
        
        with col3:
            if st.button("📋 Lihat Daftar Booking", key="nav_list_admin"):
                st.session_state.page = "list"
                st.rerun()
        
        st.markdown("---")
        admin_login()
        return
    
    # Header dan navigation untuk admin yang sudah login
    st.markdown("""
    <div class="header-nav-container">
        <div class="main-header" onclick="homeNavigate()">
            <h1>Meeting Room Booking System</h1>
        </div>
        <div class="nav-buttons">
            <!-- Navigation buttons akan ditempatkan di sini -->
        </div>
    </div>
    
    <script>
    function homeNavigate() {
        window.location.href = window.location.pathname;
    }
    </script>
    """, unsafe_allow_html=True)
    
    # Navigation buttons untuk admin yang sudah login
    col1, col2, col3, col4 = st.columns([6, 2, 2, 2])
    
    with col2:
        if st.button("Booking Room Meeting 19", key="nav_home_admin_auth"):
            st.session_state.page = "form"
            st.rerun()
    
    with col3:
        if st.button("📋 Lihat Daftar Booking", key="nav_list_admin_auth"):
            st.session_state.page = "list"
            st.rerun()
    
    with col4:
        if st.button("🚪 Logout", key="logout_btn"):
            st.session_state.admin_authenticated = False
            st.rerun()
    
    st.markdown("---")
    
    # Load dan edit data
    supabase = init_supabase()
    if supabase:
        try:
            result = supabase.table('bookings').select('*').order('tanggal_booking', desc=False).execute()
            
            if result.data:
                df = pd.DataFrame(result.data)
                
                # Konversi tipe data
                df = convert_dataframe_types(df)
                
                st.subheader("✏️ Edit & Hapus Booking")
                
                # Data editor untuk admin
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
                        "tanggal_booking": st.column_config.DateColumn(
                            "Tanggal Booking", 
                            required=True,
                            format="DD/MM/YYYY"
                        ),
                        "waktu_mulai": st.column_config.TimeColumn("Waktu Mulai", required=True),
                        "waktu_selesai": st.column_config.TimeColumn("Waktu Selesai", required=True),
                        "keterangan": st.column_config.TextColumn("Keterangan"),
                        "created_at": st.column_config.DatetimeColumn("Dibuat", disabled=True)
                    },
                    num_rows="dynamic",
                    use_container_width=True,
                    key="booking_editor"
                )
                
                # Tombol untuk menyimpan perubahan
                if st.button("💾 Simpan Perubahan", type="primary"):
                    try:
                        if "booking_editor" in st.session_state:
                            editor_state = st.session_state["booking_editor"]
                            
                            # Handle edited rows
                            if "edited_rows" in editor_state:
                                for idx, changes in editor_state["edited_rows"].items():
                                    row_id = df.iloc[idx]["id"]
                                    
                                    # Konversi perubahan ke format database
                                    db_changes = {}
                                    for key, value in changes.items():
                                        if key == 'tanggal_booking' and hasattr(value, 'strftime'):
                                            db_changes[key] = value.strftime('%Y-%m-%d')
                                        elif key in ['waktu_mulai', 'waktu_selesai'] and hasattr(value, 'strftime'):
                                            db_changes[key] = value.strftime('%H:%M:%S')
                                        else:
                                            db_changes[key] = value
                                    
                                    supabase.table('bookings').update(db_changes).eq('id', row_id).execute()
                            
                            # Handle deleted rows
                            if "deleted_rows" in editor_state:
                                for idx in editor_state["deleted_rows"]:
                                    row_id = df.iloc[idx]["id"]
                                    supabase.table('bookings').delete().eq('id', row_id).execute()
                            
                            # Handle added rows
                            if "added_rows" in editor_state:
                                for row in editor_state["added_rows"]:
                                    row_data = dict(row)
                                    
                                    # Konversi data baru ke format database
                                    if 'tanggal_booking' in row_data and hasattr(row_data['tanggal_booking'], 'strftime'):
                                        row_data['tanggal_booking'] = row_data['tanggal_booking'].strftime('%Y-%m-%d')
                                    if 'waktu_mulai' in row_data and hasattr(row_data['waktu_mulai'], 'strftime'):
                                        row_data['waktu_mulai'] = row_data['waktu_mulai'].strftime('%H:%M:%S')
                                    if 'waktu_selesai' in row_data and hasattr(row_data['waktu_selesai'], 'strftime'):
                                        row_data['waktu_selesai'] = row_data['waktu_selesai'].strftime('%H:%M:%S')
                                    
                                    row_data["created_at"] = datetime.now().isoformat()
                                    supabase.table('bookings').insert(row_data).execute()
                        
                        st.success("✅ Perubahan berhasil disimpan!")
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"Error menyimpan perubahan: {str(e)}")
                        
            else:
                st.info("Belum ada data booking")
                
        except Exception as e:
            st.error(f"Error loading data: {str(e)}")

# Main app
def main():
    load_css()
    
    # Initialize session state
    if 'page' not in st.session_state:
        st.session_state.page = "form"
    
    # Check URL parameters for navigation
    page_param = st.query_params.get("page")
    if page_param and page_param in ["form", "list", "admin"]:
        st.session_state.page = page_param
        st.query_params.clear()
    
    # Route to pages
    if st.session_state.page == "form":
        booking_form_page()
    elif st.session_state.page == "list":
        booking_list_page()
    elif st.session_state.page == "admin":
        admin_page()

if __name__ == "__main__":
    main()
