import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium, folium_static

# ==============================================================================
# 1. CẤU HÌNH GIAO DIỆN BAN ĐẦU
# ==============================================================================
st.set_page_config(page_title="Hệ Thống Trạm Phát Sóng", layout="wide")

# Cấu hình tài khoản và mật khẩu cố định
TAI_KHOAN_CHUAN = "admin"
MAT_KHAU_CHUAN = "admin"

# Thiết lập tỷ lệ cột: Khoảng trống lớn bên trái (70%), 2 cột nhỏ bên phải (15% - 15%)
col_space, col_user, col_pass = st.columns([7, 1.5, 1.5])

with col_space:
    # Khoảng trống đẩy 2 ô đăng nhập về góc phải
    st.write("")

with col_user:
    tai_khoan_nhap = st.text_input("Tên đăng nhập:", value="", key="username_input")

with col_pass:
    mat_khau_nhap = st.text_input("Mật khẩu truy cập:", type="password", key="password_input")

# Kiểm tra thông tin đăng nhập
if tai_khoan_nhap == TAI_KHOAN_CHUAN and mat_khau_nhap == MAT_KHAU_CHUAN:
    # ==============================================================================
    # GIAO DIỆN CHÍNH (MẤT HÌNH NỀN KHI VÀO ĐÂY)
    # ==============================================================================
    
    # CSS ẩn thanh Header, ép khung bản đồ giãn rộng tối đa màn hình
    st.markdown(
        """
        <style>
        header {visibility: hidden !important;}
        footer {visibility: hidden !important;}
        #MainMenu {visibility: hidden !important;}
        
        /* Mẹo ép vùng hiển thị chính của Streamlit rộng tối đa */
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 0rem !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
            max-width: 100% !important;
        }
        
        /* Ép khung chứa bản đồ folium_static căn giữa và mở rộng */
        .stFoliumStatic {
            margin: 0 auto !important;
            width: 100% !important;
        }
        
        /* Định dạng hộp Tooltip hiển thị sẵn */
        .leaflet-tooltip-top::before {
            border-top-color: #d9534f !important;
        }
        .leaflet-tooltip {
            background-color: white !important;
            border: 2px solid #d9534f !important;
            border-radius: 8px !important;
            box-shadow: 0px 4px 15px rgba(0,0,0,0.3) !important;
            padding: 10px !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.title("🛰️ HỆ THỐNG TRA CỨU VỊ TRÍ TRẠM PHÁT SÓNG")

    SHEET_ID = "101T9xJHnW9EUdz1Il6FXWTWt272oSFvkAIWwSijLRYI" 
    URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

    @st.cache_data(ttl=30) 
    def tai_du_lieu():
        data = pd.read_csv(URL, dtype=str)
        data.columns = data.columns.str.strip()
        for col in ['MCC', 'MNC', 'LAC/TAC', 'CELL ID', 'Latitude', 'Longitude']:
            if col in data.columns:
                data[col] = data[col].astype(str).str.strip()
        if 'MNC' in data.columns:
            data['MNC'] = data['MNC'].apply(lambda x: x.zfill(2) if x.isdigit() and len(x) == 1 else x)
        return data

    def lay_thong_tin_cot(row, danh_sach_ten_goi):
        for k in row.index:
            if k.lower().strip() in [x.lower() for x in danh_sach_ten_goi]:
                return row[k]
        return "Không có dữ liệu"

    try:
        df = tai_du_lieu()
        
        COT_MCC = 'MCC'
        COT_MNC = 'MNC'
        COT_LAC_TAC = 'LAC/TAC'
        COT_CELL_ID = 'CELL ID'
        COT_VI_DO = 'Latitude'
        COT_KINH_DO = 'Longitude'
        
        # THANH TÌM KIẾM SIDEBAR TRẢ VỀ ĐỂ TRA CỨU SAU KHI ĐĂNG NHẬP
        st.sidebar.header("Nhập thông số tìm kiếm")
        f1 = st.sidebar.text_input("1. Nhập số MCC:").strip()
        f2 = st.sidebar.text_input("2. Nhập số MNC:").strip()
        f3 = st.sidebar.text_input("3. Nhập số LAC/TAC:").strip()
        f4 = st.sidebar.text_input("4. Nhập số CELL ID:").strip()

        if f2.isdigit() and len(f2) == 1:
            f2 = f2.zfill(2)

        vi_do_xem, kinh_do_xem, muc_zoom = 16.047079, 108.206230, 5
        tram_tim_thay = None

        if f1 and f2 and f3 and f4:
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
                muc_zoom = 16 
                st.success(f"✅ Đã định vị thành công trạm CELL ID: {f4} (MNC: {f2})")
            else:
                st.warning(f"⚠️ Không tìm thấy trạm khớp với: MCC={f1}, MNC={f2}, LAC/TAC={f3}, CELL ID={f4}")
        else:
            st.sidebar.info("💡 Hãy gõ đầy đủ số vào cả 4 ô trên rồi nhấn Enter để xem bản đồ.")

        # KHỞI TẠO BẢN ĐỒ
        m = folium.Map(location=[vi_do_xem, kinh_do_xem], zoom_start=muc_zoom, control_scale=True)
        
        folium.TileLayer(
            tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
            attr='Google Satellite', name='Bản đồ Vệ tinh', overlay=False, control=True
        ).add_to(m)
        
        folium.TileLayer(
            tiles='https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}',
            attr='Google Maps Street', name='Bản đồ Đường phố', overlay=False, control=True
        ).add_to(m)
        
        folium.LayerControl().add_to(m)

        if tram_tim_thay is not None:
            cgi_val = lay_thong_tin_cot(tram_tim_thay, ['CGI', 'cgi'])
            dia_chi_val = lay_thong_tin_cot(tram_tim_thay, ['Địa chỉ', 'dia chi', 'địa chỉ', 'Địa Chỉ', 'Address', 'address', 'vị trí', 'vi tri'])
            ghi_chu_val = lay_thong_tin_cot(tram_tim_thay, ['Ghi chú', 'ghi chu', 'đố chữ', 'Note', 'note'])

            noi_dung_label = f"""
            <div style='font-family: Arial, sans-serif; font-size: 13px; width: 220px; color: #333333; line-height: 1.5;'>
                <h4 style='margin: 0 0 6px 0; color: #d9534f; border-bottom: 1px solid #eeeeee; padding-bottom: 4px;'>📍 Thông Tin Trạm</h4>
                <b>CGI:</b> {cgi_val}<br>
                <b>Latitude:</b> {vi_do_xem}<br>
                <b>Longitude:</b> {kinh_do_xem}<br>
                <b>Địa chỉ:</b> {dia_chi_val}<br>
                <b>Ghi chú:</b> {ghi_chu_val}
            </div>
            """
            
            folium.Marker(
                [vi_do_xem, kinh_do_xem],
                tooltip=folium.Tooltip(noi_dung_label, permanent=True, direction="top", sticky=False),
                icon=folium.Icon(color='red', icon='info-sign')
            ).add_to(m)

        # Hiển thị bản đồ kích thước lớn rộng rãi
        folium_static(m, width=1600, height=800)

    except Exception as e:
        st.error(f"❌ Lỗi cấu trúc dữ liệu: {e}")

else:
    # ==============================================================================
    # GIAO DIỆN MÀN HÌNH KHÓA (HÌNH NỀN FULL VÀ Ô ĐĂNG NHẬP Ở GÓC PHẢI)
    # ==============================================================================
    url_hinh_nen = "https://img.tripi.vn/cdn-cgi/image/width=700,height=700/https://img4.thuthuatphanmem.vn/uploads/2020/08/28/anh-bien-chu-welcome_094124627.jpg"
    
    st.markdown(
        f"""
        <style>
        header {{ visibility: hidden !important; height: 0px !important; }}
        [data-testid="stHeader"] {{ background: transparent !important; }}
        
        /* 1. Phủ kín hình nền toàn màn hình */
        .stApp {{
            background-image: url("{url_hinh_nen}");
            background-attachment: fixed;
            background-size: cover;
            background-position: center center;
            background-repeat: no-repeat;
        }}
        
        /* 2. Ẩn thanh sidebar đi khi chưa đăng nhập */
        [data-testid="stSidebar"] {{
            display: none !important;
        }}
        
        /* 3. Định dạng nhãn chữ (label) màu trắng, bóng đổ đen để nổi bật trên nền ảnh */
        label {{
            color: white !important;
            font-weight: bold !important;
            text-shadow: 1px 1px 3px rgba(0, 0, 0, 0.8) !important;
        }}
        
        /* Giảm bớt khoảng cách phía trên của cột chứa input */
        [data-testid="stColumn"] {{
            padding-top: 5px !important;
         cursor: default;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )
    
    # Hộp thông báo hệ thống đang khóa nằm ở trung tâm màn hình dưới ô đăng nhập
    st.markdown(
        """
        <div style='
            background-color: rgba(0, 0, 0, 0.6); 
            padding: 30px; 
            border-radius: 15px; 
            color: white; 
            text-align: center;
            margin-top: 12%;
            box-shadow: 0px 4px 15px rgba(0,0,0,0.5);
            backdrop-filter: blur(5px);'>
            <h2 style='color: #ffffff; margin-bottom: 10px;'>🔒 HỆ THỐNG ĐANG KHÓA</h2>
            <p style='font-size: 16px; opacity: 0.9; margin: 0;'>Vui lòng nhập chính xác Tài khoản & Mật khẩu tại góc trên bên phải để vào bản đồ vệ tinh.</p>
        </div>
        """, 
        unsafe_allow_html=True
    )
