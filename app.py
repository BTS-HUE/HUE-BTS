import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import math

# ==============================================================================
# 1. CẤU HÌNH HỆ THỐNG & QUẢN LÝ PHIÊN TRUY CẬP
# ==============================================================================
st.set_page_config(
    page_title="Hệ thống Quản lý & Định vị Trạm phát sóng BTS", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# Cấu hình tài khoản và dữ liệu mặc định
if "auth" in st.secrets:
    TOKEN_XAC_THUC = st.secrets["auth"]["token_xac_thuc"]
    TAI_KHOAN_CHUAN = st.secrets["auth"]["tai_khoan_chuan"]
    MAT_KHAU_CHUAN = st.secrets["auth"]["mat_khau_chuan"]
    SHEET_ID = st.secrets["database"]["sheet_id"]
else:
    TOKEN_XAC_THUC = "authenticated_secure_token_tuan"
    TAI_KHOAN_CHUAN = "admin"
    MAT_KHAU_CHUAN = "tuan"
    SHEET_ID = "101T9xJHnW9EUdz1Il6FXWTWt272oSFvkAIWwSijLRYI"

# Khởi tạo trạng thái đăng nhập
if "logged_in" not in st.session_state:
    if st.query_params.get("auth_token") == TOKEN_XAC_THUC:
        st.session_state.logged_in = True
        st.query_params.clear()
    else:
        st.session_state.logged_in = False

# Khởi tạo bộ nhớ tạm
if "danh_sach_luu" not in st.session_state:
    st.session_state.danh_sach_luu = []
if "tram_hien_tai" not in st.session_state:
    st.session_state.tram_hien_tai = None

# BIẾN TRẠNG THÁI ĐÓNG/MỞ BỘ LỌC TRÊN ĐIỆN THOẠI
if "show_filter_mobile" not in st.session_state:
    st.session_state.show_filter_mobile = True

# ==============================================================================
# CSS ĐÁP ỨNG THÔNG MINH - CHỐNG LỆCH HÌNH NỀN & MẤT TRƯỜNG TRÊN ĐIỆN THOẠI
# ==============================================================================
st.markdown(
    """
    <style>
    /* Ẩn các thành phần thừa của Streamlit */
    [data-testid="stSidebarNav"], [data-testid="stSidebar"] {display: none !important;}
    section[data-testid="stSidebar"] {width: 0px !important; display: none !important;}
    header, footer, #MainMenu {visibility: hidden !important; height: 0px !important;}
    iframe[title="Manage app"], .stAppDeployButton, div[data-testid="stAppDeployButton"], footer + div {
        display: none !important; visibility: hidden !important;
    }
    
    .block-container {
        padding-top: 0.5rem !important;
        padding-bottom: 0rem !important;
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
        max-width: 100% !important;
    }
    
    .stFoliumStatic { margin-top: 5px !important; width: 100% !important; }
    .stFoliumStatic > iframe { width: 100% !important; border-radius: 6px !important; }
    div.stButton > button { border-radius: 6px !important; }

    /* -------------------------------------------------------------------------- */
    /* GIAO DIỆN TRÊN ĐIỆN THOẠI (MOBILE < 768px)                                */
    /* -------------------------------------------------------------------------- */
    @media (max-width: 768px) {
        /* Đẩy cột 1 (Bộ lọc) đè hẳn lên trên bản đồ làm bảng điều khiển nổi */
        div[data-testid="column"]:nth-of-type(1) {
            position: absolute !important;
            top: 65px !important;
            left: 10px !important;
            right: 10px !important;
            width: calc(100% - 20px) !important;
            z-index: 99999 !important;
            background: transparent !important;
            padding: 0px !important;
            box-shadow: none !important;
        }

        /* Định dạng khối bộ lọc màu nền trắng, chữ đen chống lỗi Dark Mode */
        .mobile-filter-box {
            background: rgba(255, 255, 255, 0.98) !important;
            border: 1px solid #CBD5E1 !important;
            border-radius: 12px !important;
            padding: 12px !important;
            box-shadow: 0px 8px 24px rgba(0, 0, 0, 0.25) !important;
            max-height: 80vh !important;
            overflow-y: auto !important; /* Tránh tràn màn hình trên điện thoại nhỏ */
        }

        /* Sửa lỗi che khuất dữ liệu: Ép độ rộng ô nhập liệu hiển thị đủ 100% */
        div[data-testid="column"]:nth-of-type(1) [data-testid="stTextInput"] {
            width: 100% !important;
            margin-bottom: 5px !important;
        }

        /* Ép chữ đậm, rõ ràng trong vùng bộ lọc trên điện thoại */
        div[data-testid="column"]:nth-of-type(1) label,
        div[data-testid="column"]:nth-of-type(1) p,
        div[data-testid="column"]:nth-of-type(1) span,
        div[data-testid="column"]:nth-of-type(1) div {
            color: #0F172A !important;
        }

        /* Ép form input có nền trắng chữ đen */
        div[data-testid="column"]:nth-of-type(1) input {
            color: #0F172A !important;
            background-color: #FFFFFF !important;
            -webkit-text-fill-color: #0F172A !important;
            border: 1px solid #CBD5E1 !important;
            padding: 6px !important;
        }
        
        /* Định dạng nút bấm Icon mở (☰) nổi ở góc trái bản đồ */
        .mobile-toggle-container {
            position: absolute !important;
            top: 70px !important;
            left: 15px !important;
            z-index: 99999 !important;
        }
        
        .mobile-toggle-btn button {
            background-color: #1E3A8A !important;
            color: white !important;
            border-radius: 8px !important;
            padding: 8px 14px !important;
            box-shadow: 0px 4px 12px rgba(0,0,0,0.3) !important;
            font-size: 16px !important;
            font-weight: bold !important;
            border: none !important;
        }
    }

    /* -------------------------------------------------------------------------- */
    /* GIAO DIỆN TRÊN MÁY TÍNH (PC)                                              */
    /* -------------------------------------------------------------------------- */
    @media (min-width: 769px) {
        label { font-weight: 600 !important; color: #212529; }
        .mobile-toggle-container { display: none !important; }
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ==============================================================================
# 2. THUẬT TOÁN ĐỊA LÝ & TẢI DỮ LIỆU
# ==============================================================================
def tinh_khoang_cach_haversine(lat1, lon1, lat2, lon2):
    r_lat1, r_lon1, r_lat2, r_lon2 = map(math.radians, [float(lat1), float(lon1), float(lat2), float(lon2)])
    dlat = r_lat2 - r_lat1
    dlon = r_lon2 - r_lon1
    a = math.sin(dlat / 2)**2 + math.cos(r_lat1) * math.cos(r_lat2) * math.sin(dlon / 2)**2
    c = 2 * math.asin(math.sqrt(a))
    return c * 6371.0

@st.cache_data(ttl=600) 
def tai_co_so_du_lieu():
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
    tap_ten_goi = set(x.lower() for x in danh_sach_ten_goi)
    for k in row.index:
        if str(k).lower().strip() in tap_ten_goi:
            return row[k]
    return "Không có dữ liệu"

# ==============================================================================
# 3. PHÂN HỆ ĐĂNG NHẬP (LOGIN) - CỐ ĐỊNH CHỐNG LỆCH HÌNH NỀN
# ==============================================================================
if not st.session_state.logged_in:
    st.markdown("<style>.stApp, .stMarkdown, p, span, div, label { color: #FFFFFF !important; } input { color: #0F172A !important; background-color: #FFFFFF !important; -webkit-text-fill-color: #0F172A !important;}</style>", unsafe_allow_html=True)
    _, col_login_1, col_login_2 = st.columns([6.5, 1.7, 1.8])
    with col_login_1:
        tai_khoan_nhap = st.text_input("Tài khoản hệ thống:", value="", key="username_input")
    with col_login_2:
        mat_khau_nhap = st.text_input("Mật khẩu truy cập:", type="password", key="password_input")
        
    if tai_khoan_nhap == TAI_KHOAN_CHUAN and mat_khau_nhap == MAT_KHAU_CHUAN:
        st.session_state.logged_in = True
        st.rerun()

    # Sửa CSS hình nền đồng bộ cho cả Điện thoại (chống lệch) và Máy tính
    url_hinh_nen = "https://raw.githubusercontent.com/BTS-HUE/HUE-BTS/refs/heads/main/WC%20to.png"
    st.markdown(
        f"""
        <style>
        .stApp {{ 
            background-image: url('{url_hinh_nen}') !important; 
            background-attachment: fixed !important; 
            background-size: cover !important; 
            background-position: center center !important; 
            background-repeat: no-repeat !important;
        }}
        @media (max-width: 768px) {{
            .stApp {{
                background-size: 100% 100% !important; /* Ép hình nền vừa vặn khít khung điện thoại không lệch */
            }}
        }}
        </style>
        """, 
        unsafe_allow_html=True
    )
    st.markdown("<div style='background-color: rgba(15, 23, 42, 0.85); padding: 30px; border-radius: 12px; color: white; text-align: center; margin-top: 15%; box-shadow: 0px 10px 25px rgba(0,0,0,0.6); backdrop-filter: blur(5px);'><h2 style='color: #ffffff; font-weight: 700; font-size:20px;'>🔒 HỆ THỐNG YÊU CẦU ĐĂNG NHẬP</h2><p style='color: #FFFFFF !important; font-size:14px;'>Vui lòng nhập thông tin xác thực ở phía trên để truy cập cơ sở dữ liệu.</p></div>", unsafe_allow_html=True)

# ==============================================================================
# 4. PHÂN HỆ CHÍNH: BẢN ĐỒ & TRA CỨU TRẠM BTS
# ==============================================================================
else:
    col_main_title, col_logout_layout = st.columns([8.3, 1.7])
    with col_main_title:
        st.markdown("<h2 style='margin:0; color:#1E3A8A; font-weight:700; font-size:20px;'>🛰️ TRUNG TÂM ĐỊNH VỊ TRẠM PHÁT SÓNG BTS</h2>", unsafe_allow_html=True)
    with col_logout_layout:
        if st.button("🚪 Đăng xuất", use_container_width=True, type="secondary"):
            st.session_state.logged_in = False
            st.rerun()

    st.markdown("<hr style='margin-top: 5px; margin-bottom: 10px; border-color: #CBD5E1;'>", unsafe_allow_html=True)

    # Khởi tạo hai cột độc lập
    col_left_search, col_right_map = st.columns([2.4, 7.6])

    try:
        df = tai_co_so_du_lieu()
        COT_MCC, COT_MNC, COT_LAC_TAC, COT_CELL_ID, COT_VI_DO, COT_KINH_DO = 'MCC', 'MNC', 'LAC/TAC', 'CELL ID', 'Latitude', 'Longitude'
        vi_do_xem, kinh_do_xem, muc_zoom = 16.047079, 108.206230, 5

        # 1. XỬ LÝ NÚT BẤM MỞ KHI BỘ LỌC ĐANG ẨN (CHỈ DÀNH CHO MOBILE)
        if not st.session_state.show_filter_mobile:
            st.markdown('<div class="mobile-toggle-container">', unsafe_allow_html=True)
            if st.button("🔍 Mở bộ lọc", key="open_filter_mobile_btn", type="primary"):
                st.session_state.show_filter_mobile = True
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        with col_left_search:
            # 2. XỬ LÝ KHI BỘ LỌC ĐANG Ở TRẠNG THÁI MỞ
            if st.session_state.show_filter_mobile:
                st.markdown('<div class="mobile-filter-box">', unsafe_allow_html=True)
                
                # Nút bấm Đóng bộ lọc
                if st.button("✖ Ẩn bộ lọc tìm kiếm", key="close_filter_mobile_btn", type="secondary", use_container_width=True):
                    st.session_state.show_filter_mobile = False
                    st.rerun()

                st.markdown("<p style='font-weight:700; color:#1E3A8A; margin-top:8px; margin-bottom:4px; font-size:14px;'>🔍 THÔNG TIN TÌM KIẾM TRẠM</p>", unsafe_allow_html=True)
                
                # Biểu mẫu nhập liệu cố định hiển thị đầy đủ các trường
                with st.form("form_tra_cuu", clear_on_submit=False):
                    f1 = st.text_input("Mã quốc gia (MCC):", key="mcc_in", value="452").strip()
                    f2 = st.text_input("Mã mạng di động (MNC):", key="mnc_in").strip()
                    f3 = st.text_input("Mã vùng (LAC/TAC):", key="lac_in").strip()
                    f4 = st.text_input("Mã trạm (CELL ID):", key="cell_in").strip()
                    
                    if f2.isdigit() and len(f2) == 1: 
                        f2 = f2.zfill(2)
                        
                    nut_tim_kiem = st.form_submit_button("🎯 Bắt đầu tìm kiếm", use_container_width=True)

                if nut_tim_kiem:
                    if f1 and f2 and f3 and f4:
                        ket_qua = df[(df[COT_MCC].str.strip() == f1) & (df[COT_MNC].str.strip() == f2) & (df[COT_LAC_TAC].str.strip() == f3) & (df[COT_CELL_ID].str.strip() == f4)]
                        if not ket_qua.empty:
                            st.session_state.tram_hien_tai = ket_qua.iloc[0]
                            st.success(f"🎯 Tìm thấy ID: {f4}")
                            st.rerun()
                        else:
                            st.session_state.tram_hien_tai = None
                            st.warning("⚠️ Không tìm thấy dữ liệu trạm!")
                    else:
                        st.error("❌ Vui lòng nhập đủ cả 4 thông số!")

                # Các chức năng Phụ trợ (Lưu trạm, tính khoảng cách)
                if st.session_state.tram_hien_tai is not None:
                    cell_id_hien_tai = st.session_state.tram_hien_tai[COT_CELL_ID]
                    if st.button("📌 Lưu trạm phát sóng này", type="primary", use_container_width=True):
                        if not any(item[COT_CELL_ID] == cell_id_hien_tai for item in st.session_state.danh_sach_luu):
                            st.session_state.danh_sach_luu.append(st.session_state.tram_hien_tai)
                            st.toast(f"Đã lưu trạm {cell_id_hien_tai}")

                so_luong_diem = len(st.session_state.danh_sach_luu)
                if so_luong_diem >= 2:
                    with st.expander("📏 Phân tích trắc địa", expanded=False):
                        tong_khoang_cach = 0.0
                        for i in range(so_luong_diem - 1):
                            tong_khoang_cach += tinh_khoang_cach_haversine(st.session_state.danh_sach_luu[i][COT_VI_DO], st.session_state.danh_sach_luu[i][COT_KINH_DO], st.session_state.danh_sach_luu[i+1][COT_VI_DO], st.session_state.danh_sach_luu[i+1][COT_KINH_DO])
                        st.info(f"Tổng tuyến: **{tong_khoang_cach:.2f} km**")

                if so_luong_diem > 0:
                    with st.expander(f"📍 Danh sách trạm đã lưu ({so_luong_diem})", expanded=False):
                        index_can_xoa = None
                        for idx, tram_luu in enumerate(st.session_state.danh_sach_luu):
                            col_cell_name, col_del_btn = st.columns([6, 4])
                            with col_cell_name: 
                                st.markdown(f"<div style='font-size:12px; padding-top:4px;'>ID: {tram_luu[COT_CELL_ID]}</div>", unsafe_allow_html=True)
                            with col_del_btn:
                                if st.button("Xóa", key=f"del_{idx}", use_container_width=True): 
                                    index_can_xoa = idx
                        if index_can_xoa is not None:
                            st.session_state.danh_sach_luu.pop(index_can_xoa)
                            st.rerun()
                        if st.button("🗑️ Xóa sạch bộ nhớ tạm", type="secondary", use_container_width=True):
                            st.session_state.danh_sach_luu, st.session_state.tram_hien_tai = [], None
                            st.rerun()

                st.markdown('</div>', unsafe_allow_html=True)

        # Định vị tọa độ bản đồ
        so_luong_diem = len(st.session_state.danh_sach_luu)
        if st.session_state.tram_hien_tai is not None:
            vi_do_xem, kinh_do_xem, muc_zoom = float(st.session_state.tram_hien_tai[COT_VI_DO]), float(st.session_state.tram_hien_tai[COT_KINH_DO]), 16
        elif so_luong_diem > 0:
            vi_do_xem, kinh_do_xem, muc_zoom = float(st.session_state.danh_sach_luu[-1][COT_VI_DO]), float(st.session_state.danh_sach_luu[-1][COT_KINH_DO]), 14

        m = folium.Map(location=[vi_do_xem, kinh_do_xem], zoom_start=muc_zoom, control_scale=True)
        folium.TileLayer('https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}', attr='Google Satellite', name='Bản đồ Vệ tinh', overlay=False).add_to(m)
        folium.TileLayer('https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}', attr='Google Maps', name='Bản đồ Đường phố', overlay=False).add_to(m)
        folium.LayerControl().add_to(m)

        toa_do_vung = []
        for index, tram_luu in enumerate(st.session_state.danh_sach_luu):
            lat_l, lon_l = float(tram_luu[COT_VI_DO]), float(tram_luu[COT_KINH_DO])
            toa_do_vung.append([lat_l, lon_l])
            noi_dung_luu = f"<b>📌 TRẠM LƯU [{index+1}]</b><br><b>ID:</b> {tram_luu[COT_CELL_ID]}<br><b>Địa chỉ:</b> {truy_xuat_du_lieu_cot(tram_luu, ['Địa chỉ', 'dia chi', 'Address'])}"
            folium.Marker([lat_l, lon_l], popup=folium.Popup(noi_dung_luu, max_width=220), icon=folium.Icon(color='blue', icon='bookmark')).add_to(m)

        if len(toa_do_vung) == 2: folium.PolyLine(locations=toa_do_vung, color="#0275d8", weight=4).add_to(m)
        elif len(toa_do_vung) >= 3: folium.Polygon(locations=toa_do_vung, color="#0275d8", weight=3, fill=True, fill_opacity=0.15).add_to(m)

        if st.session_state.tram_hien_tai is not None:
            noi_dung_label = f"<b>🎯 KẾT QUẢ TÌM KIẾM</b><br><b>ID:</b> {st.session_state.tram_hien_tai[COT_CELL_ID]}<br><b>Địa chỉ:</b> {truy_xuat_du_lieu_cot(st.session_state.tram_hien_tai, ['Địa chỉ', 'dia chi', 'Address'])}"
            folium.Marker([vi_do_xem, kinh_do_xem], popup=folium.Popup(noi_dung_label, max_width=220, show=True), icon=folium.Icon(color='red', icon='info-sign')).add_to(m)

        with col_right_map:
            # Bản đồ lớn cao 740px toàn diện diện tích
            folium_static(m, height=740, width=None)

    except Exception as e:
        with col_right_map: 
            st.error(f"❌ Lỗi: {e}")
