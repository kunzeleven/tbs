"""
Aplikasi Booking Meeting Room
Versi: 3.1 – Calendar View
Penulis: kunz
Deskripsi:
Aplikasi Streamlit untuk melakukan booking ruang meeting dengan tampilan daftar
booking berbasis kalender (menggunakan streamlit-calendar) serta form input,
admin panel, dan validasi lengkap.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date, time
import re
from supabase import create_client, Client
import bcrypt
from typing import Tuple
import os
import uuid

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
        /* Reset & base */
        .stApp     {background-color:#ffffff;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;}

        /* Header */
        .main-header{
            background:linear-gradient(135deg,#f8f8f8 0%,#e8e8e8 50%,#d8d8d8 100%);
            border:1px solid #e0e0e0;border-radius:14px;margin-bottom:1.5rem;
            text-align:center;color:#333;box-shadow:0 1px 3px rgba(0,0,0,.05);}
        .main-header h1{font-size:1.6rem !important;font-weight:500;margin:0;}

        /* Calendar overrides */
        .fc-event         {border-radius:5px;padding:2px 5px;font-size:12px;}
        .fc-event-title   {font-weight:600;}
        .fc-daygrid-event {margin:1px 0;}
        .fc-toolbar-title {font-size:1.4rem;font-weight:700;color:#333;}
        .fc-button        {background:#4ECDC4;border-color:#4ECDC4;}
        .fc-button:hover  {background:#45B7AA;border-color:#45B7AA;}
        .fc-today         {background:#FFF3CD !important;}
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
        supabase.table("bookings").select("id").limit(1).execute()  # quick test
        return supabase
    except Exception as err:
        st.error(f"⚠️ Gagal terhubung ke Supabase: {err}")
        return None

# ──────────────────────────────────────────────────────────────────────────────
# 3. VALIDASI INPUT
# ──────────────────────────────────────────────────────────────────────────────
def validate_name(name: str) -> Tuple[bool, str]:
    if not name or len(name.strip()) < 2:
        return False, "Nama harus diisi minimal 2 karakter"
    if not re.match(r"^[A-Za-zÀ-ÖØ-öø-ÿ\s]+$", name.strip()):
        return False, "Nama hanya boleh berisi huruf dan spasi"
    return True, ""

def validate_time_range(start_time: time, end_time: time) -> Tuple[bool, str]:
    if start_time >= end_time:
        return False, "Waktu selesai harus lebih besar dari waktu mulai"
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
                    f"Konflik dengan {booking['nama']} ({existing_start}-{existing_end})",
                )
        return True, ""
    except Exception:
        return False, "Error saat memeriksa konflik jadwal"

# ──────────────────────────────────────────────────────────────────────────────
# 4. AUTHENTIKASI ADMIN
# ──────────────────────────────────────────────────────────────────────────────
def admin_authenticated() -> bool:
    if "admin_authenticated" not in st.session_state:
        st.session_state.admin_authenticated = False
    return st.session_state.admin_authenticated

def admin_login_page() -> None:
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
# 5. HALAMAN FORM BOOKING
# ──────────────────────────────────────────────────────────────────────────────
def booking_form_page() -> None:
    st.markdown(
        '<div class="main-header"><h1>📝 Form Booking Meeting Room</h1></div>',
        unsafe_allow_html=True,
    )

    # Navigasi ke daftar
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("📋 Lihat Daftar Booking", use_container_width=True):
            st.session_state.page = "list"
            st.rerun()

    st.markdown("---")

    supabase = init_supabase()
    if not supabase:
        st.stop()

    # Form input
    with st.form("booking_form", clear_on_submit=False):
        nama = st.text_input("Nama Pemesan")
        subdir = st.text_input("Sub Direktorat")
        floor = st.selectbox("Lantai", ["19"])
        ruang_meeting = st.selectbox("Ruang Meeting", ["Breakout Traction", "Cozy 19.2"])
        booking_date = st.date_input("Tanggal Booking", value=date.today())
        col1, col2 = st.columns(2)
        with col1:
            waktu_mulai = st.time_input("Waktu Mulai", value=time(9, 0))
        with col2:
            waktu_selesai = st.time_input("Waktu Selesai", value=time(10, 0))
        keterangan = st.text_area("Keterangan", height=80)

        submit = st.form_submit_button("💾 Simpan Booking")

    if submit:
        errors = []

        valid, msg = validate_name(nama)
        if not valid:
            st.error(msg)
            st.stop()

        valid, msg = validate_time_range(waktu_mulai, waktu_selesai)
        if not valid:
            st.error(msg)
            st.stop()

        valid, msg = validate_booking_conflict(
            supabase, booking_date, waktu_mulai, waktu_selesai, ruang_meeting
        )

        if not valid:
            st.error(msg)
            st.stop()

        if not floor or not floor.strip():
            errors.append("Lantai Meeting harus diisi")
            errors.append("Lantai Meeting harus diisi")

        if not ruang_meeting:
            errors.append("Ruang meeting harus dipilih")
            errors.append("Ruang meeting harus dipilih")

        if not keterangan or not keterangan.strip():
            errors.append("Keterangan Meeting harus diisi")
            errors.append("Keterangan Meeting harus diisi")
        elif len(keterangan.strip()) < 10:
            errors.append("Keterangan Meeting minimal 10 karakter")
            errors.append("Keterangan Meeting minimal 10 karakter")

        if errors:
            for err in errors:
                st.error(err)
            st.stop()

        try:
            supabase.table("bookings").insert(
                {
                    "nama": nama,
                    "subdir": subdir,
                    "floor": floor,
                    "ruang_meeting": ruang_meeting,
                    "tanggal_booking": str(booking_date),
                    "waktu_mulai": waktu_mulai.strftime("%H:%M:%S"),
                    "waktu_selesai": waktu_selesai.strftime("%H:%M:%S"),
                    "keterangan": keterangan,
                }
            ).execute()
            st.success("Booking berhasil disimpan!")
            st.session_state.page = "list"
            st.rerun()
        except Exception as err:
            st.error(f"Gagal menyimpan booking: {err}")

# ──────────────────────────────────────────────────────────────────────────────
# 6. HALAMAN LIST BOOKING – CALENDAR VIEW
# ──────────────────────────────────────────────────────────────────────────────
from streamlit_calendar import calendar  # import setelah yakin ter-install

def booking_list_page() -> None:
    st.markdown(
        '<div class="main-header"><h1>📅 Kalender Booking Meeting Room</h1></div>',
        unsafe_allow_html=True,
    )

    # Tombol navigasi
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("➕ Tambah Booking", use_container_width=True):
            st.session_state.page = "form"
            st.rerun()
    #with col2:
    #    if st.button("⚙️ Admin Panel", use_container_width=True):
    #        st.session_state.page = "admin"
    #        st.rerun()

    st.markdown("---")

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

        # ── Konversi ke event kalender ──────────────────────────────────────
        events = []
        for _, row in df.iterrows():
            start_dt = f"{row['tanggal_booking']}T{row['waktu_mulai']}"
            end_dt = f"{row['tanggal_booking']}T{row['waktu_selesai']}"
            color = "#FF6B6B" if row["ruang_meeting"] == "Breakout Traction" else "#4ECDC4"
            events.append(
                {
                    "id": row["id"],
                    "title": f"{row['nama']} - {row['ruang_meeting']}",
                    "start": start_dt,
                    "end": end_dt,
                    "color": color,
                    "extendedProps": {
                        "nama": row["nama"],
                        "subdir": row["subdir"],
                        "floor": row["floor"],
                        "ruang_meeting": row["ruang_meeting"],
                        "keterangan": row["keterangan"],
                    },
                }
            )

        # Filter ruang meeting (opsional)
        ruang_opsi = ["Semua Ruang", "Breakout Traction", "Cozy 19.2"]
        room_filter = st.selectbox("Filter Ruang Meeting", ruang_opsi)
        if room_filter != "Semua Ruang":
            events = [e for e in events if e["extendedProps"]["ruang_meeting"] == room_filter]

        # Opsi & rendering kalender
        cal_options = {
            "editable": False,
            "selectable": True,
            "headerToolbar": {
                "left": "prev,next today",
                "center": "title",
                "right": "dayGridMonth,timeGridWeek,timeGridDay",
            },
            "initialView": "dayGridMonth",
            "height": "auto",
            "slotMinTime": "08:00:00",
            "slotMaxTime": "18:00:00",
            "weekends": True,
            "locale": "id",
            "eventDisplay": "block",
            "dayMaxEvents": 3,
            "moreLinkText": "lainnya",
        }

        if "calendar_key" not in st.session_state:
            st.session_state.calendar_key = str(uuid.uuid4())

        cal_state = calendar(
            events=events,
            options=cal_options,
            key=st.session_state.calendar_key,
        )

        # ── Tampilkan detail saat event diklik ──────────────────────────────
        if cal_state.get("eventClick"):
            ev = cal_state["eventClick"]["event"]
            st.subheader("📋 Detail Booking")
            c1, c2 = st.columns(2)
            with c1:
                st.write(f"**Nama:** {ev['extendedProps']['nama']}")
                st.write(f"**Sub Direktorat:** {ev['extendedProps']['subdir']}")
                st.write(f"**Lantai:** {ev['extendedProps']['floor']}")
            with c2:
                st.write(f"**Ruang Meeting:** {ev['extendedProps']['ruang_meeting']}")
                st.write(f"**Tanggal:** {ev['start'][:10]}")
                st.write(
                    f"**Waktu:** {ev['start'][11:16]} - {ev['end'][11:16]}"
                )
            if ev["extendedProps"]["keterangan"]:
                st.write(f"**Keterangan:** {ev['extendedProps']['keterangan']}")

        # ── Legend warna ────────────────────────────────────────────────────
        st.markdown("---")
        st.subheader("📌 Keterangan Warna")
        colA, colB = st.columns(2)
        with colA:
            st.markdown("🔴 **Breakout Traction**")
        with colB:
            st.markdown("🟢 **Cozy 19.2**")

    except Exception as err:
        st.error(f"Error memuat data: {err}")

# ──────────────────────────────────────────────────────────────────────────────
# 7. ADMIN PANEL (contoh sederhana)
# ──────────────────────────────────────────────────────────────────────────────
def admin_page() -> None:
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

        # Tampilkan tabel edit/delete sederhana
        st.dataframe(
            df[
                [
                    "id",
                    "nama",
                    "ruang_meeting",
                    "tanggal_booking",
                    "waktu_mulai",
                    "waktu_selesai",
                ]
            ],
            hide_index=True,
        )

        # Hapus booking
        del_id = st.number_input(
            "Masukkan ID untuk dihapus",
            step=1,
            min_value=1,
            format="%d",
        )
        if st.button("🗑️ Hapus Booking"):
            supabase.table("bookings").delete().eq("id", del_id).execute()
            st.success("Booking dihapus")
            st.rerun()
    except Exception as err:
        st.error(f"Gagal memuat data: {err}")

# ──────────────────────────────────────────────────────────────────────────────
# 8. ROUTING APLIKASI
# ──────────────────────────────────────────────────────────────────────────────
def main() -> None:
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
