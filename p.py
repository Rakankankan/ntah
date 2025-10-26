import streamlit as st
import plotly.graph_objects as go
import serial
import time
import re
from datetime import datetime
import random

# === KONFIGURASI SERIAL ARDUINO ===
SERIAL_PORT = 'COM3'
BAUD_RATE = 9600

try:
    arduino = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    time.sleep(2)
    st.sidebar.success("✅ Koneksi ke Arduino berhasil.")
except Exception as e:
    arduino = None
    st.sidebar.warning(f"⚠️ Gagal terhubung ke Arduino: {e}\nBerjalan dalam mode simulasi...")

# === PENYIMPANAN DATA ===
history = []

# === FUNGSI BACA DATA SERIAL ===
def read_temperature():
    """Baca suhu dari Arduino atau gunakan simulasi jika tidak terhubung"""
    global arduino
    if arduino:
        try:
            line = arduino.readline().decode(errors='ignore').strip()
            if not line:
                return None
            match = re.search(r"([\d.]+)", line)
            if match:
                temp = float(match.group(1))
                return temp
        except Exception:
            return None
    return round(25 + random.random() * 10, 1)

# === FUNGSI STATUS & WARNA ===
def get_status(temp):
    if temp >= 35:
        return {
            "status": "PANAS 🔥",
            "color": "#ef4444",
            "desc": "Suhu terlalu tinggi! Segera periksa ruangan.",
            "gradient": "linear-gradient(135deg, #f87171, #ef4444)"
        }
    elif temp >= 28:
        return {
            "status": "HANGAT ☀️",
            "color": "#f59e0b",
            "desc": "Suhu nyaman, tetap stabil.",
            "gradient": "linear-gradient(135deg, #fde047, #f59e0b)"
        }
    else:
        return {
            "status": "SEJUK ❄️",
            "color": "#3b82f6",
            "desc": "Suhu aman dan sejuk.",
            "gradient": "linear-gradient(135deg, #60a5fa, #3b82f6)"
        }

# === KONFIGURASI HALAMAN ===
st.set_page_config(
    page_title="IoT Temperature Monitor",
    page_icon="🌡️",
    layout="centered",
)

st.title("🌡️ Temperature Monitoring Dashboard")
st.markdown("### Realtime DHT11 Sensor Data via Arduino")

placeholder_card = st.empty()
placeholder_chart = st.empty()

# === LOOP PEMBAHARUAN ===
while True:
    suhu = read_temperature()
    waktu = datetime.now().strftime("%H:%M:%S")

    if suhu is None:
        suhu = history[-1]['temp'] if history else 0

    history.append({'time': waktu, 'temp': suhu})
    history = history[-30:]  # simpan 30 data terakhir

    status = get_status(suhu)

    # === STATUS CARD ===
    with placeholder_card.container():
        st.markdown(
            f"""
            <div style="background:{status['gradient']};padding:30px;border-radius:20px;
                        box-shadow:0 6px 20px {status['color']}80;color:white;text-align:center;">
                <h1 style="font-size:80px;margin:0;">{suhu:.1f}°C</h1>
                <h2 style="font-size:32px;margin:5px 0;">{status['status']}</h2>
                <p style="font-size:18px;opacity:0.9;">{status['desc']}</p>
            </div>
            """,
            unsafe_allow_html=True
        )

    # === GRAFIK ===
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=[d['time'] for d in history],
        y=[d['temp'] for d in history],
        mode='lines+markers',
        line=dict(color=status['color'], width=4),
        fill='tozeroy',
        fillcolor=status['color'] + '40',
        marker=dict(size=6),
        name='Suhu (°C)'
    ))
    fig.update_layout(
        template='plotly_white',
        xaxis_title="Waktu",
        yaxis_title="Suhu (°C)",
        yaxis=dict(range=[15, 40]),
        margin=dict(l=40, r=40, t=20, b=40),
        plot_bgcolor='#f9fafb',
        paper_bgcolor='#f9fafb'
    )

    placeholder_chart.plotly_chart(fig, use_container_width=True)
    time.sleep(2)  # interval pembaruan
