import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

# ==============================================================================
# 1. CẤU HÌNH GIAO DIỆN & MẬT KHẨU
# ==============================================================================
st.set_page_config(page_title="Hệ Thống Trạm Phát Sóng", layout="wide")

# Mật khẩu truy cập trang web (Bạn có thể đổi chữ "admin" thành mật khẩu khác)
MAT_KHAU_CUA_BAN = "admin" 

mat_khau_nhap = st.sidebar.text_input("Nhập mật khẩu truy cập:", type="password")

if mat_khau_nhap == MAT_KHAU_CUA_BAN:
    st.title("🛰️ HỆ THỐNG TRA CỨU VỊ TRÍ TRẠM PHÁT SÓNG")

    # ==============================================================================
    # 2. KẾT NỐI VỚI GOOGLE SHEETS
    # ==============================================================================
    # ⚠️ HÃY THAY ĐOẠN MÃ ĐỊNH DANH DƯỚI ĐÂY BẰNG MÃ FILE GOOGLE SHEETS CỦA BẠN
    SHEET_ID = "101T9xJHnW9EUdz1Il6FXWTWt272oSFvkAIWwSijLRYI" 
    URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

    @st.cache_data(ttl=60) # Tự động tải lại dữ liệu mới sau mỗi 60 giây
    def tai_du_lieu():
        # Đọc dữ liệu và ép kiểu tất cả các cột định danh về dạng Chuỗi (String) để tránh lỗi mất số 0 ở đầu
        data = pd.read_csv(URL)
        for col in ['MCC', 'MNC', 'LAC/TAC', 'CELL ID']:
            if col in data.columns:
                data[col] = data[col].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        return data

    try:
        df = tai_du_lieu()
        
        # ==============================================================================
        # 3. ĐỊNH NGHĨA TÊN CỘT ĐÃ ĐƯỢC CHUẨN HÓA THEO GOOGLE SHEETS CỦA BẠN
        # ==============================================================================
        COT_MCC = 'MCC'
        COT_MNC = 'MNC'
        COT_LAC_TAC = 'LAC/TAC'
        COT_CELL_ID = 'CELL ID'
        COT_VI_DO = 'Latitude'
        COT_KINH_DO = 'Longitude'
        
        # ==============================================================================
        # 4. TẠO BỘ LỌC 4 THÔNG SỐ (MCC, MNC, LAC/TAC, CELL ID) Ở SIDEBAR BÊN TRÁI
        # ==============================================================================
        st.sidebar.header("Bộ lọc tìm kiếm trạm")
        
        f1 = st.sidebar.selectbox("1. Chọn MCC:", ["Chọn..."] + sorted(df[COT_MCC].dropna().unique()))
        f2 = st.sidebar.selectbox("2. Chọn MNC:", ["Chọn..."] + sorted(df[COT_MNC].dropna().unique()))
        f3 = st.sidebar.selectbox("3. Chọn LAC/TAC:", ["Chọn..."] + sorted(df[COT_LAC_TAC].dropna().unique()))
        f4 = st.sidebar.selectbox("4. Chọn CELL ID:", ["Chọn..."] + sorted(df[COT_CELL_ID].dropna().unique()))

        # Vị trí mặc định ban đầu khi chưa tìm kiếm (Trung tâm Việt Nam)
        vi_do_xem, kinh_do_xem, muc_zoom = 16.047079, 108.206230 
        tram_tim_thay = None

        # ==============================================================================
        # 5. XỬ LÝ LỌC VÀ TÌM KIẾM DỮ LIỆU
        # ==============================================================================
        if f1 != "Chọn..." and f2 != "Chọn..." and f3 != "Chọn..." and f4 != "Chọn...":
            
            # Thực hiện lọc chính xác theo 4 thông số người dùng chọn
            ket_qua = df[
                (df[COT_MCC] == f1) & 
                (df[COT_MNC] == f2) & 
                (df[COT_LAC_TAC] == f3) & 
                (df[COT_CELL_ID] == f4)
            ]
            
            if not ket_qua.empty:
                tram_tim_thay = ket_qua.iloc[0]
                vi_do_xem = float(tram_tim_thay[COT_VI_DO])
                kinh_do_xem = float(tram_tim_thay[COT_KINH_DO])
                muc_zoom = 17 # Tự động bay sát cận cảnh vào vị trí trạm giống Google Maps
                st.success(f"✅ Đã định vị thành công trạm có CELL ID: {tram_tim_thay[COT_CELL_ID]}")
            else:
                st.warning("⚠️ Không tìm thấy trạm nào khớp với 4 thông số đã chọn.")

        # ==============================================================================
        # 6. KHỞI TẠO BẢN ĐỒ VỆ TINH GOOGLE MAPS
        # ==============================================================================
        m = folium.Map(location=[vi_do_xem, kinh_do_xem], zoom_start=muc_zoom, control_scale=True)
        
        # Thêm lớp bản đồ vệ tinh Google
        folium.TileLayer(
            tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
            attr='Google Satellite', name='Bản đồ Vệ tinh', overlay=False, control=True
        ).add_to(m)
        
        # Thêm lớp bản đồ đường phố Google
        folium.TileLayer(
            tiles='https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}',
            attr='Google Maps Street', name='Bản đồ Đường phố', overlay=False, control=True
        ).add_to(m)
        
        folium.LayerControl().add_to(m)

        # Nếu tìm thấy trạm, tiến hành cắm ghim màu đỏ và hiện đầy đủ thông tin chi tiết
        if tram_tim_thay is not None:
            # Lấy thêm các thông tin phụ nếu có dữ liệu, nếu trống thì để trống
            cgi_val = tram_tim_thay.get('CGI', 'Không có dữ liệu')
            dia_chi_val = tram_tim_thay.get('Địa chỉ', 'Không có dữ liệu')
            ghi_chu_val = tram_tim_thay.get('Ghi chú', 'Không có dữ liệu')

            noi_dung_popup = f"""
            <div style='font-family: Arial, sans-serif; font-size: 13px; width: 250px;'>
                <h4 style='margin: 0 0 5px 0; color: #d9534f;'>Thông Tin Trạm</h4>
                <b>CGI:</b> {cgi_val}<br>
                <b>CELL ID:</b> {tram_tim_thay[COT_CELL_ID]}<br>
                <b>LAC/TAC:</b> {tram_tim_thay[COT_LAC_TAC]}<br>
                <b>Tọa độ:</b> {vi_do_xem}, {kinh_do_xem}<br>
                <b>Địa chỉ:</b> {dia_chi_val}<br>
                <b>Ghi chú:</b> {ghi_chu_val}
            </div>
            """
            folium.Marker(
                [vi_do_xem, kinh_do_xem],
                popup=folium.Popup(noi_dung_popup, max_width=300),
                icon=folium.Icon(color='red', icon='info-sign')
            ).add_to(m)

        # Hiển thị bản đồ ra trang web
        st_folium(m, width="100%", height=650, returned_objects=[])

    except Exception as e:
        st.error(f"❌ Lỗi cấu trúc dữ liệu: {e}")
        st.info("Hãy chắc chắn rằng hàng đầu tiên trong Google Sheets viết đúng chính xác các chữ: MCC, MNC, LAC/TAC, CELL ID, CGI, Latitude, Longitude, Địa chỉ, Ghi chú.")
else:
    st.info("🔒 Vui lòng nhập đúng mật khẩu ở thanh bên trái để truy cập hệ thống bản đồ.")
