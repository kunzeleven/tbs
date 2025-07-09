"""
Aplikasi Booking Meeting Room
Versi: 3.3 – Required Field Validation
Deskripsi: Validasi field required untuk floor, ruang_meeting, dan keterangan
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date, time
import calendar
import re
from supabase import create_client, Client
import bcrypt
from typing import Tuple
import os

# ──────────────────────────────────────────────────────────────────────────────
# 1. KONFIGURASI HALAMAN & CSS
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Meeting Room Booking",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="collapsed",
)

def load_css() -> None:
    """Memuat custom CSS bergaya minimalis Apple-like."""
    st.markdown(
        """
        <style>
        .stApp {
            background-color: #ffffff;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }
        .main-header {
            background: linear-gradient(135deg, #f8f8f8 0%, #e8e8e8 50%, #d8d8d8 100%);
            border: 1px solid #e0e0e0;
            border-radius: 14px;
            margin-bottom: 1.5rem;
            text-align: center;
            color: #333;
            box-shadow: 0 1px 3px rgba(0,0,0,.05);
        }
        .main-header h1 {
            font-size: 1.6rem !important;
            font-weight: 500;
            margin: 0;
            padding: 1rem;
        }
        .calendar-container {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 100%;
            margin: 0 auto;
        }
        .calendar-container table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        .calendar-container th, .calendar-container td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: center;
            vertical-align: top;
            height: 80px;
        }
        .calendar-container th {
            background-color: #f2f2f2;
            font-weight: bold;
            height: 40px;
        }
        .calendar-container td {
            background-color: #fff;
        }
        .calendar-container td:hover {
            background-color: #f9f9f9;
        }
        .calendar-container small {
            font-size: 10px;
            line-height: 1.2;
        }
        .booking-breakout {
            color: #FF6B6B;
            font-weight: bold;
        }
        .booking-cozy {
            color: #4ECDC4;
            font-weight: bold;
        }
        .required-field {
            color: #FF6B6B;
            font-weight: bold;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

load_css()

# ──────────────────────────────────────────────────────────────────────────────
# 2. INISIALISASI SUPABASE
# ──────────────────────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def init_supabase() -> Client | None:
    """Membuat koneksi Supabase dan melakukan pengecekan."""
    try:
        if "supabase" not in st.secrets:
            st.error("⚠️ Konfigurasi Supabase tidak ditemukan dalam secrets")
            return None
        url: str = st.secrets["supabase"]["url"]
        key: str = st.secrets["supabase"]["key"]

        if not url.startswith("https://"):
            st.error("⚠️ URL Supabase tidak valid")
            return None
        if len(key) < 100:
            st.error("⚠️ API Key Supabase tidak valid")
            return None

        supabase: Client = create_client(url, key)
        supabase.table("bookings").select("id").limit(1).execute()
        return supabase
    except Exception as err:
        st.error(f"⚠️ Gagal terhubung ke Supabase: {err}")
        return None

# ──────────────────────────────────────────────────────────────────────────────
# 3. FUNGSI CALENDAR HTML
# ──────────────────────────────────────────────────────────────────────────────
def create_html_calendar(bookings_df, selected_month=None, selected_year=None):
    """Membuat tampilan kalender HTML dengan booking data"""
    if selected_month is None:
        today = date.today()
        month = today.month
        year = today.year
    else:
        month = selected_month
        year = selected_year

    # Membuat kalender HTML
    cal = calendar.HTMLCalendar(firstweekday=0)
    month_html = cal.formatmonth(year, month)

    # Proses booking untuk bulan yang dipilih
    month_bookings = {}
    if not bookings_df.empty:
        for _, row in bookings_df.iterrows():
            booking_date = datetime.strptime(row['tanggal_booking'], '%Y-%m-%d').date()
            if booking_date.month == month and booking_date.year == year:
                day = booking_date.day
                if day not in month_bookings:
                    month_bookings[day] = []
                
                # Tentukan kelas CSS berdasarkan ruang meeting
                room_class = "booking-breakout" if row['ruang_meeting'] == "Breakout Traction" else "booking-cozy"
                
                month_bookings[day].append({
                    'nama': row['nama'],
                    'ruang': row['ruang_meeting'],
                    'waktu': f"{row['waktu_mulai'][:5]}-{row['waktu_selesai'][:5]}",
                    'class': room_class
                })

    # Menambahkan informasi booking ke kalender
    for day, bookings in month_bookings.items():
        booking_info = "<br>".join([
            f"<span class='{b['class']}'>🔹 {b['nama'][:15]}{'...' if len(b['nama']) > 15 else ''}</span><br>"
            f"<small>{b['ruang'][:10]}{'...' if len(b['ruang']) > 10 else ''} ({b['waktu']})</small>"
            for b in bookings
        ])
        month_html = month_html.replace(f'>{day}<', f'>{day}<br><small style="color: #666;">{booking_info}</small><')

    return f"<div class='calendar-container'>{month_html}</div>"

# ──────────────────────────────────────────────────────────────────────────────
# 4. VALIDASI INPUT (DIPERLUAS)
# ──────────────────────────────────────────────────────────────────────────────
def validate_name(name: str) -> Tuple[bool, str]:
    """Validasi field nama"""
    if not name or len(name.strip()) < 2:
        return False, "Nama harus diisi minimal 2 karakter"
    if not re.match(r"^[A-Za-zÀ-ÖØ-öø-ÿ\s]+$", name.strip()):
        return False, "Nama hanya boleh berisi huruf dan spasi"
    return True, ""

def validate_subdir(subdir: str) -> Tuple[bool, str]:
    """Validasi field sub direktorat"""
    if not subdir or len(subdir.strip()) < 2:
        return False, "Sub Direktorat harus diisi minimal 2 karakter"
    return True, ""

def validate_floor(floor: str) -> Tuple[bool, str]:
    """Validasi field floor"""
    if not floor or floor.strip() == "":
        return False, "Lantai harus dipilih"
    if floor not in ["16", "17", "18", "19", "20"]:
        return False, "Lantai yang dipilih tidak valid"
    return True, ""

def validate_ruang_meeting(ruang_meeting: str) -> Tuple[bool, str]:
    """Validasi field ruang meeting"""
    if not ruang_meeting or ruang_meeting.strip() == "":
        return False, "Ruang meeting harus dipilih"
    if ruang_meeting not in ["Breakout Traction", "Cozy 19.2"]:
        return False, "Ruang meeting yang dipilih tidak valid"
    return True, ""

def validate_keterangan(keterangan: str) -> Tuple[bool, str]:
    """Validasi field keterangan"""
    if not keterangan or len(keterangan.strip()) < 3:
        return False, "Keterangan harus diisi minimal 3 karakter"
    if len(keterangan.strip()) > 500:
        return False, "Keterangan tidak boleh lebih dari 500 karakter"
    return True, ""

def validate_time_range(start_time: time, end_time: time) -> Tuple[bool, str]:
    """Validasi rentang waktu"""
    if start_time >= end_time:
        return False, "Waktu selesai harus lebih besar dari waktu mulai"
    
    # Validasi jam kerja (08:00 - 18:00)
    if start_time < time(8, 0) or end_time > time(18, 0):
        return False, "Booking hanya diperbolehkan antara jam 08:00 - 18:00"
    
    return True, ""

def validate_booking_conflict(
    supabase: Client,
    booking_date: date,
    start_time: time,
    end_time: time,
    room: str,
    booking_id: int | None = None,
) -> Tuple[bool, str]:
    """Cek bentrok jadwal di database."""
    try:
        query = (
            supabase.table("bookings")
            .select("*")
            .eq("tanggal_booking", str(booking_date))
            .eq("ruang_meeting", room)
        )
        if booking_id:
            query = query.neq("id", booking_id)

        result = query.execute()
        for booking in result.data:
            existing_start = datetime.strptime(booking["waktu_mulai"], "%H:%M:%S").time()
            existing_end = datetime.strptime(booking["waktu_selesai"], "%H:%M:%S").time()
            if start_time < existing_end and end_time > existing_start:
                return (
                    False,
                    f"Konflik dengan booking {booking['nama']} ({existing_start.strftime('%H:%M')}-{existing_end.strftime('%H:%M')})",
                )
        return True, ""
    except Exception:
        return False, "Error saat memeriksa konflik jadwal"

# ──────────────────────────────────────────────────────────────────────────────
# 5. AUTHENTIKASI ADMIN
# ──────────────────────────────────────────────────────────────────────────────
def admin_authenticated() -> bool:
    """Cek status autentikasi admin"""
    if "admin_authenticated" not in st.session_state:
        st.session_state.admin_authenticated = False
    return st.session_state.admin_authenticated

def admin_login_page() -> None:
    """Halaman login admin"""
    st.subheader("🔐 Admin Login")

    col1, col2, _ = st.columns([1, 1, 8])
    with col1:
        if st.button("🔙 Daftar Booking", use_container_width=True):
            st.session_state.page = "list"
            st.rerun()
    with col2:
        if st.button("➕ Form Booking", use_container_width=True):
            st.session_state.page = "form"
            st.rerun()

    with st.form("admin_login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")

        if submit:
            cfg_admin = st.secrets.get("admin", {})
            correct_username = cfg_admin.get("username", "admin")
            correct_pw_hash = cfg_admin.get("password_hash", "")
            if (
                username == correct_username
                and bcrypt.checkpw(password.encode(), correct_pw_hash.encode())
            ):
                st.session_state.admin_authenticated = True
                st.success("Login berhasil!")
                st.rerun()
            else:
                st.error("Username atau password salah")

# ──────────────────────────────────────────────────────────────────────────────
# 6. HALAMAN FORM BOOKING (DENGAN VALIDASI EXTENDED)
# ──────────────────────────────────────────────────────────────────────────────
def booking_form_page() -> None:
    """Halaman form booking dengan validasi field required"""
    st.markdown(
        '<div class="main-header"><h1>📝 Form Booking Meeting Room</h1></div>',
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns(3)
    with col2:
        if st.button("📋 Lihat Daftar Booking", use_container_width=True):
            st.session_state.page = "list"
            st.rerun()

    st.markdown("---")

    supabase = init_supabase()
    if not supabase:
        st.stop()

    # Form input dengan field required
    with st.form("booking_form", clear_on_submit=False):
        st.markdown("### 📋 Informasi Booking")
        
        # Nama pemesan
        nama = st.text_input(
            "Nama Pemesan *", 
            placeholder="Masukkan nama lengkap pemesan",
            help="Nama lengkap penanggung jawab booking"
        )
        
        # Sub direktorat
        subdir = st.text_input(
            "Sub Direktorat *", 
            placeholder="Masukkan sub direktorat",
            help="Sub direktorat atau unit kerja"
        )
        
        # Floor dengan placeholder default
        floor = st.selectbox(
            "Lantai *", 
            ["", "16", "17", "18", "19", "20"],
            index=0,
            help="Pilih lantai tempat meeting akan dilakukan"
        )
        
        # Ruang meeting dengan placeholder default
        ruang_meeting = st.selectbox(
            "Ruang Meeting *", 
            ["", "Breakout Traction", "Cozy 19.2"],
            index=0,
            help="Pilih ruang meeting yang akan digunakan"
        )
        
        st.markdown("### 📅 Waktu Booking")
        
        # Tanggal booking
        booking_date = st.date_input(
            "Tanggal Booking *", 
            value=date.today(),
            help="Tanggal pelaksanaan meeting"
        )
        
        # Waktu mulai dan selesai
        col1, col2 = st.columns(2)
        with col1:
            waktu_mulai = st.time_input(
                "Waktu Mulai *", 
                value=time(9, 0),
                help="Waktu mulai meeting (08:00 - 18:00)"
            )
        with col2:
            waktu_selesai = st.time_input(
                "Waktu Selesai *", 
                value=time(10, 0),
                help="Waktu selesai meeting (08:00 - 18:00)"
            )
        
        st.markdown("### 📝 Detail Meeting")
        
        # Keterangan menjadi required
        keterangan = st.text_area(
            "Keterangan *", 
            height=100,
            placeholder="Masukkan keterangan, agenda, atau tujuan meeting...",
            help="Keterangan detail tentang meeting (min. 3 karakter, max. 500 karakter)"
        )

        # Info field required
        st.markdown("---")
        st.markdown("**📌 Catatan:** Field yang bertanda <span class='required-field'>*</span> wajib diisi", unsafe_allow_html=True)
        
        # Submit button
        submit = st.form_submit_button("💾 Simpan Booking", use_container_width=True)

    # Validasi yang diperluas
    if submit:
        st.markdown("### 🔍 Memvalidasi Data...")
        
        # Progress bar untuk UX yang lebih baik
        progress_bar = st.progress(0)
        
        # Validasi nama
        progress_bar.progress(10)
        valid, msg = validate_name(nama)
        if not valid:
            st.error(f"❌ **Nama:** {msg}")
            st.stop()

        # Validasi sub direktorat
        progress_bar.progress(20)
        valid, msg = validate_subdir(subdir)
        if not valid:
            st.error(f"❌ **Sub Direktorat:** {msg}")
            st.stop()

        # Validasi floor
        progress_bar.progress(30)
        valid, msg = validate_floor(floor)
        if not valid:
            st.error(f"❌ **Lantai:** {msg}")
            st.stop()

        # Validasi ruang meeting
        progress_bar.progress(40)
        valid, msg = validate_ruang_meeting(ruang_meeting)
        if not valid:
            st.error(f"❌ **Ruang Meeting:** {msg}")
            st.stop()

        # Validasi keterangan
        progress_bar.progress(50)
        valid, msg = validate_keterangan(keterangan)
        if not valid:
            st.error(f"❌ **Keterangan:** {msg}")
            st.stop()

        # Validasi waktu
        progress_bar.progress(60)
        valid, msg = validate_time_range(waktu_mulai, waktu_selesai)
        if not valid:
            st.error(f"❌ **Waktu:** {msg}")
            st.stop()

        # Validasi konflik booking
        progress_bar.progress(80)
        valid, msg = validate_booking_conflict(
            supabase, booking_date, waktu_mulai, waktu_selesai, ruang_meeting
        )
        if not valid:
            st.error(f"❌ **Konflik Jadwal:** {msg}")
            st.stop()

        # Simpan data jika semua validasi berhasil
        progress_bar.progress(100)
        try:
            supabase.table("bookings").insert(
                {
                    "nama": nama.strip(),
                    "subdir": subdir.strip(),
                    "floor": floor,
                    "ruang_meeting": ruang_meeting,
                    "tanggal_booking": str(booking_date),
                    "waktu_mulai": waktu_mulai.strftime("%H:%M:%S"),
                    "waktu_selesai": waktu_selesai.strftime("%H:%M:%S"),
                    "keterangan": keterangan.strip(),
                }
            ).execute()
            
            st.success("✅ **Booking berhasil disimpan!**")
            st.balloons()
            
            # Tampilkan ringkasan booking
            st.markdown("### 📋 Ringkasan Booking")
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Nama:** {nama}")
                st.write(f"**Sub Direktorat:** {subdir}")
                st.write(f"**Lantai:** {floor}")
                st.write(f"**Ruang:** {ruang_meeting}")
            with col2:
                st.write(f"**Tanggal:** {booking_date.strftime('%d/%m/%Y')}")
                st.write(f"**Waktu:** {waktu_mulai.strftime('%H:%M')} - {waktu_selesai.strftime('%H:%M')}")
                st.write(f"**Keterangan:** {keterangan[:50]}{'...' if len(keterangan) > 50 else ''}")
            
            # Auto redirect ke list setelah 3 detik
            st.info("📋 Akan otomatis redirect ke daftar booking...")
            import time
            time.sleep(2)
            st.session_state.page = "list"
            st.rerun()
            
        except Exception as err:
            st.error(f"❌ **Gagal menyimpan booking:** {err}")
            st.error("Silakan coba lagi atau hubungi administrator")

# ──────────────────────────────────────────────────────────────────────────────
# 7. HALAMAN LIST BOOKING – HTML CALENDAR VIEW
# ──────────────────────────────────────────────────────────────────────────────
def booking_list_page() -> None:
    """Halaman daftar booking dengan calendar view"""
    st.markdown(
        '<div class="main-header"><h1>📅 Kalender Booking Meeting Room</h1></div>',
        unsafe_allow_html=True,
    )

    # Tombol navigasi
    col1, col2, col3 = st.columns(3)
    with col2:
        if st.button("➕ Tambah Booking", use_container_width=True):
            st.session_state.page = "form"
            st.rerun()
    #with col2:
    #    if st.button("⚙️ Admin Panel", use_container_width=True):
    #        st.session_state.page = "admin"
    #        st.rerun()

    st.markdown("---")

    # Kontrol navigasi bulan
    today = date.today()
    col1, col2, col3 = st.columns([2, 2, 6])
    with col1:
        selected_month = st.selectbox(
            "Bulan", 
            range(1, 13), 
            index=today.month-1,
            format_func=lambda x: calendar.month_name[x]
        )
    with col2:
        selected_year = st.selectbox(
            "Tahun", 
            range(today.year-1, today.year+3), 
            index=1
        )

    supabase = init_supabase()
    if not supabase:
        st.stop()

    try:
        result = (
            supabase.table("bookings")
            .select("*")
            .order("tanggal_booking", desc=False)
            .execute()
        )

        if not result.data:
            st.info("Belum ada data booking")
            return

        df = pd.DataFrame(result.data)

        # Buat dan tampilkan kalender HTML
        calendar_html = create_html_calendar(df, selected_month, selected_year)
        st.markdown(calendar_html, unsafe_allow_html=True)

        # Filter booking berdasarkan bulan yang dipilih
        selected_month_str = f"{selected_year}-{selected_month:02d}"
        current_month_bookings = df[
            df['tanggal_booking'].str.startswith(selected_month_str)
        ]

        # Tampilkan detail booking dalam expander
        with st.expander(f"📋 Detail Booking {calendar.month_name[selected_month]} {selected_year}"):
            if not current_month_bookings.empty:
                for _, row in current_month_bookings.iterrows():
                    # Tentukan emoji berdasarkan ruang meeting
                    room_emoji = "🔴" if row['ruang_meeting'] == "Breakout Traction" else "🟢"
                    
                    st.write(f"**{row['tanggal_booking']}** {room_emoji} {row['nama']}")
                    st.write(f"   📍 {row['ruang_meeting']} | ⏰ {row['waktu_mulai'][:5]}-{row['waktu_selesai'][:5]}")
                    st.write(f"   👤 {row['subdir']} | 🏢 Lantai {row['floor']}")
                    st.write(f"   📝 {row['keterangan']}")
                    st.write("---")
            else:
                st.info(f"Tidak ada booking untuk {calendar.month_name[selected_month]} {selected_year}")

        # Legend
        st.markdown("---")
        st.subheader("📌 Keterangan")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("🔴 **Breakout Traction**")
        with col2:
            st.markdown("🟢 **Cozy 19.2**")

    except Exception as err:
        st.error(f"Error memuat data: {err}")

# ──────────────────────────────────────────────────────────────────────────────
# 8. ADMIN PANEL
# ──────────────────────────────────────────────────────────────────────────────
def admin_page() -> None:
    """Halaman admin panel"""
    if not admin_authenticated():
        admin_login_page()
        return

    st.markdown(
        '<div class="main-header"><h1>⚙️ Admin Panel – Booking Meeting Room</h1></div>',
        unsafe_allow_html=True,
    )

    col1, col2, _ = st.columns([1, 1, 8])
    with col1:
        if st.button("📋 Daftar Booking", use_container_width=True):
            st.session_state.page = "list"
            st.rerun()
    with col2:
        if st.button("➕ Form Booking", use_container_width=True):
            st.session_state.page = "form"
            st.rerun()

    st.markdown("---")

    supabase = init_supabase()
    if not supabase:
        st.stop()

    try:
        df = pd.DataFrame(
            supabase.table("bookings").select("*").execute().data
        )
        if df.empty:
            st.info("Belum ada data booking")
            return

        # Tampilkan tabel dengan kontrol admin
        st.subheader("📊 Data Booking")
        st.dataframe(
            df[
                [
                    "id",
                    "nama",
                    "subdir",
                    "floor",
                    "ruang_meeting",
                    "tanggal_booking",
                    "waktu_mulai",
                    "waktu_selesai",
                    "keterangan"
                ]
            ],
            hide_index=True,
            use_container_width=True
        )

        # Hapus booking
        st.subheader("🗑️ Hapus Booking")
        del_id = st.number_input(
            "Masukkan ID booking yang akan dihapus",
            step=1,
            min_value=1,
            format="%d",
            help="ID booking dapat dilihat di kolom pertama tabel di atas"
        )
        
        if st.button("🗑️ Hapus Booking", type="secondary"):
            try:
                supabase.table("bookings").delete().eq("id", del_id).execute()
                st.success(f"✅ Booking dengan ID {del_id} berhasil dihapus")
                st.rerun()
            except Exception as err:
                st.error(f"❌ Gagal menghapus booking: {err}")

        # Statistik booking
        st.subheader("📈 Statistik Booking")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Booking", len(df))
        with col2:
            st.metric("Breakout Traction", len(df[df['ruang_meeting'] == 'Breakout Traction']))
        with col3:
            st.metric("Cozy 19.2", len(df[df['ruang_meeting'] == 'Cozy 19.2']))

    except Exception as err:
        st.error(f"Gagal memuat data: {err}")

# ──────────────────────────────────────────────────────────────────────────────
# 9. ROUTING APLIKASI
# ──────────────────────────────────────────────────────────────────────────────
def main() -> None:
    """Fungsi utama routing aplikasi"""
    if "page" not in st.session_state:
        st.session_state.page = "form"

    if st.session_state.page == "form":
        booking_form_page()
    elif st.session_state.page == "list":
        booking_list_page()
    elif st.session_state.page == "admin":
        admin_page()

# Jalankan aplikasi
if __name__ == "__main__":
    main()
