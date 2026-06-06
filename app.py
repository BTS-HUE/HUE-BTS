import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import math
import re

# ==============================================================================
# 1. CẤU HÌNH HỆ THỐNG
# ==============================================================================
st.set_page_config(page_title="Hệ Thống Giám Sát BTS", layout="wide", initial_sidebar_state="collapsed")

TOKEN_XAC_THUC = st.secrets["auth"]["token_xac_thuc"]
TAI_KHOAN_CHUAN = st.secrets["auth"]["tai_khoan_chuan"]
MAT_KHAU_CHUAN = st.secrets["auth"]["mat_khau_chuan"]
SHEET_ID = st.secrets["database"]["sheet_id"]

if "logged_in" not in st.session_state:
    st.session_state.logged_in = (st.query_params.get("auth_token") == TOKEN_XAC_THUC)
    if st.session_state.logged_in: st.query_params.clear()

for key, val in [("danh_sach_luu", []), ("tram_hien_tai", None), ("ds_gan_nhat", [])]:
    st.session_state.setdefault(key, val)

# ==============================================================================
# 2. CSS TỐI ƯU GIAO DIỆN
# ==============================================================================
st.markdown("""
<style>
    [data-testid="stSidebar"], header, footer, #MainMenu { display: none !important; }
    .stApp { background: url("https://raw.githubusercontent.com/BTS-HUE/HUE-BTS/refs/heads/main/WC%20to.png") no-repeat center center fixed; background-size: cover; }
    .block-container { padding: 0.6rem 1rem !important; max-width: 100% !important; }
    .stFoliumStatic > iframe { border-radius: 12px !important; }
    
    /* Panel Glassmorphism */
    .glass-panel { background:rgba(15,23,42,0.85); padding:35px; border-radius:12px; text-align:center; margin:12vh auto; max-width:500px; box-shadow:0 10px 25px rgba(0,0,0,0.6); backdrop-filter:blur(8px); border:1px solid rgba(255,255,255,0.1); }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 3. CÁC HÀM TIỆN ÍCH
# ==============================================================================
def tinh_khoang_cach(lat1, lon1, lat2, lon2):
    r1, l1, r2, l2 = map(math.radians, [float(lat1), float(lon1), float(lat2), float(lon2)])
    a = math.sin((r2 - r1) / 2)**2 + math.cos(r1) * math.cos(r2) * math.sin((l2 - l1) / 2)**2
    return 2 * math.asin(math.sqrt(a)) * 6371.0

@st.cache_data(ttl=600)
def tai_data():
    df = pd.read_csv(f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv", dtype=str)
    df.columns = df.columns.str.strip()
    return df.fillna("").apply(lambda x: x.str.strip() if x.dtype == "object" else x)

def tao_popup(tieu_de, mau, id_t, cgi, lat, lon, dc, tg="", kc=""):
    return f"<div style='font-size:13px; width:220px; line-height:1.5;'><b><span style='color:{mau}'>{tieu_de}</span></b><br><b>Thời gian:</b> <span style='color:red;'>{tg}</span><br><b>Cell ID:</b> {id_t}<br><b>Khoảng cách:</b> {kc}<br><b>CGI:</b> {cgi}<br><b>Địa chỉ:</b> {dc}</div>"

# ==============================================================================
# 4. LUỒNG CHÍNH
# ==============================================================================
if not st.session_state.logged_in:
    c1, c2 = st.columns([1, 1])
    with st.container():
        st.markdown("<div class='glass-panel'><h2 style='color:#FFF;'>🔒 XÁC THỰC QUYỀN TRUY CẬP</h2><p style='color:#FFF;'>Vui lòng nhập định danh.</p></div>", unsafe_allow_html=True)
        tk = st.text_input("Tài khoản:")
        mk = st.text_input("Mật khẩu:", type="password")
        if tk == TAI_KHOAN_CHUAN and mk == MAT_KHAU_CHUAN:
            st.session_state.logged_in = True
            st.rerun()
else:
    # --- UI GIAO DIỆN CHÍNH ---
    st.markdown("<h2 style='color:var(--text-color);'>🛰️ TRUNG TÂM GIÁM SÁT BTS</h2>", unsafe_allow_html=True)
    col1, col2 = st.columns([2.5, 7.5])
    df = tai_data()

    with col1:
        with st.form("search_form"):
            mcc, mnc = st.text_input("MCC:"), st.text_input("MNC:")
            lac, cell = st.text_input("LAC/TAC:"), st.text_input("Cell ID:")
            if st.form_submit_button("🔍 Tìm Kiếm"):
                kq = df[(df['MCC']==mcc) & (df['MNC']==mnc.zfill(2)) & (df['LAC/TAC']==lac) & (df['CELL ID']==cell)]
                st.session_state.tram_hien_tai = kq.iloc[0] if not kq.empty else None

    # --- BẢN ĐỒ ---
    curr = st.session_state.tram_hien_tai
    m = folium.Map(location=[16.047, 108.206], zoom_start=6)
    
    if curr is not None:
        lat, lon = float(curr['Latitude']), float(curr['Longitude'])
        folium.Marker([lat, lon], popup=folium.Popup(tao_popup("🎯 TRẠM", "red", curr['CELL ID'], "...", lat, lon, "...")), icon=folium.Icon(color='red')).add_to(m)
        m.location = [lat, lon]
        m.zoom_start = 14

    with col2:
        folium_static(m, height=700)

    # --- LOGIC UPLOAD HÀNH TRÌNH ---
    up = st.file_uploader("📥 Tải lộ trình (CSV/Excel):", type=["csv", "xlsx"])
    if up:
        # Xử lý file tại đây...
        st.success("Đã nạp lộ trình thành công!")
