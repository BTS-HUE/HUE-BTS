import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
import math
import re

# ==============================================================================
# 1. KIẾN TRÚC NỀN TẢNG & QUẢN LÝ PHÂN HỆ PHIÊN TRUY CẬP (SESSION MANAGEMENT)
# ==============================================================================
st.set_page_config(page_title="Hệ Thống Giám Sát & Định Vị TRẠM BTS", layout="wide", initial_sidebar_state="collapsed")

TOKEN_XAC_THUC = st.secrets["auth"]["token_xac_thuc"]
TAI_KHOAN_CHUAN = st.secrets["auth"]["tai_khoan_chuan"]
MAT_KHAU_CHUAN = st.secrets["auth"]["mat_khau_chuan"]
SHEET_ID = st.secrets["database"]["sheet_id"]

if "logged_in" not in st.session_state:
    st.session_state.logged_in = (st.query_params.get("auth_token") == TOKEN_XAC_THUC)
    if st.session_state.logged_in: st.query_params.clear()

# Khởi tạo gọn gàng các biến session
for key, val in [("danh_sach_luu", []), ("tram_hien_tai", None), ("ds_gan_nhat", [])]:
    st.session_state.setdefault(key, val)

# ==============================================================================
# 2. KHỞI TẠO LỚP ĐỊNH DẠNG GIAO DIỆN (UI/UX STYLE Overrides)
# ==============================================================================
st.markdown("""
<style>
    /* Ẩn các thành phần mặc định của Streamlit */
    [data-testid="stSidebarNav"], [data-testid="stSidebar"], header, footer, #MainMenu, iframe[title="Manage app"], .stAppDeployButton, footer + div { display: none !important; }
    .block-container { padding: 0.6rem 1rem 0rem 1rem !important; max-width: 100% !important; }
    .stFoliumStatic { margin-top: 0px !important; width: 100% !important; }
    .stFoliumStatic > iframe { width: 100% !important; border-radius: 12px !important; }

    /* Tối ưu Upload file */
    [data-testid="stFileUploader"] section { padding: 8px !important; min-height: 40px !important; background-color: var(--secondary-background-color) !important; }
    [data-testid="stFileUploader"] small { display: none !important; }

    /* Bảng màu và thành phần nổi */
    label, p, span, summary, div { color: var(--text-color) !important; }
    .stExpander { background-color: var(--background-color) !important; border: 1px solid var(--border-color) !important; border-radius: 12px !important; box-shadow: 0px 4px 15px rgba(0, 0, 0, 0.1) !important; }
    .stExpander summary p { font-weight: 700 !important; }
    .stExpander input { background-color: var(--secondary-background-color) !important; border-radius: 8px !important; border: 1px solid var(--border-color) !important; }
    div[data-testid="stForm"] button { background-color: #3B82F6 !important; color: #FFFFFF !important; font-weight: 700 !important; border-radius: 8px !important; transition: 0.2s; border: none !important; }
    div[data-testid="stForm"] button:hover { background-color: #2563EB !important; box-shadow: 0px 4px 12px rgba(59, 130, 246, 0.3) !important; }

    /* Cấu trúc Lơ lửng & Lưới Mobile (Tránh tràn viền) */
    div[data-testid="stHorizontalBlock"]:has(.stFoliumStatic) { position: relative !important; display: block !important; height: 730px !important; }
    div[data-testid="stHorizontalBlock"]:has(.stFoliumStatic) > div:nth-child(2) { position: absolute !important; top: 0; left: 0; width: 100%; height: 100%; z-index: 1; padding: 0 !important; }
    div[data-testid="stHorizontalBlock"]:has(.stFoliumStatic) > div:nth-child(1) { position: absolute !important; top: 15px; left: 15px; width: 320px; z-index: 9999; padding: 0 !important; }
    div[data-testid="stForm"] div[data-testid="stHorizontalBlock"] { display: grid !important; grid-template-columns: 1fr 1fr !important; gap: 8px !important; width: 100% !important; }
    div[data-testid="stForm"] div[data-testid="stHorizontalBlock"] > div { width: 100% !important; min-width: 0 !important; padding: 0 !important; }

    @media (max-width: 768px) {
        div[data-testid="stHorizontalBlock"]:has(.stFoliumStatic) > div:nth-child(1) { top: 10px !important; left: 10px !important; width: 230px !important; max-width: 85% !important; }
        .stExpander summary p { font-size: 13px !important; } .stExpander label p { font-size: 11px !important; } .stExpander input { font-size: 12px !important; padding: 4px 8px !important; }
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 3. THUẬT TOÁN KHÔNG GIAN & HÀM TIỆN ÍCH (HELPER FUNCTIONS)
# ==============================================================================
def tinh_khoang_cach(lat1, lon1, lat2, lon2):
    r_lat1, r_lon1, r_lat2, r_lon2 = map(math.radians, [float(lat1), float(lon1), float(lat2), float(lon2)])
    a = math.sin((r_lat2 - r_lat1) / 2)**2 + math.cos(r_lat1) * math.cos(r_lat2) * math.sin((r_lon2 - r_lon1) / 2)**2
    return 2 * math.asin(math.sqrt(a)) * 6371.0 

@st.cache_data(ttl=600) 
def tai_co_so_du_lieu():
    data = pd.read_csv(f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv", dtype=str)
    data.columns = data.columns.str.strip()
    data = data.fillna("").apply(lambda x: x.str.strip() if x.dtype == "object" else x)
    if 'MNC' in data.columns: data['MNC'] = data['MNC'].apply(lambda x: x.zfill(2) if x.isdigit() and len(x) == 1 else x)
    return data

def tim_du_lieu(row, keys):
    keys_lower = set(k.lower() for k in keys)
    return next((row[k] for k in row.index if str(k).lower() in keys_lower), "Không có dữ liệu")

def tao_popup_html(tieu_de, mau_sac, id_tram, cgi, lat, lon, dia_chi, thoi_gian="", khoang_cach=""):
    """Hàm tối ưu việc sinh HTML cho các marker trên bản đồ"""
    html_tg = f"<b>Thời gian:</b> <span style='color:red;'>{thoi_gian}</span><br>" if thoi_gian and thoi_gian != "Không có dữ liệu" else ""
    html_kc = f"<b>Khoảng cách:</b> {khoang_cach}<br>" if khoang_cach else ""
    return f"""
    <div style='font-family: Arial, sans-serif; font-size: 13px; width: 220px; color: #333; line-height: 1.5;'>
        <b style='color: {mau_sac};'>{tieu_de}</b><br>{html_tg}
        <b>Cell ID:</b> {id_tram}<br>{html_kc}
        <b>CGI:</b> {cgi}<br><b>Tọa độ:</b> {lat}, {lon}<br><b>Địa chỉ:</b> {dia_chi}
    </div>"""

# ==============================================================================
# 4. XÁC THỰC BẢO MẬT (LOGIN GATEWAY)
# ==============================================================================
if not st.session_state.logged_in:
    st.markdown("""<style>.stApp, p, label { color: #FFF !important; } input { color: #000 !important; background: #FFF !important; }</style>""", unsafe_allow_html=True)
    _, c1, c2 = st.columns([7, 1.5, 1.5])
    with c1: tk = st.text_input("Tài khoản:")
    with c2: mk = st.text_input("Mật khẩu:", type="password")
    
    if tk == TAI_KHOAN_CHUAN and mk == MAT_KHAU_CHUAN:
        st.session_state.logged_in = True
        st.rerun()

    st.markdown("<script>window.parent.document.querySelectorAll('input').forEach(i => i.setAttribute('autocomplete', 'new-password'));</script>", unsafe_allow_html=True)
    st.markdown("""<style>.stApp { background: url("https://raw.githubusercontent.com/BTS-HUE/HUE-BTS/refs/heads/main/WC%20to.png") fixed center/cover; }</style>
        <div style='background:rgba(15,23,42,0.85); padding:35px; border-radius:12px; text-align:center; margin-top:12%; box-shadow:0 10px 25px rgba(0,0,0,0.6); backdrop-filter:blur(8px); border:1px solid rgba(255,255,255,0.1);'>
            <h2 style='color:#FFF; font-weight:700;'>🔒 XÁC THỰC QUYỀN TRUY CẬP</h2>
            <p style='font-size:15px; opacity:0.85;'>Vui lòng cung cấp thông tin định danh tại góc phải màn hình.</p>
        </div>""", unsafe_allow_html=True)

# ==============================================================================
# 5. GIS MASTER MODULE (GIAO DIỆN CHÍNH & BẢN ĐỒ)
# ==============================================================================
else:
    c_title, c_logout = st.columns([8.5, 1.5])
    c_title.markdown("<h2 style='margin:0; font-size:22px;'>🛰️ TRUNG TÂM GIÁM SÁT VÀ ĐỊNH VỊ TRẠM BTS <span style='font-size:12px; color:#3B82F6; background:rgba(59,130,246,0.15); padding:3px 8px; border-radius:6px;'>☁️ LIVE CLOUD</span></h2>", unsafe_allow_html=True)
    if c_logout.button("🚪 ĐĂNG XUẤT", use_container_width=True):
        st.session_state.clear()
        st.rerun()

    st.markdown("<hr style='margin: 5px 0 10px 0; border-color: var(--border-color);'>", unsafe_allow_html=True)
    col_left, col_right = st.columns([2.4, 7.6])

    try:
        df = tai_co_so_du_lieu()
        C_MCC, C_MNC, C_LAC, C_CELL, C_LAT, C_LON = 'MCC', 'MNC', 'LAC/TAC', 'CELL ID', 'Latitude', 'Longitude'

        with col_left:
            # 5.1 FORM TÌM KIẾM
            with st.expander("🔍 TÌM KIẾM TRẠM", expanded=True):
                with st.form("form_tra_cuu", clear_on_submit=True):
                    f_mcc, f_mnc = st.columns(2)
                    with f_mcc: val_mcc = st.text_input("MCC:", placeholder="MCC").strip()
                    with f_mnc: val_mnc = st.text_input("MNC:", placeholder="MNC").strip()
                    f_lac, f_cell = st.columns(2)
                    with f_lac: val_lac = st.text_input("LAC/TAC:", placeholder="LAC/TAC").strip()
                    with f_cell: val_cell = st.text_input("Cell ID:", placeholder="Cell ID").strip()
                    
                    if val_mnc.isdigit() and len(val_mnc) == 1: val_mnc = val_mnc.zfill(2)
                    submit = st.form_submit_button("🔍 Tìm Kiếm", use_container_width=True)

            if submit:
                if all([val_mcc, val_mnc, val_lac, val_cell]):
                    kq = df[(df[C_MCC] == val_mcc) & (df[C_MNC] == val_mnc) & (df[C_LAC] == val_lac) & (df[C_CELL] == val_cell)]
                    st.session_state.tram_hien_tai = kq.iloc[0] if not kq.empty else None
                    st.session_state.ds_gan_nhat = []
                    if not kq.empty: st.success(f"🎯 Đã phát hiện ID: {val_cell}")
                    else: st.warning("⚠️ Không tìm thấy trạm!")
                else: st.error("❌ Yêu cầu nhập đầy đủ tham số!")

            # 5.2 XỬ LÝ TRẠM HIỆN TẠI
            curr = st.session_state.tram_hien_tai
            if curr is not None:
                if st.button("📌 Gắn thẻ tọa độ trạm này", type="primary", use_container_width=True):
                    if len(st.session_state.danh_sach_luu) >= 50: st.toast("❌ Đạt giới hạn ghim!")
                    elif not any(i[C_CELL] == curr[C_CELL] for i in st.session_state.danh_sach_luu):
                        st.session_state.danh_sach_luu.append(curr)
                        st.toast(f"Đã lưu trạm {curr[C_CELL]}")

                if st.button("📡 Tìm các trạm gần nhất", use_container_width=True):
                    df_other = df[df[C_CELL] != curr[C_CELL]].copy()
                    df_other['KhoangCach'] = df_other.apply(lambda r: tinh_khoang_cach(curr[C_LAT], curr[C_LON], r[C_LAT], r[C_LON]), axis=1)
                    st.session_state.ds_gan_nhat = df_other.sort_values('KhoangCach').head(5).to_dict('records')
                    st.toast("🎯 Đã cập nhật trạm gần nhất!")

            # 5.3 HIỂN THỊ TRẠM GẦN NHẤT
            if curr is not None and st.session_state.ds_gan_nhat:
                with st.expander("📡 TRẠM GẦN NHẤT", expanded=True):
                    for idx, t_near in enumerate(st.session_state.ds_gan_nhat):
                        c_info, c_btn = st.columns([7.2, 2.8])
                        c_info.markdown(f"**{idx+1}. ID: {t_near[C_CELL]}** (`{t_near['KhoangCach']:.2f} km`)<br><span style='font-size:11px; opacity:0.8;'>{tim_du_lieu(pd.Series(t_near), ['Địa chỉ', 'Address'])}</span>", unsafe_allow_html=True)
                        if c_btn.button("Ghim", key=f"pin_{t_near[C_CELL]}", use_container_width=True):
                            if not any(i[C_CELL] == t_near[C_CELL] for i in st.session_state.danh_sach_luu):
                                st.session_state.danh_sach_luu.append(pd.Series(t_near))
                                st.rerun()
                        st.markdown("<hr style='margin:4px 0;'>", unsafe_allow_html=True)

            # 5.4 LỘ TRÌNH VÀ QUẢN LÝ GHIM
            dsl = st.session_state.danh_sach_luu
            if len(dsl) >= 2:
                with st.expander("📏 LỘ TRÌNH", expanded=False):
                    tong_kc = sum(tinh_khoang_cach(dsl[i][C_LAT], dsl[i][C_LON], dsl[i+1][C_LAT], dsl[i+1][C_LON]) for i in range(len(dsl)-1))
                    st.info(f"Tổng lộ trình: **{tong_kc:.2f} km**")

            if dsl:
                with st.expander(f"📍 Điểm ghim ({len(dsl)})", expanded=False):
                    for idx, t in enumerate(dsl):
                        cx, cy = st.columns([7, 3])
                        tg = tim_du_lieu(t, ['Thời gian đo_mapped', 'Thời gian'])
                        cx.markdown(f"<div style='font-size:12px; padding-top:5px;'>ID: {t[C_CELL]}" + (f" ({tg})" if tg != "Không có dữ liệu" else "") + "</div>", unsafe_allow_html=True)
                        if cy.button("Hủy", key=f"del_{t[C_CELL]}_{idx}", use_container_width=True):
                            dsl.pop(idx); st.rerun()
                    if st.button("🗑️ Xóa toàn bộ", use_container_width=True):
                        st.session_state.danh_sach_luu.clear(); st.session_state.tram_hien_tai = None; st.session_state.ds_gan_nhat.clear(); st.rerun()

        # ==============================================================================
        # 6. KHỞI TẠO BẢN ĐỒ & VẼ ĐỒ HỌA
        # ==============================================================================
        lat_map, lon_map, zoom_map = (curr[C_LAT], curr[C_LON], 14) if curr is not None else ((dsl[-1][C_LAT], dsl[-1][C_LON], 14) if dsl else (16.047, 108.206, 5))
        m = folium.Map(location=[float(lat_map), float(lon_map)], zoom_start=zoom_map)
        folium.TileLayer('https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}', attr='Google', name='Vệ tinh').add_to(m)
        folium.TileLayer('https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}', attr='Google', name='Đường phố').add_to(m)
        
        route_coords = []
        # Vẽ các điểm đã ghim
        for i, t in enumerate(dsl):
            lat, lon = float(t[C_LAT]), float(t[C_LON])
            route_coords.append([lat, lon])
            html = tao_popup_html(f"📌 ĐIỂM LỘ TRÌNH [{i+1}]", "#0275d8", t[C_CELL], tim_du_lieu(t, ['CGI']), lat, lon, tim_du_lieu(t, ['Địa chỉ', 'Address']), tim_du_lieu(t, ['Thời gian đo_mapped']))
            folium.Marker([lat, lon], popup=folium.Popup(html, max_width=240), icon=folium.Icon(color='blue', icon='bookmark')).add_to(m)

        if len(route_coords) > 1: folium.PolyLine(route_coords, color="#0275d8", weight=4).add_to(m)

        # Vẽ trạm hiện tại & lân cận
        if curr is not None:
            lat_c, lon_c = float(curr[C_LAT]), float(curr[C_LON])
            html_c = tao_popup_html("🎯 TRẠM BTS HIỆN TẠI", "#D9534F", curr[C_CELL], tim_du_lieu(curr, ['CGI']), lat_c, lon_c, tim_du_lieu(curr, ['Địa chỉ']), tim_du_lieu(curr, ['Thời gian đo_mapped']))
            folium.Marker([lat_c, lon_c], popup=folium.Popup(html_c, max_width=240, show=True), icon=folium.Icon(color='red', icon='info-sign')).add_to(m)

            for tn in st.session_state.ds_gan_nhat:
                tn_s = pd.Series(tn)
                lat_n, lon_n = float(tn[C_LAT]), float(tn[C_LON])
                html_n = tao_popup_html("📡 TRẠM LÂN CẬN", "#28a745", tn[C_CELL], tim_du_lieu(tn_s, ['CGI']), lat_n, lon_n, tim_du_lieu(tn_s, ['Địa chỉ']), khoang_cach=f"{tn['KhoangCach']:.2f} km")
                folium.Marker([lat_n, lon_n], popup=folium.Popup(html_n, max_width=240), icon=folium.Icon(color='green', icon='broadcast-tower', prefix='fa')).add_to(m)
                folium.PolyLine([[lat_c, lon_c], [lat_n, lon_n]], color="green", weight=1.5, dash_array='5, 5').add_to(m)

        with col_right: folium_static(m, height=730, width=None)

        # ==============================================================================
        # 7. UPLOAD & MAPPING HÀNH TRÌNH TỰ ĐỘNG
        # ==============================================================================
        st.markdown("<hr style='margin: 15px 0;'>", unsafe_allow_html=True)
        up_col1, up_col2, _ = st.columns([4, 2, 4])
        uploaded_file = up_col1.file_uploader("📥 Tải lộ trình (Excel/CSV có cột CGI):", type=["csv", "xlsx"])
        if up_col2.button("🗑️ Xóa Lộ Trình Mới", use_container_width=True):
            st.session_state.danh_sach_luu.clear(); st.session_state.tram_hien_tai = None; st.rerun()

        if uploaded_file:
            df_route = pd.read_csv(uploaded_file, dtype=str) if uploaded_file.name.endswith(".csv") else pd.read_excel(uploaded_file, dtype=str)
            c_cgi = next((c for c in df_route.columns if 'cgi' in str(c).lower()), None)
            c_time = next((c for c in df_route.columns if any(x in str(c).lower() for x in ['thời gian', 'time', 'ngày'])), None)

            if not c_cgi: st.error("❌ File thiếu cột chứa 'CGI'.")
            else:
                ds_moi, loi = [], 0
                for _, r in df_route.iterrows():
                    cgi_raw = str(r[c_cgi]).strip()
                    if not cgi_raw or cgi_raw == 'nan': continue
                    p = re.split(r'[-_]', cgi_raw)
                    if len(p) >= 4:
                        mcc, mnc, lac, cell = p[-4], p[-3].zfill(2), p[-2], p[-1]
                        match = df[(df[C_MCC] == mcc) & (df[C_MNC] == mnc) & (df[C_LAC] == lac) & (df[C_CELL] == cell)]
                        if not match.empty:
                            t_info = match.iloc[0].copy()
                            if c_time and pd.notna(r[c_time]): t_info['Thời gian đo_mapped'] = str(r[c_time])
                            ds_moi.append(t_info)
                        else: loi += 1
                if ds_moi:
                    st.session_state.danh_sach_luu = ds_moi
                    st.session_state.tram_hien_tai = ds_moi[0]
                    st.success(f"🎉 Đã map {len(ds_moi)} điểm. (Bỏ qua {loi} điểm lỗi)"); st.rerun()
                else: st.error("⚠️ Không có mã CGI nào khớp CSDL.")

    except Exception as e:
        col_right.error(f"❌ Lỗi hệ thống: {e}")
