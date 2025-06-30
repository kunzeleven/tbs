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

# CSS untuk styling Apple-like
def load_css():
    st.markdown("""
    <style>
    /* Reset dan base styling */
    .stApp {
        background-color: #ffffff;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }
    
    /* Header styling - Minimalist Apple Style */
    .main-header {
        background: linear-gradient(135deg, #f8f8f8 0%, #e8e8e8 50%, #d8d8d8 100%);
        #padding: 1rem 2rem;
        border-radius: 14px;
        margin-bottom: 1.5rem;
        color: #333333;
        text-align: center;
        border: 1px solid #e0e0e0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    
    .main-header h1 {
        font-size: 1.5rem !important;
        font-weight: 500 !important;
        margin: 0 !important;
        color: #2c2c2c;
        letter-spacing: -0.02em;
    }

    nav_left, nav_right = st.columns([8,2])   # kolom lebar & sempit
    with nav_right:
        if st.button("📋 Lihat Daftar Booking", use_container_width=True):
            st.session_state.page = "list"
            st.rerun()

    /* Override Streamlit button styling for navigation */
    .nav-buttons .stButton > button {
        background: linear-gradient(135deg, #ffffff 0%, #f5f5f5 50%, #ebebeb 100%) !important;
        border: 1px solid #d1d1d1 !important;
        border-radius: 14px !important;
        padding: 0.4rem 0.8rem !important;
        font-size: 0.85rem !important;
        font-weight: 400 !important;
        color: #333333 !important;
        transition: all 0.2s ease !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.04) !important;
        height: auto !important;
        min-height: auto !important;
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, #f8f8f8 0%, #eeeeee 50%, #e0e0e0 100%) !important;
        border-color: #b8b8b8 !important;
        transform: translateY(-0.5px) !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.08) !important;
        color: #1a1a1a !important;
    }
    
    .stButton > button:active {
        transform: translateY(0px) !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.06) !important;
    }


    /* Primary action buttons (Submit) */
    .stButton > button[kind="primary"], 
    .stButton > button:contains("Submit") {
        background: linear-gradient(135deg, #007AFF 0%, #0056CC 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 14px !important;
        padding: 0.75rem 1.5rem !important;
        font-weight: 500 !important;
        transition: all 0.2s ease !important;
    }
    
    /* Form styling */
    .stForm {
        background: #f8f9fa;
        padding: 2rem;
        border-radius: 12px;
        border: 1px solid #e9ecef;
        box-shadow: 0 2px 12px rgba(0,0,0,0.08);
    }
    
    /* Input styling */
    .stTextInput > div > div > input,
    .stSelectbox > div > div > select,
    .stDateInput > div > div > input,
    .stTimeInput > div > div > input {
        border: 1px solid #d1d5db;
        border-radius: 14px;
        padding: 0.75rem;
        font-size: 16px;
        transition: border-color 0.2s ease;
    }
    
    .stTextInput > div > div > input:focus,
    .stSelectbox > div > div > select:focus {
        border-color: #007AFF;
        box-shadow: 0 0 0 3px rgba(0,122,255,0.1);
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
        # Validasi apakah secrets tersedia
        if "supabase" not in st.secrets:
            st.error("⚠️ Konfigurasi Supabase tidak ditemukan dalam secrets")
            return None
            
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        
        # Validasi format URL dan key
        if not url or not url.startswith("https://"):
            st.error("⚠️ URL Supabase tidak valid")
            return None
            
        if not key or len(key) < 100:  # Anon key biasanya panjang
            st.error("⚠️ API Key Supabase tidak valid")
            return None
            
        # Buat client Supabase
        supabase = create_client(url, key)
        
        # Test koneksi
        try:
            # Coba query sederhana untuk test koneksi
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

#def validate_phone(phone: str) -> Tuple[bool, str]:
#    if not phone:
#        return False, "Nomor HP harus diisi"
#    phone_clean = re.sub(r'[^\d]', '', phone)
#    if len(phone_clean) < 10 or len(phone_clean) > 15:
#        return False, "Nomor HP tidak valid (10-15 digit)"
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

    # Navigation buttons
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("🔙 Kembali ke Daftar Booking", use_container_width=True):
            st.session_state.page = "list"
            st.rerun()
    with col2:
        if st.button("🔙 Kembali ke Form", use_container_width=True):
            st.session_state.page = "form"
            st.rerun()
    
    with st.form("admin_login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")
        
        if submit:
            # Hash password yang benar (ganti dengan password yang diinginkan)
            correct_username = st.secrets.get("admin", {}).get("username", "admin")
            correct_password_hash = st.secrets.get("admin", {}).get("password_hash", "")
            
            if username == correct_username and bcrypt.checkpw(password.encode('utf-8'), correct_password_hash.encode('utf-8')):
                st.session_state.admin_authenticated = True
                st.success("Login berhasil!")
                st.rerun()
            else:
                st.error("Username atau password salah")

# Halaman Form Booking
def booking_form_page():
    st.markdown('<div class="main-header"><h1>🏢 Booking Room Meeting 19</h1></div>', unsafe_allow_html=True)
  
    # Navigation buttons
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("📋 Lihat Daftar Booking", use_container_width=True):
            st.session_state.page = "list"
            st.rerun()
    #with col3:
    #    if st.button("⚙️ Admin Panel", use_container_width=True):
    #        st.session_state.page = "admin"
    #        st.rerun()
    
    st.markdown("---")
    
    # Form booking
    with st.form("booking_form", clear_on_submit=True):
        st.subheader("📝 Form Booking Meeting Room")
        
        col1, col2 = st.columns(2)
        
        with col1:
            nama = st.text_input("Nama *", placeholder="Masukkan Nama Lengkap")
            subdir = st.text_input("Sub Direktorat", placeholder="Masukkan Sub Direktorat")
            floor = st.text_input("Lantai Meeting *", placeholder="19")
            
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
                
            #is_valid, error = validate_phone(floor)
            #if not is_valid:
            #    errors.append(error)
                
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
                                "floor": floor.strip(),
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

def debug_supabase_connection():
    """Fungsi untuk debugging koneksi Supabase"""
    if st.button("🔍 Test Koneksi Supabase"):
        try:
            # Cek apakah secrets tersedia
            if "supabase" not in st.secrets:
                st.error("❌ Secrets supabase tidak ditemukan")
                return
                
            url = st.secrets["supabase"]["url"]
            key = st.secrets["supabase"]["key"]
            
            # Tampilkan info tanpa mengekspos key lengkap
            st.info(f"📍 URL: {url}")
            st.info(f"🔑 Key: {key[:20]}...{key[-10:]}")
            
            # Test koneksi
            supabase = create_client(url, key)
            result = supabase.table('bookings').select('count').execute()
            
            st.success("✅ Koneksi berhasil!")
            
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")


# Halaman List Booking
def booking_list_page():
    st.markdown('<div class="main-header"><h1>📋 Daftar Booking Meeting Room</h1></div>', unsafe_allow_html=True)
    
    # Navigation buttons
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("🔙 Kembali ke Form", use_container_width=True):
            st.session_state.page = "form"
            st.rerun()
    #with col2:
    #    if st.button("⚙️ Admin Panel", use_container_width=True):
    #        st.session_state.page = "admin"
    #        st.rerun()
    
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
                
                display_df = df[['Tanggal', 'Waktu', 'nama', 'subdir', 'floor', 'ruang_meeting', 'keterangan']].copy()
                display_df.columns = ['Tanggal', 'Waktu', 'Nama', 'Sub Direktorat', 'Lantai', 'Ruang', 'Keterangan']
                
                st.dataframe(display_df, use_container_width=True, hide_index=True)
                
                # Filter berdasarkan tanggal
                st.subheader("🔍 Filter Booking")
                filter_date = st.date_input("Pilih tanggal", value=date.today())
                
                filtered_df = df[df['tanggal_booking'] == str(filter_date)]
                if not filtered_df.empty:
                    st.write(f"**Booking untuk tanggal {filter_date.strftime('%d/%m/%Y')}:**")
                    display_filtered = filtered_df[['Waktu', 'nama', 'subdir', 'floor', 'ruang_meeting', 'keterangan']].copy()
                    display_filtered.columns = ['Waktu', 'Nama', 'Sub Direktorat', 'Lantai', 'Ruang', 'Keterangan']
                    st.dataframe(display_filtered, use_container_width=True, hide_index=True)
                else:
                    st.info("Tidak ada booking pada tanggal tersebut")
                    
            else:
                st.info("Belum ada data booking")
                
        except Exception as e:
            st.error(f"Error loading data: {str(e)}")

    st.markdown("")
    st.markdown("")
    st.markdown("")
    
    # ----- TOMBOL ADMIN DI BAWAH FORM -----
    bottom_left, bottom_center, bottom_right = st.columns(3)
    with bottom_center:
        if st.button("adminpanel", key="admin_panel_bottom",use_container_width=True, type="tertiary"):
            st.session_state.page = "admin"
            st.rerun()
                     
# Halaman Admin
def admin_page():
    st.markdown('<div class="main-header"><h1>⚙️ Admin Panel</h1></div>', unsafe_allow_html=True)
    
    if not check_admin_auth():
        admin_login()
        return
    
    # Navigation buttons
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🔙 Kembali ke Form", use_container_width=True):
            st.session_state.page = "form"
            st.rerun()
    with col2:
        if st.button("📋 Lihat Daftar", use_container_width=True):
            st.session_state.page = "list"
            st.rerun()
    with col3:
        if st.button("🚪 Logout", use_container_width=True):
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
                df.drop(columns=["floor"], inplace=True, errors="ignore")
              
                # PERBAIKAN: Konversi tipe data yang benar
                try:
                    df['tanggal_booking'] = pd.to_datetime(df['tanggal_booking'], errors='coerce').dt.date
                    df['waktu_mulai'] = pd.to_datetime(df['waktu_mulai'], format='%H:%M:%S', errors='coerce').dt.time
                    df['waktu_selesai'] = pd.to_datetime(df['waktu_selesai'], format='%H:%M:%S', errors='coerce').dt.time
                    if 'created_at' in df.columns:
                        df['created_at'] = pd.to_datetime(df['created_at'], errors='coerce')
                except Exception as e:
                    st.error(f"Error konversi data: {str(e)}")
                    return
                
                st.subheader("✏️ Edit & Hapus Booking")
                
                # Data editor dengan konfigurasi yang tepat
                edited_df = st.data_editor(
                    df,
                    column_config={
                        "id": st.column_config.NumberColumn("ID", disabled=True),
                        "nama": st.column_config.TextColumn("Nama", required=True),
                        "subdir": st.column_config.TextColumn("Sub Direktorat"),
                        "floor": st.column_config.TextColumn("No. HP", required=True),
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
    
    # Route to pages
    if st.session_state.page == "form":
        booking_form_page()
    elif st.session_state.page == "list":
        booking_list_page()
    elif st.session_state.page == "admin":
        admin_page()

if __name__ == "__main__":
    main()
