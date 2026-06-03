import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import math

# ==============================================================================
# 1. CẤU HÌNH HỆ THỐNG & QUẢN LÝ PHIÊN TRUY CẬP (ĐỒNG BỘ URL + SESSION STATE)
# ==============================================================================
st.set_page_config(
    page_title="Hệ thống Quản lý & Định vị Trạm phát sóng BTS", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# Hệ thống tự động kiểm tra cấu hình bảo mật từ Secrets hoặc mặc định
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

# Biến cờ để kiểm tra xem có cần xóa tham số URL hay không
can_xoa_url = False

# Đồng bộ trạng thái đăng nhập giữa URL và Session State
if "logged_in" not in st.session_state:
    if st.query_params.get("auth_token") == TOKEN_XAC_THUC:
        st.session_state.logged_in = True
        can_xoa_url = True
    else:
        st.session_state.logged_in = False

if can_xoa_url:
    st.query_params.clear()

# Khởi tạo bộ nhớ tạm cho phiên làm việc
if "danh_sach_luu" not in st.session_state:
    st.session_state.danh_sach_luu = []
if "tram_hien_tai" not in st.session_state:
    st.session_state.tram_hien_tai = None

# ==============================================================================
# 2. CSS ĐÁP ỨNG THÔNG MINH - ĐẶC TRỊ LỖI CỘT TÌM KIẾM BỊ DỌC TRÊN MOBILE
# ==============================================================================
st.markdown(
    """
    <style>
    /* -------------------------------------------------------------------------- */
    /* 1. ẨN CÁC THÀNH PHẦN THỪA CỦA STREAMLIT                                    */
    /* -------------------------------------------------------------------------- */
    [data-testid="stSidebarNav"], [data-testid="stSidebar"], section[data-testid="stSidebar"], 
    header, footer, #MainMenu, iframe[title="Manage app"], .stAppDeployButton, div[data-testid="stAppDeployButton"], footer + div {
        display: none !important; visibility: hidden !important; width: 0px !important; height: 0px !important;
    }
    
    .block-container {
        padding: 0.5rem 0.8rem 0rem 0.8rem !important;
        max-width: 100% !important;
    }

    /* -------------------------------------------------------------------------- */
    /* 2. ĐỒNG BỘ MÀU SẮC THEME HỆ THỐNG                                         */
    /* -------------------------------------------------------------------------- */
    label, p, span, summary, div {
        color: var(--text-color) !important;
    }
    
    .stExpander {
        background-color: var(--background-color) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 12px !important;
        box-shadow: 0px 4px 15px rgba(0, 0, 0, 0.1) !important;
    }

    .stExpander summary p {
        font-weight: 700 !important;
    }

    .stExpander input {
        background-color: var(--secondary-background-color) !important;
        color: var(--text-color) !important;
        -webkit-text-fill-color: var(--text-color) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 8px !important;
    }

    div[data-testid="stForm"] button[data-testid="baseButton-secondaryFormSubmit"] {
        background-color: #3B82F6 !important; 
        color: #FFFFFF !important;
        -webkit-text-fill-color: #FFFFFF !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
        border: none !important;
    }

    /* -------------------------------------------------------------------------- */
    /* 3. THIẾT KẾ ĐÈ LAYOUT (OVERLAY) - FIX LỖI CO CỘT TÌM KIẾM TRÊN DI ĐỘNG      */
    /* -------------------------------------------------------------------------- */
    
    /* Giao diện trên Máy tính (PC) */
    div[data-testid="stHorizontalBlock"]:has(.stFoliumStatic) {
        position: relative !important;
        display: block !important;
        height: 740px !important; 
    }
    /* Bản đồ nằm nền dưới */
    div[data-testid="stHorizontalBlock"]:has(.stFoliumStatic) > div[data-testid="column"]:nth-of-type(2) {
        position: absolute !important;
        top: 0 !important; left: 0 !important; width: 100% !important; height: 100% !important;
        z-index: 1 !important; padding: 0px !important;
    }
    /* Khung tìm kiếm đè lên góc trái */
    div[data-testid="stHorizontalBlock"]:has(.stFoliumStatic) > div[data-testid="column"]:nth-of-type(1) {
        position: absolute !important;
        top: 15px !important; left: 15px !important; width: 330px !important;
        z-index: 9999 !important; background: transparent !important; padding: 0px !important;
    }
    .stFoliumStatic, .stFoliumStatic > iframe { width: 100% !important; height: 100% !important; border-radius: 12px !important; }

    /* SỬA LỖI GIAO DIỆN TRÊN MOBILE (MÀN HÌNH < 768PX) */
    @media (max-width: 768px) {
        /* Ép khung chứa chính cố định cao độ theo màn hình điện thoại, chống trượt dòng */
        div[data-testid="stHorizontalBlock"]:has(.stFoliumStatic) {
            display: block !important;
            position: relative !important;
            height: 80vh !important;
            min-height: 520px !important;
            overflow: hidden !important;
        }

        /* FIX KHÓA CỨNG: Ép cột 2 (Bản đồ) bung rộng toàn vẹn, không bị ép hẹp ngang */
        div[data-testid="stHorizontalBlock"]:has(.stFoliumStatic) > div[data-testid="column"]:nth-of-type(2) {
            position: absolute !important;
            top: 0 !important;
            left: 0 !important;
            width: 100% !important;
            min-width: 100% !important;
            max-width: 100% !important;
            height: 100% !important;
            z-index: 1 !important;
            padding: 0px !important;
        }

        /* FIX KHÓA CỨNG: Ép cột 1 (Cột tìm kiếm) giữ nguyên hình dạng khối chữ nhật nằm lơ lửng */
        div[data-testid="stHorizontalBlock"]:has(.stFoliumStatic) > div[data-testid="column"]:nth-of-type(1) {
            position: absolute !important;
            top: 12px !important;
            left: 12px !important;
            
            /* Đảm bảo chiều ngang hộp tìm kiếm vừa vặn tay cầm, không bị biến dạng cột dọc */
            width: 300px !important;
            min-width: 300px !important;
            max-width: 88% !important;
            
            z-index: 9999 !important;
            padding: 0px !important;
            
            /* Tạo cuộn nội bộ nếu danh sách lưu quá dài */
            max-height: 80% !important;
            overflow-y: auto !important;
        }

        .stFoliumStatic, .stFoliumStatic > iframe {
            height: 100% !important;
            min-height: 520px !important;
        }

        .stExpander {
            border-radius: 14px !important;
            box-shadow: 0px 6px 20px rgba(0, 0, 0, 0.3) !important;
            backdrop-filter: blur(10px) !important;
            background-color: rgba(var(--background-color-rgb), 0.95) !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ==============================================================================
# 3. THUẬT TOÁN XỬ LÝ TOÁN HỌC & ĐỊA LÝ
# ==============================================================================
def tinh_khoang_cach_haversine(lat1, lon1, lat2, lon2):
    r_lat1, r_lon1, r_lat2, r_lon2 = map(math.radians, [float(lat1), float(lon1), float(lat2), float(lon2)])
    dlat = r_lat2 - r_lat1
    dlon = r_lon2 - r_lon1
    a = math.sin(dlat / 2)**2 + math.cos(r_lat1) * math.cos(r_lat2) * math.sin(dlon / 2)**2
    c = 2 * math.asin(math.sqrt(a))
    BAN_KINH_TRAI_DAT_KM = 6371.0
    return c * BAN_KINH_TRAI_DAT_KM

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
# 4. PHÂN HỆ KHÓA XÁC THỰC TRUY CẬP (LOGIN)
# ==============================================================================
if not st.session_state.logged_in:
    st.markdown(
        """
        <style>
        .stApp, .stMarkdown, p, span, div, label { color: #FFFFFF !important; }
        input { color: #0F172A !important; background-color: #FFFFFF !important; -webkit-text-fill-color: #0F172A !important;}
        
        @media (max-width: 768px) {
            .stApp div[data-testid="stHorizontalBlock"] {
                display: flex !important;
                flex-direction: row !important;
                flex-wrap: nowrap !important;
                width: 100% !important;
                gap: 8px !important;
            }
            .stApp div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-of-type(1) {
                display: none !important; width: 0px !important;
            }
            .stApp div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-of-type(2),
            .stApp div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-of-type(3) {
                display: block !important; width: 50% !important; min-width: 50% !important; max-width: 50% !important; flex: 1 1 50% !important; padding: 0px !important;
            }
        }
        </style>
        """, 
        unsafe_allow_html=True
    )
    
    _, col_login_1, col_login_2 = st.columns([7.0, 1.5, 1.5])

    with col_login_1:
        tai_khoan_nhap = st.text_input("Tài khoản hệ thống:", value="", key="username_input")

    with col_login_2:
        mat_khau_nhap = st.text_input("Mật khẩu truy cập:", type="password", key="password_input")
        
    if tai_khoan_nhap == TAI_KHOAN_CHUAN and mat_khau_nhap == MAT_KHAU_CHUAN:
        st.session_state.logged_in = True
        st.rerun()

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
        </style>
        """,
        unsafe_allow_html=True
    )
    
    st.markdown(
        """
        <div style='
            background-color: rgba(15, 23, 42, 0.8); 
            padding: 35px; 
            border-radius: 12px; 
            color: white; 
            text-align: center;
            margin-top: 12%;
            box-shadow: 0px 10px 25px rgba(0,0,0,0.6);
            backdrop-filter: blur(8px);
            border: 1px solid rgba(255,255,255,0.1);'>
            <h2 style='color: #ffffff; margin-bottom: 12px; font-weight: 700; letter-spacing: 1px;'>🔒 HỆ THỐNG YÊU CẦU ĐĂNG NHẬP</h2>
            <p style='font-size: 15px; opacity: 0.85; margin: 0; font-family: sans-serif; color: #FFFFFF !important;'>Vui lòng nhập thông tin định danh tại góc phải màn hình để truy cập cơ sở dữ liệu hạ tầng.</p>
        </div>
        """, 
        unsafe_allow_html=True
    )

# ==============================================================================
# 5. PHÂN HỆ ĐIỀU HÀNH CHÍNH (BẢN ĐỒ & TRA CỨU HẠ TẦNG)
# ==============================================================================
else:
    col_main_title, col_logout_layout = st.columns([8.5, 1.5])
    with col_main_title:
        st.markdown(
            "<h2 style='margin:0; color: var(--text-color); font-weight:700; font-size:20px; text-shadow: none;'>"
            "🛰️ TRUNG TÂM ĐỊNH VỊ TRẠM PHÁT SÓNG BTS"
            "</h2>", 
            unsafe_allow_html=True
        )
    with col_logout_layout:
        if st.button("🚪 Đăng xuất", use_container_width=True, type="secondary"):
            st.query_params.clear()
            st.session_state.logged_in = False
            st.session_state.danh_sach_luu = []
            st.session_state.tram_hien_tai = None
            st.rerun()

    st.markdown("<hr style='margin-top: 5px; margin-bottom: 10px; border-color: var(--border-color);'>", unsafe_allow_html=True)

    col_left_search, col_right_map = st.columns([2.4, 7.6])

    try:
        df = tai_co_so_du_lieu()
        
        COT_MCC = 'MCC'
        COT_MNC = 'MNC'
        COT_LAC_TAC = 'LAC/TAC'
        COT_CELL_ID = 'CELL ID'
        COT_VI_DO = 'Latitude'
        COT_KINH_DO = 'Longitude'

        vi_do_xem, kinh_do_xem, muc_zoom = 16.047079, 108.206230, 5

        with col_left_search:
            with st.expander("🔍 Tìm kiếm trạm", expanded=True):
                with st.form("form_tra_cuu", clear_on_submit=True):
                    f1 = st.text_input("MCC (Country):", key="mcc_in").strip()
                    f2 = st.text_input("MNC (Network):", key="mnc_in").strip()
                    f3 = st.text_input("LAC / TAC:", key="lac_in").strip()
                    f4 = st.text_input("Cell ID:", key="cell_in").strip()
                    
                    if f2.isdigit() and len(f2) == 1:
                        f2 = f2.zfill(2)
                    
                    nut_tim_kiem = st.form_submit_button("🔍 Lọc & Định vị", use_container_width=True)
            
            st.markdown(
                """
                <script>
                var inputs = window.parent.document.querySelectorAll('input');
                inputs.forEach(function(input) {
                    input.setAttribute('autocomplete', 'one-time-code');
                });
                </script>
                """,
                unsafe_allow_html=True
            )

            if nut_tim_kiem:
                if f1 and f2 and f3 and f4:
                    ket_qua = df[
                        (df[COT_MCC].str.strip() == f1) & 
                        (df[COT_MNC].str.strip() == f2) & 
                        (df[COT_LAC_TAC].str.strip() == f3) & 
                        (df[COT_CELL_ID].str.strip() == f4)
                    ]
                    
                    if not ket_qua.empty:
                        st.session_state.tram_hien_tai = ket_qua.iloc[0]
                        st.success(f"🎯 Tìm thấy ID: {f4}")
                        st.rerun()
                    else:
                        st.session_state.tram_hien_tai = None
                        st.warning("⚠️ Không có dữ liệu!")
                else:
                    st.error("❌ Điền đủ thông số!")

            if st.session_state.tram_hien_tai is not None:
                cell_id_hien_tai = st.session_state.tram_hien_tai[COT_CELL_ID]
                if st.button("📌 Lưu trạm", type="primary", use_container_width=True):
                    da_ton_tai = any(item[COT_CELL_ID] == cell_id_hien_tai for item in st.session_state.danh_sach_luu)
                    if not da_ton_tai:
                        st.session_state.danh_sach_luu.append(st.session_state.tram_hien_tai)
                        st.toast(f"Đã lưu trạm {cell_id_hien_tai}")
                    else:
                        st.toast("Trạm này đã lưu trước đó.")
            
            so_luong_diem = len(st.session_state.danh_sach_luu)
            
            if so_luong_diem >= 2:
                with st.expander("📏 Khoảng cách tuyến", expanded=False):
                    tong_khoang_cach = 0.0
                    for i in range(so_luong_diem - 1):
                        p1 = st.session_state.danh_sach_luu[i]
                        p2 = st.session_state.danh_sach_luu[i+1]
                        kc = tinh_khoang_cach_haversine(p1[COT_VI_DO], p1[COT_KINH_DO], p2[COT_VI_DO], p2[COT_KINH_DO])
                        tong_khoang_cach += kc
                    st.info(f"Tổng: **{tong_khoang_cach:.2f} km**")

            if so_luong_diem > 0:
                with st.expander(f"📍 Danh sách đã lưu ({so_luong_diem})", expanded=False):
                    index_can_xoa = None
                    for idx, tram_luu in enumerate(st.session_state.danh_sach_luu):
                        col_cell_name, col_del_btn = st.columns([6, 4])
                        with col_cell_name:
                            st.markdown(f"<div style='font-size:12px; padding-top:5px;'>ID: {tram_luu[COT_CELL_ID]}</div>", unsafe_allow_html=True)
                        with col_del_btn:
                            if st.button("Xóa", key=f"del_{tram_luu[COT_CELL_ID]}_{idx}", use_container_width=True):
                                index_can_xoa = idx
                    
                    if index_can_xoa is not None:
                        st.session_state.danh_sach_luu.pop(index_can_xoa)
                        st.rerun()

                    if st.button("🗑️ Xóa sạch", type="secondary", use_container_width=True):
                        st.session_state.danh_sach_luu = []
                        st.session_state.tram_hien_tai = None
                        st.rerun()

        if st.session_state.tram_hien_tai is not None:
            vi_do_xem = float(st.session_state.tram_hien_tai[COT_VI_DO])
            kinh_do_xem = float(st.session_state.tram_hien_tai[COT_KINH_DO])
            muc_zoom = 16
        elif so_luong_diem > 0:
            vi_do_xem = float(st.session_state.danh_sach_luu[-1][COT_VI_DO])
            kinh_do_xem = float(st.session_state.danh_sach_luu[-1][COT_KINH_DO])
            muc_zoom = 14

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

        toa_do_vung = []

        for index, tram_luu in enumerate(st.session_state.danh_sach_luu):
            lat_l = float(tram_luu[COT_VI_DO])
            lon_l = float(tram_luu[COT_KINH_DO])
            toa_do_vung.append([lat_l, lon_l])
            
            cgi_l = truy_xuat_du_lieu_cot(tram_luu, ['CGI', 'cgi'])
            addr_l = truy_xuat_du_lieu_cot(tram_luu, ['Địa chỉ', 'dia chi', 'Address'])
            cell_l = tram_luu[COT_CELL_ID]

            noi_dung_luu = f"""
            <div style='font-family: Arial, sans-serif; font-size: 13px; width: 220px; color: #333333; line-height: 1.4;'>
                <b>📌 TRẠM LƯU [{index+1}]</b><br>
                <b>ID:</b> {cell_l}<br>
                <b>CGI:</b> {cgi_l}<br>
                <b>Tọa độ:</b> {lat_l}, {lon_l}<br>
                <b>Địa chỉ:</b> {addr_l}
            </div>
            """
            folium.Marker([lat_l, lon_l], popup=folium.Popup(noi_dung_luu, max_width=240), icon=folium.Icon(color='blue', icon='bookmark')).add_to(m)

        if len(toa_do_vung) == 2:
            folium.PolyLine(locations=toa_do_vung, color="#0275d8", weight=4, opacity=0.8).add_to(m)
        elif len(toa_do_vung) >= 3:
            folium.Polygon(locations=toa_do_vung, color="#0275d8", weight=3, fill=True, fill_color="#0275d8", fill_opacity=0.15).add_to(m)

        if st.session_state.tram_hien_tai is not None:
            cgi_val = truy_xuat_du_lieu_cot(st.session_state.tram_hien_tai, ['CGI', 'cgi'])
            dia_chi_val = truy_xuat_du_lieu_cot(st.session_state.tram_hien_tai, ['Địa chỉ', 'dia chi', 'Address'])
            cell_val = st.session_state.tram_hien_tai[COT_CELL_ID]
            lat_val = st.session_state.tram_hien_tai[COT_VI_DO]
            lon_val = st.session_state.tram_hien_tai[COT_KINH_DO]

            noi_dung_label = f"""
            <div style='font-family: Arial, sans-serif; font-size: 13px; width: 220px; color: #333333; line-height: 1.4;'>
                <b style='color: #D9534F;'>🎯 KẾT QUẢ TÌM KIẾM: {cell_val}</b><br>
                <b>CGI:</b> {cgi_val}<br>
                <b>Tọa độ:</b> {lat_val}, {lon_val}<br>
                <b>Địa chỉ:</b> {dia_chi_val}
            </div>
            """
            folium.Marker([vi_do_xem, kinh_do_xem], popup=folium.Popup(noi_dung_label, max_width=240, show=True), icon=folium.Icon(color='red', icon='info-sign')).add_to(m)

        with col_right_map:
            folium_static(m, height=730, width=None)

    except Exception as e:
        with col_right_map:
            st.error(f"❌ Khởi tạo thất bại: {e}")
