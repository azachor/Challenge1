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

# Convert types
df["transactiondate"] = pd.to_datetime(df["transactiondate"], errors="coerce")
df["purchaseamount"] = pd.to_numeric(df["purchaseamount"], errors="coerce")
df["customersatisfaction"] = pd.to_numeric(df["customersatisfaction"], errors="coerce")

# Drop null revenue
df = df.dropna(subset=["purchaseamount"])

# -------------------- SIDEBAR FILTERS --------------------
st.sidebar.header("Filters")

def create_filter(column, label):
    unique_vals = sorted(df[column].dropna().astype(str).unique())
    options = ["All"] + unique_vals
    return st.sidebar.multiselect(label, options, default=["All"])

segment_filter = create_filter("label", "Customer Segment")
region_filter = create_filter("customerregion", "Customer Region")
category_filter = create_filter("productcategory", "Product Category")
channel_filter = create_filter("retailchannel", "Retail Channel")
age_filter = create_filter("customeragegroup", "Customer Age Group")
gender_filter = create_filter("customergender", "Customer Gender")

# -------------------- FILTERING LOGIC --------------------
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

col1, col2, col3, col4 = st.columns(4)

col1.metric("Total Revenue", f"${total_revenue:,.2f}" if not np.isnan(total_revenue) else "0")
col2.metric("Average Purchase", f"${avg_purchase:,.2f}" if not np.isnan(avg_purchase) else "0")
col3.metric("Total Transactions", f"{int(total_transactions)}")
col4.metric("Avg Customer Satisfaction", f"{avg_satisfaction:.2f}" if not np.isnan(avg_satisfaction) else "N/A")

# -------------------- AGGREGATIONS --------------------
def safe_groupby(data, group_col):
    if group_col not in data.columns:
        return pd.DataFrame()
    grouped = (
        data.dropna(subset=[group_col])
        .groupby(group_col)["purchaseamount"]
        .sum()
        .reset_index()
    )
    grouped = grouped.sort_values(by=group_col)
    return grouped

rev_segment = safe_groupby(filtered_df, "label")
rev_region = safe_groupby(filtered_df, "customerregion")
rev_channel = safe_groupby(filtered_df, "retailchannel")
rev_category = safe_groupby(filtered_df, "productcategory")

# Segment × Channel
seg_channel = (
    filtered_df.dropna(subset=["label", "retailchannel"])
    .groupby(["label", "retailchannel"])["purchaseamount"]
    .sum()
    .reset_index()
)

# -------------------- VISUALIZATIONS --------------------
if not rev_segment.empty:
    fig1 = px.bar(rev_segment, x="label", y="purchaseamount",
                  title="Revenue by Segment", template="plotly_white")
    st.plotly_chart(fig1, use_container_width=True)

if not rev_channel.empty:
    fig2 = px.bar(rev_channel, x="retailchannel", y="purchaseamount",
                  title="Revenue by Channel", template="plotly_white")
    st.plotly_chart(fig2, use_container_width=True)

if not rev_category.empty:
    fig3 = px.bar(rev_category, x="productcategory", y="purchaseamount",
                  title="Revenue by Product Category", template="plotly_white")
    st.plotly_chart(fig3, use_container_width=True)

if not rev_region.empty:
    fig4 = px.bar(rev_region, x="customerregion", y="purchaseamount",
                  title="Revenue by Region", template="plotly_white")
    st.plotly_chart(fig4, use_container_width=True)

if not seg_channel.empty:
    fig5 = px.bar(seg_channel, x="label", y="purchaseamount",
                  color="retailchannel",
                  title="Revenue by Segment × Channel",
                  template="plotly_white",
                  barmode="group")
    st.plotly_chart(fig5, use_container_width=True)

# -------------------- STRATEGIC INSIGHTS --------------------
st.markdown("## Strategic Insights")

if not rev_segment.empty:
    top_segment = rev_segment.loc[rev_segment["purchaseamount"].idxmax()]
    bottom_segment = rev_segment.loc[rev_segment["purchaseamount"].idxmin()]
else:
    top_segment = bottom_segment = None

if not rev_channel.empty:
    top_channel = rev_channel.loc[rev_channel["purchaseamount"].idxmax()]
    bottom_channel = rev_channel.loc[rev_channel["purchaseamount"].idxmin()]
else:
    top_channel = bottom_channel = None

decline_revenue = 0
if "label" in filtered_df.columns:
    decline_df = filtered_df[
        filtered_df["label"].astype(str).str.strip().str.lower() == "decline"
    ]
    decline_revenue = decline_df["purchaseamount"].sum()

strongest_combo = None
if not seg_channel.empty:
    strongest_combo = seg_channel.loc[seg_channel["purchaseamount"].idxmax()]

st.write(f"Highest revenue segment: {top_segment['label'] if top_segment is not None else 'N/A'}")
st.write(f"Lowest revenue segment: {bottom_segment['label'] if bottom_segment is not None else 'N/A'}")
st.write(f"Strongest channel: {top_channel['retailchannel'] if top_channel is not None else 'N/A'}")
st.write(f"Weakest channel: {bottom_channel['retailchannel'] if bottom_channel is not None else 'N/A'}")

if top_segment is not None:
    comparison = "significantly lower" if decline_revenue < top_segment["purchaseamount"] else "comparable"
    st.write(f"Decline segment revenue is {comparison} than the top segment.")

if strongest_combo is not None:
    st.write(
        f"Strongest Segment × Channel combination: "
        f"{strongest_combo['label']} via {strongest_combo['retailchannel']}"
    )

st.markdown("### Recommended Actions")
st.write("1. Prioritize investment in the highest-performing segment and channel combination.")
st.write("2. Develop targeted retention campaigns for the lowest-performing segment.")
st.write("3. Reallocate marketing budget toward high-revenue product categories and regions.")

# -------------------- DISPLAY FILTERED DATA --------------------
st.markdown("## Filtered Dataset")
st.dataframe(filtered_df.reset_index(drop=True))
