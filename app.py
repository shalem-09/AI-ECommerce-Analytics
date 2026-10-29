from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from ai.assistant import answer_business_question
from analytics.business_insights import generate_business_insights
from analytics.customer_segmentation import segment_customers
from analytics.data_cleaning import clean_customers, clean_dataframes
from analytics.kpi_calculations import compute_kpis
from analytics.sales_analysis import (
    build_monthly_sales,
    build_regional_sales,
    build_sales_by_category,
    build_top_products,
    get_order_status_breakdown,
)
from analytics.sales_forecasting import build_forecast_summary
from database.connection import load_analytics_data


st.set_page_config(page_title="E-Commerce Analytics HQ", page_icon="📊", layout="wide")


@st.cache_data(show_spinner=False)
def load_dashboard_data():
    orders, items, products, customers, source_status = load_analytics_data()
    orders, items, products, quality_report = clean_dataframes(orders, items, products)
    customers, customer_report = clean_customers(customers)
    for metric in (
        "missing_values",
        "duplicate_records",
        "invalid_records",
        "corrected_records",
        "requires_investigation",
    ):
        quality_report[metric] += customer_report[metric]
    if customer_report["invalid_records"] or customer_report["requires_investigation"]:
        quality_report["warnings"].append(
            f"Customers: {customer_report['invalid_records']} invalid rows."
        )
    return orders, items, products, customers, source_status, quality_report


def format_currency(value):
    if pd.isna(value):
        return "₹0.00"
    return f"₹{value:,.2f}"


def format_percent(value):
    if pd.isna(value):
        return "0.00%"
    return f"{value * 100:.2f}%"


def render_kpi_card(title, value, delta=None, accent="blue"):
    delta_text = ""
    if delta is not None:
        delta_text = f"<div style='font-size: 12px; color: #9ad0ff; margin-top: 8px;'>↗ {delta}</div>"
    st.markdown(
        f"""
        <div style="background: linear-gradient(135deg, rgba(17,24,39,0.9), rgba(15,118,110,0.32)); border: 1px solid rgba(96,165,250,0.2); border-radius: 18px; padding: 18px 18px 16px; margin-bottom: 12px; min-height: 120px; box-shadow: 0 10px 35px rgba(12,18,35,0.22);">
            <div style="font-size: 12px; color: #8eaacf; letter-spacing: 0.08em; text-transform: uppercase;">{title}</div>
            <div style="font-size: 32px; font-weight: 700; color: #f7fbff; margin-top: 12px; line-height: 1.1;">{value}</div>
            {delta_text}
        </div>
        """,
        unsafe_allow_html=True,
    )


def sidebar_filters(orders, products):
    st.sidebar.title("Analytics HQ")
    st.sidebar.caption("E-commerce performance")
    with st.sidebar:
        st.markdown("### Filters")
        status_options = sorted(orders["order_status"].dropna().unique()) if "order_status" in orders else []
        selected_status = st.multiselect(
            "Order status",
            status_options,
            default=status_options,
        )
        category_options = sorted(products["category"].dropna().unique()) if "category" in products else []
        selected_category = st.multiselect(
            "Category",
            options=category_options,
            default=category_options,
        )
        region_options = sorted(orders["shipping_state"].dropna().unique()) if "shipping_state" in orders else []
        selected_regions = st.multiselect(
            "Region",
            options=region_options,
            default=region_options,
        )
        if "order_date" in orders and not orders.empty:
            dates = pd.to_datetime(orders["order_date"], errors="coerce").dropna()
            if not dates.empty:
                date_range = st.date_input(
                    "Order date range",
                    value=(dates.min().date(), dates.max().date()),
                    min_value=dates.min().date(),
                    max_value=dates.max().date(),
                )
            else:
                date_range = ()
        else:
            date_range = ()
        st.markdown("---")
        if st.button("Refresh data", width="stretch"):
            load_dashboard_data.clear()
            st.rerun()
        st.markdown("---")
        st.caption("Local AI assistant is enabled without API keys.")
    return selected_status, selected_category, selected_regions, date_range


def render_chart(fig):
    fig.update_layout(
        paper_bgcolor="#0a1220",
        plot_bgcolor="#0a1220",
        font={"color": "#dfeaf9", "family": "Inter, sans-serif"},
        legend={"orientation": "h", "y": 1.12, "x": 0},
        margin={"l": 12, "r": 12, "t": 40, "b": 12},
        hovermode="x unified",
    )
    st.plotly_chart(fig, width="stretch")


def render_overview(df_orders, df_order_items, products, customers):
    kpis = compute_kpis(df_orders, df_order_items, products)
    overview = st.container()
    with overview:
        col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
        with col1:
            render_kpi_card("Net sales", format_currency(kpis.get("net_merchandise_sales", 0)))
        with col2:
            render_kpi_card("Est. gross profit", format_currency(kpis.get("estimated_gross_profit", 0)), delta=f"margin {format_percent(kpis.get('gross_profit_margin', 0))}")
        with col3:
            render_kpi_card("Completed orders", str(int(kpis.get("completed_orders", 0))))
        with col4:
            render_kpi_card("Avg order value", format_currency(kpis.get("average_order_value", 0)))
        with col5:
            render_kpi_card("Units sold", str(int(kpis.get("units_sold", 0))))
        with col6:
            render_kpi_card("Sales growth", format_percent(kpis.get("month_over_month_growth", 0)), delta="month over month")
        with col7:
            render_kpi_card("Avg. line discount", format_percent(kpis.get("average_discount", 0)))

        st.markdown("### Executive overview")
        c1, c2 = st.columns([2, 1])
        with c1:
            monthly = build_monthly_sales(df_orders, df_order_items, products)
            fig = px.line(
                monthly,
                x="order_month",
                y="net_sales",
                title="Monthly sales trend",
                color_discrete_sequence=["#38bdf8"],
            )
            render_chart(fig)
        with c2:
            status_breakdown = get_order_status_breakdown(df_orders)
            fig = px.pie(
                status_breakdown,
                names="order_status",
                values="order_count",
                hole=0.45,
                color_discrete_sequence=["#38bdf8", "#2dd4bf", "#f59e0b", "#f97316", "#94a3b8"],
                title="Order status mix",
            )
            render_chart(fig)

        c1, c2 = st.columns(2)
        with c1:
            cat_sales = build_sales_by_category(df_orders, df_order_items, products)
            fig = px.bar(
                cat_sales,
                x="category",
                y="net_sales",
                title="Sales by category",
                color="category",
                color_discrete_sequence=px.colors.sequential.Blues_r[:6],
            )
            render_chart(fig)
        with c2:
            reg_sales = build_regional_sales(df_orders, df_order_items, products)
            fig = px.bar(
                reg_sales,
                x="state",
                y="net_sales",
                title="Sales by region",
                color="state",
                color_discrete_sequence=px.colors.sequential.Teal_r[:6],
            )
            render_chart(fig)

        st.markdown("---")
        st.subheader("Business insights")
        insights = generate_business_insights(df_orders, df_order_items, products)
        for insight in insights[:4]:
            st.info(f"{insight['headline']} — {insight['summary']}")


def render_product_analysis(df_orders, df_order_items, products):
    st.markdown("### Product analytics")
    top_products = build_top_products(df_orders, df_order_items, products, limit=10)
    fig = px.bar(
        top_products,
        x="product_name",
        y="net_sales",
        title="Top selling products",
        color="product_name",
        color_discrete_sequence=px.colors.qualitative.Bold,
    )
    render_chart(fig)

    c1, c2 = st.columns(2)
    with c1:
        df = top_products.head(8)
        st.dataframe(
            df[[
                "product_name",
                "units_sold",
                "net_sales",
                "estimated_gross_profit",
                "average_discount_percent",
            ]].sort_values("net_sales", ascending=False),
            width="stretch",
        )
        st.download_button(
            "Download product analytics CSV",
            top_products.to_csv(index=False).encode("utf-8"),
            "product_analytics.csv",
            "text/csv",
        )
    with c2:
        category_summary = build_sales_by_category(df_orders, df_order_items, products)
        fig = px.bar(
            category_summary,
            x="category",
            y="estimated_gross_profit",
            title="Category profitability",
            color="category",
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        render_chart(fig)
        st.dataframe(category_summary, width="stretch")


def render_customer_analysis(df_orders, df_order_items, products, customers):
    st.markdown("### Customer analytics")
    seg = segment_customers(df_orders, df_order_items, products, customers)
    if seg.empty:
        st.warning("No customer segmentation data is available for the current selection.")
    else:
        kpis = compute_kpis(df_orders, df_order_items, products)
        col1, col2 = st.columns(2)
        col1.metric("Repeat customer rate", format_percent(kpis["repeat_customer_rate"]))
        col2.metric("Customers in RFM analysis", int(len(seg)))
        segment_summary = seg.groupby("segment", as_index=False).agg(
            customer_count=("customer_id", "nunique"),
            total_spend=("total_spend", "sum"),
            average_spend=("total_spend", "mean"),
        ).sort_values("total_spend", ascending=False)
        st.dataframe(segment_summary, width="stretch")
        fig = px.scatter(
            seg,
            x="total_spend",
            y="purchase_frequency",
            color="segment",
            size="total_spend",
            title="Customer segmentation",
            color_discrete_sequence=["#38bdf8", "#2dd4bf", "#a78bfa"],
        )
        render_chart(fig)
    st.dataframe(seg.head(10), width="stretch")
    if not seg.empty:
        st.download_button(
            "Download customer segments CSV",
            seg.to_csv(index=False).encode("utf-8"),
            "customer_segments.csv",
            "text/csv",
        )


def render_regional_analysis(df_orders, df_order_items, products):
    st.markdown("### Regional analytics")
    reg = build_regional_sales(df_orders, df_order_items, products)
    st.dataframe(reg.head(20), width="stretch")
    fig = px.choropleth(
        reg,
        locations="state",
        locationmode="USA-states",
        color="net_sales",
        scope="usa",
        title="Regional sales performance",
        color_continuous_scale="Teal",
    )
    render_chart(fig)


def render_forecasting(df_orders, df_order_items, products):
    st.markdown("### Sales forecasting")
    forecast = build_forecast_summary(df_orders, df_order_items, products)
    if forecast.empty or "actual" not in forecast.columns:
        st.warning("Forecasting could not run because the dataset is too short or data is incomplete.")
        return
    fig = px.line(forecast, x="period", y=["actual", "predicted"], title="Actual vs predicted sales")
    render_chart(fig)
    st.write("### Forecast metrics")
    metric_df = forecast[
        ["model", "mae", "rmse", "mape", "baseline_model", "baseline_mae", "baseline_rmse"]
    ].drop_duplicates().reset_index(drop=True)
    st.dataframe(metric_df, width="stretch")
    future = forecast[forecast["actual"].isna()]
    st.caption("Monthly completed net sales; linear regression is compared with a last-observed-month baseline. Forecasts are estimates and may not capture seasonality or business changes.")
    st.dataframe(future[["period", "predicted"]], width="stretch")


def render_quality(quality_report):
    st.markdown("### Data quality")
    cols = st.columns(5)
    metrics = [
        ("Missing values", quality_report["missing_values"]),
        ("Duplicate records", quality_report["duplicate_records"]),
        ("Invalid records", quality_report["invalid_records"]),
        ("Corrected records", quality_report["corrected_records"]),
        ("Needs review", quality_report["requires_investigation"]),
    ]
    for col, (label, value) in zip(cols, metrics):
        with col:
            st.metric(label, value)
    if quality_report["warnings"]:
        for warning in quality_report["warnings"]:
            st.warning(warning)
    else:
        st.success("No critical data quality issues were flagged in the current analytical frame.")


def render_ai_assistant(df_orders, df_order_items, products, customers):
    st.markdown("### AI business assistant")
    suggested = [
        "Which category generated the highest estimated gross profit?",
        "What were the monthly sales trends?",
        "Which five products sold the most units?",
        "Which state generated the highest sales?",
    ]
    for question in suggested:
        if st.button(question, key=question):
            st.session_state["assistant_question"] = question
            st.session_state["assistant_input"] = question

    question = st.text_input(
        "Ask a business question",
        value=st.session_state.get(
            "assistant_question",
            "Which category generated the highest estimated gross profit?",
        ),
        key="assistant_input",
    )
    if st.button("Generate answer"):
        answer = answer_business_question(question, {"orders": df_orders, "order_items": df_order_items, "products": products, "customers": customers})
        st.markdown("#### Answer")
        st.write(answer)


def main():
    st.markdown(
        """
        <style>
        html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"], [data-testid="stSidebar"] {
            background: #07111d;
            color: #e5f1ff;
        }
        .stApp {
            background: radial-gradient(circle at top left, rgba(14,165,233,0.16), transparent 28%), #07111d;
        }
        [data-testid="stSidebar"] {
            background: rgba(9, 17, 29, 0.96);
            border-right: 1px solid rgba(148, 163, 184, 0.2);
        }
        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 1.5rem;
        }
        .stTabs [role="tablist"] {
            background: rgba(15, 23, 42, 0.8);
            border-radius: 12px;
            padding: 6px;
            border: 1px solid rgba(148,163,184,0.18);
        }
        .stTabs [role="tab"] {
            color: #dfeaf9;
            font-weight: 600;
        }
        .stTabs [role="tab"][aria-selected="true"] {
            background: linear-gradient(135deg, rgba(56,189,248,0.2), rgba(45,212,191,0.18));
            border-radius: 10px;
        }
        div[data-testid="stDataFrame"] {
            background: rgba(15, 23, 42, 0.78);
            border: 1px solid rgba(148,163,184,0.1);
            border-radius: 12px;
        }
        .stMetric, .stDataFrame, table {
            color: #e6f3ff;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div style='padding: 0 0 18px 0;'>
            <div style='font-size: 12px; letter-spacing: 0.16em; text-transform: uppercase; color: #67e8f9;'>AI E-commerce analytics</div>
            <div style='font-size: 36px; font-weight: 700; color: #f8fbff; margin-top: 8px;'>Executive intelligence dashboard</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.spinner("Loading analytics from MySQL..."):
        orders, order_items, products, customers, source_status, quality_report = load_dashboard_data()
    if "could not be loaded" in source_status or "not configured" in source_status:
        st.sidebar.error(source_status)
    else:
        st.sidebar.info(source_status)

    if orders.empty and order_items.empty and products.empty:
        st.warning(
            "No database rows are available for the dashboard. Initialize the MySQL schema "
            "and load authorized data, then select **Refresh data**."
        )
        return

    filtered_status, selected_category, selected_regions, date_range = sidebar_filters(orders, products)
    orders = orders[orders["order_status"].isin(filtered_status)]
    if selected_category:
        products = products[products["category"].isin(selected_category)]
        product_ids = products["product_id"].tolist()
        order_items = order_items[order_items["product_id"].isin(product_ids)]
        filtered_item_ids = order_items["order_id"].unique().tolist()
        orders = orders[orders["order_id"].isin(filtered_item_ids)]
    else:
        products = products.iloc[0:0]
        order_items = order_items.iloc[0:0]
        orders = orders.iloc[0:0]

    if selected_regions:
        orders = orders[orders["shipping_state"].isin(selected_regions)]
    else:
        orders = orders.iloc[0:0]
    if len(date_range) == 2:
        start_date, end_date = (pd.Timestamp(value) for value in date_range)
        order_dates = pd.to_datetime(orders["order_date"], errors="coerce")
        orders = orders.loc[
            order_dates.ge(start_date)
            & order_dates.lt(end_date + pd.Timedelta(days=1))
        ]

    order_ids = orders["order_id"].tolist()
    filtered_items = order_items[order_items["order_id"].isin(order_ids)]
    tabs = st.tabs(["Executive Overview", "Sales Analytics", "Product Analytics", "Customer Analytics", "Regional Analytics", "Sales Forecasting", "Data Quality", "AI Business Assistant"])

    with tabs[0]:
        render_overview(orders, filtered_items, products, customers)
    with tabs[1]:
        st.markdown("### Sales analytics")
        monthly_sales = build_monthly_sales(orders, filtered_items, products)
        if monthly_sales.empty:
            st.info("No completed net sales are available for the selected filters.")
        else:
            render_chart(px.line(monthly_sales, x="order_month", y="net_sales", title="Monthly net sales"))
            st.dataframe(monthly_sales, width="stretch")
            st.download_button(
                "Download monthly sales CSV",
                monthly_sales.to_csv(index=False).encode("utf-8"),
                "monthly_sales.csv",
                "text/csv",
            )
    with tabs[2]:
        render_product_analysis(orders, filtered_items, products)
    with tabs[3]:
        render_customer_analysis(orders, filtered_items, products, customers)
    with tabs[4]:
        render_regional_analysis(orders, filtered_items, products)
    with tabs[5]:
        render_forecasting(orders, filtered_items, products)
    with tabs[6]:
        render_quality(quality_report)
    with tabs[7]:
        render_ai_assistant(orders, filtered_items, products, customers)


if __name__ == "__main__":
    main()
