#!/usr/bin/env python3
"""
Chroma GTM - Minimal shadcn-style viewer
Run: streamlit run chroma_viewer.py
"""

import streamlit as st
import chromadb
import pandas as pd
import plotly.express as px

# === PAGE CONFIG ===
st.set_page_config(page_title="Chroma GTM", page_icon="◈", layout="wide", initial_sidebar_state="collapsed")

# === SIMPLE PASSWORD PROTECTION ===
# Set password via Streamlit secrets or use default
APP_PASSWORD = st.secrets.get("APP_PASSWORD", "chroma2024")

def check_password():
    """Simple password protection for internal use"""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    
    if not st.session_state.authenticated:
        st.markdown("### 🔐 Chroma GTM")
        password = st.text_input("Enter password", type="password")
        if st.button("Login"):
            if password == APP_PASSWORD:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Incorrect password")
        st.stop()

check_password()

# === SHADCN-STYLE CSS ===
st.markdown("""
<style>
    /* Base */
    .block-container {padding: 2rem 3rem; max-width: 1400px;}
    html, body, [class*="css"] {font-size: 15px; color: #0a0a0a;}
    
    /* Search */
    .stTextInput > div > div > input {
        border: 1px solid #e5e5e5;
        border-radius: 8px;
        padding: 0.6rem 1rem;
        font-size: 0.95rem;
        background: #fafafa;
    }
    .stTextInput > div > div > input:focus {
        border-color: #a3a3a3;
        box-shadow: none;
        background: #fff;
    }
    .stTextInput > div > div > input::placeholder {color: #a3a3a3;}
    
    /* Multiselect */
    .stMultiSelect > div > div {
        border-radius: 8px;
        font-size: 0.85rem;
        border-color: #e5e5e5;
    }
    .stMultiSelect label {font-size: 0.75rem; color: #737373; font-weight: 500; text-transform: uppercase; letter-spacing: 0.05em;}
    
    /* Select */
    .stSelectbox > div > div {
        border-radius: 8px;
        font-size: 0.9rem;
        border-color: #e5e5e5;
    }
    .stSelectbox label {font-size: 0.75rem; color: #737373; font-weight: 500; text-transform: uppercase; letter-spacing: 0.05em;}
    
    /* Table */
    .stDataFrame {border: 1px solid #e5e5e5; border-radius: 10px;}
    .stDataFrame [data-testid="stDataFrameResizable"] {font-size: 0.9rem;}
    
    /* Buttons */
    .stButton > button, .stDownloadButton > button {
        border: 1px solid #e5e5e5;
        border-radius: 8px;
        font-size: 0.85rem;
        font-weight: 500;
        padding: 0.5rem 1rem;
        background: #fff;
        color: #0a0a0a;
    }
    .stButton > button:hover, .stDownloadButton > button:hover {background: #fafafa; border-color: #d4d4d4;}
    
    /* Metric override */
    [data-testid="stMetricValue"] {font-size: 1.8rem; font-weight: 600; color: #0a0a0a;}
    [data-testid="stMetricLabel"] {font-size: 0.8rem; color: #737373;}
    [data-testid="stMetricDelta"] {display: none;}
    
    /* Divider */
    hr {border: none; border-top: 1px solid #e5e5e5; margin: 1rem 0;}
    
    /* Hide streamlit */
    #MainMenu, footer, header {visibility: hidden;}
    
    /* Helpers */
    .text-muted {color: #737373; font-size: 0.85rem;}
    .section-title {font-size: 1rem; font-weight: 600; margin-bottom: 0.75rem; color: #0a0a0a;}
    
    /* Filter section */
    .filter-section {
        background: #fafafa;
        border: 1px solid #e5e5e5;
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    
    /* Active filter pills */
    .filter-pill {
        display: inline-block;
        background: #0a0a0a;
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.75rem;
        margin-right: 0.5rem;
        margin-bottom: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# === DATABASE ===
@st.cache_resource
def get_client():
    return chromadb.CloudClient(
        api_key=st.secrets.get("CHROMA_API_KEY", "ck-2i6neFLSKhd5pEqLP3jZKUkG6tX3yo4RVUZEeRxs4fHm"),
        tenant=st.secrets.get("CHROMA_TENANT", "aa8f571e-03dc-4cd8-b888-723bd00b83f0"),
        database=st.secrets.get("CHROMA_DATABASE", "customer")
    )

@st.cache_data(ttl=10)
def load_data(_client, name):
    collection = _client.get_collection(name)
    count = collection.count()
    
    # Paginate to handle quota limits (max 300 per request)
    all_metadatas = []
    batch_size = 250
    offset = 0
    
    while offset < count:
        data = collection.get(include=["metadatas"], limit=batch_size, offset=offset)
        if data['metadatas']:
            all_metadatas.extend(data['metadatas'])
        offset += batch_size
    
    return pd.DataFrame(all_metadatas) if all_metadatas else pd.DataFrame()

client = get_client()
collections = [c.name for c in client.list_collections()]

if not collections:
    st.error("No collections found")
    st.stop()

# === COLUMN CONFIG ===
COL_NAMES = {
    'company_name': 'Company', 'category': 'Type', 'vector_db_used': 'Vector DB',
    'source_channel': 'Source', 'source': 'Source', 'use_case': 'Use Case',
    'industry': 'Industry', 'company_size': 'Size', 'notes': 'Notes', 'relevance': 'Score',
}
HIDDEN = ['source_section', 'added_at', 'date_found', 'updated_at', 'last_verified_at', 
          'source_url', 'video_title', 'context', 'extracted_from', 'added_date', 
          'confidence', 'selection_rationale']

def format_df(df):
    df = df.drop(columns=[c for c in HIDDEN if c in df.columns], errors='ignore')
    df = df.rename(columns={k: v for k, v in COL_NAMES.items() if k in df.columns})
    priority = ['Score', 'Company', 'Type', 'Vector DB', 'Source', 'Use Case', 'Industry']
    return df[[c for c in priority if c in df.columns] + [c for c in df.columns if c not in priority]]

# === HEADER ===
h1, h2 = st.columns([6, 1])
with h1:
    st.markdown("### ◈ Chroma GTM")
with h2:
    selected = st.selectbox("Collection", collections, label_visibility="collapsed")

all_df = load_data(client, selected)
collection = client.get_collection(selected)
src_col = 'source_channel' if 'source_channel' in all_df.columns else 'source' if 'source' in all_df.columns else None

# === STATS ===
s1, s2, s3, s4, s5 = st.columns(5)
s1.metric("Records", len(all_df))
s2.metric("Companies", all_df['company_name'].nunique() if 'company_name' in all_df.columns else 0)
s3.metric("Vector DBs", all_df['vector_db_used'].nunique() if 'vector_db_used' in all_df.columns else 0)
s4.metric("Types", all_df['category'].nunique() if 'category' in all_df.columns else 0)
s5.metric("Sources", all_df[src_col].nunique() if src_col else 0)

st.markdown("---")

# === SEARCH BAR ===
search_col, clear_col = st.columns([6, 1])
with search_col:
    query = st.text_input("Search", placeholder="🔍 Semantic search... e.g. 'AI companies in healthcare'", label_visibility="collapsed")
with clear_col:
    if st.button("Clear All", use_container_width=True):
        st.rerun()

# === FILTERS ===
st.markdown("<p style='font-size:0.8rem; color:#737373; margin: 1rem 0 0.5rem 0; font-weight:500;'>FILTERS</p>", unsafe_allow_html=True)

f1, f2, f3, f4 = st.columns(4)

# Get filter options with counts
def get_options_with_counts(df, col):
    if col not in df.columns:
        return []
    counts = df[col].value_counts()
    return [f"{val} ({count})" for val, count in counts.items()]

def extract_value(option):
    """Extract value from 'Value (count)' format"""
    if '(' in option:
        return option.rsplit(' (', 1)[0]
    return option

# Type filter (multiselect)
with f1:
    cat_options = get_options_with_counts(all_df, 'category')
    cat_selected = st.multiselect("Type", cat_options, placeholder="All types")

# Vector DB filter (multiselect)
with f2:
    db_options = get_options_with_counts(all_df, 'vector_db_used')
    db_selected = st.multiselect("Vector DB", db_options, placeholder="All databases")

# Source filter (multiselect)
with f3:
    if src_col:
        src_options = get_options_with_counts(all_df, src_col)
        src_selected = st.multiselect("Source", src_options, placeholder="All sources")
    else:
        src_selected = []

# Company name text filter
with f4:
    company_filter = st.text_input("Company", placeholder="Filter by name...", label_visibility="visible")

# === APPLY FILTERS ===
if query:
    results = collection.query(query_texts=[query], n_results=200, include=["metadatas", "distances"])
    if results['metadatas'] and results['metadatas'][0]:
        df = pd.DataFrame(results['metadatas'][0])
        df.insert(0, 'relevance', [f"{max(0,1-d)*100:.0f}%" for d in results['distances'][0]])
    else:
        df = pd.DataFrame()
else:
    df = all_df.copy()

if not df.empty:
    # Apply type filter
    if cat_selected:
        cat_values = [extract_value(x) for x in cat_selected]
        df = df[df['category'].isin(cat_values)]
    
    # Apply vector DB filter
    if db_selected:
        db_values = [extract_value(x) for x in db_selected]
        df = df[df['vector_db_used'].isin(db_values)]
    
    # Apply source filter
    if src_selected and src_col:
        src_values = [extract_value(x) for x in src_selected]
        df = df[df[src_col].isin(src_values)]
    
    # Apply company name filter
    if company_filter:
        df = df[df['company_name'].str.contains(company_filter, case=False, na=False)]

# === ACTIVE FILTERS DISPLAY ===
active_filters = []
if cat_selected:
    active_filters.extend([f"Type: {extract_value(x)}" for x in cat_selected])
if db_selected:
    active_filters.extend([f"DB: {extract_value(x)}" for x in db_selected])
if src_selected:
    active_filters.extend([f"Source: {extract_value(x)}" for x in src_selected])
if company_filter:
    active_filters.append(f"Company: {company_filter}")
if query:
    active_filters.append(f"Search: {query[:30]}...")

if active_filters:
    pills_html = ''.join([f'<span class="filter-pill">{f}</span>' for f in active_filters])
    st.markdown(f'<div style="margin: 0.5rem 0;">{pills_html}</div>', unsafe_allow_html=True)

# === RESULTS COUNT ===
st.markdown(f"<p class='text-muted' style='margin:0.5rem 0;'>Showing <b>{len(df)}</b> of {len(all_df)} records</p>", unsafe_allow_html=True)

# === TABLE ===
if not df.empty:
    st.dataframe(format_df(df), use_container_width=True, height=380, hide_index=True)
    
    c1, c2, c3, _ = st.columns([1, 1, 1, 5])
    c1.download_button("📥 CSV", format_df(df).to_csv(index=False), f"{selected}.csv")
    c2.download_button("📥 JSON", format_df(df).to_json(orient='records'), f"{selected}.json")
    with c3:
        if st.button("🔄 Refresh Data"):
            st.cache_data.clear()
            st.rerun()
else:
    st.markdown("<p class='text-muted'>No results match your filters</p>", unsafe_allow_html=True)

# === INSIGHTS ===
st.markdown("---")
st.markdown("<p class='section-title'>Insights</p>", unsafe_allow_html=True)

# Use filtered data for insights
insight_df = df if not df.empty else all_df

if not insight_df.empty:
    c1, c2, c3, c4 = st.columns(4)
    
    # Vector DB - Donut
    with c1:
        if 'vector_db_used' in insight_df.columns:
            counts = insight_df['vector_db_used'].value_counts().head(8)
            fig = px.pie(
                values=counts.values, 
                names=counts.index, 
                hole=0.5,
                color_discrete_sequence=px.colors.qualitative.Set2,
                title="Vector DB"
            )
            fig.update_traces(
                textposition='inside', 
                textinfo='percent+label',
                hovertemplate='<b>%{label}</b><br>%{value} records<br>%{percent}<extra></extra>'
            )
            fig.update_layout(
                margin=dict(t=40, b=20, l=20, r=20), 
                height=280,
                showlegend=False,
                title_x=0.5,
                title_font_size=14
            )
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    
    # Category - Donut
    with c2:
        if 'category' in insight_df.columns:
            counts = insight_df['category'].value_counts()
            fig = px.pie(
                values=counts.values, 
                names=counts.index, 
                hole=0.5,
                color_discrete_sequence=px.colors.qualitative.Pastel,
                title="Type"
            )
            fig.update_traces(
                textposition='inside', 
                textinfo='percent+label',
                hovertemplate='<b>%{label}</b><br>%{value} records<br>%{percent}<extra></extra>'
            )
            fig.update_layout(
                margin=dict(t=40, b=20, l=20, r=20), 
                height=280,
                showlegend=False,
                title_x=0.5,
                title_font_size=14
            )
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    
    # Source - Bar
    with c3:
        if src_col and src_col in insight_df.columns:
            counts = insight_df[src_col].value_counts().head(6)
            fig = px.bar(
                x=counts.values, 
                y=counts.index, 
                orientation='h',
                color=counts.index,
                color_discrete_sequence=px.colors.qualitative.Safe,
                title="Source"
            )
            fig.update_traces(
                texttemplate='%{x}', 
                textposition='outside',
                hovertemplate='<b>%{y}</b><br>%{x} records<extra></extra>'
            )
            fig.update_layout(
                margin=dict(t=40, b=20, l=20, r=20), 
                height=280,
                showlegend=False,
                title_x=0.5,
                title_font_size=14,
                xaxis_title="",
                yaxis_title="",
                yaxis=dict(categoryorder='total ascending')
            )
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    
    # Industry - Bar
    with c4:
        if 'industry' in insight_df.columns:
            counts = insight_df['industry'].dropna().value_counts().head(6)
            if not counts.empty:
                fig = px.bar(
                    x=counts.values, 
                    y=counts.index, 
                    orientation='h',
                    color=counts.index,
                    color_discrete_sequence=px.colors.qualitative.Vivid,
                    title="Industry"
                )
                fig.update_traces(
                    texttemplate='%{x}', 
                    textposition='outside',
                    hovertemplate='<b>%{y}</b><br>%{x} records<extra></extra>'
                )
                fig.update_layout(
                    margin=dict(t=40, b=20, l=20, r=20), 
                    height=280,
                    showlegend=False,
                    title_x=0.5,
                    title_font_size=14,
                    xaxis_title="",
                    yaxis_title="",
                    yaxis=dict(categoryorder='total ascending')
                )
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
