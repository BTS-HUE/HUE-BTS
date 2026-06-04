import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import math

# ==============================================================================
# 1. CẤU HÌNH HỆ THỐNG & QUẢN LÝ PHIÊN TRUY CẬP
# ==============================================================================
st.set_page_config(
    page_title="Hệ Thống Giám Sát & Định Vị TRẠM BTS", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# Đọc cấu hình bảo mật
TOKEN_XAC_THUC = st.secrets["auth"]["token_xac_thuc"]
TAI_KHOAN_CHUAN = st.secrets["auth"]["tai_khoan_chuan"]
MAT_KHAU_CHUAN = st.secrets["auth"]["mat_khau_chuan"]
SHEET_ID = st.secrets["database"]["sheet_id"]

# Khởi tạo & Đồng bộ trạng thái phiên làm việc
if "logged_in" not in st.session_state:
    if st.query_params.get("auth_token") == TOKEN_XAC_THUC:
        st.session_state.logged_in = True
        st.query_params.clear()
    else:
        st.session_state.logged_in = False

st.session_state.setdefault("danh_sach_luu", [])
st.session_state.setdefault("tram_hien_tai", None)

# ==============================================================================
# 2. CSS ĐÁP ỨNG THÔNG MINH (UI/UX)
# ==============================================================================
st.markdown(
    """
    <style>
    /* 1. Ẩn thành phần thừa của Streamlit */
    [data-testid="stSidebarNav"], [data-testid="stSidebar"], section[data-testid="stSidebar"], 
    header, footer, #MainMenu, iframe[title="Manage app"], .stAppDeployButton, div[data-testid="stAppDeployButton"], footer + div {
        display: none !important; visibility: hidden !important; width: 0px !important; height: 0px !important;
    }
    .block-container { padding: 0.6rem 1rem 0rem 1rem !important; max-width: 100% !important; }
    .stFoliumStatic { margin-top: 0px !important; width: 100% !important; }
    .stFoliumStatic > iframe { width: 100% !important; border-radius: 12px !important; }

    /* 2. Đồng bộ màu sắc Sáng/Tối */
    label, p, span, summary, div { color: var(--text-color) !important; }
    .stExpander {
        background-color: var(--background-color) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 12px !important;
        box-shadow: 0px 4px 15px rgba(0, 0, 0, 0.1) !important;
    }
    .stExpander summary p { font-weight: 700 !important; }
    .stExpander input {
        background-color: var(--secondary-background-color) !important;
        color: var(--text-color) !important;
        -webkit-text-fill-color: var(--text-color) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 8px !important;
    }
    div[data-testid="stForm"] button[data-testid="baseButton-secondaryFormSubmit"] {
        background-color: #3B82F6 !important; color: #FFFFFF !important; -webkit-text-fill-color: #FFFFFF !important;
        font-weight: 700 !important; border-radius: 8px !important; border: none !important; transition: all 0.2s ease;
    }
    div[data-testid="stForm"] button[data-testid="baseButton-secondaryFormSubmit"]:hover {
        background-color: #2563EB !important; box-shadow: 0px 4px 12px rgba(59, 130, 246, 0.3) !important;
    }

    /* 3. Layout lơ lửng cho Bản đồ & Bộ lọc */
    div[data-testid="stHorizontalBlock"]:has(.stFoliumStatic) { position: relative !important; display: block !important; height: 730px !important; }
    div[data-testid="stHorizontalBlock"]:has(.stFoliumStatic) div[data-testid="column"]:nth-of-type(2) {
        position: absolute !important; top: 0 !important; left: 0 !important; width: 100% !important; height: 100% !important; z-index: 1 !important; padding: 0px !important;
    }
    div[data-testid="stHorizontalBlock"]:has(.stFoliumStatic) div[data-testid="column"]:nth-of-type(1) {
        position: absolute !important; top: 15px !important; left: 15px !important; width: 320px !important; z-index: 9999 !important; background: transparent !important; padding: 0px !important;
    }

    /* Tối ưu Mobile */
    @media (max-width: 768px) {
        div[data-testid="stHorizontalBlock"]:has(.stFoliumStatic) div[data-testid="column"]:nth-of-type(1) {
            top: 10px !important; left: 10px !important; width: 230px !important; max-width: 85% !important;
        }
        .stExpander summary p { font-size: 13px !important; }
        .stExpander label p { font-size: 11px !important; }
        .stExpander input { font-size: 12px !important; padding: 4px 8px !important; }
        div[data-testid="stForm"] button[data-testid="baseButton-secondaryFormSubmit"] { font-size: 13px !important; padding: 4px !important; }
        .stExpander { border-radius: 10px !important; box-shadow: 0px 6px 20px rgba(0, 0, 0, 0.3) !important; backdrop-filter: blur(8px) !important; }
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ==============================================================================
# 3. THUẬT TOÁN & TRUY XUẤT DỮ LIỆU
# ==============================================================================
def tinh_khoang_cach_haversine(lat1, lon1, lat2, lon2):
    r_lat1, r_lon1, r_lat2, r_lon2 = map(math.radians, [float(lat1), float(lon1), float(lat2), float(lon2)])
    a = math.sin((r_lat2 - r_lat1) / 2)**2 + math.cos(r_lat1) * math.cos(r_lat2) * math.sin((r_lon2 - r_lon1) / 2)**2
    return 2 * math.asin(math.sqrt(a)) * 6371.0 # Bán kính trái đất (km)

@st.cache_data(ttl=600) 
def tai_co_so_du_lieu():
    URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"
    data = pd.read_csv(URL, dtype=str)
    
    # Tối ưu: Làm sạch dữ liệu ngay từ bước load cache để truy vấn mượt hơn
    data.columns = data.columns.str.strip()
    for col in data.columns:
        data[col] = data[col].fillna("").astype(str).str.strip()
            
    if 'MNC' in data.columns:
        data['MNC'] = data['MNC'].apply(lambda x: x.zfill(2) if x.isdigit() and len(x) == 1 else x)
    return data

def truy_xuat_du_lieu_cot(row, danh_sach_ten_goi):
    tap_ten_goi = set(x.lower() for x in danh_sach_ten_goi)
    for k in row.index:
        if str(k).lower() in tap_ten_goi:
            return row[k]
    return "Không có dữ liệu"

# ==============================================================================
# 4. PHÂN HỆ XÁC THỰC TRUY CẬP (LOGIN)
# ==============================================================================
if not st.session_state.logged_in:
    st.markdown(
        """<style>.stApp, .stMarkdown, p, span, div, label { color: #FFFFFF !important; }
        input { color: #0F172A !important; background-color: #FFFFFF !important; -webkit-text-fill-color: #0F172A !important;}</style>""", 
        unsafe_allow_html=True
    )
    
    _, col_login_1, col_login_2 = st.columns([7.0, 1.5, 1.5])
    with col_login_1:
        tai_khoan_nhap = st.text_input("Tài khoản định danh:", value="", key="username_input")
    with col_login_2:
        mat_khau_nhap = st.text_input("Mã xác thực:", type="password", key="password_input")
        
    if tai_khoan_nhap == TAI_KHOAN_CHUAN and mat_khau_nhap == MAT_KHAU_CHUAN:
        st.session_state.logged_in = True
        st.rerun()

    # Vô hiệu hóa auto-fill trình duyệt
    st.markdown("<script>window.parent.document.querySelectorAll('input').forEach(i => i.setAttribute('autocomplete', 'new-password'));</script>", unsafe_allow_html=True)

    url_hinh_nen = "https://raw.githubusercontent.com/BTS-HUE/HUE-BTS/refs/heads/main/WC%20to.png"
    st.markdown(
        f"""<style>.stApp {{ background-image: url("{url_hinh_nen}"); background-attachment: fixed; background-size: cover; background-position: center; }}</style>""",
        unsafe_allow_html=True
    )
    
    st.markdown(
        """
        <div style='background-color: rgba(15, 23, 42, 0.85); padding: 35px; border-radius: 12px; color: white; text-align: center; margin-top: 12%; box-shadow: 0px 10px 25px rgba(0,0,0,0.6); backdrop-filter: blur(8px); border: 1px solid rgba(255,255,255,0.1);'>
            <h2 style='color: #ffffff; margin-bottom: 12px; font-weight: 700; letter-spacing: 1px;'>🔒 XÁC THỰC QUYỀN TRUY CẬP</h2>
            <p style='font-size: 15px; opacity: 0.85; margin: 0;'>Vui lòng cung cấp thông tin định danh tại góc phải màn hình để truy cập cơ sở dữ liệu hạ tầng.</p>
        </div>
        """, 
        unsafe_allow_html=True
    )

# ==============================================================================
# 5. TRUNG TÂM ĐIỀU HÀNH & GIÁM SÁT BẢN ĐỒ
# ==============================================================================
else:
    col_main_title, col_logout_layout = st.columns([8.5, 1.5])
    with col_main_title:
        st.markdown(
            "<h2 style='margin:0; color: var(--text-color); font-weight:700; font-size:22px; text-shadow: none;'>"
            "🛰️ TRUNG TÂM GIÁM SÁT VÀ ĐỊNH VỊ TRẠM BTS"
            "</h2>", 
            unsafe_allow_html=True
        )
    with col_logout_layout:
        if st.button("🚪 Thoát phiên", use_container_width=True, type="secondary"):
            st.query_params.clear()
            st.session_state.logged_in = False
            st.session_state.danh_sach_luu.clear()
            st.session_state.tram_hien_tai = None
            st.rerun()

    st.markdown("<hr style='margin-top: 5px; margin-bottom: 10px; border-color: var(--border-color);'>", unsafe_allow_html=True)

    col_left_search, col_right_map = st.columns([2.4, 7.6])

    try:
        df = tai_co_so_du_lieu()
        
        # Biến tĩnh định danh cột
        COT_MCC, COT_MNC, COT_LAC_TAC, COT_CELL_ID, COT_VI_DO, COT_KINH_DO = 'MCC', 'MNC', 'LAC/TAC', 'CELL ID', 'Latitude', 'Longitude'
        vi_do_xem, kinh_do_xem, muc_zoom = 16.047079, 108.206230, 5

        with col_left_search:
            with st.expander("🔍 TÌM KIẾM TRẠM", expanded=True):
                with st.form("form_tra_cuu", clear_on_submit=True):
                    f1 = st.text_input("Mã Quốc gia (MCC):", key="mcc_in").strip()
                    f2 = st.text_input("Mã Mạng (MNC):", key="mnc_in").strip()
                    f3 = st.text_input("Mã Vùng (LAC/TAC):", key="lac_in").strip()
                    f4 = st.text_input("Cell ID:", key="cell_in").strip()
                    
                    if f2.isdigit() and len(f2) == 1: f2 = f2.zfill(2)
                    nut_tim_kiem = st.form_submit_button("🔍 Tìm Kiếm", use_container_width=True)
            
            st.markdown("<script>window.parent.document.querySelectorAll('input').forEach(i => i.setAttribute('autocomplete', 'one-time-code'));</script>", unsafe_allow_html=True)

            if nut_tim_kiem:
                if all([f1, f2, f3, f4]):
                    # Do dữ liệu đã được strip() trong cache nên chỉ cần so sánh trực tiếp
                    ket_qua = df[(df[COT_MCC] == f1) & (df[COT_MNC] == f2) & (df[COT_LAC_TAC] == f3) & (df[COT_CELL_ID] == f4)]
                    
                    if not ket_qua.empty:
                        st.session_state.tram_hien_tai = ket_qua.iloc[0]
                        st.success(f"🎯 Đã phát hiện ID: {f4}")
                    else:
                        st.session_state.tram_hien_tai = None
                        st.warning("⚠️ Bản ghi không tồn tại!")
                else:
                    st.error("❌ Yêu cầu nhập đầy đủ tham số!")

            if st.session_state.tram_hien_tai is not None:
                cell_id_hien_tai = st.session_state.tram_hien_tai[COT_CELL_ID]
                if st.button("📌 Gắn thẻ tọa độ", type="primary", use_container_width=True):
                    if not any(item[COT_CELL_ID] == cell_id_hien_tai for item in st.session_state.danh_sach_luu):
                        st.session_state.danh_sach_luu.append(st.session_state.tram_hien_tai)
                        st.toast(f"Đã lưu tọa độ trạm {cell_id_hien_tai}")
                    else:
                        st.toast("Cảnh báo: Trạm này đã được ghim trước đó.")
            
            so_luong_diem = len(st.session_state.danh_sach_luu)
            
            if so_luong_diem >= 2:
                with st.expander("📏 Phân tích khoảng cách", expanded=False):
                    tong_khoang_cach = sum(
                        tinh_khoang_cach_haversine(
                            st.session_state.danh_sach_luu[i][COT_VI_DO], st.session_state.danh_sach_luu[i][COT_KINH_DO],
                            st.session_state.danh_sach_luu[i+1][COT_VI_DO], st.session_state.danh_sach_luu[i+1][COT_KINH_DO]
                        ) for i in range(so_luong_diem - 1)
                    )
                    st.info(f"Tổng chiều dài tuyến: **{tong_khoang_cach:.2f} km**")

            if so_luong_diem > 0:
                with st.expander(f"📍 Dữ liệu điểm ghim ({so_luong_diem})", expanded=False):
                    index_can_xoa = None
                    for idx, tram_luu in enumerate(st.session_state.danh_sach_luu):
                        col_cell_name, col_del_btn = st.columns([7, 3])
                        with col_cell_name:
                            st.markdown(f"<div style='font-size:12px; padding-top:5px;'>ID: {tram_luu[COT_CELL_ID]}</div>", unsafe_allow_html=True)
                        with col_del_btn:
                            if st.button("Hủy", key=f"del_{tram_luu[COT_CELL_ID]}_{idx}", use_container_width=True):
                                index_can_xoa = idx
                    
                    if index_can_xoa is not None:
                        st.session_state.danh_sach_luu.pop(index_can_xoa)
                        st.rerun()

                    if st.button("🗑️ Xóa toàn bộ", type="secondary", use_container_width=True):
                        st.session_state.danh_sach_luu.clear()
                        st.session_state.tram_hien_tai = None
                        st.rerun()

        # Thiết lập vị trí trung tâm bản đồ
        if st.session_state.tram_hien_tai is not None:
            vi_do_xem, kinh_do_xem, muc_zoom = float(st.session_state.tram_hien_tai[COT_VI_DO]), float(st.session_state.tram_hien_tai[COT_KINH_DO]), 16
        elif so_luong_diem > 0:
            vi_do_xem, kinh_do_xem, muc_zoom = float(st.session_state.danh_sach_luu[-1][COT_VI_DO]), float(st.session_state.danh_sach_luu[-1][COT_KINH_DO]), 14

        m = folium.Map(location=[vi_do_xem, kinh_do_xem], zoom_start=muc_zoom, control_scale=True)
        
        # Thêm các lớp bản đồ
        folium.TileLayer('https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}', attr='Google Satellite', name='Vệ tinh (Satellite)', overlay=False).add_to(m)
        folium.TileLayer('https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}', attr='Google Maps Street', name='Đường phố (Street)', overlay=False).add_to(m)
        folium.LayerControl().add_to(m)

        toa_do_vung = []

        # Hiển thị các trạm đã lưu
        for index, tram_luu in enumerate(st.session_state.danh_sach_luu):
            lat_l, lon_l = float(tram_luu[COT_VI_DO]), float(tram_luu[COT_KINH_DO])
            toa_do_vung.append([lat_l, lon_l])
            
            cgi_l = truy_xuat_du_lieu_cot(tram_luu, ['CGI', 'cgi'])
            addr_l = truy_xuat_du_lieu_cot(tram_luu, ['Địa chỉ', 'dia chi', 'Address'])
            cell_l = tram_luu[COT_CELL_ID]

            noi_dung_luu = f"""
            <div style='font-family: Arial, sans-serif; font-size: 13px; width: 220px; color: #333333; line-height: 1.4;'>
                <b>📌 ĐIỂM GHIM [{index+1}]</b><br>
                <b>Cell ID:</b> {cell_l}<br>
                <b>CGI:</b> {cgi_l}<br>
                <b>Tọa độ:</b> {lat_l}, {lon_l}<br>
                <b>Địa chỉ:</b> {addr_l}
            </div>
            """
            folium.Marker([lat_l, lon_l], popup=folium.Popup(noi_dung_luu, max_width=240), icon=folium.Icon(color='blue', icon='bookmark')).add_to(m)

        # Vẽ Line hoặc Polygon nếu có nhiều điểm
        if len(toa_do_vung) == 2:
            folium.PolyLine(locations=toa_do_vung, color="#0275d8", weight=4, opacity=0.8).add_to(m)
        elif len(toa_do_vung) >= 3:
            folium.Polygon(locations=toa_do_vung, color="#0275d8", weight=3, fill=True, fill_color="#0275d8", fill_opacity=0.15).add_to(m)

        # Hiển thị trạm đang truy vấn hiện tại
        if st.session_state.tram_hien_tai is not None:
            cgi_val = truy_xuat_du_lieu_cot(st.session_state.tram_hien_tai, ['CGI', 'cgi'])
            dia_chi_val = truy_xuat_du_lieu_cot(st.session_state.tram_hien_tai, ['Địa chỉ', 'dia chi', 'Address'])
            cell_val = st.session_state.tram_hien_tai[COT_CELL_ID]
            lat_val, lon_val = st.session_state.tram_hien_tai[COT_VI_DO], st.session_state.tram_hien_tai[COT_KINH_DO]

            noi_dung_label = f"""
            <div style='font-family: Arial, sans-serif; font-size: 13px; width: 220px; color: #333333; line-height: 1.4;'>
                <b style='color: #D9534F;'>🎯 THÔNG TIN TRẠM: {cell_val}</b><br>
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
            st.error(f"❌ Lỗi khởi tạo cơ sở dữ liệu: {e}")
