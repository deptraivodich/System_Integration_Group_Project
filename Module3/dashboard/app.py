import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import os

# Cấu hình giao diện Streamlit
st.set_page_config(
    page_title="NOAH Retail - Unified Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS cho giao diện Premium
st.markdown("""
<style>
    .main {
        background-color: #f8f9fa;
    }
    .stMetric {
        background-color: white;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .metric-title {
        color: #6c757d;
        font-weight: 600;
        font-size: 14px;
        margin-bottom: 5px;
    }
    h1, h2, h3 {
        color: #2c3e50;
        font-family: 'Inter', sans-serif;
    }
    .header-box {
        padding: 20px;
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        border-radius: 15px;
        color: white;
        margin-bottom: 30px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    .header-box h1 {
        color: white;
        margin: 0;
        padding: 0;
    }
    .header-box p {
        margin: 5px 0 0 0;
        font-size: 1.1em;
        opacity: 0.9;
    }
</style>
""", unsafe_allow_html=True)

# URL API (Sử dụng biến môi trường hoặc mặc định là internal network của Docker)
REPORT_API_URL = os.getenv("REPORT_API_URL", "http://report_api:5002/api/report")

def load_data(page=1, limit=50):
    try:
        response = requests.get(f"{REPORT_API_URL}?page={page}&limit={limit}", timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Lỗi khi tải dữ liệu: {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        st.error(f"Không thể kết nối đến Report API: {e}")
        return None

# Tiêu đề
st.markdown("""
<div class="header-box">
    <h1>NOAH Retail Unified Commerce</h1>
    <p>Real-time Command Center & Sales Analytics</p>
</div>
""", unsafe_allow_html=True)

# Lấy dữ liệu
with st.spinner("Đang tải dữ liệu từ hệ thống..."):
    data = load_data(page=1, limit=100) # Load 100 bản ghi mới nhất

if data:
    orders_df = pd.DataFrame(data.get("orders", []))
    revenue_df = pd.DataFrame(data.get("revenue_by_user", []))
    
    if not orders_df.empty:
        # Tính toán KPIs
        total_orders = len(orders_df)
        total_revenue = orders_df['amount'].sum()
        completed_orders = len(orders_df[orders_df['status'] == 'COMPLETED'])
        pending_orders = total_orders - completed_orders
        success_rate = (completed_orders / total_orders * 100) if total_orders > 0 else 0

        # Layout KPI Metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(label="Tổng Số Đơn Hàng", value=f"{total_orders:,}")
        with col2:
            st.metric(label="Tổng Doanh Thu ($)", value=f"${total_revenue:,.2f}")
        with col3:
            st.metric(label="Đơn Hoàn Thành", value=f"{completed_orders}", delta=f"{success_rate:.1f}%")
        with col4:
            st.metric(label="Đơn Đang Xử Lý", value=f"{pending_orders}", delta_color="inverse")

        st.markdown("---")

        # Biểu đồ và Bảng dữ liệu chia 2 cột
        left_col, right_col = st.columns([1, 1])

        with left_col:
            st.subheader("Doanh Thu Theo User")
            if not revenue_df.empty:
                # Đổi tên cột cho đẹp
                rev_plot_df = revenue_df.rename(columns={"user_id": "Mã KH", "amount": "Doanh Thu"})
                rev_plot_df['Mã KH'] = rev_plot_df['Mã KH'].astype(str) # Ép kiểu chuỗi để vẽ biểu đồ bar đẹp hơn
                
                fig = px.bar(
                    rev_plot_df, 
                    x="Mã KH", 
                    y="Doanh Thu", 
                    color="Doanh Thu",
                    color_continuous_scale="Blues",
                    text_auto='.2s'
                )
                fig.update_layout(
                    plot_bgcolor="white", 
                    paper_bgcolor="white", 
                    margin=dict(t=10, l=10, r=10, b=10),
                    xaxis_title="Khách Hàng (User ID)",
                    yaxis_title="Doanh Thu ($)"
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Chưa có dữ liệu doanh thu.")

        with right_col:
            st.subheader("Trạng Thái Đơn Hàng")
            status_counts = orders_df['status'].value_counts().reset_index()
            status_counts.columns = ['Trạng Thái', 'Số Lượng']
            
            fig2 = px.pie(
                status_counts, 
                values='Số Lượng', 
                names='Trạng Thái', 
                hole=0.4,
                color='Trạng Thái',
                color_discrete_map={'COMPLETED': '#27ae60', 'PENDING': '#f39c12', 'FAILED': '#c0392b'}
            )
            fig2.update_traces(textposition='inside', textinfo='percent+label')
            fig2.update_layout(margin=dict(t=10, l=10, r=10, b=10))
            st.plotly_chart(fig2, use_container_width=True)

        st.markdown("---")
        
        # Bảng dữ liệu chi tiết
        st.subheader("Chi Tiết Đơn Hàng Gần Đây")
        
        # Format lại bảng trước khi hiển thị
        display_df = orders_df.copy()
        display_df = display_df[['order_id', 'user_id', 'product_id', 'quantity', 'status', 'amount', 'payment_status']]
        display_df.columns = ['Mã Đơn', 'Mã KH', 'Mã SP', 'Số Lượng', 'Trạng Thái', 'Giá Trị ($)', 'Trạng Thái TT']
        
        # Highlight các đơn hàng theo status
        def color_status(val):
            color = 'green' if val == 'COMPLETED' else 'orange' if val == 'PENDING' else 'red'
            return f'color: {color}; font-weight: bold;'

        st.dataframe(
            display_df.style.map(color_status, subset=['Trạng Thái']).format({"Giá Trị ($)": "${:,.2f}"}),
            use_container_width=True,
            hide_index=True
        )

    else:
        st.warning("Hệ thống chưa có đơn hàng nào. Hãy thử gửi một đơn qua Order API.")
else:
    st.error("Không thể lấy dữ liệu để hiển thị Dashboard.")
