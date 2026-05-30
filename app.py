import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

# ==============================================================================
# 1. CẤU HÌNH GIAO DIỆN & MẬT KHẨU
# ==============================================================================
st.set_page_config(page_title="Hệ Thống Trạm Phát Sóng", layout="wide")

# Mật khẩu truy cập trang web (Bạn có thể đổi chữ "admin" thành mật khẩu khác)
MAT_KHAU_CUA_BAN = "admin" 

mat_khau_nhap = st.sidebar.text_input("Nhập mật khẩu truy cập:", type="password")

if mat_khau_nhap == MAT_KHAU_CUA_BAN:
    st.title("🛰️ HỆ THỐNG TRA CỨU VỊ TRÍ TRẠM PHÁT SÓNG")

    # ==============================================================================
    # 2. KẾT NỐI VỚI GOOGLE SHEETS
    # ==============================================================================
    # ⚠️ HÃY THAY ĐOẠN MÃ ĐỊNH DANH DƯỚI ĐÂY BẰNG MÃ FILE GOOGLE SHEETS CỦA BẠN
    SHEET_ID = "101T9xJHnW9EUdz1Il6FXWTWt272oSFvkAIWwSijLRYI" 
    URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

    @st.cache_data(ttl=30) # Tự động tải lại dữ liệu mới sau mỗi 30 giây
    def tai_du_lieu():
        # Ép buộc đọc tất cả dữ liệu dưới dạng văn bản (String) để KHÔNG bị mất số 0 ở đầu
        data = pd.read_csv(URL, dtype=str)
        
        # Làm sạch khoảng trắng thừa và đuôi .0 (nếu có lỗi định dạng)
        for col in ['MCC', 'MNC', 'LAC/TAC', 'CELL ID']:
            if col in data.columns:
                data[col] = data[col].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        
        # XỬ LÝ DỮ LIỆU SHEET: Nếu MNC bị mất số 0 (chỉ có số 1, 2...), tự động bù thành 01, 02
        if 'MNC' in data.columns:
            data['MNC'] = data['MNC'].apply(lambda x: x.zfill(2) if x.isdigit() and len(x) == 1 else x)
            
        return data

    try:
        df = tai_du_lieu()
        
        # Tên các cột theo đúng file Google Sheets của bạn
        COT_MCC = 'MCC'
        COT_MNC = 'MNC'
        COT_LAC_TAC = 'LAC/TAC'
        COT_CELL_ID = 'CELL ID'
        COT_VI_DO = 'Latitude'
        COT_KINH_DO = 'Longitude'
        
        # ==============================================================================
        # 4. DÒNG TÌM KIẾM: BẤM SỐ CHỨ KHÔNG THẢ
        # ==============================================================================
        st.sidebar.header("Nhập thông số tìm kiếm")
        
        # Tạo các ô trống để bạn tự tay nhập số từ bàn phím
        f1 = st.sidebar.text_input("1. Nhập số MCC:").strip()
        f2 = st.sidebar.text_input("2. Nhập số MNC:").strip()
        f3 = st.sidebar.text_input("3. Nhập số LAC/TAC:").strip()
        f4 = st.sidebar.text_input("4. Nhập số CELL ID:").strip()

        # XỬ LÝ Ô NHẬP: Nếu bạn lỡ gõ số "1" vào ô MNC, code tự động sửa thành "01" để tìm cho đúng
        if f2.isdigit() and len(f2) == 1:
            f2 = f2.zfill(2)

        # Vị trí mặc định ban đầu khi chưa tìm kiếm (Trung tâm Việt Nam)
        vi_do_xem, kinh_do_xem, muc_zoom = 16.047079, 108.206230 
        tram_tim_thay = None

        # ==============================================================================
        # 5. XỬ LÝ LỌC VÀ TÌM KIẾM DỮ LIỆU
        # ==============================================================================
        # Chỉ kích hoạt tìm kiếm khi bạn đã gõ chữ/số vào cả 4 ô trống
        if f1 and f2 and f3 and f4:
            
            # Tìm kiếm chính xác tuyệt đối theo các thông số đã gõ
            ket_qua = df[
                (df[COT_MCC] == f1) & 
                (df[COT_MNC] == f2) & 
                (df[COT_LAC_TAC] == f3) & 
                (df[COT_CELL_ID] == f4)
            ]
            
            if not ket_qua.empty:
                tram_tim_thay = ket_qua.iloc[0]
                vi_do_xem = float(tram_tim_thay[COT_VI_DO])
                kinh_do_xem = float(tram_tim_thay[COT_KINH_DO])
                muc_zoom = 17 # Tự động zoom sát vạch vào vị trí trạm
                st.success(f"✅ Đã định vị thành công trạm CELL ID: {f4} (MNC: {f2})")
            else:
                st.warning(f"⚠️ Không tìm thấy trạm khớp với: MCC={f1}, MNC={f2}, LAC/TAC={f3}, CELL ID={f4}")
        else:
            st.sidebar.info("💡 Hãy gõ đầy đủ số vào cả 4 ô trên rồi nhấn Enter để xem bản đồ.")

        # ==============================================================================
        # 6. KHỞI TẠO BẢN ĐỒ VỆ TINH GOOGLE MAPS
        # ==============================================================================
        m = folium.Map(location=[vi_do_xem, kinh_do_xem], zoom_start=muc_zoom, control_scale=True)
        
        # Thêm lớp bản đồ vệ tinh Google
        folium.TileLayer(
            tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
            attr='Google Satellite', name='Bản đồ Vệ tinh', overlay=False, control=True
        ).add_to(m)
        
        # Thêm lớp bản đồ đường phố Google
        folium.TileLayer(
            tiles='https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}',
            attr='Google Maps Street', name='Bản đồ Đường phố', overlay=False, control=True
        ).add_to(m)
        
        folium.LayerControl().add_to(m)

        # Nếu tìm thấy trạm, ghim màu đỏ và hiện popup thông tin chi tiết
        if tram_tim_thay is not None:
            cgi_val = tram_tim_thay.get('CGI', 'Không có dữ liệu')
            dia_chi_val = tram_tim_thay.get('Địa chỉ', 'Không có dữ liệu')
            ghi_chu_val = tram_tim_thay.get('Ghi chú', 'Không có dữ liệu')

            noi_dung_popup = f"""
            <div style='font-family: Arial, sans-serif; font-size: 13px; width: 250px;'>
                <h4 style='margin: 0 0 5px 0; color: #d9534f;'>Thông Tin Trạm</h4>
                <b>CGI:</b> {cgi_val}<br>
                <b>CELL ID:</b> {f4}<br>
                <b>LAC/TAC:</b> {f3}<br>
                <b>MNC:</b> {f2}<br>
                <b>Tọa độ:</b> {vi_do_xem}, {kinh_do_xem}<br>
                <b>Địa chỉ:</b> {dia_chi_val}<br>
                <b>Ghi chú:</b> {ghi_chu_val}
            </div>
            """
            folium.Marker(
                [vi_do_xem, kinh_do_xem],
                popup=folium.Popup(noi_dung_popup, max_width=300),
                icon=folium.Icon(color='red', icon='info-sign')
            ).add_to(m)

        # Hiển thị bản đồ ra trang web
        st_folium(m, width="100%", height=650, returned_objects=[])

    except Exception as e:
        st.error(f"❌ Lỗi cấu trúc dữ liệu: {e}")
else:
    st.info("🔒 Vui lòng nhập đúng mật khẩu ở thanh bên trái để truy cập hệ thống bản đồ.")
