import streamlit as st
import plotly.graph_objects as go
import serial
import serial.tools.list_ports
import time
import re
from datetime import datetime
import random

# ---------- Helper: konversi HEX -> RGBA ----------
def hex_to_rgba(hex_color: str, alpha: float = 0.3) -> str:
    hex_color = hex_color.lstrip('#')
    if len(hex_color) != 6:
        return f'rgba(128,128,128,{alpha})'
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return f'rgba({r},{g},{b},{alpha})'

# ---------- Auto-detect port helper ----------
def find_arduino_port():
    ports = list(serial.tools.list_ports.comports())
    for p in ports:
        desc = (p.description or "").lower()
        if "arduino" in desc or "ch340" in desc or "usb serial" in desc or "usb-to-serial" in desc:
            return p.device
    return None

# ---------- Streamlit UI / state ----------
st.set_page_config(page_title="IoT Temperature Monitor", page_icon="🌡️", layout="centered")
st.title("🌡️ Temperature Monitoring Dashboard")
st.markdown("Realtime DHT11 Sensor Data via Arduino")

# Sidebar controls
with st.sidebar:
    st.header("Koneksi Serial")
    detected = find_arduino_port()
    st.write("Autodetect:", detected if detected else "Tidak ditemukan")
    manual_port = st.text_input("Port manual (kosong = auto)", value="")
    use_sim_override = st.checkbox("Paksa simulasi (jika ingin)", value=False)
    if 'running' not in st.session_state:
        st.session_state['running'] = False
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Start"):
            st.session_state['running'] = True
    with col2:
        if st.button("Stop"):
            st.session_state['running'] = False
    st.markdown("---")
    st.markdown("Tips:")
    st.write("- Pastikan Serial Monitor di Arduino IDE **tertutup** sebelum menjalankan dashboard.")
    st.write("- Jika memakai laptop, cek Device Manager → Ports (COM & LPT) untuk nama port.")

# Determine port to use
SERIAL_PORT = manual_port.strip() if manual_port.strip() else detected
BAUD_RATE = 9600

# Initialize serial in session_state once
if 'serial_obj' not in st.session_state:
    st.session_state['serial_obj'] = None
    st.session_state['serial_ok'] = False
    st.session_state['serial_err'] = None
    st.session_state['last_raw'] = None

# Try (re)connect if a port is available and not connected
if SERIAL_PORT and not st.session_state['serial_ok'] and not use_sim_override:
    try:
        st.session_state['serial_obj'] = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        # small delay to stabilize
        time.sleep(1.0)
        st.session_state['serial_ok'] = True
        st.session_state['serial_err'] = None
    except Exception as e:
        st.session_state['serial_obj'] = None
        st.session_state['serial_ok'] = False
        st.session_state['serial_err'] = str(e)

# show connection status
conn_col1, conn_col2 = st.columns([2,3])
with conn_col1:
    if st.session_state['serial_ok'] and not use_sim_override:
        st.success(f"✅ Terhubung: {SERIAL_PORT} @ {BAUD_RATE}")
    else:
        st.warning("⚠️ Tidak terhubung ke Arduino. Mode simulasi aktif." if use_sim_override or not SERIAL_PORT else f"⚠️ Gagal buka {SERIAL_PORT}: {st.session_state['serial_err']}")
with conn_col2:
    last = st.session_state.get('last_raw') or "-"
    st.caption(f"Baris serial terakhir: {last}")

# placeholders
placeholder_card = st.empty()
placeholder_chart = st.empty()
placeholder_logs = st.empty()

# initialize history
if 'history' not in st.session_state:
    st.session_state['history'] = []

# ---------- Function to read one sample ----------
def read_one():
    """Return (temp, raw_line) or (None, None) if no new data"""
    # if serial connected and not forcing sim:
    if st.session_state['serial_ok'] and not use_sim_override:
        try:
            raw = st.session_state['serial_obj'].readline().decode(errors='ignore').strip()
            if not raw:
                return None, None
            st.session_state['last_raw'] = raw
            m = re.search(r"([-+]?\d*\.\d+|\d+)", raw)
            if m:
                try:
                    return float(m.group(0)), raw
                except:
                    return None, raw
            return None, raw
        except Exception as e:
            st.session_state['serial_ok'] = False
            st.session_state['serial_err'] = str(e)
            return None, None
    # simulation fallback
    val = round(25 + random.random() * 10, 1)
    raw = f"SIMULASI {val}"
    st.session_state['last_raw'] = raw
    return val, raw

# ---------- Live loop if running ----------
if st.session_state['running']:
    # Read one sample
    temp, rawline = read_one()
    now = datetime.now().strftime("%H:%M:%S")
    if temp is None:
        # if no fresh numeric reading, keep last value if exists
        if st.session_state['history']:
            temp = st.session_state['history'][-1]['temp']
        else:
            temp = 25.0

    # append history
    st.session_state['history'].append({'time': now, 'temp': temp})
    st.session_state['history'] = st.session_state['history'][-60:]  # cap 60 points

    # Build UI
    status_color = "#3b82f6"
    if temp >= 35:
        status_text = "PANAS 🔥"
        status_color = "#ef4444"
        status_desc = "Suhu terlalu tinggi! Segera periksa ruangan."
    elif temp >= 28:
        status_text = "HANGAT ☀️"
        status_color = "#f59e0b"
        status_desc = "Suhu nyaman, tetap stabil."
    else:
        status_text = "SEJUK ❄️"
        status_color = "#3b82f6"
        status_desc = "Suhu aman dan sejuk."

    rgba_fill = hex_to_rgba(status_color, alpha=0.28)

    # Card
    card_html = f"""
    <div style="background:linear-gradient(135deg,{status_color},#ffffff10);
                padding:24px;border-radius:12px;color:white;text-align:center;
                box-shadow:0 10px 30px {status_color}33;">
      <div style="font-size:64px;font-weight:700">{temp:.1f}°C</div>
      <div style="font-size:22px;margin-top:6px">{status_text}</div>
      <div style="font-size:14px;margin-top:6px;opacity:0.9">{status_desc}</div>
      <div style="margin-top:8px;font-size:12px;opacity:0.8">Waktu: {now} · Raw: {st.session_state.get('last_raw')}</div>
    </div>
    """
    placeholder_card.markdown(card_html, unsafe_allow_html=True)

    # Chart
    hist = st.session_state['history']
    times = [d['time'] for d in hist]
    temps = [d['temp'] for d in hist]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=times, y=temps, mode='lines+markers',
        line=dict(color=status_color, width=3),
        fill='tozeroy', fillcolor=rgba_fill, marker=dict(size=6)
    ))
    fig.update_layout(template='plotly_white', xaxis_title="Waktu", yaxis_title="Suhu (°C)",
                      yaxis=dict(range=[15, 40]), margin=dict(l=40, r=20, t=20, b=40), height=420)
    placeholder_chart.plotly_chart(fig, use_container_width=True)

    # Logs
    placeholder_logs.info(f"Last raw: {st.session_state.get('last_raw')}")

    # wait and rerun
    time.sleep(2)
    st.rerun()
else:
    # Not running: show static summary & last readings
    st.markdown("**Status:** " + ("Running" if st.session_state['running'] else "Stopped"))
    if st.session_state['history']:
        last = st.session_state['history'][-1]
        st.write(f"Last reading: {last['temp']} °C at {last['time']}")
    st.write("Klik *Start* di sidebar untuk mulai streaming data (atau isi port manual).")
    st.write("Jika anda mendapatkan `Tidak terhubung` tetapi Arduino terhubung, pastikan:")
    st.write("- Serial Monitor di Arduino IDE ditutup.")
    st.write("- Port yang benar dipilih (cek Device Manager pada Windows).")
    st.write("- Driver CH340 terpasang jika menggunakan board clone.")
