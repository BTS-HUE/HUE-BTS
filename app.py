import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
# 📦 Thư viện quản lý cookie trình duyệt
from streamlit_cookies_controller import CookieController

# Khởi tạo bộ điều khiển Cookie
cookies = CookieController()

# ==============================================================================
# 1. CẤU HÌNH GIAO DIỆN & STYLE BAN ĐẦU
# ==============================================================================
st.set_page_config(page_title="Hệ Thống Trạm Phát Sóng", layout="wide", initial_sidebar_state="collapsed")

# Đọc trạng thái đăng nhập từ Cookie trình duyệt trước để tránh bị mất khi F5
auth_cookie = cookies.get("bts_logged_in")

if "logged_in" not in st.session_state:
    # Nếu có cookie hợp lệ, tự động đăng nhập luôn
    if auth_cookie == "authenticated_secure_token_tuan":
        st.session_state.logged_in = True
    else:
        st.session_state.logged_in = False

if "danh_sach_luu" not in st.session_state:
    st.session_state.danh_sach_luu = []
if "tram_hien_tai" not in st.session_state:
    st.session_state.tram_hien_tai = None

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
        transform: translateX(-50%) !important;
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
        # 🔑 LƯU VÀO COOKIE: Token bảo mật lưu trên trình duyệt người dùng (Hết hạn sau 1 ngày)
        cookies.set("bts_logged_in", "authenticated_secure_token_tuan", max_age=3600)
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
            st.session_state.danh_sach_luu = []
            st.session_state.tram_hien_tai = None
            # 🗑️ XÓA COOKIE: Khi đăng xuất, xóa cookie để ngăn tự động đăng nhập lại trái phép
            cookies.remove("bts_logged_in")
            st.rerun()

    st.markdown("---")

    # Chia layout cố định
    col_left_search, col_right_map = st.columns([2.3, 7.7])

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

    try:
        df = tai_du_lieu()
        
        COT_MCC = 'MCC'
        COT_MNC = 'MNC'
        COT_LAC_TAC = 'LAC/TAC'
        COT_CELL_ID = 'CELL ID'
        COT_VI_DO = 'Latitude'
        COT_KINH_DO = 'Longitude'

        vi_do_xem, kinh_do_xem, muc_zoom = 16.047079, 108.206230, 5

        # KHƯ VỰC NHẬP LIỆU VÀ NÚT BẤM (CỘT TRÁI)
        with col_left_search:
            with st.form("form_tra_cuu"):
                st.markdown("### 🔍 Thông Số Tra Cứu")
                f1 = st.text_input("1. Số MCC:", key="mcc_in").strip()
                f2 = st.text_input("2. Số MNC:", key="mnc_in").strip()
                f3 = st.text_input("3. Số LAC/TAC:", key="lac_in").strip()
                f4 = st.text_input("4. Số CELL ID:", key="cell_in").strip()
                
                if f2.isdigit() and len(f2) == 1:
                    f2 = f2.zfill(2)
                
                nut_tim_kiem = st.form_submit_button("🔍 Tìm kiếm trạm", use_container_width=True)
            
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
                        st.success(f"✅ Tìm thấy CELL ID: {f4}")
                    else:
                        st.session_state.tram_hien_tai = None
                        st.warning("⚠️ Không tìm thấy trạm!")
                else:
                    st.error("❌ Vui lòng nhập đủ 4 thông số!")

            # Xử lý Lưu điểm
            if st.session_state.tram_hien_tai is not None:
                cell_id_hien_tai = st.session_state.tram_hien_tai[COT_CELL_ID]
                if st.button(f"📌 Lưu điểm CELL ID: {cell_id_hien_tai}", type="primary", use_container_width=True):
                    da_ton_tai = any(item[COT_CELL_ID] == cell_id_hien_tai for item in st.session_state.danh_sach_luu)
                    if not da_ton_tai:
                        st.session_state.danh_sach_luu.append(st.session_state.tram_hien_tai)
                        st.toast(f"Đã lưu trạm {cell_id_hien_tai}!")
                    else:
                        st.toast("Trạm này đã được lưu trước đó!")
            
            # QUẢN LÝ VÀ XÓA TỪNG ĐIỂM ĐÃ LƯU
            if len(st.session_state.danh_sach_luu) > 0:
                st.markdown("---")
                st.markdown(f"### 📍 Điểm Đã Lưu ({len(st.session_state.danh_sach_luu)})")
                
                index_can_xoa = None
                for idx, tram_luu in enumerate(st.session_state.danh_sach_luu):
                    col_cell_name, col_del_btn = st.columns([7, 3])
                    with col_cell_name:
                        st.write(f"🔹 **ID: {tram_luu[COT_CELL_ID]}**")
                    with col_del_btn:
                        if st.button("🗑️ Xóa", key=f"del_{tram_luu[COT_CELL_ID]}_{idx}", use_container_width=True):
                            index_can_xoa = idx
                
                if index_can_xoa is not None:
                    tram_bi_xoa = st.session_state.danh_sach_luu.pop(index_can_xoa)
                    st.toast(f"❌ Đã xóa CELL ID: {tram_bi_xoa[COT_CELL_ID]}")
                    st.rerun()

                st.write("")
                if st.button("🗑️ Xóa tất cả điểm lưu", type="secondary", use_container_width=True):
                    st.session_state.danh_sach_luu = []
                    st.session_state.tram_hien_tai = None
                    st.rerun()

        # Định vị góc nhìn bản đồ
        if st.session_state.tram_hien_tai is not None:
            vi_do_xem = float(st.session_state.tram_hien_tai[COT_VI_DO])
            kinh_do_xem = float(st.session_state.tram_hien_tai[COT_KINH_DO])
            muc_zoom = 16

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

        # 🔵 VẼ CÁC ĐIỂM ĐÃ ĐƯỢC BẤM LƯU
        for index, tram_luu in enumerate(st.session_state.danh_sach_luu):
            lat_l = float(tram_luu[COT_VI_DO])
            lon_l = float(tram_luu[COT_KINH_DO])
            cgi_l = lay_thong_tin_cot(tram_luu, ['CGI', 'cgi'])
            addr_l = lay_thong_tin_cot(tram_luu, ['Địa chỉ', 'dia chi', 'địa chỉ', 'Địa Chỉ', 'Address', 'address'])
            note_l = lay_thong_tin_cot(tram_luu, ['Ghi chú', 'ghi chu', 'Note'])
            cell_l = tram_luu[COT_CELL_ID]

            noi_dung_luu = f"""
            <div style='font-family: Arial, sans-serif; font-size: 13px; width: 240px; color: #333333; line-height: 1.5;'>
                <h4 style='margin: 0 0 6px 0; color: #0275d8; border-bottom: 1px solid #eeeeee; padding-bottom: 4px; text-align: center;'>📌 ĐIỂM ĐÃ LƯU ({index+1})</h4>
                <b>CELL ID:</b> {cell_l}<br>
                <b>CGI:</b> {cgi_l}<br>
                <b>Latitude:</b> {lat_l}<br>
                <b>Longitude:</b> {lon_l}<br>
                <b>Địa chỉ:</b> {addr_l}<br>
                <b>Ghi chú:</b> {note_l}
            </div>
            """
            folium.Marker(
                [lat_l, lon_l],
                tooltip=folium.Tooltip(noi_dung_luu, permanent=True, direction="top", sticky=False, offset=(0, -45)),
                icon=folium.Icon(color='blue', icon='bookmark')
            ).add_to(m)

        # 🔴 VẼ ĐIỂM ĐANG TÌM KIẾM HIỆN TẠI
        if st.session_state.tram_hien_tai is not None:
            cgi_val = lay_thong_tin_cot(st.session_state.tram_hien_tai, ['CGI', 'cgi'])
            dia_chi_val = lay_thong_tin_cot(st.session_state.tram_hien_tai, ['Địa chỉ', 'dia chi', 'địa chỉ', 'Địa Chỉ', 'Address', 'address'])
            ghi_chu_val = lay_thong_tin_cot(st.session_state.tram_hien_tai, ['Ghi chú', 'ghi chu', 'Note'])
            cell_val = st.session_state.tram_hien_tai[COT_CELL_ID]

            noi_dung_label = f"""
            <div style='font-family: Arial, sans-serif; font-size: 13px; width: 240px; color: #333333; line-height: 1.5;'>
                <h4 style='margin: 0 0 6px 0; color: #d9534f; border-bottom: 1px solid #eeeeee; padding-bottom: 4px; text-align: center;'>📍 KẾT QUẢ TÌM KIẾM</h4>
                <b>CELL ID:</b> {cell_val}<br>
                <b>CGI:</b> {cgi_val}<br>
                <b>Latitude:</b> {vi_do_xem}<br>
                <b>Longitude:</b> {kinh_do_xem}<br>
                <b>Địa chỉ:</b> {dia_chi_val}<br>
                <b>Ghi chú:</b> {ghi_chu_val}
            </div>
            """
            folium.Marker(
                [vi_do_xem, kinh_do_xem],
                tooltip=folium.Tooltip(noi_dung_label, permanent=True, direction="top", sticky=False, offset=(0, -45)),
                icon=folium.Icon(color='red', icon='info-sign')
            ).add_to(m)

        with col_right_map:
            folium_static(m, height=760, width=None)

    except Exception as e:
        with col_right_map:
            st.error(f"❌ Không thể tải cơ sở dữ liệu trạm phát sóng. Chi tiết lỗi: {e}")
