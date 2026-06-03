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

TOKEN_XAC_THUC = "authenticated_secure_token_tuan"
TAI_KHOAN_CHUAN = "admin"
MAT_KHAU_CHUAN = "tuan"

# Đồng bộ trạng thái đăng nhập giữa URL và Session State để chống lỗi F5
if "logged_in" not in st.session_state:
    if st.query_params.get("auth_token") == TOKEN_XAC_THUC:
        st.session_state.logged_in = True
    else:
        st.session_state.logged_in = False

# Khởi tạo bộ nhớ tạm cho phiên làm việc
if "danh_sach_luu" not in st.session_state:
    st.session_state.danh_sach_luu = []
if "tram_hien_tai" not in st.session_state:
    st.session_state.tram_hien_tai = None

# Giao diện CSS tùy biến (Ẩn Sidebar, Header và căn chỉnh kích thước nút bấm)
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
    
    /* Tối ưu khoảng cách và kích thước nút bấm */
    div.stButton > button {
        border-radius: 6px !important;
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
    tap_ten_goi = set(x.lower() for x in danh_sach_ten_goi)
    for k in row.index:
        if str(k).lower().strip() in tap_ten_goi:
            return row[k]
    return "Không có dữ liệu"

# ==============================================================================
# 3. PHÂN HỆ KHÓA XÁC THỰC TRUY CẬP (LOGIN)
# ==============================================================================
if not st.session_state.logged_in:
    _, col_login_1, col_login_2 = st.columns([7.0, 1.5, 1.5])

    with col_login_1:
        tai_khoan_nhap = st.text_input("Tài khoản hệ thống:", value="", key="username_input")

    with col_login_2:
        mat_khau_nhap = st.text_input("Mật khẩu truy cập:", type="password", key="password_input")
        
    if tai_khoan_nhap == TAI_KHOAN_CHUAN and mat_khau_nhap == MAT_KHAU_CHUAN:
        st.session_state.logged_in = True
        st.query_params.auth_token = TOKEN_XAC_THUC
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
    if st.query_params.get("auth_token") != TOKEN_XAC_THUC:
        st.query_params.auth_token = TOKEN_XAC_THUC

    # Định hình thanh tiêu đề chính và nút Đăng xuất có độ rộng vừa phải ở góc phải
    col_main_title, col_logout_layout = st.columns([8.8, 1.2])
    with col_main_title:
        st.markdown(
            "<h2 style='margin:0; color:#1E3A8A; font-weight:700; font-size:26px;'>"
            "🛰️ TRUNG TÂM GIÁM SÁT VÀ ĐỊNH VỊ TRẠM PHÁT SÓNG BTS"
            "</h2>", 
            unsafe_allow_html=True
        )
    with col_logout_layout:
        st.write('<div style="margin-top: 2px;"></div>', unsafe_allow_html=True) # Căn chỉnh lề dọc nút bấm
        if st.button("🚪 Đăng xuất", use_container_width=True, type="secondary"):
            st.query_params.clear()
            st.session_state.logged_in = False
            st.session_state.danh_sach_luu = []
            st.session_state.tram_hien_tai = None
            st.rerun()

    st.markdown("<hr style='margin-top: 10px; margin-bottom: 15px; border-color: #CBD5E1;'>", unsafe_allow_html=True)

    col_left_search, col_right_map = st.columns([2.3, 7.7])

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
            with st.form("form_tra_cuu", clear_on_submit=True):
                st.markdown("<h4 style='margin:0 0 10px 0; color:#0F172A; font-size:16px;'>🔍 BỘ LỌC TÌM KIẾM TRẠM</h4>", unsafe_allow_html=True)
                f1 = st.text_input("Mã quốc gia (MCC):", key="mcc_in").strip()
                f2 = st.text_input("Mã mạng di động (MNC):", key="mnc_in").strip()
                f3 = st.text_input("Mã vùng (LAC/TAC):", key="lac_in").strip()
                f4 = st.text_input("Mã trạm (CELL ID):", key="cell_in").strip()
                
                if f2.isdigit() and len(f2) == 1:
                    f2 = f2.zfill(2)
                
                nut_tim_kiem = st.form_submit_button("🔍 Tìm kiếm", use_container_width=True)
            
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
                        st.success(f"🎯 Đã tìm thấy mục tiêu ID: {f4}")
                        st.rerun()
                    else:
                        st.session_state.tram_hien_tai = None
                        st.warning("⚠️ Không tìm thấy dữ liệu trạm tương thích!")
                else:
                    st.error("❌ Yêu cầu nhập đầy đủ cả 4 thông số kỹ thuật!")

            if st.session_state.tram_hien_tai is not None:
                cell_id_hien_tai = st.session_state.tram_hien_tai[COT_CELL_ID]
                if st.button("📌 Lưu trạm", type="primary", use_container_width=True):
                    da_ton_tai = any(item[COT_CELL_ID] == cell_id_hien_tai for item in st.session_state.danh_sach_luu)
                    if not da_ton_tai:
                        st.session_state.danh_sach_luu.append(st.session_state.tram_hien_tai)
                        st.toast(f"Đã thêm trạm {cell_id_hien_tai} vào bộ nhớ.")
                    else:
                        st.toast("Trạm này đã có trong danh sách lưu.")
            
            so_luong_diem = len(st.session_state.danh_sach_luu)
            
            if so_luong_diem >= 2:
                st.markdown("<hr style='margin: 15px 0 10px 0;'>", unsafe_allow_html=True)
                st.markdown("<h4 style='margin:0 0 10px 0; color:#0F172A; font-size:16px;'>📏 PHÂN TÍCH TRẮC ĐỊA TUYẾN</h4>", unsafe_allow_html=True)
                
                tong_khoang_cach = 0.0
                ds_chi_tiet = []
                
                for i in range(so_luong_diem - 1):
                    p1 = st.session_state.danh_sach_luu[i]
                    p2 = st.session_state.danh_sach_luu[i+1]
                    kc = tinh_khoang_cach_haversine(p1[COT_VI_DO], p1[COT_KINH_DO], p2[COT_VI_DO], p2[COT_KINH_DO])
                    tong_khoang_cach += kc
                    ds_chi_tiet.append(f"• Chặng {i+1} → {i+2}: **{kc:.2f} km**")
                
                if so_luong_diem >= 3:
                    p_cuoi = st.session_state.danh_sach_luu[-1]
                    p_dau = st.session_state.danh_sach_luu[0]
                    kc_khay_vong = tinh_khoang_cach_haversine(p_cuoi[COT_VI_DO], p_cuoi[COT_KINH_DO], p_dau[COT_VI_DO], p_dau[COT_KINH_DO])
                    tong_khoang_cach += kc_khay_vong
                    ds_chi_tiet.append(f"• Khép góc ({so_luong_diem} → 1): **{kc_khay_vong:.2f} km**")
                
                if so_luong_diem == 2:
                    st.info(f"📍 Chiều dài tuyến liên kết:\n**{tong_khoang_cach:.2f} km**")
                else:
                    st.info(f"🔄 Chu vi đa giác khu vực:\n**{tong_khoang_cach:.2f} km**")
                    with st.expander("Báo cáo chi tiết từng phân đoạn"):
                        for dong in ds_chi_tiet:
                            st.write(dong)

            if so_luong_diem > 0:
                st.markdown("<hr style='margin: 15px 0 10px 0;'>", unsafe_allow_html=True)
                st.markdown(f"<h4 style='margin:0 0 10px 0; color:#0F172A; font-size:16px;'>📍 DANH SÁCH ĐIỂM ĐÃ LƯU ({so_luong_diem})</h4>", unsafe_allow_html=True)
                
                index_can_xoa = None
                for idx, tram_luu in enumerate(st.session_state.danh_sach_luu):
                    col_cell_name, col_del_btn = st.columns([7, 3])
                    with col_cell_name:
                        st.markdown(f"<div style='padding-top:4px;'><b>[{idx+1}]</b> ID: {tram_luu[COT_CELL_ID]}</div>", unsafe_allow_html=True)
                    with col_del_btn:
                        if st.button("Xóa", key=f"del_{tram_luu[COT_CELL_ID]}_{idx}", use_container_width=True):
                            index_can_xoa = idx
                
                if index_can_xoa is not None:
                    tram_bi_xoa = st.session_state.danh_sach_luu.pop(index_can_xoa)
                    st.toast(f"Đã loại bỏ trạm {tram_bi_xoa[COT_CELL_ID]}.")
                    st.rerun()

                st.write("")
                if st.button("🗑 nighttime Xóa toàn bộ danh sách lưu", type="secondary", use_container_width=True):
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
            attr='Google Satellite', name='Bản đồ Địa hình Vệ tinh', overlay=False, control=True
        ).add_to(m)
        
        folium.TileLayer(
            tiles='https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}',
            attr='Google Maps Street', name='Bản đồ Giao thông Đường phố', overlay=False, control=True
        ).add_to(m)
        
        folium.LayerControl().add_to(m)

        toa_do_vung = []

        for index, tram_luu in enumerate(st.session_state.danh_sach_luu):
            lat_l = float(tram_luu[COT_VI_DO])
            lon_l = float(tram_luu[COT_KINH_DO])
            toa_do_vung.append([lat_l, lon_l])
            
            cgi_l = truy_xuat_du_lieu_cot(tram_luu, ['CGI', 'cgi'])
            addr_l = truy_xuat_du_lieu_cot(tram_luu, ['Địa chỉ', 'dia chi', 'địa chỉ', 'Địa Chỉ', 'Address', 'address'])
            note_l = truy_xuat_du_lieu_cot(tram_luu, ['Ghi chú', 'ghi chu', 'Note'])
            cell_l = tram_luu[COT_CELL_ID]

            noi_dung_luu = f"""
            <div style='font-family: Arial, sans-serif; font-size: 13px; width: 240px; color: #333333; line-height: 1.5; word-wrap: break-word; white-space: normal;'>
                <h4 style='margin: 0 0 6px 0; color: #0275d8; border-bottom: 1px solid #eeeeee; padding-bottom: 4px; text-align: center;'>📌 ĐIỂM ĐÃ LƯU ({index+1})</h4>
                <b>CELL ID:</b> {cell_l}<br>
                <b>CGI:</b> {cgi_l}<br>
                <b>Tọa độ:</b> {lat_l}, {lon_l}<br>
                <b>Địa chỉ:</b> {addr_l}<br>
                <b>Ghi chú:</b> {note_l}
            </div>
            """
            
            folium.Marker(
                [lat_l, lon_l],
                popup=folium.Popup(noi_dung_luu, max_width=260),
                icon=folium.Icon(color='blue', icon='bookmark')
            ).add_to(m)

        if len(toa_do_vung) == 2:
            folium.PolyLine(
                locations=toa_do_vung, color="#0275d8", weight=4, opacity=0.8, dash_array='5, 10'
            ).add_to(m)
        elif len(toa_do_vung) >= 3:
            folium.Polygon(
                locations=toa_do_vung,
                color="#0275d8",       
                weight=3,              
                fill=True,             
                fill_color="#0275d8",  
                fill_opacity=0.15,     
                dash_array='5, 5'      
            ).add_to(m)

        if st.session_state.tram_hien_tai is not None:
            cgi_val = truy_xuat_du_lieu_cot(st.session_state.tram_hien_tai, ['CGI', 'cgi'])
            dia_chi_val = truy_xuat_du_lieu_cot(st.session_state.tram_hien_tai, ['Địa chỉ', 'dia chi', 'địa chỉ', 'Địa Chỉ', 'Address', 'address'])
            ghi_chu_val = truy_xuat_du_lieu_cot(st.session_state.tram_hien_tai, ['Ghi chú', 'ghi chu', 'Note'])
            cell_val = st.session_state.tram_hien_tai[COT_CELL_ID]

            noi_dung_label = f"""
            <div style='font-family: Arial, sans-serif; font-size: 13px; width: 240px; color: #333333; line-height: 1.5; word-wrap: break-word; white-space: normal;'>
                <h4 style='margin: 0 0 6px 0; color: #d9534f; border-bottom: 1px solid #eeeeee; padding-bottom: 4px; text-align: center;'>📍 KẾT QUẢ TÌM KIẾM</h4>
                <b>CELL ID:</b> {cell_val}<br>
                <b>CGI:</b> {cgi_val}<br>
                <b>Tọa độ:</b> {vi_do_xem}, {kinh_do_xem}<br>
                <b>Địa chỉ:</b> {dia_chi_val}<br>
                <b>Ghi chú:</b> {ghi_chu_val}
            </div>
            """
            
            folium.Marker(
                [vi_do_xem, kinh_do_xem],
                popup=folium.Popup(noi_dung_label, max_width=260, show=True),
                icon=folium.Icon(color='red', icon='info-sign')
            ).add_to(m)

        with col_right_map:
            folium_static(m, height=750, width=None)

    except Exception as e:
        with col_right_map:
            st.error(f"❌ Hệ thống không thể tải hoặc xử lý cơ sở dữ liệu hạ tầng toàn quốc. Chi tiết: {e}")
