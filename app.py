import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import math

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

    /* 2.3. CẤU TRÚC LỚP LƠ LỬNG (FLOATING PANEL): Định hình khung điều hướng không gian GIS Map */
    div[data-testid="stHorizontalBlock"]:has(.stFoliumStatic) { position: relative !important; display: block !important; height: 730px !important; }
    div[data-testid="stHorizontalBlock"]:has(.stFoliumStatic) div[data-testid="column"]:nth-of-type(2) {
        position: absolute !important; top: 0 !important; left: 0 !important; width: 100% !important; height: 100% !important; z-index: 1 !important; padding: 0px !important;
    }
    div[data-testid="stHorizontalBlock"]:has(.stFoliumStatic) div[data-testid="column"]:nth-of-type(1) {
        position: absolute !important; top: 15px !important; left: 15px !important; width: 320px !important; z-index: 9999 !important; background: transparent !important; padding: 0px !important;
    }

    /* 2.4. ĐÁP ỨNG THIẾT BỊ DI ĐỘNG (MOBILE RESPONSIVE) - FIX TRÀN KHUNG HOÀN HẢO */
    @media (max-width: 768px) {
        div[data-testid="stHorizontalBlock"]:has(.stFoliumStatic) div[data-testid="column"]:nth-of-type(1) {
            top: 10px !important; left: 10px !important; width: 230px !important; max-width: 85% !important;
        }
        .stExpander summary p { font-size: 13px !important; }
        .stExpander label p { 
            font-size: 11px !important; 
            white-space: nowrap !important; 
            overflow: hidden !important; 
            text-overflow: ellipsis !important; 
        }
        div[data-testid="stForm"] button[data-testid="baseButton-secondaryFormSubmit"] { font-size: 13px !important; padding: 4px !important; }
        .stExpander { border-radius: 10px !important; box-shadow: 0px 6px 20px rgba(0, 0, 0, 0.3) !important; backdrop-filter: blur(8px) !important; }
        
        /* Khóa chặt lưới 2 cột song song cho các hàng nhập liệu, ngăn việc rớt dòng tự động */
        div[data-testid="stForm"] div[data-testid="stHorizontalBlock"] {
            display: grid !important;
            grid-template-columns: 1fr 1fr !important;
            gap: 6px !important;
            width: 100% !important;
            box-sizing: border-box !important;
            margin-bottom: 2px !important;
        }
        /* Đồng bộ hóa khung chứa cột con */
        div[data-testid="stForm"] div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
            width: 100% !important;
            max-width: 100% !important;
            min-width: 0 !important;
            padding: 0 !important;
        }
        /* Ép chuẩn kích thước ô nhập liệu thu mình gọn gàng */
        div[data-testid="stForm"] input {
            font-size: 12px !important;
            padding: 4px 6px !important;
            width: 100% !important;
            box-sizing: border-box !important;
            height: 32px !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ==============================================================================
# 3. PHÂN HỆ THUẬT TOÁN KHÔNG GIAN VÀ XỬ XÝ CƠ SỞ DỮ LIỆU (CORE GEOGRAPHIC ENGINE)
# ==============================================================================
def tinh_khoang_cach_haversine(lat1, lon1, lat2, lon2):
    """Tính khoảng cách cung lớn giữa 2 tọa độ địa lý dựa trên mô hình hình cầu (Đơn vị: km)"""
    r_lat1, r_lon1, r_lat2, r_lon2 = map(math.radians, [float(lat1), float(lon1), float(lat2), float(lon2)])
    a = math.sin((r_lat2 - r_lat1) / 2)**2 + math.cos(r_lat1) * math.cos(r_lat2) * math.sin((r_lon2 - r_lon1) / 2)**2
    return 2 * math.asin(math.sqrt(a)) * 6371.0 

@st.cache_data(ttl=600) 
def tai_co_so_du_lieu():
    """Đọc, chuẩn hóa định dạng phân đoạn dữ liệu và ghi bộ nhớ đệm luồng thông tin từ Cloud Sheet"""
    URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"
    data = pd.read_csv(URL, dtype=str)
    data.columns = data.columns.str.strip()
    for col in data.columns:
        data[col] = data[col].fillna("").astype(str).str.strip()
            
    if 'MNC' in data.columns:
        data['MNC'] = data['MNC'].apply(lambda x: x.zfill(2) if x.isdigit() and len(x) == 1 else x)
    return data

def truy_xuat_du_lieu_cot(row, danh_sach_ten_goi):
    """Ánh xạ linh hoạt từ dữ liệu dòng để truy xuất thuộc tính không phụ thuộc chữ hoa/thường"""
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
        """<style>.stApp, .stMarkdown, p, span, div, label { color: #FFFFFF !important; }
        input { color: #0F172A !important; background-color: #FFFFFF !important; -webkit-text-fill-color: #0F172A !important;}</style>""", 
        unsafe_allow_html=True
    )
    
    _, col_login_1, col_login_2 = st.columns([7.0, 1.5, 1.5])
    with col_login_1:
        tai_khoan_nhap = st.text_input("Tài khoản:", value="", key="username_input")
    with col_login_2:
        mat_khau_nhap = st.text_input("Mật khẩu:", type="password", key="password_input")
        
    if tai_khoan_nhap == TAI_KHOAN_CHUAN and mat_khau_nhap == MAT_KHAU_CHUAN:
        st.session_state.logged_in = True
        st.rerun()

    st.markdown("<script>window.parent.document.querySelectorAll('input').forEach(i => i.setAttribute('autocomplete', 'new-password'));</script>", unsafe_allow_html=True)

    url_hinh_nen = "https://raw.githubusercontent.com/HUE-06/Doi1/refs/heads/main/%C4%90%E1%BB%99i%201.png"
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
# 5. KHÔNG GIAN ĐIỀU HÀNH TRỰC QUAN & HỆ THỐNG THÔNG TIN ĐỊA LÝ (GIS MASTER MODULE)
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
                    # --- Hàng số 1: Quốc gia (MCC) & Mạng di động (MNC) ---
                    col_f1, col_f2 = st.columns(2)
                    with col_f1:
                        f1 = st.text_input("Mã Quốc gia:", key="mcc_in", placeholder="MCC").strip()
                    with col_f2:
                        f2 = st.text_input("Mã Mạng:", key="mnc_in", placeholder="MNC").strip()
                    
                    # --- Hàng số 2: Vùng phủ sóng (LAC/TAC) & ID Trạm phát (Cell ID) ---
                    col_f3, col_f4 = st.columns(2)
                    with col_f3:
                        f3 = st.text_input("Mã Vùng:", key="lac_in", placeholder="LAC/TAC").strip()
                    with col_f4:
                        f4 = st.text_input("Cell ID:", key="cell_in", placeholder="Cell ID").strip()
                    
                    if f2.isdigit() and len(f2) == 1: f2 = f2.zfill(2)
                    st.markdown("<div style='margin-top: 6px;'></div>", unsafe_allow_html=True)
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

            # 5.1. XỬ LÝ QUY TRÌNH NGHIỆP VỤ KHI CÓ TRẠM ĐANG CHỌN TRUY VẤN
            if st.session_state.tram_hien_tai is not None:
                cell_id_hien_tai = st.session_state.tram_hien_tai[COT_CELL_ID]
                
                if st.button("📌 Gắn thẻ tọa độ trạm này", type="primary", use_container_width=True):
                    if len(st.session_state.danh_sach_luu) >= 10:
                        st.toast("❌ Đã đạt giới hạn tối đa 10 điểm ghim!")
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
            
            # 5.2. TRỰC QUAN HÓA KẾT QUẢ PHÂN TÍCH KHÔNG GIAN
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
                                if len(st.session_state.danh_sach_luu) >= 10:
                                    st.toast("❌ Đã đạt giới hạn tối đa 10 điểm ghim!")
                                elif not any(item[COT_CELL_ID] == tram_near[COT_CELL_ID] for item in st.session_state.danh_sach_luu):
                                    st.session_state.danh_sach_luu.append(pd.Series(tram_near))
                                    st.toast(f"Đã ghim trạm {tram_near[COT_CELL_ID]}")
                                    st.rerun()
                                else:
                                    st.toast("Trạm này đã ghim trước đó.")
                        st.markdown("<hr style='margin:4px 0px; border-color:var(--border-color);'>", unsafe_allow_html=True)

            so_luong_diem = len(st.session_state.danh_sach_luu)
            
            # 5.3. TÍNH TOÁN CÁC CHỈ SỐ HÌNH HỌC HẠ TẦNG (KHOẢNG CÁCH NỐI TIẾP)
            if so_luong_diem >= 2:
                with st.expander("📏 KHOẢNG CÁCH", expanded=False):
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
                    
                    st.info(f"Tổng chiều dài tuyến (theo thứ tự ghim): **{tong_khoang_cach:.2f} km**")

            # 5.4. ĐIỀU KHIỂN DANH SÁCH TOẠ ĐỘ GHIM LƯU TRỮ
            if so_luong_diem > 0:
                with st.expander(f"📍 Dữ liệu điểm ghim ({so_luong_diem}/10)", expanded=False):
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
                        st.session_state.ds_gan_nhat.clear()
                        st.rerun()

        # 5.5. KHỞI TẠO VÀ PHÂN LỚP ĐỒ HỌA BẢN ĐỒ LỚN (MAP CANVAS LAYERS)
        if st.session_state.tram_hien_tai is not None:
            vi_do_xem, kinh_do_xem, muc_zoom = float(st.session_state.tram_hien_tai[COT_VI_DO]), float(st.session_state.tram_hien_tai[COT_KINH_DO]), 14
        elif so_luong_diem > 0:
            vi_do_xem, kinh_do_xem, muc_zoom = float(st.session_state.danh_sach_luu[-1][COT_VI_DO]), float(st.session_state.danh_sach_luu[-1][COT_KINH_DO]), 14

        m = folium.Map(location=[vi_do_xem, kinh_do_xem], zoom_start=muc_zoom, control_scale=True)
        
        folium.TileLayer('https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}', attr='Google Satellite', name='Vệ tinh (Satellite)', overlay=False).add_to(m)
        folium.TileLayer('https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}', attr='Google Maps Street', name='Đường phố (Street)', overlay=False).add_to(m)
        folium.LayerControl().add_to(m)

        toa_do_vung = []

        # 5.6. VẼ CÁC THỰC THỂ LƯU TRỮ LÊN PHÂN LỚP ĐỊA LÝ VÀ VẼ ĐƯỜNG LIÊN KẾT
        for index, tram_luu in enumerate(st.session_state.danh_sach_luu):
            lat_l, lon_l = float(tram_luu[COT_VI_DO]), float(tram_luu[COT_KINH_DO])
            toa_do_vung.append([lat_l, lon_l])
            
            cgi_l = truy_xuat_du_lieu_cot(tram_luu, ['CGI', 'cgi'])
            addr_l = truy_xuat_du_lieu_cot(tram_luu, ['Địa chỉ', 'dia chi', 'Address'])
            cell_l = tram_luu[COT_CELL_ID]

            noi_dung_luu = f"""
            <div style='font-family: Arial, sans-serif; font-size: 13px; width: 220px; color: #333333; line-height: 1.5;'>
                <b style='color: #0275d8;'>📌 THÔNG TIN TRẠM ĐÃ GHIM [{index+1}]</b><br>
                <b>Cell ID:</b> {cell_l}<br>
                <b>CGI:</b> {cgi_l}<br>
                <b>Tọa độ:</b> {lat_l}, {lon_l}<br>
                <b>Địa chỉ:</b> {addr_l}
            </div>
            """
            folium.Marker([lat_l, lon_l], popup=folium.Popup(noi_dung_luu, max_width=240), icon=folium.Icon(color='blue', icon='bookmark')).add_to(m)

        # Luôn vẽ đường thẳng (PolyLine) nối chuỗi các điểm đã ghim
        if len(toa_do_vung) >= 2:
            folium.PolyLine(locations=toa_do_vung, color="#0275d8", weight=4, opacity=0.8).add_to(m)

        # 5.7. THIẾT LẬP ĐỒ HỌA MỤC TIÊU TRA CỨU VÀ ĐỒ THỊ LIÊN KẾT LÂN CẬN
        if st.session_state.tram_hien_tai is not None:
            cgi_val = truy_xuat_du_lieu_cot(st.session_state.tram_hien_tai, ['CGI', 'cgi'])
            dia_chi_val = truy_xuat_du_lieu_cot(st.session_state.tram_hien_tai, ['Địa chỉ', 'dia chi', 'Address'])
            cell_val = st.session_state.tram_hien_tai[COT_CELL_ID]
            lat_val, lon_val = float(st.session_state.tram_hien_tai[COT_VI_DO]), float(st.session_state.tram_hien_tai[COT_KINH_DO])

            noi_dung_label = f"""
            <div style='font-family: Arial, sans-serif; font-size: 13px; width: 220px; color: #333333; line-height: 1.5;'>
                <b style='color: #D9534F;'>🎯 THÔNG TIN TRẠM BTS: {cell_val}</b><br>
                <b>CGI:</b> {cgi_val}<br>
                <b>Tọa độ:</b> {lat_val}, {lon_val}<br>
                <b>Địa chỉ:</b> {dia_chi_val}
            </div>
            """
            folium.Marker([lat_val, lon_val], popup=folium.Popup(noi_dung_label, max_width=240, show=True), icon=folium.Icon(color='red', icon='info-sign')).add_to(m)

            for tram_near in st.session_state.ds_gan_nhat:
                lat_n, lon_n = float(tram_near[COT_VI_DO]), float(tram_near[COT_KINH_DO])
                kc_n = float(tram_near['KhoangCach'])
                cell_n = tram_near[COT_CELL_ID]
                cgi_n = truy_xuat_du_lieu_cot(pd.Series(tram_near), ['CGI', 'cgi'])
                addr_n = truy_xuat_du_lieu_cot(pd.Series(tram_near), ['Địa chỉ', 'dia chi', 'Address'])
                
                noi_dung_near = f"""
                <div style='font-family: Arial, sans-serif; font-size: 13px; width: 220px; color: #333333; line-height: 1.5;'>
                    <b style='color: #28a745;'>📡 THÔNG TIN TRẠM LÂN CẬN</b><br>
                    <b>Cell ID:</b> {cell_n}<br>
                    <b>Khoảng cách:</b> {kc_n:.2f} km<br>
                    <b>CGI:</b> {cgi_n}<br>
                    <b>Địa chỉ:</b> {addr_n}
                </div>
                """
                folium.Marker(
                    [lat_n, lon_n], 
                    popup=folium.Popup(noi_dung_near, max_width=240), 
                    icon=folium.Icon(color='green', icon='broadcast-tower', prefix='fa')
                ).add_to(m)
                folium.PolyLine(locations=[[lat_val, lon_val], [lat_n, lon_n]], color="green", weight=1.5, opacity=0.6, dash_array='5, 5').add_to(m)

        with col_right_map:
            folium_static(m, height=730, width=None)

    except Exception as e:
        with col_right_map:
            st.error(f"❌ Lỗi cấu trúc hoặc xử lý cơ sở dữ liệu: {e}")
