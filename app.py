import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

# ==============================================================================
# 1. CẤU HÌNH GIAO DIỆN & MẬT KHẨU
# ==============================================================================
st.set_page_config(page_title="Hệ Thống Trạm Phát Sóng", layout="wide")

# Mật khẩu truy cập trang web
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
        data = pd.read_csv(URL, dtype=str)
        
        # Tự động xóa khoảng trắng thừa ở tên các cột trong Google Sheet
        data.columns = data.columns.str.strip()
        
        # Làm sạch dữ liệu các cột thông số tìm kiếm
        for col in ['MCC', 'MNC', 'LAC/TAC', 'CELL ID', 'Latitude', 'Longitude']:
            if col in data.columns:
                data[col] = data[col].astype(str).str.strip()
        
        # Tự động sửa lỗi MNC bị mất số 0 ở đầu
        if 'MNC' in data.columns:
            data['MNC'] = data['MNC'].apply(lambda x: x.zfill(2) if x.isdigit() and len(x) == 1 else x)
                
        return data

    # Hàm thông minh: Tự động tìm kiếm giá trị của cột bất kể viết hoa, viết thường hay viết có/không dấu
    def lay_thong_tin_cot(row, danh_sach_ten_goi):
        for k in row.index:
            if k.lower().strip() in [x.lower() for x in danh_sach_ten_goi]:
                return row[k]
        return "Không có dữ liệu"

    try:
        df = tai_du_lieu()
        
        # Tên các cột tìm kiếm bắt buộc (Phải khớp trên Sheet)
        COT_MCC = 'MCC'
        COT_MNC = 'MNC'
        COT_LAC_TAC = 'LAC/TAC'
        COT_CELL_ID = 'CELL ID'
        COT_VI_DO = 'Latitude'
        COT_KINH_DO = 'Longitude'
        
        # ==============================================================================
        # 4. DÒNG TÌM KIẾM (BẤM SỐ CHỨ KHÔNG THẢ)
        # ==============================================================================
        st.sidebar.header("Nhập thông số tìm kiếm")
        
        f1 = st.sidebar.text_input("1. Nhập số MCC:").strip()
        f2 = st.sidebar.text_input("2. Nhập số MNC:").strip()
        f3 = st.sidebar.text_input("3. Nhập số LAC/TAC:").strip()
        f4 = st.sidebar.text_input("4. Nhập số CELL ID:").strip()

        if f2.isdigit() and len(f2) == 1:
            f2 = f2.zfill(2)

        # Vị trí mặc định ban đầu khi chưa tìm kiếm (Trung tâm Việt Nam)
        vi_do_xem, kinh_do_xem, muc_zoom = 16.047079, 108.206230, 5
        tram_tim_thay = None

        # ==============================================================================
        # 5. XỬ LÝ LỌC VÀ TÌM KIẾM DỮ LIỆU
        # ==============================================================================
        if f1 and f2 and f3 and f4:
            
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
                muc_zoom = 17 
                st.success(f"✅ Đã định vị thành công trạm CELL ID: {f4} (MNC: {f2})")
            else:
                st.warning(f"⚠️ Không tìm thấy trạm khớp với: MCC={f1}, MNC={f2}, LAC/TAC={f3}, CELL ID={f4}")
        else:
            st.sidebar.info("💡 Hãy gõ đầy đủ số vào cả 4 ô trên rồi nhấn Enter để xem bản đồ.")

        # ==============================================================================
        # 6. KHỞI TẠO BẢN ĐỒ VỆ TINH GOOGLE MAPS
        # ==============================================================================
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

        # HIỂN THỊ THÔNG TIN CHUẨN XÁC NGAY TRÊN ĐỈNH GHIM TỌA ĐỘ
        if tram_tim_thay is not None:
            # Quét thông minh thông tin từ Google Sheet
            cgi_val = lay_thong_tin_cot(tram_tim_thay, ['CGI', 'cgi'])
            dia_chi_val = lay_thong_tin_cot(tram_tim_thay, ['Địa chỉ', 'dia chi', 'địa chỉ', 'Địa Chỉ', 'Address', 'address', 'vị trí', 'vi tri'])
            ghi_chu_val = lay_thong_tin_cot(tram_tim_thay, ['Ghi chú', 'ghi chu', 'đố chữ', 'Note', 'note'])

            # Thiết kế giao diện hộp thông tin trắng, chữ đen, viền đổ bóng bóng bẩy
            noi_dung_label = f"""
            <div style='font-family: Arial, sans-serif; font-size: 13px; width: 240px; color: #333333; padding: 2px;'>
                <h4 style='margin: 0 0 6px 0; color: #d9534f; border-bottom: 1px solid #eeeeee; padding-bottom: 4px;'>📍 Thông Tin Trạm</h4>
                <b>CGI:</b> {cgi_val}<br>
                <b>CELL ID:</b> {f4}<br>
                <b>LAC/TAC:</b> {f3}<br>
                <b>MNC:</b> {f2}<br>
                <b>Tọa độ:</b> {vi_do_xem}, {kinh_do_xem}<br>
                <b>Địa chỉ:</b> {dia_chi_val}<br>
                <b>Ghi chú:</b> {ghi_chu_val}
            </div>
            """
            
            # SỬA ĐỔI QUAN TRỌNG: Dùng Tooltip permanent=True để gắn chặt nhãn vào ghim, chống bay lệch
            folium.Marker(
                [vi_do_xem, kinh_do_xem],
                tooltip=folium.Tooltip(noi_dung_label, permanent=True, direction="top", sticky=False),
                icon=folium.Icon(color='red', icon='info-sign')
            ).add_to(m)

        st_folium(m, width="100%", height=650, returned_objects=[])

    except Exception as e:
        st.error(f"❌ Lỗi cấu trúc dữ liệu: {e}")
else:
    st.info("🔒 Vui lòng nhập đúng mật khẩu ở thanh bên trái để truy cập hệ thống bản đồ.")
