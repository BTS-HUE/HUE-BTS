import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import math # BỔ SUNG: Thư viện tính toán khoảng cách

# BỔ SUNG: Hàm tính khoảng cách giữa 2 tọa độ (Haversine)
def tinh_khoang_cach_haversine(lat1, lon1, lat2, lon2):
    r_lat1, r_lon1, r_lat2, r_lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    a = math.sin((r_lat2 - r_lat1) / 2)**2 + math.cos(r_lat1) * math.cos(r_lat2) * math.sin((r_lon2 - r_lon1) / 2)**2
    return 2 * math.asin(math.sqrt(a)) * 6371.0

# =========================
# 1. CONFIG
# =========================
st.set_page_config(page_title="BTS Timeline Map", layout="wide")

st.title("📡 BTS CELL TRACKING MAP + TIMELINE")

# =========================
# 2. UPLOAD FILE
# =========================
uploaded_file = st.file_uploader("Upload Google Sheet (CSV/Excel)", type=["csv", "xlsx"])

@st.cache_data
def load_data(file):
    if file.name.endswith(".csv"):
        df = pd.read_csv(file)
    else:
        df = pd.read_excel(file)

    return df


if uploaded_file:
    df = load_data(uploaded_file)

    # =========================
    # 3. CLEAN COLUMN NAMES
    # =========================
    df.columns = [c.strip() for c in df.columns]

    # =========================
    # 4. REQUIRED COLUMNS CHECK
    # =========================
    required_cols = [
        "CGI",
        "Latitude",
        "Longitude",
        "Địa chỉ"
    ]

    missing = [c for c in required_cols if c not in df.columns]

    if missing:
        st.error(f"Thiếu cột: {missing}")
        st.stop()

    # =========================
    # 5. CLEAN DATA
    # =========================
    df["Latitude"] = pd.to_numeric(df["Latitude"], errors="coerce")
    df["Longitude"] = pd.to_numeric(df["Longitude"], errors="coerce")

    df = df.dropna(subset=["Latitude", "Longitude"])

    # =========================
    # 6. SIDEBAR FILTER
    # =========================
    st.sidebar.header("🔎 Filter BTS")

    mcc_filter = st.sidebar.multiselect(
        "MCC",
        df["MCC"].dropna().unique() if "MCC" in df.columns else []
    )

    mnc_filter = st.sidebar.multiselect(
        "MNC",
        df["MNC"].dropna().unique() if "MNC" in df.columns else []
    )

    if mcc_filter:
        df = df[df["MCC"].isin(mcc_filter)]

    if mnc_filter:
        df = df[df["MNC"].isin(mnc_filter)]

    # SỬA LỖI: Kiểm tra nếu sau khi lọc dữ liệu bị trống thì dừng lại, không để Map bị lỗi NaN
    if df.empty:
        st.warning("⚠️ Không tìm thấy dữ liệu trạm BTS nào phù hợp với bộ lọc hiện tại!")
        st.stop()

    # =========================
    # 7. MAP INIT
    # =========================
    center_lat = df["Latitude"].mean()
    center_lng = df["Longitude"].mean()

    m = folium.Map(location=[center_lat, center_lng], zoom_start=12)

    # =========================
    # 8. ADD MARKERS & TRACK PATH
    # =========================
    # BỔ SUNG: Khởi tạo dữ liệu để vẽ tuyến hành trình di chuyển
    toa_do_tuyen_duong = []
    tong_quang_duong = 0.0
    
    # Reset lại chỉ mục để vòng lặp tính khoảng cách chạy chính xác
    df_plot = df.reset_index(drop=True)

    for idx, row in df_plot.iterrows():
        lat_curr = row["Latitude"]
        lon_curr = row["Longitude"]
        toa_do_tuyen_duong.append([lat_curr, lon_curr])

        # Tính toán tích lũy khoảng cách từ trạm này sang trạm tiếp theo
        if idx > 0:
            lat_prev = df_plot.loc[idx - 1, "Latitude"]
            lon_prev = df_plot.loc[idx - 1, "Longitude"]
            tong_quang_duong += tinh_khoang_cach_haversine(lat_prev, lon_prev, lat_curr, lon_curr)

        # GIỮ NGUYÊN BẢN: Định dạng Popup gốc của bạn
        popup_html = f"""
        <b>CGI:</b> {row.get('CGI','')}<br>
        <b>Cell ID:</b> {row.get('CELL ID','')}<br>
        <b>LAC/TAC:</b> {row.get('LAC/TAC','')}<br>
        <b>Địa chỉ:</b> {row.get('Địa chỉ','')}<br>
        <b>Ghi chú:</b> {row.get('Ghi chú','')}
        """

        folium.Marker(
            location=[lat_curr, lon_curr],
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=row.get("CGI", "BTS Cell")
        ).add_to(m)

    # BỔ SUNG: Vẽ đường nối liền các trạm hành trình (Màu cam nét đứt)
    if len(toa_do_tuyen_duong) >= 2:
        folium.PolyLine(
            locations=toa_do_tuyen_duong, 
            color="#e67e22", 
            weight=4, 
            opacity=0.8, 
            dash_array='6, 6'
        ).add_to(m)

    # =========================
    # 9. DISPLAY MAP
    # =========================
    st.subheader("🗺️ BTS Map")
    
    # BỔ SUNG: Hiển thị tổng quãng đường của file Timeline lên phía trên bản đồ
    if len(toa_do_tuyen_duong) >= 2:
        st.info(f"🐾 Tổng chiều dài lộ trình di chuyển theo Timeline: **{tong_quang_duong:.2f} km**")
        
    folium_static(m)

    # =========================
    # 10. TABLE VIEW
    # =========================
    st.subheader("📊 Data Table")
    st.dataframe(df)

else:
    st.info("⬆️ Upload file Excel/CSV để bắt đầu")
