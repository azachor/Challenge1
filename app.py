# app.py

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# -----------------------------------
# STEP 2 — Page Config
# -----------------------------------
st.set_page_config(layout="wide")
st.title("NovaRetail Customer Intelligence Dashboard")
st.subheader("Revenue Optimization and Customer Segment Analytics")

# -----------------------------------
# STEP 3 — Load Data
# -----------------------------------
def normalize_columns(df):
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "_", regex=False)
    )
    return df

def match_required_fields(df_columns):
    required = [
        "idx",
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
    matched = {}
    missing = []

    for logical in required:
        found = None
        for col in df_columns:
            if col.replace("_", "") == logical:
                found = col
                break
        if found:
            matched[logical] = found
        else:
            missing.append(logical)

    return matched, missing

try:
    df = pd.read_excel("NR_dataset.xlsx")
except FileNotFoundError:
    st.error("Dataset file not found in repository.")
    st.stop()
except Exception as e:
    st.error(f"Error loading dataset: {e}")
    st.stop()

df = normalize_columns(df)
matched_fields, missing_fields = match_required_fields(df.columns)

if missing_fields:
    st.error(f"Missing required logical fields: {missing_fields}")
    st.write(df.columns)
    st.stop()

rename_map = {v: k for k, v in matched_fields.items()}
df = df.rename(columns=rename_map)

df["transactiondate"] = pd.to_datetime(df["transactiondate"], errors="coerce")
df["purchaseamount"] = pd.to_numeric(df["purchaseamount"], errors="coerce")
df["customersatisfaction"] = pd.to_numeric(df["customersatisfaction"], errors="coerce")

df = df.dropna(subset=["purchaseamount"])

# -----------------------------------
# STEP 4 — Sidebar Filters
# -----------------------------------
st.sidebar.header("Filters")

def create_filter(field, label):
    if field not in df.columns:
        return ["All"]
    options = sorted(df[field].dropna().astype(str).unique())
    options = ["All"] + options
    return st.sidebar.multiselect(label, options, default=["All"])

segment_filter = create_filter("label", "Customer Segment")
region_filter = create_filter("customerregion", "Customer Region")
category_filter = create_filter("productcategory", "Product Category")
channel_filter = create_filter("retailchannel", "Retail Channel")
age_filter = create_filter("customeragegroup", "Customer Age Group")
gender_filter = create_filter("customergender", "Customer Gender")

# -----------------------------------
# STEP 5 — Filtering Logic
# -----------------------------------
filtered_df = df.copy()

def apply_filter(data, field, selection):
    if field not in data.columns:
        return data
    if "All" in selection:
        return data
    return data[data[field].astype(str).isin(selection)]

filtered_df = apply_filter(filtered_df, "label", segment_filter)
filtered_df = apply_filter(filtered_df, "customerregion", region_filter)
filtered_df = apply_filter(filtered_df, "productcategory", category_filter)
filtered_df = apply_filter(filtered_df, "retailchannel", channel_filter)
filtered_df = apply_filter(filtered_df, "customeragegroup", age_filter)
filtered_df = apply_filter(filtered_df, "customergender", gender_filter)

if filtered_df.empty:
    st.warning("No data matches selected filters.")
    st.stop()

# -----------------------------------
# STEP 6 — KPI Calculations
# -----------------------------------
total_revenue = filtered_df["purchaseamount"].sum()
avg_purchase = filtered_df["purchaseamount"].mean()
total_transactions = filtered_df["transactionid"].nunique() if "transactionid" in filtered_df.columns else 0
avg_satisfaction = filtered_df["customersatisfaction"].mean()

k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Revenue", f"${total_revenue:,.2f}")
k2.metric("Average Purchase Amount", f"${avg_purchase:,.2f}" if not np.isnan(avg_purchase) else "N/A")
k3.metric("Total Transactions", total_transactions)
k4.metric("Average Customer Satisfaction", f"{avg_satisfaction:.2f}" if not np.isnan(avg_satisfaction) else "N/A")

# -----------------------------------
# STEP 7 — Aggregations
# -----------------------------------
def safe_group_sum(data, group_col):
    if group_col not in data.columns:
        return pd.DataFrame(columns=[group_col, "purchaseamount"])
    result = (
        data.dropna(subset=[group_col])
        .groupby(group_col)["purchaseamount"]
        .sum()
        .reset_index()
        .sort_values(group_col)
    )
    return result

rev_by_segment = safe_group_sum(filtered_df, "label")
rev_by_region = safe_group_sum(filtered_df, "customerregion")
rev_by_channel = safe_group_sum(filtered_df, "retailchannel")
rev_by_category = safe_group_sum(filtered_df, "productcategory")

# Time-based aggregation
time_df = filtered_df.dropna(subset=["transactiondate"]).copy()

if not time_df.empty:
    time_df["year_month"] = (
        time_df["transactiondate"]
        .dt.to_period("M")
        .dt.to_timestamp()
    )

    monthly_trend = (
        time_df.groupby("year_month")["purchaseamount"]
        .sum()
        .reset_index()
        .sort_values("year_month")
    )
else:
    monthly_trend = pd.DataFrame(columns=["year_month", "purchaseamount"])

# Decline trend
decline_df = time_df[
    time_df["label"].astype(str).str.strip().str.lower() == "decline"
]

if not decline_df.empty:
    decline_trend = (
        decline_df.groupby("year_month")["purchaseamount"]
        .sum()
        .reset_index()
        .sort_values("year_month")
    )
else:
    decline_trend = pd.DataFrame(columns=["year_month", "purchaseamount"])

# -----------------------------------
# STEP 8 — Visualizations
# -----------------------------------
def style(fig):
    fig.update_layout(template="plotly_white", autosize=True)
    return fig

c1, c2 = st.columns(2)

with c1:
    if not rev_by_segment.empty:
        fig = px.bar(rev_by_segment, x="label", y="purchaseamount", title="Revenue by Segment")
        st.plotly_chart(style(fig), use_container_width=True)

with c2:
    if not rev_by_channel.empty:
        fig = px.bar(rev_by_channel, x="retailchannel", y="purchaseamount", title="Revenue by Channel")
        st.plotly_chart(style(fig), use_container_width=True)

c3, c4 = st.columns(2)

with c3:
    if not rev_by_category.empty:
        fig = px.bar(rev_by_category, x="productcategory", y="purchaseamount", title="Revenue by Product Category")
        st.plotly_chart(style(fig), use_container_width=True)

with c4:
    if not rev_by_region.empty:
        fig = px.bar(rev_by_region, x="customerregion", y="purchaseamount", title="Revenue by Region")
        st.plotly_chart(style(fig), use_container_width=True)

if not monthly_trend.empty:
    fig = px.line(monthly_trend, x="year_month", y="purchaseamount", title="Monthly Revenue Trend")
    st.plotly_chart(style(fig), use_container_width=True)

if not decline_trend.empty:
    fig = px.line(decline_trend, x="year_month", y="purchaseamount", title="Decline Segment Revenue Trend")
    st.plotly_chart(style(fig), use_container_width=True)

# -----------------------------------
# STEP 9 — Strategic Insights
# -----------------------------------
st.markdown("## Strategic Insights")

if not rev_by_segment.empty:
    top_segment = rev_by_segment.sort_values("purchaseamount", ascending=False).iloc[0]
    bottom_segment = rev_by_segment.sort_values("purchaseamount").iloc[0]
else:
    top_segment = bottom_segment = None

if not rev_by_channel.empty:
    top_channel = rev_by_channel.sort_values("purchaseamount", ascending=False).iloc[0]
else:
    top_channel = None

decline_trend_direction = "insufficient data"
if len(decline_trend) >= 2:
    first = decline_trend["purchaseamount"].iloc[0]
    last = decline_trend["purchaseamount"].iloc[-1]
    if last > first:
        decline_trend_direction = "increasing"
    elif last < first:
        decline_trend_direction = "decreasing"
    else:
        decline_trend_direction = "stable"

if top_segment is not None and bottom_segment is not None and top_channel is not None:
    st.write(f"• Highest revenue segment: {top_segment['label']} (${top_segment['purchaseamount']:,.2f})")
    st.write(f"• Lowest performing segment: {bottom_segment['label']} (${bottom_segment['purchaseamount']:,.2f})")
    st.write(f"• Decline segment revenue trend is {decline_trend_direction}.")
    st.write(f"• Strongest performing channel: {top_channel['retailchannel']} (${top_channel['purchaseamount']:,.2f})")

    st.write("### Recommended Strategic Actions")
    st.write(f"1. Increase investment in the {top_segment['label']} segment to amplify revenue momentum.")
    st.write(f"2. Deploy targeted retention initiatives for the {bottom_segment['label']} segment to mitigate revenue risk.")
    st.write(f"3. Scale marketing efforts in the {top_channel['retailchannel']} channel while monitoring Decline segment shifts.")

# -----------------------------------
# STEP 10 — Display Filtered Data
# -----------------------------------
st.markdown("## Filtered Dataset")
st.dataframe(filtered_df.reset_index(drop=True))
