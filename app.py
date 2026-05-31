import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static

# ==============================================================================
# 1. CẤU HÌNH GIAO DIỆN & STYLE BAN ĐẦU
# ==============================================================================
st.set_page_config(page_title="Hệ Thống Trạm Phát Sóng", layout="wide", initial_sidebar_state="collapsed")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

TAI_KHOAN_CHUAN = "admin"
MAT_KHAU_CHUAN = "admin"

# CSS chung cho hệ thống
st.markdown(
    """
    <style>
    [data-testid="stSidebarNav"] {display: none !important;}
    [data-testid="stSidebar"] {display: none !important;}
    section[data-testid="stSidebar"] {width: 0px !important; display: none !important;}
    
    header {visibility: hidden !important; height: 0px !important;}
    footer {visibility: hidden !important;}
    #MainMenu {visibility: hidden !important;}
    
    .block-container {
        padding-top: 0.5rem !important;
        padding-bottom: 0rem !important;
        padding-left: 1.5rem !important;
        padding-right: 1.5rem !important;
        max-width: 100% !important;
    }
    
    label { font-weight: bold !important; }
    
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

# ==============================================================================
# 2. MÀN HÌNH ĐĂNG NHẬP (SỬ DỤNG FORM ĐỂ CHỐNG ĐÓNG BĂNG CHUỘT)
# ==============================================================================
if not st.session_state.logged_in:
    # Set hình nền cho màn hình khóa
    url_hinh_nen = "https://raw.githubusercontent.com/BTS-HUE/HUE-BTS/refs/heads/main/WC%20to.png"
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: url("{url_hinh_nen}") !important;
            background-attachment: fixed !important;
            background-size: cover !important;
            background-position: center center !important;
            background-repeat: no-repeat !important;
        }}
        /* Tùy chỉnh màu chữ form đăng nhập hiển thị rõ trên nền ảnh */
        .stForm label {{
            color: #ffffff !important;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

    # Đưa Form Đăng nhập ra chính giữa màn hình
    _, col_center_login, _ = st.columns([3.5, 3.0, 3.5])
    
    with col_center_login:
        st.write("<br><br><br>", unsafe_allow_html=True) # Đẩy khung xuống vị trí vừa mắt
        
        # Sử dụng st.form để gom cụm xử lý dữ liệu, click mượt mà không bị lỗi tương tác chuột
        with st.form(key="login_form"):
            st.markdown("<h2 style='text-align: center; color: white; margin-top:0;'>🔒 HỆ THỐNG ĐANG KHÓA</h2>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; color: #dddddd; font-size:14px;'>Vui lòng xác thực tài khoản để vào bản đồ trạm phát sóng</p>", unsafe_allow_html=True)
            
            tai_khoan_nhap = st.text_input("Tên đăng nhập:", value="")
            mat_khau_nhap = st.text_input("Mật khẩu truy cập:", type="password")
            
            nut_dang_nhap = st.form_submit_button("🔑 Đăng Nhập Hệ Thống", use_container_width=True)
            
            if nut_dang_nhap:
                if tai_khoan_nhap == TAI_KHOAN_CHUAN and mat_khau_nhap == MAT_KHAU_CHUAN:
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("❌ Sai tài khoản hoặc mật khẩu!")
                    
    st.stop() # Chặn không cho chạy phần giao diện bản đồ phía dưới khi chưa đăng nhập thành công

# ==============================================================================
# 3. GIAO DIỆN CHÍNH (SAU KHI ĐĂNG NHẬP THÀNH CÔNG - ẨN HOÀN TOÀN FORM TRÊN)
# ==============================================================================
else:
    # Xóa bỏ background ảnh khi đã vào giao diện bản đồ chính
    st.markdown(
        """
        <style>
        .stApp {
            background-image: none !important;
            background-color: transparent !important;
        }
        label { color: inherit !important; text-shadow: none !important; }
        </style>
        """,
        unsafe_allow_html=True
    )

    # Thanh tiêu đề chính và nút đăng xuất
    col_main_title, col_logout_btn = st.columns([8.5, 1.5])
    with col_main_title:
        st.title("🛰️ HỆ THỐNG TRA CỨU TRẠM PHÁT SÓNG")
    with col_logout_btn:
        st.write("") 
        if st.button("🚪 Đăng xuất khỏi hệ thống", use_container_width=True):
            st.session_state.logged_in = False
            st.rerun()

    st.markdown("---")

    # Bố cục yêu cầu: Cột trái (4 hàng tìm kiếm xếp dọc) | Cột phải (Bản đồ)
    col_left_search, col_right_map = st.columns([2.0, 8.0])

    with col_left_search:
        st.markdown("### 🔍 Thông Số Tra Cứu")
        f1 = st.text_input("1. Số MCC:", key="mcc_in").strip()
        f2 = st.text_input("2. Số MNC:", key="mnc_in").strip()
        f3 = st.text_input("3. Số LAC/TAC:", key="lac_in").strip()
        f4 = st.text_input("4. Số CELL ID:", key="cell_in").strip()

        if f2.isdigit() and len(f2) == 1:
            f2 = f2.zfill(2)

        st.write("")
        if not (f1 and f2 and f3 and f4):
            st.info("💡 Nhập đầy đủ 4 thông số bên trên rồi nhấn **Enter** để tra cứu trạm trên bản đồ.")

    # Kết nối dữ liệu Google Sheets
    SHEET_ID = "101T9xJHnW9EUdz1Il6FXWTWt272oSFvkAIWwSijLRYI" 
    URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

    @st.cache_data(ttl=30) 
    def tai_du_lieu():
        try:
            data = pd.read_csv(URL, dtype=str)
            data.columns = data.columns.str.strip()
            for col in ['MCC', 'MNC', 'LAC/TAC', 'CELL ID', 'Latitude', 'Longitude']:
                if col in data.columns:
                    data[col] = data[col].astype(str).str.strip()
            if 'MNC' in data.columns:
                data['MNC'] = data['MNC'].apply(lambda x: x.zfill(2) if x.isdigit() and len(x) == 1 else x)
            return data
        except Exception as e:
            return pd.DataFrame()

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

        if f1 and f2 and f3 and f4 and not df.empty:
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
                with col_left_search:
                    st.success(f"✅ Tìm thấy CELL ID: {f4}")
            else:
                with col_left_search:
                    st.warning("⚠️ Không tìm thấy trạm trong hệ thống!")

        # KHỞI TẠO BẢN ĐỒ FOLIAM
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

        # Đưa bản đồ vào cột bên phải với tính năng tự động co giãn full khung hình
        with col_right_map:
            folium_static(m, height=760, width=None)

    except Exception as e:
        with col_right_map:
            st.error(f"❌ Lỗi cấu trúc dữ liệu hoặc kết nối mạng: {e}")
