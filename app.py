import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

# 1. Cấu hình giao diện
st.set_page_config(page_title="Hệ Thống Trạm Phát Sóng", layout="wide")

# 2. Mật khẩu đăng nhập (Thay đổi theo ý bạn)
PASSWORD = "admin" 
user_pwd = st.sidebar.text_input("Nhập mật khẩu truy cập:", type="password")

if user_pwd == PASSWORD:
    st.title("🛰️ TRA CỨU VỊ TRÍ TRẠM PHÁT SÓNG")

    # 3. KẾT NỐI GOOGLE SHEETS
    # THAY ĐOẠN MÃ DƯỚI ĐÂY BẰNG MÃ FILE CỦA BẠN (Lấy từ Bước 1)
    SHEET_ID = "101T9xJHnW9EUdz1Il6FXWTWt272oSFvkAIWwSijLRYI" 
    URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

    @st.cache_data(ttl=60) # Tự động tải lại dữ liệu mới sau mỗi 60 giây
    def load_data():
        return pd.read_csv(URL)

    try:
        df = load_data()
        
        # 4. BỘ LỌC 4 THÔNG SỐ
        st.sidebar.header("Bộ lọc tìm kiếm")
        f1 = st.sidebar.selectbox("Thông số 1", ["Chọn..."] + sorted(df['Thong_So_1'].unique().astype(str)))
        f2 = st.sidebar.selectbox("Thông số 2", ["Chọn..."] + sorted(df['Thong_So_2'].unique().astype(str)))
        f3 = st.sidebar.selectbox("Thông số 3", ["Chọn..."] + sorted(df['Thong_So_3'].unique().astype(str)))
        f4 = st.sidebar.selectbox("Thông số 4", ["Chọn..."] + sorted(df['Thong_So_4'].unique().astype(str)))

        # Vị trí mặc định (Trung tâm VN)
        lat_view, lon_view, zoom_view = 16.0, 108.0, 5
        found_station = None

        # 5. XỬ LÝ TÌM KIẾM
        if f1 != "Chọn..." and f2 != "Chọn..." and f3 != "Chọn..." and f4 != "Chọn...":
            result = df[(df['Thong_So_1'].astype(str) == f1) & 
                        (df['Thong_So_2'].astype(str) == f2) & 
                        (df['Thong_So_3'].astype(str) == f3) & 
                        (df['Thong_So_4'].astype(str) == f4)]
            
            if not result.empty:
                found_station = result.iloc[0]
                lat_view = found_station['Latitude']
                lon_view = found_station['Longitude']
                zoom_view = 17 # Phóng to như Google Maps
                st.success(f"✅ Đã tìm thấy Mã Trạm: {found_station['Ma_Tram']}")
            else:
                st.warning("⚠️ Không tìm thấy trạm phù hợp.")

        # 6. HIỂN THỊ BẢN ĐỒ VỆ TINH
        m = folium.Map(location=[lat_view, lon_view], zoom_start=zoom_view)
        
        # Thêm lớp vệ tinh Google
        folium.TileLayer(
            tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
            attr='Google Satellite', name='Vệ tinh', overlay=False
        ).add_to(m)
        
        # Nếu có trạm thì cắm ghim
        if found_station is not None:
            folium.Marker(
                [lat_view, lon_view],
                popup=f"Trạm: {found_station['Ma_Tram']}",
                icon=folium.Icon(color='red', icon='info-sign')
            ).add_to(m)

        st_folium(m, width="100%", height=600)

    except Exception as e:
        st.error(f"Lỗi kết nối dữ liệu: {e}")
else:
    st.info("Vui lòng nhập mật khẩu ở bên trái để sử dụng hệ thống.")
