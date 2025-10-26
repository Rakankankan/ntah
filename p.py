import streamlit as st
import plotly.graph_objects as go
import serial
import time
import re
from datetime import datetime
import random

# ---------- Helper: konversi HEX -> RGBA ----------
def hex_to_rgba(hex_color: str, alpha: float = 0.3) -> str:
    """Ubah '#rrggbb' menjadi 'rgba(r,g,b,a)'"""
    hex_color = hex_color.lstrip('#')
    if len(hex_color) != 6:
        return f'rgba(128,128,128,{alpha})'
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return f'rgba({r},{g},{b},{alpha})'

# ---------- Konfigurasi serial ----------
SERIAL_PORT = 'COM3'   # Ganti sesuai port Arduino kamu
BAUD_RATE = 9600

# ---------- Inisialisasi session state ----------
if 'arduino' not in st.session_state:
    try:
        st.session_state['arduino'] = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        time.sleep(2)
        st.session_state['serial_ok'] = True
        st.session_state['serial_err'] = None
    except Exception as e:
        st.session_state['arduino'] = None
        st.session_state['serial_ok'] = False
        st.session_state['serial_err'] = str(e)

if 'history' not in st.session_state:
    st.session_state['history'] = []

if 'last_update' not in st.session_state:
    st.session_state['last_update'] = None

# ---------- Fungsi baca suhu ----------
def read_temperature():
    """Baca suhu dari Arduino; return None jika tidak ada data baru."""
    arduino = st.session_state.get('arduino')
    if arduino:
        try:
            raw = arduino.readline().decode(errors='ignore').strip()
            if not raw:
                return None
            m = re.search(r"([-+]?\d*\.\d+|\d+)", raw)
            if m:
                return float(m.group(0))
            return None
        except Exception:
            st.session_state['serial_ok'] = False
            st.session_state['serial_err'] = 'Error membaca serial'
            return None
    # Simulasi jika tidak ada Arduino
    return round(25 + random.random() * 10, 1)

# ---------- Status suhu / styling ----------
def get_status(temp):
    if temp >= 35:
        return {"status": "PANAS 🔥", "color": "#ef4444", "desc": "Suhu terlalu tinggi! Segera periksa ruangan."}
    elif temp >= 28:
        return {"status": "HANGAT ☀️", "color": "#f59e0b", "desc": "Suhu nyaman, tetap stabil."}
    else:
        return {"status": "SEJUK ❄️", "color": "#3b82f6", "desc": "Suhu aman dan sejuk."}

# ---------- UI: konfigurasi halaman ----------
st.set_page_config(page_title="IoT Temperature Monitor", page_icon="🌡️", layout="centered")
st.title("🌡️ Temperature Monitoring Dashboard")
st.markdown("Realtime DHT11 Sensor Data via Arduino")

# Sidebar info koneksi
with st.sidebar:
    st.header("Koneksi")
    if st.session_state['serial_ok']:
        st.success(f"✅ Terkoneksi: {SERIAL_PORT}")
        if st.button("Tutup koneksi serial"):
            try:
                if st.session_state['arduino']:
                    st.session_state['arduino'].close()
                st.session_state['arduino'] = None
                st.session_state['serial_ok'] = False
                st.rerun()
            except Exception:
                st.session_state['serial_ok'] = False
                st.rerun()
    else:
        st.warning("⚠️ Tidak terhubung ke Arduino.")
        st.caption(st.session_state.get('serial_err') or "Mode simulasi aktif")
        if st.button("Coba konek ulang"):
            try:
                st.session_state['arduino'] = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
                time.sleep(2)
                st.session_state['serial_ok'] = True
                st.session_state['serial_err'] = None
            except Exception as e:
                st.session_state['serial_ok'] = False
                st.session_state['serial_err'] = str(e)
            st.rerun()

    st.markdown("---")
    st.markdown("**Kontrol Manual**")
    if st.button("Refresh Sekarang"):
        st.rerun()

placeholder_card = st.empty()
placeholder_chart = st.empty()

# ---------- Update data ----------
suhu_baru = read_temperature()
waktu_now = datetime.now().strftime("%H:%M:%S")

if suhu_baru is None:
    suhu = st.session_state['history'][-1]['temp'] if st.session_state['history'] else 25.0
else:
    suhu = suhu_baru

st.session_state['history'].append({'time': waktu_now, 'temp': suhu})
st.session_state['history'] = st.session_state['history'][-30:]
st.session_state['last_update'] = waktu_now

status = get_status(suhu)
rgba_fill = hex_to_rgba(status['color'], 0.3)

# ---------- Tampilkan status ----------
card_html = f"""
<div style="
    background: linear-gradient(135deg,{status['color']},#ffffff10);
    padding: 28px;
    border-radius: 16px;
    box-shadow: 0 8px 30px {status['color']}33;
    color: white;
    text-align: center;">
    <div style="font-size:72px;font-weight:700;margin:0;">{suhu:.1f}°C</div>
    <div style="font-size:28px;margin-top:6px;">{status['status']}</div>
    <div style="font-size:15px;margin-top:8px;opacity:0.95;">{status['desc']}</div>
</div>
"""
placeholder_card.markdown(card_html, unsafe_allow_html=True)

# ---------- Grafik ----------
history = st.session_state['history']
times = [d['time'] for d in history]
temps = [d['temp'] for d in history]

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=times,
    y=temps,
    mode='lines+markers',
    line=dict(color=status['color'], width=3),
    fill='tozeroy',
    fillcolor=rgba_fill,
    marker=dict(size=6),
    name='Suhu (°C)'
))
fig.update_layout(
    template='plotly_white',
    xaxis_title="Waktu",
    yaxis_title="Suhu (°C)",
    yaxis=dict(range=[15, 40]),
    margin=dict(l=40, r=20, t=20, b=40),
    plot_bgcolor='#fbfdff',
    paper_bgcolor='#fbfdff',
    height=420
)
placeholder_chart.plotly_chart(fig, use_container_width=True)

# ---------- Auto-refresh ----------
time.sleep(2)
st.rerun()
