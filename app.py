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
        .str.replace(" ", "_")
    )
    return df

def match_required_fields(df_columns):
    logical_fields = {
        "idx": ["idx"],
        "label": ["label"],
        "customerid": ["customerid"],
        "transactionid": ["transactionid"],
        "transactiondate": ["transactiondate"],
        "productcategory": ["productcategory"],
        "purchaseamount": ["purchaseamount"],
        "customeragegroup": ["customeragegroup"],
        "customergender": ["customergender"],
        "customerregion": ["customerregion"],
        "customersatisfaction": ["customersatisfaction"],
        "retailchannel": ["retailchannel"],
    }

    matched = {}
    missing = []

    for key, variants in logical_fields.items():
        found = None
        for col in df_columns:
            if col.replace("_", "") == key:
                found = col
                break
        if found:
            matched[key] = found
        else:
            missing.append(key)

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
    st.write("Actual dataset columns:")
    st.write(df.columns)
    st.stop()

# Rename matched columns to logical names
df = df.rename(columns={
    matched_fields["transactiondate"]: "transactiondate",
    matched_fields["purchaseamount"]: "purchaseamount",
    matched_fields["customersatisfaction"]: "customersatisfaction",
    matched_fields["label"]: "label",
    matched_fields["customerregion"]: "customerregion",
    matched_fields["productcategory"]: "productcategory",
    matched_fields["retailchannel"]: "retailchannel",
    matched_fields["customeragegroup"]: "customeragegroup",
    matched_fields["customergender"]: "customergender",
    matched_fields["transactionid"]: "transactionid",
    matched_fields["customerid"]: "customerid",
})

# Convert data types
df["transactiondate"] = pd.to_datetime(df["transactiondate"], errors="coerce")
df["purchaseamount"] = pd.to_numeric(df["purchaseamount"], errors="coerce")
df["customersatisfaction"] = pd.to_numeric(df["customersatisfaction"], errors="coerce")

df = df.dropna(subset=["purchaseamount"])

# -----------------------------------
# STEP 4 — Sidebar Filters
# -----------------------------------
st.sidebar.header("Filters")

def create_filter(field_name, display_name):
    options = sorted(df[field_name].dropna().astype(str).unique())
    options_with_all = ["All"] + options
    selection = st.sidebar.multiselect(display_name, options_with_all, default=["All"])
    return selection

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
avg_purchase = filtered_df["purchaseamount"].mean() if len(filtered_df) > 0 else 0
total_transactions = filtered_df["transactionid"].nunique()
avg_satisfaction = filtered_df["customersatisfaction"].mean()

kpi1, kpi2, kpi3, kpi4 = st.columns(4)

kpi1.metric("Total Revenue", f"${total_revenue:,.2f}")
kpi2.metric("Average Purchase Amount", f"${avg_purchase:,.2f}" if not np.isnan(avg_purchase) else "N/A")
kpi3.metric("Total Transactions", total_transactions)
kpi4.metric("Average Customer Satisfaction", f"{avg_satisfaction:.2f}" if not np.isnan(avg_satisfaction) else "N/A")

# -----------------------------------
# STEP 7 — Aggregations
# -----------------------------------
rev_by_segment = (
    filtered_df.groupby("label", dropna=True)["purchaseamount"]
    .sum()
    .reset_index()
    .sort_values("label")
)

rev_by_region = (
    filtered_df.groupby("customerregion", dropna=True)["purchaseamount"]
    .sum()
    .reset_index()
    .sort_values("customerregion")
)

rev_by_channel = (
    filtered_df.groupby("retailchannel", dropna=True)["purchaseamount"]
    .sum()
    .reset_index()
    .sort_values("retailchannel")
)

rev_by_category = (
    filtered_df.groupby("productcategory", dropna=True)["purchaseamount"]
    .sum()
    .reset_index()
    .sort_values("productcategory")
)

filtered_df["year_month"] = filtered_df["transactiondate"].dt.to_period("M").astype(str)

monthly_trend = (
    filtered_df.groupby("year_month")["purchaseamount"]
    .sum()
    .reset_index()
    .sort_values("year_month")
)

decline_df = filtered_df[filtered_df["label"].str.lower() == "decline"]

decline_trend = (
    decline_df.groupby("year_month")["purchaseamount"]
    .sum()
    .reset_index()
    .sort_values("year_month")
)

# -----------------------------------
# STEP 8 — Visualizations
# -----------------------------------
def style_fig(fig):
    fig.update_layout(
        template="plotly_white",
        autosize=True
    )
    return fig

col1, col2 = st.columns(2)

with col1:
    fig1 = px.bar(rev_by_segment, x="label", y="purchaseamount",
                  title="Revenue by Segment")
    st.plotly_chart(style_fig(fig1), use_container_width=True)

with col2:
    fig2 = px.bar(rev_by_channel, x="retailchannel", y="purchaseamount",
                  title="Revenue by Channel")
    st.plotly_chart(style_fig(fig2), use_container_width=True)

col3, col4 = st.columns(2)

with col3:
    fig3 = px.bar(rev_by_category, x="productcategory", y="purchaseamount",
                  title="Revenue by Product Category")
    st.plotly_chart(style_fig(fig3), use_container_width=True)

with col4:
    fig4 = px.bar(rev_by_region, x="customerregion", y="purchaseamount",
                  title="Revenue by Region")
    st.plotly_chart(style_fig(fig4), use_container_width=True)

fig5 = px.line(monthly_trend, x="year_month", y="purchaseamount",
               title="Monthly Revenue Trend")
st.plotly_chart(style_fig(fig5), use_container_width=True)

fig6 = px.line(decline_trend, x="year_month", y="purchaseamount",
               title="Decline Segment Revenue Trend")
st.plotly_chart(style_fig(fig6), use_container_width=True)

# -----------------------------------
# STEP 9 — Strategic Insights Section
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

decline_trend_direction = "stable"
if len(decline_trend) >= 2:
    if decline_trend["purchaseamount"].iloc[-1] > decline_trend["purchaseamount"].iloc[0]:
        decline_trend_direction = "increasing"
    elif decline_trend["purchaseamount"].iloc[-1] < decline_trend["purchaseamount"].iloc[0]:
        decline_trend_direction = "decreasing"

if top_segment is not None and bottom_segment is not None and top_channel is not None:
    st.write(f"• Highest revenue segment: {top_segment['label']} (${top_segment['purchaseamount']:,.2f})")
    st.write(f"• Lowest performing segment: {bottom_segment['label']} (${bottom_segment['purchaseamount']:,.2f})")
    st.write(f"• Decline segment revenue trend is {decline_trend_direction}.")
    st.write(f"• Strongest performing channel: {top_channel['retailchannel']} (${top_channel['purchaseamount']:,.2f})")

    st.write("### Recommended Strategic Actions")
    st.write(f"1. Increase targeted investment in the {top_segment['label']} segment to accelerate revenue momentum.")
    st.write(f"2. Investigate root causes behind the performance of the {bottom_segment['label']} segment and implement corrective engagement strategies.")
    st.write(f"3. Optimize marketing allocation toward the {top_channel['retailchannel']} channel while closely monitoring Decline segment behavior.")

# -----------------------------------
# STEP 10 — Display Filtered Data
# -----------------------------------
st.markdown("## Filtered Dataset")
st.dataframe(filtered_df.reset_index(drop=True))
