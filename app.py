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
# CSS ĐÁP ỨNG THÔNG MINH (RESPONSIVE): THÍCH ỨNG LINH HOẠT NỀN SÁNG / NỀN TỐI
# ==============================================================================
st.markdown(
    """
    <style>
    /* Ẩn các thành phần thanh công cụ mặc định của Streamlit */
    [data-testid="stSidebarNav"] {display: none !important;}
    [data-testid="stSidebar"] {display: none !important;}
    section[data-testid="stSidebar"] {width: 0px !important; display: none !important;}
    header {visibility: hidden !important; height: 0px !important;}
    footer {visibility: hidden !important;}
    #MainMenu {visibility: hidden !important;}
    iframe[title="Manage app"], .stAppDeployButton, div[data-testid="stAppDeployButton"], footer + div {
        display: none !important; visibility: hidden !important;
    }
    
    /* Thiết lập khoảng cách khung viền chung */
    .block-container {
        padding-top: 0.6rem !important;
        padding-bottom: 0rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        max-width: 100% !important;
    }
    
    .stFoliumStatic { margin-top: 5px !important; width: 100% !important; }
    .stFoliumStatic > iframe { width: 100% !important; border-radius: 6px !important; }
    div.stButton > button { border-radius: 6px !important; }

    /* -------------------------------------------------------------------------- */
    /* CẤU HÌNH MÁY TÍNH (PC): Sử dụng biến hệ thống để tự thích ứng Sáng/Tối     */
    /* -------------------------------------------------------------------------- */
    @media (min-width: 769px) {
        label { font-weight: 600 !important; color: var(--text-color) !important; }
        .stExpander {
            border: 1px solid var(--border-color, #CBD5E1) !important;
            border-radius: 6px !important;
            background-color: var(--background-color) !important;
        }
    }

    /* -------------------------------------------------------------------------- */
    /* CẤU HÌNH ĐIỆN THOẠI (MOBILE): Ép nền sáng cố định để nổi bật trên bản đồ  */
    /* -------------------------------------------------------------------------- */
    @media (max-width: 768px) {
        /* Ép cột chứa bộ lọc lơ lửng lên trên bản đồ */
        div[data-testid="column"]:nth-of-type(1) {
            position: absolute !important;
            top: 65px !important;
            left: 15px !important;
            right: 15px !important;
            width: auto !important;
            z-index: 99999 !important;
            background: transparent !important;
            padding: 0px !important;
            box-shadow: none !important;
        }
        
        /* Đổ nền trắng cố định cho hộp tìm kiếm lơ lửng để dễ đọc trên bản đồ vệ tinh */
        .stExpander {
            background: #FFFFFF !important;
            border: 1px solid #CBD5E1 !important;
            border-radius: 8px !important;
            box-shadow: 0px 6px 18px rgba(0, 0, 0, 0.2) !important;
        }

        /* Chống lỗi mất chữ trên điện thoại: Ép chữ trong hộp nổi luôn là màu tối */
        .stExpander, .stExpander *, .stExpander label, .stExpander p, .stExpander span, .stExpander div {
            color: #0F172A !important;
        }
        
        .stExpander summary p {
            font-weight: 700 !important;
            color: #1E3A8A !important;
        }
        
        /* Đảm bảo các ô nhập liệu luôn hiển thị rõ ràng trên thiết bị di động */
        .stExpander input {
            color: #0F172A !important;
            background-color: #FFFFFF !important;
            -webkit-text-fill-color: #0F172A !important;
            border: 1px solid #CBD5E1 !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ==============================================================================
# 2. THUẬT TOÁN XỬ LÝ TOÁN HỌC & ĐỊA LÝ
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
# 3. PHÂN HỆ KHÓA XÁC THỰC TRUY CẬP (LOGIN)
# ==============================================================================
if not st.session_state.logged_in:
    st.markdown(
        """
        <style>
        .stApp, .stMarkdown, p, span, div, label { color: #FFFFFF !important; }
        input { color: #0F172A !important; background-color: #FFFFFF !important; -webkit-text-fill-color: #0F172A !important;}
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
# 4. PHÂN HỆ ĐIỀU HÀNH CHÍNH (BẢN ĐỒ & TRA CỨU HẠ TẦNG)
# ==============================================================================
else:
    col_main_title, col_logout_layout = st.columns([8.5, 1.5])
    with col_main_title:
        # Thay đổi thuộc tính màu chữ tiêu đề chính thành biến hệ thống động var(--text-color)
        st.markdown(
            "<h2 style='margin:0; color: var(--text-color); font-weight:700; font-size:22px; text-shadow: none;'>"
            "🛰️ TRUNG TÂM GIÁM SÁT VÀ ĐỊNH VỊ TRẠM PHÁT SÓNG BTS"
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

    st.markdown("<hr style='margin-top: 5px; margin-bottom: 10px; border-color: #CBD5E1;'>", unsafe_allow_html=True)

    # Đặt tỷ lệ cột chuẩn dạng 2.4 và 7.6 để hiển thị hoàn hảo trên máy tính
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
            # Thanh bộ lọc tìm kiếm linh hoạt (Tự lơ lửng & Co giãn trên mobile, cố định trên PC)
            with st.expander("🔍 Bộ lọc tìm kiếm trạm", expanded=True):
                with st.form("form_tra_cuu", clear_on_submit=True):
                    f1 = st.text_input("Mã quốc gia (MCC):", key="mcc_in").strip()
                    f2 = st.text_input("Mã mạng di động (MNC):", key="mnc_in").strip()
                    f3 = st.text_input("Mã vùng (LAC/TAC):", key="lac_in").strip()
                    f4 = st.text_input("Mã trạm (CELL ID):", key="cell_in").strip()
                    
                    if f2.isdigit() and len(f2) == 1:
                        f2 = f2.zfill(2)
                    
                    nut_tim_kiem = st.form_submit_button("🔍 Tìm kiếm trạm", use_container_width=True)
            
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
                        st.warning("⚠️ Không có dữ liệu phù hợp!")
                else:
                    st.error("❌ Điền đủ 4 thông số!")

            if st.session_state.tram_hien_tai is not None:
                cell_id_hien_tai = st.session_state.tram_hien_tai[COT_CELL_ID]
                if st.button("📌 Lưu trạm phát sóng", type="primary", use_container_width=True):
                    da_ton_tai = any(item[COT_CELL_ID] == cell_id_hien_tai for item in st.session_state.danh_sach_luu)
                    if not da_ton_tai:
                        st.session_state.danh_sach_luu.append(st.session_state.tram_hien_tai)
                        st.toast(f"Đã lưu trạm {cell_id_hien_tai}")
                    else:
                        st.toast("Trạm này đã lưu trước đó.")
            
            so_luong_diem = len(st.session_state.danh_sach_luu)
            
            if so_luong_diem >= 2:
                with st.expander("📏 Phân tích trắc địa tuyến", expanded=False):
                    tong_khoang_cach = 0.0
                    for i in range(so_luong_diem - 1):
                        p1 = st.session_state.danh_sach_luu[i]
                        p2 = st.session_state.danh_sach_luu[i+1]
                        kc = tinh_khoang_cach_haversine(p1[COT_VI_DO], p1[COT_KINH_DO], p2[COT_VI_DO], p2[COT_KINH_DO])
                        tong_khoang_cach += kc
                    st.info(f"Tổng tuyến: **{tong_khoang_cach:.2f} km**")

            if so_luong_diem > 0:
                with st.expander(f"📍 Trạm đã lưu vào máy ({so_luong_diem})", expanded=False):
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

                    if st.button("🗑️ Xóa sạch danh sách", type="secondary", use_container_width=True):
                        st.session_state.danh_sach_luu = []
                        st.session_state.tram_hien_tai = None
                        st.rerun()

        # Cân đối tọa độ điểm nhìn
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

            # Thêm Vĩ độ & Kinh độ vào 1 dòng trong Popup Trạm lưu
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

            # Cập nhật Popup: Cell ID lên tiêu đề, Vĩ độ và Kinh độ đưa vào 1 dòng chung
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
            # Chiều cao 730px tối ưu hiển thị bản đồ rộng và đẹp mắt
            folium_static(m, height=730, width=None)

    except Exception as e:
        with col_right_map:
            st.error(f"❌ Khởi tạo thất bại: {e}")
