import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import math

# ==========================================
# CÁC HÀM BỔ SUNG ĐỂ TÍNH TOÁN VÀ CHỐNG SẬP APP
# ==========================================
def tinh_khoang_cach_haversine(lat1, lon1, lat2, lon2):
    """Thuật toán tính khoảng cách địa lý (km)"""
    r_lat1, r_lon1, r_lat2, r_lon2 = map(math.radians, [float(lat1), float(lon1), float(lat2), float(lon2)])
    a = math.sin((r_lat2 - r_lat1) / 2)**2 + math.cos(r_lat1) * math.cos(r_lat2) * math.sin((r_lon2 - r_lon1) / 2)**2
    return 2 * math.asin(math.sqrt(a)) * 6371.0

def khu_loi_ky_tu_popup(row, key):
    """Xử lý triệt để lỗi ký tự đặc biệt (dấu nháy, nan) làm vỡ JavaScript của bản đồ"""
    val = row.get(key, '')
    if pd.isna(val):
        return ''
    # Khử toàn bộ dấu nháy và xuống dòng nguy hiểm
    return str(val).replace("'", "\\'").replace('"', '\\"').replace('\n', ' ').strip()


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
    # BẪY LỖI 1: Phòng trường hợp máy bạn chưa cài thư viện đọc file Excel (openpyxl)
    try:
        df = load_data(uploaded_file)
    except Exception as e:
        st.error(f"❌ Lỗi xảy ra khi đọc file dữ liệu: {e}")
        if "openpyxl" in str(e).lower():
            st.info("💡 **Cách sửa:** Bạn hãy mở Terminal/Command Prompt lên và chạy lệnh: `pip install openpyxl` rồi khởi động lại Streamlit nhé.")
        st.stop()

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

    # BẪY LỖI 2: Nếu bộ lọc Sidebar làm trống dữ liệu, chặn lại không cho vẽ Map để tránh crash
    if df.empty:
        st.warning("⚠️ Không tìm thấy trạm BTS nào phù hợp với bộ lọc hiện tại của bạn!")
        st.stop()

    # BẪY LỖI 3: Bọc toàn bộ quá trình dựng bản đồ để bắt lỗi chính xác thay vì sập ứng dụng
    try:
        # =========================
        # 7. MAP INIT
        # =========================
        center_lat = df["Latitude"].mean()
        center_lng = df["Longitude"].mean()

        m = folium.Map(location=[center_lat, center_lng], zoom_start=12)

        # =========================
        # 8. ADD MARKERS & ROUTE LINE
        # =========================
        toa_do_tuyen_duong = []
        tong_quang_duong = 0.0
        
        # Reset index để vòng lặp tính tiến trình timeline chính xác theo thứ tự dòng
        df_plot = df.reset_index(drop=True)

        for idx, row in df_plot.iterrows():
            lat_curr = float(row["Latitude"])
            lon_curr = float(row["Longitude"])
            toa_do_tuyen_duong.append([lat_curr, lon_curr])

            # Tính tích lũy quãng đường di chuyển nối tiếp giữa các trạm theo dòng thời gian
            if idx > 0:
                lat_prev = float(df_plot.loc[idx - 1, "Latitude"])
                lon_prev = float(df_plot.loc[idx - 1, "Longitude"])
                tong_quang_duong += tinh_khoang_cach_haversine(lat_prev, lon_prev, lat_curr, lon_curr)

            # Chuẩn hóa an toàn các chuỗi ký tự trước khi truyền vào mã HTML của Popup
            cgi_s = khu_loi_ky_tu_popup(row, 'CGI')
            cell_s = khu_loi_ky_tu_popup(row, 'CELL ID')
            lac_s = khu_loi_ky_tu_popup(row, 'LAC/TAC')
            diachi_s = khu_loi_ky_tu_popup(row, 'Địa chỉ')
            ghichu_s = khu_loi_ky_tu_popup(row, 'Ghi chú')

            popup_html = f"""
            <b>CGI:</b> {cgi_s}<br>
            <b>Cell ID:</b> {cell_s}<br>
            <b>LAC/TAC:</b> {lac_s}<br>
            <b>Địa chỉ:</b> {diachi_s}<br>
            <b>Ghi chú:</b> {ghichu_s}
            """

            folium.Marker(
                location=[lat_curr, lon_curr],
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=row.get("CGI", "BTS Cell")
            ).add_to(m)

        # Vẽ đường nối đứt đoạn màu cam kết nối các vị trí trạm BTS hành trình
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
        
        # Hiển thị tổng độ dài hành trình tính toán được lên phía trên bản đồ
        if len(toa_do_tuyen_duong) >= 2:
            st.info(f"🐾 Tổng chiều dài lộ trình di chuyển theo tiến trình Timeline: **{tong_quang_duong:.2f} km**")
            
        folium_static(m)

    except Exception as map_error:
        st.error(f"❌ Lỗi trong quá trình khởi tạo hoặc hiển thị Bản đồ Folium: {map_error}")
        st.exception(map_error) # Hiển thị chi tiết lỗi kỹ thuật để dễ tra cứu

    # =========================
    # 10. TABLE VIEW
    # =========================
    st.subheader("📊 Data Table")
    st.dataframe(df)

else:
    st.info("⬆️ Upload file Excel/CSV để bắt đầu")
