import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# -------------------- PAGE CONFIG --------------------
st.set_page_config(layout="wide")
st.title("NovaRetail Customer Intelligence Dashboard")
st.subheader("Revenue Optimization and Customer Segment Analytics")

# -------------------- LOAD DATA --------------------
try:
    df = pd.read_excel("NR_dataset.xlsx")
except FileNotFoundError:
    st.error("Dataset file not found in repository.")
    st.stop()
except Exception:
    st.error("Error loading dataset.")
    st.stop()

# Normalize column names
df.columns = (
    df.columns.str.strip()
    .str.lower()
    .str.replace(" ", "_", regex=False)
)

required_fields = [
    "label",
    "customerid",
    "transactionid",
    "transactiondate",
    "productcategory",
    "purchaseamount",
    "customeragegroup",
    "customergender",
    "customerregion",
    "customersatisfaction",
    "retailchannel",
]

missing_fields = [col for col in required_fields if col not in df.columns]

if missing_fields:
    st.error(f"Missing required logical fields: {missing_fields}")
    st.write(df.columns)
    st.stop()

# Type conversions
df["transactiondate"] = pd.to_datetime(df["transactiondate"], errors="coerce")
df["purchaseamount"] = pd.to_numeric(df["purchaseamount"], errors="coerce")
df["customersatisfaction"] = pd.to_numeric(df["customersatisfaction"], errors="coerce")

df = df.dropna(subset=["purchaseamount"])

# -------------------- SIDEBAR FILTERS --------------------
st.sidebar.header("Filters")

def create_filter(column, label):
    values = sorted(df[column].dropna().astype(str).unique())
    options = ["All"] + values
    return st.sidebar.multiselect(label, options, default=["All"])

segment_filter = create_filter("label", "Customer Segment")
region_filter = create_filter("customerregion", "Customer Region")
category_filter = create_filter("productcategory", "Product Category")
channel_filter = create_filter("retailchannel", "Retail Channel")
age_filter = create_filter("customeragegroup", "Customer Age Group")
gender_filter = create_filter("customergender", "Customer Gender")

# -------------------- FILTERING --------------------
filtered_df = df.copy()

def apply_filter(data, column, selected):
    if "All" in selected:
        return data
    return data[data[column].astype(str).isin(selected)]

filtered_df = apply_filter(filtered_df, "label", segment_filter)
filtered_df = apply_filter(filtered_df, "customerregion", region_filter)
filtered_df = apply_filter(filtered_df, "productcategory", category_filter)
filtered_df = apply_filter(filtered_df, "retailchannel", channel_filter)
filtered_df = apply_filter(filtered_df, "customeragegroup", age_filter)
filtered_df = apply_filter(filtered_df, "customergender", gender_filter)

if filtered_df.empty:
    st.warning("No data matches selected filters.")
    st.stop()

# -------------------- KPIs --------------------
total_revenue = filtered_df["purchaseamount"].sum()
avg_purchase = filtered_df["purchaseamount"].mean()
total_transactions = filtered_df["transactionid"].nunique()
avg_satisfaction = filtered_df["customersatisfaction"].mean()

k1, k2, k3, k4 = st.columns(4)

k1.metric("Total Revenue", f"${total_revenue:,.2f}" if not np.isnan(total_revenue) else "$0.00")
k2.metric("Average Purchase Amount", f"${avg_purchase:,.2f}" if not np.isnan(avg_purchase) else "$0.00")
k3.metric("Total Transactions", f"{int(total_transactions)}")
k4.metric("Average Customer Satisfaction", f"{avg_satisfaction:.2f}" if not np.isnan(avg_satisfaction) else "N/A")

# -------------------- AGGREGATIONS --------------------
def grouped_revenue(data, group_col):
    if group_col not in data.columns:
        return pd.DataFrame()
    result = (
        data.dropna(subset=[group_col])
        .groupby(group_col)["purchaseamount"]
        .sum()
        .reset_index()
    )
    result = result.sort_values(by=group_col)
    return result

rev_segment = grouped_revenue(filtered_df, "label")
rev_region = grouped_revenue(filtered_df, "customerregion")
rev_channel = grouped_revenue(filtered_df, "retailchannel")
rev_category = grouped_revenue(filtered_df, "productcategory")

seg_channel = (
    filtered_df.dropna(subset=["label", "retailchannel"])
    .groupby(["label", "retailchannel"])["purchaseamount"]
    .sum()
    .reset_index()
)

# -------------------- VISUALIZATIONS --------------------
if not rev_segment.empty:
    fig1 = px.bar(
        rev_segment,
        x="label",
        y="purchaseamount",
        title="Revenue by Customer Segment",
        labels={"label": "Customer Segment", "purchaseamount": "Revenue"},
        template="plotly_white"
    )
    st.plotly_chart(fig1, use_container_width=True)

if not rev_channel.empty:
    fig2 = px.bar(
        rev_channel,
        x="retailchannel",
        y="purchaseamount",
        title="Revenue by Retail Channel",
        labels={"retailchannel": "Retail Channel", "purchaseamount": "Revenue"},
        template="plotly_white"
    )
    st.plotly_chart(fig2, use_container_width=True)

if not rev_category.empty:
    fig3 = px.bar(
        rev_category,
        x="productcategory",
        y="purchaseamount",
        title="Revenue by Product Category",
        labels={"productcategory": "Product Category", "purchaseamount": "Revenue"},
        template="plotly_white"
    )
    st.plotly_chart(fig3, use_container_width=True)

if not rev_region.empty:
    fig4 = px.bar(
        rev_region,
        x="customerregion",
        y="purchaseamount",
        title="Revenue by Customer Region",
        labels={"customerregion": "Customer Region", "purchaseamount": "Revenue"},
        template="plotly_white"
    )
    st.plotly_chart(fig4, use_container_width=True)

if not seg_channel.empty:
    pivot = seg_channel.pivot(index="label", columns="retailchannel", values="purchaseamount").fillna(0)
    fig5 = px.imshow(
        pivot,
        text_auto=True,
        aspect="auto",
        title="Revenue Heatmap: Customer Segment × Retail Channel",
        labels=dict(x="Retail Channel", y="Customer Segment", color="Revenue"),
        template="plotly_white"
    )
    st.plotly_chart(fig5, use_container_width=True)

# -------------------- STRATEGIC INSIGHTS --------------------
st.markdown("## Strategic Insights")

top_segment = bottom_segment = None
top_channel = bottom_channel = None
strongest_combo = None

if not rev_segment.empty:
    top_segment = rev_segment.loc[rev_segment["purchaseamount"].idxmax()]
    bottom_segment = rev_segment.loc[rev_segment["purchaseamount"].idxmin()]

if not rev_channel.empty:
    top_channel = rev_channel.loc[rev_channel["purchaseamount"].idxmax()]
    bottom_channel = rev_channel.loc[rev_channel["purchaseamount"].idxmin()]

if not seg_channel.empty:
    strongest_combo = seg_channel.loc[seg_channel["purchaseamount"].idxmax()]

decline_revenue = 0
decline_df = filtered_df[
    filtered_df["label"].astype(str).str.strip().str.lower() == "decline"
]
if not decline_df.empty:
    decline_revenue = decline_df["purchaseamount"].sum()

if top_segment is not None:
    st.write(f"Highest revenue segment: {top_segment['label']}")
if bottom_segment is not None:
    st.write(f"Lowest revenue segment: {bottom_segment['label']}")
if top_channel is not None:
    st.write(f"Strongest retail channel: {top_channel['retailchannel']}")
if bottom_channel is not None:
    st.write(f"Weakest retail channel: {bottom_channel['retailchannel']}")

if top_segment is not None:
    if decline_revenue < top_segment["purchaseamount"]:
        st.write("Decline segment revenue is significantly lower than the top-performing segment.")
    else:
        st.write("Decline segment revenue is comparable to the top-performing segment.")

if strongest_combo is not None:
    st.write(
        f"Strongest Segment × Channel combination: "
        f"{strongest_combo['label']} via {strongest_combo['retailchannel']}"
    )

st.markdown("### Data-Driven Strategic Actions")
st.write("1. Allocate additional marketing investment toward the highest revenue segment and its strongest-performing channel.")
st.write("2. Design targeted retention strategies for the lowest revenue segment to mitigate potential customer decline.")
st.write("3. Rebalance channel and product focus toward combinations generating the highest revenue concentration.")

decline_percentage = (
    (decline_revenue / total_revenue) * 100
    if total_revenue > 0
    else 0
)

st.subheader("Early Warning Indicator")

if decline_percentage > 25:
    st.error(
        f"Decline Segment Revenue is {decline_percentage:.2f}% of total revenue."
    )
else:
    st.success(
        f"Decline Segment Revenue is {decline_percentage:.2f}% of total revenue."
    )
    

# -------------------- DISPLAY DATA --------------------
st.markdown("## Filtered Dataset")
st.dataframe(filtered_df.reset_index(drop=True))
