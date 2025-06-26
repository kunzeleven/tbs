import streamlit as st
import psycopg2
from datetime import datetime

st.title("Booking Ruangan Meeting Lt19 Wing Traction")

# Form input
with st.form("booking_form"):
    name = st.text_input("Nama Lengkap You (Wajib)")
    email = st.text_input("Email You (Wajib)")
    room = st.selectbox("Ruangan", ["Breakout Traction", "Cozy 19.2"])
    booking_date = st.date_input("Tanggal Booking")
    booking_time = st.time_input("Waktu Booking")
    submitted = st.form_submit_button("Submit")

# Fungsi untuk menyimpan data ke Supabase PostgreSQL
def save_booking(name, email, room, booking_date, booking_time):
    try:
        conn = psycopg2.connect(
            host=st.secrets["host"],
            database=st.secrets["database"],
            user=st.secrets["user"],
            password=st.secrets["password"],
            port=st.secrets["port"]
        )
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO bookings (name, email, room, booking_date, booking_time)
            VALUES (%s, %s, %s, %s, %s)
        """, (name, email, room, booking_date, booking_time))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Gagal menyimpan data: {e}")
        return False

# Proses penyimpanan saat form disubmit
if submitted:
    if name and email:
        success = save_booking(name, email, room, booking_date, booking_time)
        if success:
            st.success("Booking berhasil disimpan ke database Supabase.")
    else:
        st.warning("Nama dan Email wajib diisi.")

# Informasi tambahan
st.markdown("---")
st.info("Aplikasi ini terhubung ke Supabase PostgreSQL menggunakan kredensial dari `st.secrets`. Pastikan Anda telah menambahkan secrets di Streamlit Cloud.")

