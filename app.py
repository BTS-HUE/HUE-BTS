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
MAT_KHAU_CHUAN = "tuan"

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
    
    /* 🛠️ CĂN CHỈNH CSS: Ép khung thông tin Tooltip cân bằng ở chính giữa */
    .leaflet-tooltip-top::before { 
        border-top-color: #d9534f !important; 
        left: 50% !important;
        margin-left: -6px !important;
    }
    .leaflet-tooltip {
        background-color: white !important;
        border: 2px solid #d9534f !important;
        border-radius: 8px !important;
        box-shadow: 0px 4px 15px rgba(0,0,0,0.3) !important;
        padding: 12px !important;
        transform: translateX(-50%) !important; /* Đẩy khung về tâm đối xứng của Marker */
    }
    .stFoliumStatic { margin-top: 10px !important; width: 100% !important; }
    </style>
    """,
    unsafe_allow_html=True
)

# ==============================================================================
# 2. KIỂM TRA ĐIỀU KIỆN ĐĂNG NHẬP
# ==============================================================================
if not st.session_state.logged_in:
    col_space, col_login_1, col_login_2 = st.columns([7.0, 1.5, 1.5])

    with col_login_1:
        tai_khoan_nhap = st.text_input("Tên đăng nhập:", value="", key="username_input")

    with col_login_2:
        mat_khau_nhap = st.text_input("Mật khẩu truy cập:", type="password", key="password_input")
        
    if tai_khoan_nhap == TAI_KHOAN_CHUAN and mat_khau_nhap == MAT_KHAU_CHUAN:
        st.session_state.logged_in = True
        st.rerun()

    url_hinh_nen = "https://raw.githubusercontent.com/BTS-HUE/HUE-BTS/refs/heads/main/WC%20to.png"
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

# ==============================================================================
# 3. GIAO DIỆN CHÍNH (SAU KHI ĐĂNG NHẬP THÀNH CÔNG)
# ==============================================================================
else:
    col_main_title, col_logout_btn = st.columns([8.5, 1.5])
    with col_main_title:
        st.title("🛰️ HỆ THỐNG TRA CỨU TRẠM PHÁT SÓNG")
    with col_logout_btn:
        st.write("") 
        if st.button("🚪 Đăng xuất khỏi hệ thống", use_container_width=True):
            st.session_state.logged_in = False
            st.rerun()

    st.markdown("---")

    # Chia layout cố định: Cột trái (Form nhập liệu) | Cột phải (Khu vực hiển thị bản đồ)
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
        data = pd.read_csv(URL, dtype=str)
        data.columns = data.columns.str.strip()
        for col in ['MCC', 'MNC', 'LAC/TAC', 'CELL ID', 'Latitude', 'Longitude']:
            if col in data.columns:
                data[col] = data[col].fillna("").astype(str).str.strip()
        if 'MNC' in data.columns:
            data['MNC'] = data['MNC'].apply(lambda x: x.zfill(2) if x.isdigit() and len(x) == 1 else x)
        return data

    def lay_thong_tin_cot(row, danh_sach_ten_goi):
        for k in row.index:
            if k.lower().strip() in [x.lower() for x in danh_sach_ten_goi]:
                return row[k]
        return "Không có dữ liệu"

    # Xử lý dữ liệu và dựng bản đồ
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
                (df[COT_MCC].str.strip() == f1.strip()) & 
                (df[COT_MNC].str.strip() == f2.strip()) & 
                (df[COT_LAC_TAC].str.strip() == f3.strip()) & 
                (df[COT_CELL_ID].str.strip() == f4.strip())
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

        # KHỞI TẠO BẢN ĐỒ FOLIUM
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

            # 📦 NỘI DUNG LABEL: Gom địa chỉ gọn gàng vào trong một khung duy nhất
            noi_dung_label = f"""
            <div style='font-family: Arial, sans-serif; font-size: 13px; width: 240px; color: #333333; line-height: 1.5;'>
                <h4 style='margin: 0 0 6px 0; color: #d9534f; border-bottom: 1px solid #eeeeee; padding-bottom: 4px; text-align: center;'>📍 THÔNG TIN TRẠM</h4>
                <b>CGI:</b> {cgi_val}<br>
                <b>Latitude:</b> {vi_do_xem}<br>
                <b>Longitude:</b> {kinh_do_xem}<br>
                <b>Địa chỉ:</b> {dia_chi_val}<br>
                <b>Ghi chú:</b> {ghi_chu_val}
            </div>
            """
            
            # 🎯 CẤU HÌNH MARKER: Đẩy offset=(0, -45) giúp đẩy hẳn khung thông tin lên trên, lộ ghim tọa độ
            folium.Marker(
                [vi_do_xem, kinh_do_xem],
                tooltip=folium.Tooltip(
                    noi_dung_label, 
                    permanent=True, 
                    direction="top", 
                    sticky=False,
                    offset=(0, -45) # Khoảng cách lùi lên trên (theo pixel) giúp giải phóng không gian cho Marker
                ),
                icon=folium.Icon(color='red', icon='info-sign')
            ).add_to(m)

        with col_right_map:
            folium_static(m, height=760, width=None)

    except Exception as e:
        with col_right_map:
            st.error(f"❌ Không thể tải cơ sở dữ liệu trạm phát sóng. Chi tiết lỗi: {e}")
