import streamlit as st
import pandas as pd
import json
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from collections import defaultdict

# Page configuration
st.set_page_config(
    page_title="RMG Invoice Analysis",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load data
@st.cache_data
def load_data():
    with open("contractor_invoices.json", "r") as f:
        data = json.load(f)
    return data

# Process invoices into DataFrame
@st.cache_data
def process_invoices(data):
    invoices = []
    for invoice in data["contractorInvoices"]:
        invoices.append({
            "category": invoice["category"],
            "heading": invoice["heading"],
            "internalReference": invoice["internalReference"],
            "invoiceDate": invoice["invoiceDate"],
            "invoiceGross": invoice["invoiceGross"],
            "supplierInvoice": invoice["supplierInvoice"],
            "supplierName": invoice["supplierName"],
            "propertyAmount": sum(prop["amount"] for prop in invoice["properties"]),
            "propertyCount": len(invoice["properties"])
        })
    
    df = pd.DataFrame(invoices)
    df["invoiceDate"] = pd.to_datetime(df["invoiceDate"])
    df["year"] = df["invoiceDate"].dt.year
    df["month"] = df["invoiceDate"].dt.month
    df["yearMonth"] = df["invoiceDate"].dt.to_period("M").astype(str)
    return df

def main():
    st.title("📊 RMG Invoice Analysis Dashboard")
    st.markdown("---")
    
    # Load data
    data = load_data()
    df = process_invoices(data)
    
    # Sidebar filters
    st.sidebar.header("Filters")
    
    # Date range filter
    min_date = df["invoiceDate"].min().date()
    max_date = df["invoiceDate"].max().date()
    date_range = st.sidebar.date_input(
        "Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )
    
    if len(date_range) == 2:
        start_date, end_date = date_range
        df_filtered = df[(df["invoiceDate"].dt.date >= start_date) & 
                        (df["invoiceDate"].dt.date <= end_date)]
    else:
        df_filtered = df
    
    # Category filter
    categories = ["All"] + sorted(df_filtered["category"].unique().tolist())
    selected_category = st.sidebar.selectbox("Category", categories)
    if selected_category != "All":
        df_filtered = df_filtered[df_filtered["category"] == selected_category]
    
    # Supplier filter
    suppliers = ["All"] + sorted(df_filtered["supplierName"].unique().tolist())
    selected_supplier = st.sidebar.selectbox("Supplier", suppliers)
    if selected_supplier != "All":
        df_filtered = df_filtered[df_filtered["supplierName"] == selected_supplier]
    
    # Key metrics
    st.header("Key Metrics")
    col1, col2, col3, col4 = st.columns(4)
    
    total_invoices = len(df_filtered)
    total_amount = df_filtered["invoiceGross"].sum()
    avg_invoice = df_filtered["invoiceGross"].mean()
    unique_suppliers = df_filtered["supplierName"].nunique()
    
    col1.metric("Total Invoices", f"{total_invoices:,}")
    col2.metric("Total Amount", f"£{total_amount:,.2f}")
    col3.metric("Average Invoice", f"£{avg_invoice:,.2f}")
    col4.metric("Unique Suppliers", f"{unique_suppliers}")
    
    st.markdown("---")
    
    # Visualizations
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Spending by Category")
        category_totals = df_filtered.groupby("category")["invoiceGross"].sum().sort_values(ascending=False)
        fig_category = px.bar(
            x=category_totals.values,
            y=category_totals.index,
            orientation='h',
            labels={"x": "Total Amount (£)", "y": "Category"},
            title="Total Spending by Category"
        )
        fig_category.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig_category, use_container_width=True)
    
    with col2:
        st.subheader("Top 10 Suppliers")
        supplier_totals = df_filtered.groupby("supplierName")["invoiceGross"].sum().sort_values(ascending=False).head(10)
        fig_supplier = px.bar(
            x=supplier_totals.values,
            y=supplier_totals.index,
            orientation='h',
            labels={"x": "Total Amount (£)", "y": "Supplier"},
            title="Top 10 Suppliers by Total Amount"
        )
        fig_supplier.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig_supplier, use_container_width=True)
    
    # Time series
    st.subheader("Spending Over Time")
    monthly_totals = df_filtered.groupby("yearMonth")["invoiceGross"].sum().reset_index()
    monthly_totals["yearMonth"] = pd.to_datetime(monthly_totals["yearMonth"])
    monthly_totals = monthly_totals.sort_values("yearMonth")
    
    fig_timeline = px.line(
        monthly_totals,
        x="yearMonth",
        y="invoiceGross",
        markers=True,
        labels={"yearMonth": "Month", "invoiceGross": "Total Amount (£)"},
        title="Monthly Spending Trend"
    )
    fig_timeline.update_layout(height=400)
    st.plotly_chart(fig_timeline, use_container_width=True)
    
    # Category breakdown over time
    st.subheader("Category Spending Over Time")
    category_monthly = df_filtered.groupby(["yearMonth", "category"])["invoiceGross"].sum().reset_index()
    category_monthly["yearMonth"] = pd.to_datetime(category_monthly["yearMonth"])
    category_monthly = category_monthly.sort_values("yearMonth")
    
    # Get top categories for clarity
    top_categories = df_filtered.groupby("category")["invoiceGross"].sum().sort_values(ascending=False).head(5).index
    category_monthly_filtered = category_monthly[category_monthly["category"].isin(top_categories)]
    
    fig_category_time = px.line(
        category_monthly_filtered,
        x="yearMonth",
        y="invoiceGross",
        color="category",
        markers=True,
        labels={"yearMonth": "Month", "invoiceGross": "Total Amount (£)", "category": "Category"},
        title="Top 5 Categories - Monthly Spending Trend"
    )
    fig_category_time.update_layout(height=400)
    st.plotly_chart(fig_category_time, use_container_width=True)
    
    # Invoice distribution
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Invoice Amount Distribution")
        fig_hist = px.histogram(
            df_filtered,
            x="invoiceGross",
            nbins=50,
            labels={"invoiceGross": "Invoice Amount (£)", "count": "Number of Invoices"},
            title="Distribution of Invoice Amounts"
        )
        fig_hist.update_layout(height=400)
        st.plotly_chart(fig_hist, use_container_width=True)
    
    with col2:
        st.subheader("Invoices by Month")
        monthly_counts = df_filtered.groupby("yearMonth").size().reset_index(name="count")
        monthly_counts["yearMonth"] = pd.to_datetime(monthly_counts["yearMonth"])
        monthly_counts = monthly_counts.sort_values("yearMonth")
        
        fig_counts = px.bar(
            monthly_counts,
            x="yearMonth",
            y="count",
            labels={"yearMonth": "Month", "count": "Number of Invoices"},
            title="Number of Invoices per Month"
        )
        fig_counts.update_layout(height=400)
        st.plotly_chart(fig_counts, use_container_width=True)
    
    # Data table
    st.markdown("---")
    st.subheader("Invoice Details")
    
    # Display options
    col1, col2 = st.columns(2)
    with col1:
        show_properties = st.checkbox("Show Property Details", value=False)
    with col2:
        rows_per_page = st.selectbox("Rows per page", [10, 25, 50, 100], index=1)
    
    # Prepare display dataframe
    display_df = df_filtered[[
        "invoiceDate", "category", "heading", "supplierName", 
        "supplierInvoice", "invoiceGross", "propertyAmount", "propertyCount"
    ]].copy()
    display_df = display_df.sort_values("invoiceDate", ascending=False)
    display_df["invoiceDate"] = display_df["invoiceDate"].dt.strftime("%Y-%m-%d")
    display_df.columns = [
        "Date", "Category", "Heading", "Supplier", 
        "Supplier Invoice", "Invoice Gross", "Property Amount", "Property Count"
    ]
    
    # Pagination
    total_rows = len(display_df)
    total_pages = (total_rows - 1) // rows_per_page + 1
    
    if total_pages > 1:
        page = st.number_input("Page", min_value=1, max_value=total_pages, value=1)
        start_idx = (page - 1) * rows_per_page
        end_idx = start_idx + rows_per_page
        display_df_page = display_df.iloc[start_idx:end_idx]
        st.caption(f"Showing {start_idx + 1}-{min(end_idx, total_rows)} of {total_rows} invoices")
    else:
        display_df_page = display_df
    
    st.dataframe(display_df_page, use_container_width=True, hide_index=True)
    
    # Download button
    csv = display_df.to_csv(index=False)
    st.download_button(
        label="Download filtered data as CSV",
        data=csv,
        file_name=f"invoice_data_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )

if __name__ == "__main__":
    main()
