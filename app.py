import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static

# ==============================================================================
# 1. CẤU HÌNH GIAO DIỆN BAN ĐẦU
# ==============================================================================
st.set_page_config(page_title="Hệ Thống Trạm Phát Sóng", layout="wide", initial_sidebar_state="collapsed")

# Cấu hình tài khoản và mật khẩu cố định
TAI_KHOAN_CHUAN = "admin"
MAT_KHAU_CHUAN = "admin"

# Ép toàn bộ ứng dụng ẩn Sidebar bằng CSS và định dạng layout chung
st.markdown(
    """
    <style>
    [data-testid="stSidebarNav"] {display: none !important;}
    [data-testid="stSidebar"] {display: none !important;}
    section[data-testid="stSidebar"] {width: 0px !important; display: none !important;}
    
    header {visibility: hidden !important; height: 0px !important;}
    footer {visibility: hidden !important;}
    #MainMenu {visibility: hidden !important;}
    
    /* Ép khung giao diện chính giãn rộng tối đa */
    .block-container {
        padding-top: 0.5rem !important;
        padding-bottom: 0rem !important;
        padding-left: 1.5rem !important;
        padding-right: 1.5rem !important;
        max-width: 100% !important;
    }
    
    label {
        font-weight: bold !important;
    }
    
    /* Giảm bớt khoảng cách lề (margin) của các ô nhập liệu cho khít và gọn hơn */
    div[data-testid="stTextInput"] {
        margin-bottom: -10px !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Khởi tạo các biến lưu thông số tìm kiếm trước để tránh lỗi crash logic
f1, f2, f3, f4 = "", "", "", ""

# Chia khung trên cùng thành: Khoảng trống lớn bên trái (75%), và 2 cột nhỏ bên phải (12.5% mỗi cột)
col_space, col_right_1, col_right_2 = st.columns([7.5, 1.25, 1.25])

with col_space:
    # Vùng trống bên trái dùng để hiển thị tiêu đề lớn sau này
    pass

with col_right_1:
    tai_khoan_nhap = st.text_input("Tên đăng nhập:", value="", key="username_input")

with col_right_2:
    mat_khau_nhap = st.text_input("Mật khẩu truy cập:", type="password", key="password_input")


# 2. KIỂM TRA ĐIỀU KIỆN ĐĂNG NHẬP
if tai_khoan_nhap == TAI_KHOAN_CHUAN and mat_khau_nhap == MAT_KHAU_CHUAN:
    # ==============================================================================
    # GIAO DIỆN CHÍNH (SAU KHI ĐĂNG NHẬP THÀNH CÔNG)
    # ==============================================================================
    
    # Tiếp tục chèn 4 ô tìm kiếm xếp dọc (chia làm 2 cặp cột) ngay dưới ô đăng nhập tương ứng
    with col_right_1:
        f1 = st.text_input("1. Số MCC:", key="mcc_in").strip()
        f3 = st.text_input("3. Số LAC/TAC:", key="lac_in").strip()
        
    with col_right_2:
        f2 = st.text_input("2. Số MNC:", key="mnc_in").strip()
        f4 = st.text_input("4. Số CELL ID:", key="cell_in").strip()

    # Viết tiêu đề hệ thống sang bên vùng trống góc trái
    with col_space:
        st.title("🛰️ HỆ THỐNG TRA CỨU TRẠM PHÁT SÓNG")
        if f1 and f2 and f3 and f4:
            st.write("") # Giữ khoảng trống đẹp
        else:
            st.info("💡 Điền đầy đủ thông số MCC, MNC, LAC, CELL ID ở góc phải rồi nhấn Enter để tra cứu.")

    # CSS định dạng riêng cho Tooltip và bản đồ vệ tinh
    st.markdown(
        """
        <style>
        .leaflet-tooltip-top::before { border-top-color: #d9534f !important; }
        .leaflet-tooltip {
            background-color: white !important;
            border: 2px solid #d9534f !important;
            border-radius: 8px !important;
            box-shadow: 0px 4px 15px rgba(0,0,0,0.3) !important;
            padding: 10px !important;
        }
        .stFoliumStatic { margin-top: 10px !important; width: 100% !important; }
        </style>
        """,
        unsafe_allow_html=True
    )

    if f2.isdigit() and len(f2) == 1:
        f2 = f2.zfill(2)

    # Kết nối dữ liệu Google Sheets
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
                st.success(f"✅ Định vị thành công trạm CELL ID: {f4}")
            else:
                st.warning(f"⚠️ Không tìm thấy trạm: MCC={f1}, MNC={f2}, LAC/TAC={f3}, CELL ID={f4}")

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

        # Hiển thị bản đồ lớn, rộng hết màn hình
        folium_static(m, width=1650, height=780)

    except Exception as e:
        st.error(f"❌ Lỗi cấu trúc dữ liệu: {e}")

else:
    # ==============================================================================
    # GIAO DIỆN MÀN HÌNH KHÓA (KHI CHƯA ĐĂNG NHẬP)
    # ==============================================================================
    url_hinh_nen = "https://img.tripi.vn/cdn-cgi/image/width=700,height=700/https://img4.thuthuatphanmem.vn/uploads/2020/08/28/anh-bien-chu-welcome_094124627.jpg"
    
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: url("{url_hinh_nen}");
            background-attachment: fixed;
            background-size: cover;
            background-position: center center;
            background-repeat: no-repeat;
        }}
        label {{
            color: white !important;
            text-shadow: 1px 1px 3px rgba(0, 0, 0, 0.8) !important;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )
    
    # Hộp thông báo hệ thống đang khóa đặt ở giữa màn hình
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
            <p style='font-size: 16px; opacity: 0.9; margin: 0;'>Vui lòng nhập chính xác Tài khoản & Mật khẩu tại góc trên bên phải để bắt đầu làm việc.</p>
        </div>
        """, 
        unsafe_allow_html=True
    )
