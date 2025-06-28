import streamlit as st
import pandas as pd
from datetime import datetime, date, time
import re
from supabase import create_client, Client

# =========================
# Load CSS dengan style yang diminta
# =========================
def load_css():
    st.markdown("""
    <style>
    /* Reset dan base styling */
    .stApp {
        background-color: #ffffff;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }

    /* Header utama: ukuran sama dengan tombol "Lihat Daftar Booking" dan posisi sejajar */
    .header-container {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 1rem;
        padding: 0 1rem;
    }

    /* Header "Meeting Room Booking System" */
    .main-header {
        font-size: 14px; /* sama dengan tombol "Lihat Daftar Booking" */
        font-weight: bold;
        cursor: pointer;
        margin: 0;
        padding: 0;
        color: #007AFF;
        transition: opacity 0.2s ease;
    }
    .main-header:hover {
        opacity: 0.8;
        text-decoration: underline;
    }

    /* Button style yang sama dengan tombol "Lihat Daftar Booking" */
    .styled-button {
        background: #007AFF;
        color: white;
        border: none;
        border-radius: 25px;
        padding: 0.6rem 1.2rem;
        font-size: 14px;
        font-weight: 500;
        cursor: pointer;
        min-width: 140px;
        height: 42px;
        transition: all 0.2s ease;
    }
    .styled-button:hover {
        background: #0056CC;
        box-shadow: 0 4px 12px rgba(0,122,255,0.3);
        transform: translateY(-1px);
    }

    /* Container untuk tombol dan header agar sejajar */
    .top-bar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0 1rem;
        margin-bottom: 1rem;
    }

    /* Tombol tanpa label di halaman "Lihat Daftar Booking" (hilangkan) */
    /* Tidak perlu style khusus karena kita akan hapus button tersebut */

    /* Link "Admin Panel" di bagian bawah */
    .admin-link {
        text-align: center;
        margin-top: 3rem;
        padding: 2rem 0;
        border-top: 1px solid #f0f0f0;
    }
    .admin-link a {
        color: #007AFF;
        text-decoration: underline;
        font-size: 14px;
        opacity: 0.7;
        transition: opacity 0.2s ease;
        cursor: pointer;
    }
    .admin-link a:hover {
        opacity: 1;
    }

    /* Style form dan table tetap sama */
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
        box-shadow: 0 4px 12px rgba(0,122,255,0.3);
        transform: translateY(-1px);
    }
    /* Input styling dan lainnya tetap sama */
    </style>
    """, unsafe_allow_html=True)

# =========================
# Inisialisasi koneksi Supabase
# =========================
@st.cache_resource
def init_supabase():
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"Error koneksi ke database: {str(e)}")
        return None

# =========================
# Validasi input
# =========================
def validate_name(name):
    if not name or len(name.strip()) < 2:
        return False, "Nama harus diisi minimal 2 karakter"
    if not re.match(r'^[A-Za-z\s]+$', name.strip()):
        return False, "Nama hanya boleh berisi huruf dan spasi"
    return True, ""

def validate_phone(phone):
    if not phone:
        return False, "Nomor HP harus diisi"
    phone_clean = re.sub(r'[^\d]', '', phone)
    if len(phone_clean) < 10 or len(phone_clean) > 15:
        return False, "Nomor HP tidak valid (10-15 digit)"
    return True, ""

def validate_time_range(start_time, end_time):
    if start_time >= end_time:
        return False, "Waktu selesai harus lebih besar dari waktu mulai"
    return True, ""

def validate_booking_conflict(supabase, date_booking, start_time, end_time, room, exclude_id=None):
    try:
        query = supabase.table('bookings').select('*').eq('tanggal_booking', str(date_booking)).eq('ruang_meeting', room)
        if exclude_id:
            query = query.neq('id', exclude_id)
        result = query.execute()
        for b in result.data:
            existing_start = datetime.strptime(b['waktu_mulai'], '%H:%M:%S').time()
            existing_end = datetime.strptime(b['waktu_selesai'], '%H:%M:%S').time()
            if (start_time < existing_end and end_time > existing_start):
                return False, f"Konflik jadwal dengan {b['nama']} ({existing_start}-{existing_end})"
        return True, ""
    except:
        return False, "Gagal validasi konflik jadwal"

# =========================
# Halaman utama: form booking
# =========================
def booking_form_page():
    # Header dan tombol sejajar
    st.markdown('<div class="header-container">', unsafe_allow_html=True)
    # Header sebagai hyperlink ke homepage
    st.markdown('<h1 class="main-header" onclick="window.location.reload()" style="margin:0;">Meeting Room Booking System</h1>', unsafe_allow_html=True)
    # Tombol "Lihat Daftar Booking"
    st.markdown(f'''
        <button class="styled-button" onclick="window.location.href='?page=list'">Lihat Daftar Booking</button>
    ''', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

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
                            "created_at": datetime.now().isoformat()
                        }
                        try:
                            supabase.table('bookings').insert(data).execute()
                            st.success("Booking berhasil disimpan!")
                        except:
                            st.error("Gagal menyimpan data.")

# =========================
# Halaman daftar booking
# =========================
def booking_list_page():
    # Header dan tombol
    st.markdown('<div class="header-container">', unsafe_allow_html=True)
    # Header sebagai hyperlink ke homepage
    st.markdown('<h1 class="main-header" onclick="window.location.reload()" style="margin:0;">📋 Daftar Booking Meeting Room</h1>', unsafe_allow_html=True)
    # Tombol "Booking Room Meeting 19" jika tidak di halaman form
    if st.session_state.get('page') != 'form':
        st.markdown(f'''
            <button class="styled-button" onclick="window.location.href='?page=form'">Booking Room Meeting 19</button>
        ''', unsafe_allow_html=True)
    # Tombol "Lihat Daftar Booking" (sebagai link)
    st.markdown(f'''
        <button class="styled-button" onclick="window.location.href='?page=list'">Lihat Daftar Booking</button>
    ''', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

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
            else:
                st.info("Belum ada data booking.")
        except:
            st.error("Gagal memuat data.")

# =========================
# Halaman admin login
# =========================
def admin_login_page():
    st.markdown('<div class="main-header"><h1 style="font-size:14px;">Admin Login</h1></div>', unsafe_allow_html=True)
    with st.form("admin_login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        if submitted:
            try:
                correct_username = st.secrets["admin"]["username"]
                correct_hash = st.secrets["admin"]["password_hash"]
                if username == correct_username and bcrypt.checkpw(password.encode('utf-8'), correct_hash.encode('utf-8')):
                    st.session_state['admin_logged_in'] = True
                    st.success("Login berhasil!")
                else:
                    st.error("Username atau password salah")
            except:
                st.error("Terjadi error saat login.")

# =========================
# Halaman utama pengontrol
# =========================
def main():
    load_css()
    if 'page' not in st.session_state:
        st.session_state['page'] = 'form'
    page = st.experimental_get_query_params().get('page', [st.session_state['page']])[0]
    st.session_state['page'] = page

    if page == 'form':
        booking_form_page()
    elif page == 'list':
        booking_list_page()
    elif page == 'admin':
        if not st.session_state.get('admin_logged_in', False):
            admin_login_page()
        else:
            # Halaman admin utama
            st.markdown('<div class="header-container">', unsafe_allow_html=True)
            # Header sebagai hyperlink ke homepage
            st.markdown('<h1 class="main-header" onclick="window.location.reload()" style="margin:0;">⚙️ Admin Panel</h1>', unsafe_allow_html=True)
            # Button logout
            if st.button("Logout"):
                st.session_state['admin_logged_in'] = False
                st.experimental_rerun()
            st.markdown('</div>', unsafe_allow_html=True)
            # Tambahkan halaman admin lainnya sesuai kebutuhan
            st.info("Halaman admin belum diimplementasikan.")
    else:
        st.error("Halaman tidak ditemukan.")

if __name__ == "__main__":
    main()
