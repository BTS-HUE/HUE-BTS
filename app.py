import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import math
import re

# ==============================================================================
# 1. KIẾN TRÚC NỀN TẢNG & QUẢN LÝ PHÂN HỆ PHIÊN TRUY CẬP (SESSION MANAGEMENT)
# ==============================================================================
st.set_page_config(
    page_title="Hệ Thống Giám Sát & Định Vị TRẠM BTS", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# Khởi tạo thông tin cấu hình từ hệ thống quản trị bảo mật (Secrets Manager)
TOKEN_XAC_THUC = st.secrets["auth"]["token_xac_thuc"]
TAI_KHOAN_CHUAN = st.secrets["auth"]["tai_khoan_chuan"]
MAT_KHAU_CHUAN = st.secrets["auth"]["mat_khau_chuan"]
SHEET_ID = st.secrets["database"]["sheet_id"]

# Kiểm tra cơ chế định danh tự động qua URL Token và đồng bộ trạng thái phân hệ
if "logged_in" not in st.session_state:
    if st.query_params.get("auth_token") == TOKEN_XAC_THUC:
        st.session_state.logged_in = True
        st.query_params.clear()
    else:
        st.session_state.logged_in = False

st.session_state.setdefault("danh_sach_luu", [])
st.session_state.setdefault("tram_hien_tai", None)
st.session_state.setdefault("ds_gan_nhat", [])

# ==============================================================================
# 2. KHỞI TẠO LỚP ĐỊNH DẠNG GIAO DIỆN ĐÁP ỨNG NÂNG CAO (UI/UX STYLE Overrides)
# ==============================================================================
st.markdown(
    """
    <style>
    /* 2.1. TỐI ƯU KHÔNG GIAN: Loại bỏ các thành phần giao diện mặc định của nền tảng */
    [data-testid="stSidebarNav"], [data-testid="stSidebar"], section[data-testid="stSidebar"], 
    header, footer, #MainMenu, iframe[title="Manage app"], .stAppDeployButton, div[data-testid="stAppDeployButton"], footer + div {
        display: none !important; visibility: hidden !important; width: 0px !important; height: 0px !important;
    }
    .block-container { padding: 0.6rem 1rem 0rem 1rem !important; max-width: 100% !important; }
    .stFoliumStatic { margin-top: 0px !important; width: 100% !important; }
    .stFoliumStatic > iframe { width: 100% !important; border-radius: 12px !important; }

    /* TỐI ƯU KHUNG UPLOAD FILE: Thu nhỏ và ẩn giới hạn 200MB */
    [data-testid="stFileUploader"] section {
        padding: 8px !important;
        min-height: 40px !important;
        background-color: var(--secondary-background-color) !important;
    }
    [data-testid="stFileUploader"] small { display: none !important; }
    [data-testid="stFileUploadDropzone"] div { margin: 0px !important; padding: 2px !important; }

    /* 2.2. ĐỒNG BỘ PALETTE MÀU: Đảm bảo tương thích hiển thị đồng nhất giữa Light/Dark Mode */
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

    /* 2.3. CẤU TRÚC LỚP LƠ LỬNG (FLOATING PANEL) */
    div[data-testid="stHorizontalBlock"]:has(.stFoliumStatic) { position: relative !important; display: block !important; height: 730px !important; }
    div[data-testid="stHorizontalBlock"]:has(.stFoliumStatic) div[data-testid="column"]:nth-of-type(2) {
        position: absolute !important; top: 0 !important; left: 0 !important; width: 100% !important; height: 100% !important; z-index: 1 !important; padding: 0px !important;
    }
    div[data-testid="stHorizontalBlock"]:has(.stFoliumStatic) div[data-testid="column"]:nth-of-type(1) {
        position: absolute !important; top: 15px !important; left: 15px !important; width: 320px !important; z-index: 9999 !important; background: transparent !important; padding: 0px !important;
    }

    /* 2.4. ĐÁP ỨNG THIẾT BỊ DI ĐỘNG */
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
# 3. PHÂN HỆ THUẬT TOÁN KHÔNG GIAN VÀ XỬ LÝ CƠ SỞ DỮ LIỆU (CORE GEOGRAPHIC ENGINE)
# ==============================================================================
def tinh_khoang_cach_haversine(lat1, lon1, lat2, lon2):
    r_lat1, r_lon1, r_lat2, r_lon2 = map(math.radians, [float(lat1), float(lon1), float(lat2), float(lon2)])
    a = math.sin((r_lat2 - r_lat1) / 2)**2 + math.cos(r_lat1) * math.cos(r_lat2) * math.sin((r_lon2 - r_lon1) / 2)**2
    return 2 * math.asin(math.sqrt(a)) * 6371.0 

@st.cache_data(ttl=600) 
def tai_co_so_du_lieu():
    URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"
    data = pd.read_csv(URL, dtype=str)
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
# 4. PHÂN HỆ XÁC THỰC AN NINH & KIỂM SOÁT CỔNG TRUY CẬP (SECURITY GATEWAY)
# ==============================================================================
if not st.session_state.logged_in:
    st.markdown(
        """<style>
        .stApp, .stMarkdown, p, span, div, label { color: #FFFFFF !important; }
        input { color: #0F172A !important; background-color: #FFFFFF !important; -webkit-text-fill-color: #0F172A !important;}
        div[data-testid="stColumn"] { padding: 0px 4px !important; }
        
        /* Thu gọn tối đa khung báo lỗi: Nhỏ gọn, chữ mỏng */
        div[data-testid="stNotification"] { 
            padding: 6px 12px !important; 
            font-size: 12.5px !important; 
            border-radius: 6px !important;
            margin-top: 4px !important;
        }
        div[data-testid="stNotification"] div { line-height: 1.2 !important; }
        </style>""", 
        unsafe_allow_html=True
    )
    
    # Thiết kế thanh đăng nhập siêu gọn nằm tại góc trên bên phải màn hình
    col_space, col_login_1, col_login_2, col_btn = st.columns([5.5, 1.8, 1.8, 0.9])
    with col_login_1:
        tai_khoan_nhap = st.text_input("Tài khoản", value="", key="username_input", label_visibility="collapsed", placeholder="Tài khoản")
    with col_login_2:
        mat_khau_nhap = st.text_input("Mật khẩu", type="password", key="password_input", label_visibility="collapsed", placeholder="Mật khẩu")
    with col_btn:
        nut_dang_nhap = st.button("Đăng nhập", type="primary", use_container_width=True)
        
    # Xử lý logic kiểm tra thông tin
    if nut_dang_nhap:
        if tai_khoan_nhap == TAI_KHOAN_CHUAN and mat_khau_nhap == MAT_KHAU_CHUAN:
            st.session_state.logged_in = True
            st.toast("🔑 Xác thực thành công!")
            st.rerun()
        else:
            st.session_state["loi_dang_nhap"] = True

    # Định vị dải thông báo lỗi: Gom gọn vào phạm vi bên phải dưới chân cụm đăng nhập
    if st.session_state.get("loi_dang_nhap", False):
        col_space_err, col_err = st.columns([5.5, 4.5])
        with col_err:
            st.error("❌ Tài khoản hoặc mật khẩu không chính xác.")
            st.session_state["loi_dang_nhap"] = False

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
            <p style='font-size: 15px; opacity: 0.85; margin: 0;'>Vui lòng cung cấp thông định danh tại góc phải màn hình để truy cập cơ sở dữ liệu hạ tầng.</p>
        </div>
        """, 
        unsafe_allow_html=True
    )

# ==============================================================================
# 5. KHÔNG GIAN ĐIỀU HÀNH TRỰC QUAN & HỆ THỐNG THÔNG TIN ĐỊA LÝ (GIS MASTER MODULE)
# ==============================================================================
else:
    col_main_title, col_logout_layout = st.columns([8.5, 1.5])
    with col_main_title:
        st.markdown(
            f"<h2 style='margin:0; color: var(--text-color); font-weight:700; font-size:22px; text-shadow: none;'>"
            f"🛰️ TRUNG TÂM GIÁM SÁT VÀ ĐỊNH VỊ TRẠM BTS <span style='font-size:12px; color:#3B82F6; background:rgba(59,130,246,0.15); padding:3px 8px; border-radius:6px; margin-left:10px;'>☁️ LIVE CLOUD</span>"
            f"</h2>", 
            unsafe_allow_html=True
        )
    with col_logout_layout:
        if st.button("🚪 ĐĂNG XUẤT", use_container_width=True, type="secondary"):
            st.query_params.clear()
            st.session_state.logged_in = False
            st.session_state.danh_sach_luu.clear()
            st.session_state.tram_hien_tai = None
            st.session_state.ds_gan_nhat.clear()
            st.rerun()

    st.markdown("<hr style='margin-top: 5px; margin-bottom: 10px; border-color: var(--border-color);'>", unsafe_allow_html=True)

    col_left_search, col_right_map = st.columns([2.4, 7.6])

    try:
        df = tai_co_so_du_lieu()
        
        COT_MCC, COT_MNC, COT_LAC_TAC, COT_CELL_ID, COT_VI_DO, COT_KINH_DO = 'MCC', 'MNC', 'LAC/TAC', 'CELL ID', 'Latitude', 'Longitude'
        vi_do_xem, kinh_do_xem, muc_zoom = 16.047079, 108.206230, 5

        with col_left_search:
            with st.expander("🔍 TÌM KIẾM TRẠM", expanded=True):
                with st.form("form_tra_cuu", clear_on_submit=True):
                    # --- Hàng 1: MCC và MNC ---
                    col_f1, col_f2 = st.columns(2)
                    with col_f1:
                        f1 = st.text_input("Mã Quốc gia:", key="mcc_in", placeholder="MCC").strip()
                    with col_f2:
                        f2 = st.text_input("Mã Mạng:", key="mnc_in", placeholder="MNC").strip()
                    
                    # --- Hàng 2: LAC/TAC và Cell ID ---
                    col_f3, col_f4 = st.columns(2)
                    with col_f3:
                        f3 = st.text_input("Mã Vùng:", key="lac_in", placeholder="LAC/TAC").strip()
                    with col_f4:
                        f4 = st.text_input("Cell ID:", key="cell_in", placeholder="Cell ID").strip()
                    
                    if f2.isdigit() and len(f2) == 1: f2 = f2.zfill(2)
                    st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
                    nut_tim_kiem = st.form_submit_button("🔍 Tìm Kiếm", use_container_width=True)
            
            st.markdown("<script>window.parent.document.querySelectorAll('input').forEach(i => i.setAttribute('autocomplete', 'one-time-code'));</script>", unsafe_allow_html=True)

            if nut_tim_kiem:
                if all([f1, f2, f3, f4]):
                    ket_qua = df[(df[COT_MCC] == f1) & (df[COT_MNC] == f2) & (df[COT_LAC_TAC] == f3) & (df[COT_CELL_ID] == f4)]
                    
                    if not ket_qua.empty:
                        st.session_state.tram_hien_tai = ket_qua.iloc[0]
                        st.session_state.ds_gan_nhat = [] 
                        st.success(f"🎯 Đã phát hiện ID: {f4}")
                    else:
                        st.session_state.tram_hien_tai = None
                        st.session_state.ds_gan_nhat = []
                        st.warning("⚠️ Không tìm thấy trạm!")
                else:
                    st.error("❌ Yêu cầu nhập đầy đủ tham số!")

            # XỬ LÝ QUY TRÌNH NGHIỆP VỤ KHI CÓ TRẠM ĐANG CHỌN TRUY VẤN
            if st.session_state.tram_hien_tai is not None:
                cell_id_hien_tai = st.session_state.tram_hien_tai[COT_CELL_ID]
                
                if st.button("📌 Gắn thẻ tọa độ trạm này", type="primary", use_container_width=True):
                    if len(st.session_state.danh_sach_luu) >= 50: 
                        st.toast("❌ Đã đạt giới hạn tối đa điểm ghim!")
                    elif not any(item[COT_CELL_ID] == cell_id_hien_tai for item in st.session_state.danh_sach_luu):
                        st.session_state.danh_sach_luu.append(st.session_state.tram_hien_tai)
                        st.toast(f"Đã lưu tọa độ trạm {cell_id_hien_tai}")
                    else:
                        st.toast("Cảnh báo: Trạm này đã được ghim trước đó.")
                
                if st.button("📡 Tìm các trạm gần nhất", type="secondary", use_container_width=True):
                    lat_curr = float(st.session_state.tram_hien_tai[COT_VI_DO])
                    lon_curr = float(st.session_state.tram_hien_tai[COT_KINH_DO])
                    
                    df_others = df[df[COT_CELL_ID] != cell_id_hien_tai].copy()
                    if not df_others.empty:
                        df_others['KhoangCach'] = df_others.apply(
                            lambda r: tinh_khoang_cach_haversine(lat_curr, lon_curr, r[COT_VI_DO], r[COT_KINH_DO]), axis=1
                        )
                        top_gan_nhat = df_others.sort_values(by='KhoangCach').head(5)
                        st.session_state.ds_gan_nhat = top_gan_nhat.to_dict(orient='records')
                        st.toast("🎯 Đã cập nhật danh sách trạm gần nhất!")
                    else:
                        st.session_state.ds_gan_nhat = []
                        st.toast("⚠️ Không tìm thấy trạm nào khác trong CSDL.")
            
            # TRỰC QUAN HÓA KẾT QUẢ PHÂN TÍCH KHÔNG GIAN
            if st.session_state.tram_hien_tai is not None and st.session_state.ds_gan_nhat:
                with st.expander("📡 TRẠM BTS GẦN NHẤT", expanded=True):
                    for idx, tram_near in enumerate(st.session_state.ds_gan_nhat):
                        kc_gan = float(tram_near['KhoangCach'])
                        addr_near = truy_xuat_du_lieu_cot(pd.Series(tram_near), ['Địa chỉ', 'dia chi', 'Address'])
                        
                        col_near_info, col_near_pin = st.columns([7.2, 2.8])
                        with col_near_info:
                            st.markdown(f"**{idx+1}. ID: {tram_near[COT_CELL_ID]}** (`{kc_gan:.2f} km`)", unsafe_allow_html=True)
                            st.markdown(f"<div style='font-size:11px; opacity:0.8;'>Đ/C: {addr_near}</div>", unsafe_allow_html=True)
                        with col_near_pin:
                            if st.button("Ghim", key=f"pin_near_{tram_near[COT_CELL_ID]}_{idx}", use_container_width=True):
                                if len(st.session_state.danh_sach_luu) >= 50:
                                    st.toast("❌ Đã đạt giới hạn tối đa điểm ghim!")
                                elif not any(item[COT_CELL_ID] == tram_near[COT_CELL_ID] for item in st.session_state.danh_sach_luu):
                                    st.session_state.danh_sach_luu.append(pd.Series(tram_near))
                                    st.toast(f"Đã ghim trạm {tram_near[COT_CELL_ID]}")
                                    st.rerun()
                                else:
                                    st.toast("Trạm này đã ghim trước đó.")
                        st.markdown("<hr style='margin:4px 0px; border-color:var(--border-color);'>", unsafe_allow_html=True)

            so_luong_diem = len(st.session_state.danh_sach_luu)
            
            # TÍNH TOÁN CÁC CHỈ SỐ HÌNH HỌC HẠ TẦNG
            if so_luong_diem >= 2:
                with st.expander("📏 KHOẢNG CÁCH / LỘ TRÌNH", expanded=False):
                    tong_khoang_cach = 0.0
                    for i in range(so_luong_diem - 1):
                        p1 = st.session_state.danh_sach_luu[i]
                        p2 = st.session_state.danh_sach_luu[i+1]
                        
                        kc_chi_tiet = tinh_khoang_cach_haversine(
                            p1[COT_VI_DO], p1[COT_KINH_DO],
                            p2[COT_VI_DO], p2[COT_KINH_DO]
                        )
                        tong_khoang_cach += kc_chi_tiet
                        
                        st.markdown(
                            f"<div style='font-size: 13px; margin-bottom: 6px;'>"
                            f"🔹 <b>Trạm {p1[COT_CELL_ID]}</b> ➡️ <b>Trạm {p2[COT_CELL_ID]}</b>: <code>{kc_chi_tiet:.2f} km</code>"
                            f"</div>", 
                            unsafe_allow_html=True
                        )
                    
                    st.
