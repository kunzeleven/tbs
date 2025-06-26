import streamlit as st
from datetime import datetime

# Inisialisasi session state untuk menyimpan data booking
if 'bookings' not in st.session_state:
    st.session_state.bookings = []

if 'admin_logged_in' not in st.session_state:
    st.session_state.admin_logged_in = False

# Fungsi untuk login admin
def admin_login():
    with st.expander("🔐 Admin Login"):
        username = st.text_input("Username", key="admin_user")
        password = st.text_input("Password", type="password", key="admin_pass")
        if st.button("Login"):
            if username == "admin" and password == "admin123":
                st.session_state.admin_logged_in = True
                st.success("Login berhasil!")
            else:
                st.error("Username atau password salah.")

# Fungsi untuk menampilkan form booking
def booking_form():
    st.header("📅 Form Booking Ruangan")
    with st.form("booking_form"):
        name = st.text_input("Nama Lengkap")
        email = st.text_input("Email")
        room = st.selectbox("Pilih Ruangan", ["Ruang A", "Ruang B", "Ruang C"])
        date = st.date_input("Tanggal")
        time = st.time_input("Waktu")
        submitted = st.form_submit_button("Submit Booking")
        if submitted:
            st.session_state.bookings.append({
                "name": name,
                "email": email,
                "room": room,
                "date": date.strftime("%Y-%m-%d"),
                "time": time.strftime("%H:%M")
            })
            st.success("Booking berhasil disimpan!")

# Fungsi untuk menampilkan daftar booking
def show_bookings():
    st.header("📋 Daftar Booking")
    if not st.session_state.bookings:
        st.info("Belum ada booking.")
        return

    for i, booking in enumerate(st.session_state.bookings):
        with st.expander(f"{booking['name']} - {booking['room']} ({booking['date']} {booking['time']})"):
            st.write(f"**Email:** {booking['email']}")
            st.write(f"**Ruangan:** {booking['room']}")
            st.write(f"**Tanggal:** {booking['date']}")
            st.write(f"**Waktu:** {booking['time']}")

            if st.session_state.admin_logged_in:
                col1, col2 = st.columns(2)
                if col1.button("✏️ Edit", key=f"edit_{i}"):
                    with st.form(f"edit_form_{i}"):
                        new_name = st.text_input("Nama", value=booking["name"])
                        new_email = st.text_input("Email", value=booking["email"])
                        new_room = st.selectbox("Ruangan", ["Ruang A", "Ruang B", "Ruang C"], index=["Ruang A", "Ruang B", "Ruang C"].index(booking["room"]))
                        new_date = st.date_input("Tanggal", value=datetime.strptime(booking["date"], "%Y-%m-%d"))
                        new_time = st.time_input("Waktu", value=datetime.strptime(booking["time"], "%H:%M"))
                        if st.form_submit_button("Simpan Perubahan"):
                            st.session_state.bookings[i] = {
                                "name": new_name,
                                "email": new_email,
                                "room": new_room,
                                "date": new_date.strftime("%Y-%m-%d"),
                                "time": new_time.strftime("%H:%M")
                            }
                            st.success("Booking berhasil diperbarui.")
                            st.experimental_rerun()

                if col2.button("🗑️ Hapus", key=f"delete_{i}"):
                    st.session_state.bookings.pop(i)
                    st.success("Booking berhasil dihapus.")
                    st.experimental_rerun()

# Tampilan utama aplikasi
st.title("📌 Aplikasi Booking Ruangan Meeting")

booking_form()
admin_login()
show_bookings()

