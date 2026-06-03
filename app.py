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

# BIẾN TRẠNG THÁI ĐÓNG/MỞ BỘ LỌC TRÊN ĐIỆN THOẠI (Mặc định mở khi mới vào)
if "show_filter_mobile" not in st.session_state:
    st.session_state.show_filter_mobile = True

# ==============================================================================
# CSS ĐÁP ỨNG THÔNG MINH - CHUYÊN BIỆT CHO ĐIỆN THOẠI (ẨN / HIỆN FLOATING PANEL)
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
        padding-left: 1rem !important;
        padding-right: 1rem !important;
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
            top: 75px !important;
            left: 15px !important;
            right: 15px !important;
            width: auto !important;
            z-index: 99999 !important;
            background: transparent !important;
            padding: 0px !important;
            box-shadow: none !important;
        }

        /* Định dạng khối bộ lọc màu nền trắng, chữ đen chống lỗi Dark Mode điện thoại */
        .mobile-filter-box {
            background: rgba(255, 255, 255, 0.98) !important;
            border: 1px solid #CBD5E1 !important;
            border-radius: 12px !important;
            padding: 15px !important;
            box-shadow: 0px 8px 24px rgba(0, 0, 0, 0.25) !important;
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
        }
        
        /* Định dạng riêng nút bấm icon Mở bộ lọc (☰) nằm lơ lửng góc trái */
        .mobile-toggle-btn button {
            background-color: #1E3A8A !important;
            color: white !important;
            border-radius: 50% !important;
            width: 45px !important;
            height: 45px !important;
            box-shadow: 0px 4px 10px rgba(0,0,0,0.3) !important;
            font-size: 18px !important;
        }
    }

    /* -------------------------------------------------------------------------- */
    /* GIAO DIỆN TRÊN MÁY TÍNH (PC) - Giữ nguyên không thay đổi                  */
    /* -------------------------------------------------------------------------- */
    @media (min-width: 769px) {
        label { font-weight: 600 !important; color: #212529; }
        .mobile-toggle-btn { display: none !important; } /* Ẩn nút đóng mở trên PC */
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
# 3. PHÂN HỆ ĐĂNG NHẬP (LOGIN)
# ==============================================================================
if not st.session_state.logged_in:
    st.markdown("<style>.stApp, .stMarkdown, p, span, div, label { color: #FFFFFF !important; } input { color: #0F172A !important; background-color: #FFFFFF !important; -webkit-text-fill-color: #0F172A !important;}</style>", unsafe_allow_html=True)
    _, col_login_1, col_login_2 = st.columns([7.0, 1.5, 1.5])
    with col_login_1:
        tai_khoan_nhap = st.text_input("Tài khoản hệ thống:", value="", key="username_input")
    with col_login_2:
        mat_khau_nhap = st.text_input("Mật khẩu truy cập:", type="password", key="password_input")
        
    if tai_khoan_nhap == TAI_KHOAN_CHUAN and mat_khau_nhap == MAT_KHAU_CHUAN:
        st.session_state.logged_in = True
        st.rerun()

    url_hinh_nen = "https://raw.githubusercontent.com/BTS-HUE/HUE-BTS/refs/heads/main/WC%20to.png"
    st.markdown(f"<style>.stApp {{ background-image: url('{url_hinh_nen}'); background-attachment: fixed; background-size: cover; }}</style>", unsafe_allow_html=True)
    st.markdown("<div style='background-color: rgba(15, 23, 42, 0.8); padding: 35px; border-radius: 12px; color: white; text-align: center; margin-top: 12%; box-shadow: 0px 10px 25px rgba(0,0,0,0.6);'><h2 style='color: #ffffff; font-weight: 700;'>🔒 HỆ THỐNG YÊU CẦU ĐĂNG NHẬP</h2><p style='color: #FFFFFF !important;'>Vui lòng nhập thông tin định danh tại góc phải màn hình để truy cập cơ sở dữ liệu.</p></div>", unsafe_allow_html=True)

# ==============================================================================
# 4. PHÂN HỆ CHÍNH: BẢN ĐỒ & TRA CỨU TRẠM BTS
# ==============================================================================
else:
    col_main_title, col_logout_layout = st.columns([8.5, 1.5])
    with col_main_title:
        st.markdown("<h2 style='margin:0; color:#1E3A8A; font-weight:700; font-size:22px;'>🛰️ TRUNG TÂM ĐỊNH VỊ TRẠM PHÁT SÓNG BTS</h2>", unsafe_allow_html=True)
    with col_logout_layout:
        if st.button("🚪 Đăng xuất", use_container_width=True, type="secondary"):
            st.session_state.logged_in = False
            st.rerun()

    st.markdown("<hr style='margin-top: 5px; margin-bottom: 10px; border-color: #CBD5E1;'>", unsafe_allow_html=True)

    # Khởi tạo bố cục: Cột left (Bộ lọc), Cột right (Bản đồ rộng 100% nền)
    col_left_search, col_right_map = st.columns([2.4, 7.6])

    try:
        df = tai_co_so_du_lieu()
        COT_MCC, COT_MNC, COT_LAC_TAC, COT_CELL_ID, COT_VI_DO, COT_KINH_DO = 'MCC', 'MNC', 'LAC/TAC', 'CELL ID', 'Latitude', 'Longitude'
        vi_do_xem, kinh_do_xem, muc_zoom = 16.047079, 108.206230, 5

        with col_left_search:
            # KIỂM TRA TRẠNG THÁI TRÊN ĐIỆN THOẠI ĐỂ ĐÓNG HOẶC MỞ KHUNG TÌM KIẾM
            if not st.session_state.show_filter_mobile:
                # Nút bấm Icon Tròn (☰) xuất hiện khi bộ lọc đang ẩn trên Mobile
                st.markdown('<div class="mobile-toggle-btn">', unsafe_allow_html=True)
                if st.button("☰", key="open_filter_btn"):
                    st.session_state.show_filter_mobile = True
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                # Bọc toàn bộ bộ lọc vào thẻ div để áp CSS nổi trên Mobile
                st.markdown('<div class="mobile-filter-box">', unsafe_allow_html=True)
                
                # Nút bấm thu gọn vào góc trái (chỉ có tác dụng hiển thị trên Điện thoại)
                st.markdown('<div class="mobile-close-container">', unsafe_allow_html=True)
                if st.button("✖ Đóng bộ lọc tìm kiếm", key="close_filter_btn", type="secondary", use_container_width=True):
                    st.session_state.show_filter_mobile = False
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

                # Ruột của bộ lọc tìm kiếm trạm
                st.markdown("<p style='font-weight:700; color:#1E3A8A; margin-top:5px; margin-bottom:5px;'>🔍 BỘ LỌC TÌM KIẾM TRẠM</p>", unsafe_allow_html=True)
                with st.form("form_tra_cuu", clear_on_submit=False):
                    f1 = st.text_input("Mã quốc gia (MCC):", key="mcc_in").strip()
                    f2 = st.text_input("Mã mạng di động (MNC):", key="mnc_in").strip()
                    f3 = st.text_input("Mã vùng (LAC/TAC):", key="lac_in").strip()
                    f4 = st.text_input("Mã trạm (CELL ID):", key="cell_in").strip()
                    if f2.isdigit() and len(f2) == 1: f2 = f2.zfill(2)
                    nut_tim_kiem = st.form_submit_button("🔍 Tìm kiếm trạm", use_container_width=True)

                if nut_tim_kiem:
                    if f1 and f2 and f3 and f4:
                        ket_qua = df[(df[COT_MCC].str.strip() == f1) & (df[COT_MNC].str.strip() == f2) & (df[COT_LAC_TAC].str.strip() == f3) & (df[COT_CELL_ID].str.strip() == f4)]
                        if not ket_qua.empty:
                            st.session_state.tram_hien_tai = ket_qua.iloc[0]
                            st.success(f"🎯 Tìm thấy ID: {f4}")
                            st.rerun()
                        else:
                            st.session_state.tram_hien_tai = None
                            st.warning("⚠️ Không có dữ liệu!")
                    else:
                        st.error("❌ Điền đủ 4 thông số!")

                if st.session_state.tram_hien_tai is not None:
                    cell_id_hien_tai = st.session_state.tram_hien_tai[COT_CELL_ID]
                    if st.button("📌 Lưu trạm phát sóng", type="primary", use_container_width=True):
                        if not any(item[COT_CELL_ID] == cell_id_hien_tai for item in st.session_state.danh_sach_luu):
                            st.session_state.danh_sach_luu.append(st.session_state.tram_hien_tai)
                            st.toast(f"Đã lưu trạm {cell_id_hien_tai}")

                so_luong_diem = len(st.session_state.danh_sach_luu)
                if so_luong_diem >= 2:
                    with st.expander("📏 Phân tích tuyến", expanded=False):
                        tong_khoang_cach = 0.0
                        for i in range(so_luong_diem - 1):
                            tong_khoang_cach += tinh_khoang_cach_haversine(st.session_state.danh_sach_luu[i][COT_VI_DO], st.session_state.danh_sach_luu[i][COT_KINH_DO], st.session_state.danh_sach_luu[i+1][COT_VI_DO], st.session_state.danh_sach_luu[i+1][COT_KINH_DO])
                        st.info(f"Tổng: **{tong_khoang_cach:.2f} km**")

                if so_luong_diem > 0:
                    with st.expander(f"📍 Trạm đã lưu ({so_luong_diem})", expanded=False):
                        index_can_xoa = None
                        for idx, tram_luu in enumerate(st.session_state.danh_sach_luu):
                            col_cell_name, col_del_btn = st.columns([6, 4])
                            with col_cell_name: st.markdown(f"<div style='font-size:12px;'>ID: {tram_luu[COT_CELL_ID]}</div>", unsafe_allow_html=True)
                            with col_del_btn:
                                if st.button("Xóa", key=f"del_{idx}", use_container_width=True): index_can_xoa = idx
                        if index_can_xoa is not None:
                            st.session_state.danh_sach_luu.pop(index_can_xoa)
                            st.rerun()
                        if st.button("🗑️ Xóa sạch bộ nhớ", type="secondary", use_container_width=True):
                            st.session_state.danh_sach_luu, st.session_state.tram_hien_tai = [], None
                            st.rerun()

                st.markdown('</div>', unsafe_allow_html=True) # Đóng khối mobile-filter-box

        # Tính toán tọa độ hiển thị bản đồ
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
            # Bản đồ lớn cố định 740px trên màn hình máy tính lẫn điện thoại
            folium_static(m, height=740, width=None)

    except Exception as e:
        with col_right_map: st.error(f"❌ Lỗi hệ thống: {e}")
