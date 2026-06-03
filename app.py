import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import math

# ==============================================================================
# 1. CẤU HÌNH HỆ THỐNG & QUẢN LÝ PHIÊN TRUY CẬP (URL PARAMETERS)
# ==============================================================================
st.set_page_config(
    page_title="Hệ thống Quản lý & Định vị Trạm phát sóng BTS", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# Khởi tạo hằng số xác thực
TOKEN_XAC_THUC = "authenticated_secure_token_tuan"
TAI_KHOAN_CHUAN = "admin"
MAT_KHAU_CHUAN = "tuan"

# Kiểm tra trạng thái phiên làm việc từ URL ẩn dòng thời gian thực
truy_van_url = st.query_params

if truy_van_url.get("auth_token") == TOKEN_XAC_THUC:
    st.session_state.logged_in = True
else:
    st.session_state.logged_in = False

# Khởi tạo bộ nhớ tạm cho phiên làm việc
if "danh_sach_luu" not in st.session_state:
    st.session_state.danh_sach_luu = []
if "tram_hien_tai" not in st.session_state:
    st.session_state.tram_hien_tai = None

# Tối ưu hóa giao diện (Ẩn Sidebar và Header mặc định của Streamlit)
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
        padding-top: 0.8rem !important;
        padding-bottom: 0rem !important;
        padding-left: 1.5rem !important;
        padding-right: 1.5rem !important;
        max-width: 100% !important;
    }
    label { font-weight: 600 !important; color: #212529; }
    .stFoliumStatic { margin-top: 5px !important; width: 100% !important; }
    </style>
    """,
    unsafe_allow_html=True
)

# ==============================================================================
# 2. THUẬT TOÁN XỬ LÝ TOÁN HỌC & ĐỊA LÝ
# ==============================================================================
def tinh_khoang_cach_haversine(lat1, lon1, lat2, lon2):
    """Tính khoảng cách đường cong giữa 2 tọa độ theo độ kinh/vĩ."""
    r_lat1, r_lon1, r_lat2, r_lon2 = map(math.radians, [float(lat1), float(lon1), float(lat2), float(lon2)])
    dlat = r_lat2 - r_lat1
    dlon = r_lon2 - r_lon1
    a = math.sin(dlat / 2)**2 + math.cos(r_lat1) * math.cos(r_lat2) * math.sin(dlon / 2)**2
    c = 2 * math.asin(math.sqrt(a))
    BAN_KINH_TRAI_DAT_KM = 6371.0
    return c * BAN_KINH_TRAI_DAT_KM

@st.cache_data(ttl=600) 
def tai_co_so_du_lieu():
    """Tải và chuẩn hóa dữ liệu trạm từ Google Sheets."""
    SHEET_ID = "101T9xJHnW9EUdz1Il6FXWTWt272oSFvkAIWwSijLRYI" 
    URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"
    data = pd.read_csv(URL, dtype=str)
    data.columns = data.columns.str.strip()
    
    danh_sach_cot_chuan = ['MCC', 'MNC', 'LAC/TAC', 'CELL ID', 'Latitude', 'Longitude']
    for col in danh_sach_cot_chuan:
        if col in data.columns:
            data[col] = data[col].fillna("").astype(str).str.strip()
            
    if 'MNC' in data.columns:
        data['MNC'] = data['MNC'].apply(lambda x: x.zfill(2) if x.isdigit() and len(x) == 1 else x)
    return data

def truy_xuat_du_lieu_cot(row, danh_sach_ten_goi):
    """Hỗ trợ tìm kiếm dữ liệu linh hoạt dựa trên danh sách tiêu đề tương đương."""
    tap_ten_goi = set(x.lower() for x in danh_sach_ten_goi)
    for k in row.index:
        if str(k).lower().strip() in tap_ten_goi:
            return row[k]
    return "Không có dữ liệu"

# ==============================================================================
# 3. PHÂN HỆ KHÓA XÁC THỰC TRUY CẬP (LOGIN)
# ==============================================================================
if not st.session_state.logged_in:
    # Bố trí biểu mẫu đăng nhập tinh gọn phía góc trên bên phải
    _, col_login_1, col_login_2 = st.columns([7.0, 1.5, 1.5])

    with col_login_1:
        tai_khoan_nhap = st.text_input("Tài khoản hệ thống:", value="", key="username_input")

    with col_login_2:
        mat_khau_nhap = st.text_input("Mật khẩu truy cập:", type="password", key="password_input")
        
    if tai_khoan_nhap == TAI_KHOAN_CHUAN and mat_khau_nhap == MAT_KHAU_CHUAN:
        # Ghi mã token lên URL để bảo lưu trạng thái khi F5
        st.query_params.auth_token = TOKEN_XAC_THUC
        st.session_state.logged_in = True
        st.rerun()

    # Tắt tính năng tự động điền không mong muốn từ trình duyệt
    st.markdown(
        """
        <script>
        var inputs = window.parent.document.querySelectorAll('input');
        inputs.forEach(function(input) {
            input.setAttribute('autocomplete', 'new-password');
        });
        </script>
        """,
        unsafe_allow_html=True
    )

    # Hiển thị màn hình chờ chuẩn hóa doanh nghiệp
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
            color: #ffffff !important;
            text-shadow: 1px 1px 4px rgba(0, 0, 0, 0.8) !important;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )
    
    st.markdown(
        """
        <div style='
            background-color: rgba(15, 23, 42, 0.75); 
            padding: 35px; 
            border-radius: 12px; 
            color: white; 
            text-align: center;
            margin-top: 12%;
            box-shadow: 0px 10px 25px rgba(0,0,0,0.6);
            backdrop-filter: blur(8px);
            border: 1px solid rgba(255,255,255,0.1);'>
            <h2 style='color: #ffffff; margin-bottom: 12px; font-weight: 700; letter-spacing: 1px;'>🔒 HỆ THỐNG YÊU CẦU ĐĂNG NHẬP</h2>
            <p style='font-size: 15px; opacity: 0.85; margin: 0; font-family: sans-serif;'>Vui lòng nhập thông tin định danh tại góc phải màn hình để truy cập cơ sở dữ liệu hạ tầng.</p>
        </div>
        """, 
        unsafe_allow_html=True
    )

# ==============================================================================
# 4. PHÂN HỆ ĐIỀU HÀNH CHÍNH (BẢN ĐỒ & TRA CỨU HẠ TẦNG)
# ==============================================================================
else:
    # Thanh Header chuyên nghiệp điều hướng hệ thống
    col_main_title, col_logout_btn = st.columns([8.2, 1.8])
    with col_main_title:
        st.markdown(
            "<h2 style='margin:0; color:#1E3A8A; font-weight:700; font-size:26px;'>"
            "🛰️ TRUNG TÂM GIÁM SÁT VÀ ĐỊNH VỊ TRẠM PHÁT SÓNG BTS"
            "</h2>", 
            unsafe_allow_html=True
        )
    with col_logout_btn:
        if st.button("🚪 Đăng xuất khỏi hệ thống", use_container_width=True, type="secondary"):
            # Xóa hoàn toàn tham số trên URL thanh địa chỉ
            st.query_params.clear()
            st.session_state.logged_in = False
            st.session_state.danh_sach_luu = []
            st.session_state.tram_h
