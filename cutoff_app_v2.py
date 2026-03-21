#!/usr/bin/env python
# coding: utf-8

# In[1]:
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import io
import numpy as np

# Styling
st.markdown("""
<style>
.metric-card {background: linear-gradient(135deg,#f5f7fa 0%,#c3cfe2 100%);padding:1rem;border-radius:10px;border-left:5px solid #1f77b4;}
.stMetric > label {font-size:1.2rem!important;color:#1f1f1f!important;}
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data(file_bytes):
    df = pd.read_excel(io.BytesIO(file_bytes))
    required_cols = ['Sector', 'Final report score (Average)', 'Absorption rate (Average)', 
                    'Progress report score', 'QS report score']
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        st.error(f"❌ Missing columns: {', '.join(missing)}")
        st.stop()
    return df

def safe_clamp(value, min_val, max_val):
    """Clamp value between min/max, handle NaN"""
    if pd.isna(value) or np.isnan(value):
        return (min_val + max_val) / 2
    return max(min_val, min(float(value), max_val))

def cutoff_input(label, col, min_val, max_val, df_col):
    """Dual slider + number input (FIXED)"""
    st.markdown(f"**{label}**")
    
    # Get safe default from filtered data
    data = df_col.dropna()
    q75 = safe_clamp(data.quantile(0.75) if len(data) > 0 else 75.0, min_val, max_val)
    
    col1, col2 = st.columns([3, 1])
    with col1:
        slider_val = st.slider(" ", min_value=min_val, max_value=max_val, 
                             value=q75, step=0.5, key=f"slider_{label}")
    with col2:
        # FIXED: Use slider_val as initial value, clamp properly
        number_val = st.number_input(" ", min_value=min_val, max_value=max_val, 
                                   value=slider_val, step=0.5, 
                                   key=f"num_{label}", format="%.1f")
    return number_val

def show_data_preview(df, cutoffs):
    st.header("📊 Data Distribution (Filtered)")
    criteria = ['Final report score (Average)', 'Absorption rate (Average)', 
               'Progress report score', 'QS report score']
    criteria_display = {
        'Final report score (Average)': 'Final Report',
        'Absorption rate (Average)': 'Absorption Rate', 
        'Progress report score': 'Progress Report',
        'QS report score': 'QS Report'
    }

    # Stats
    stats_data = []
    for col in criteria:
        data = df[col].dropna()
        stats_data.append({
            'Criterion': criteria_display[col],
            'N': len(data),
            'Min': f"{data.min():.1f}" if len(data) else "-",
            'Max': f"{data.max():.1f}" if len(data) else "-",
            'Mean': f"{data.mean():.1f}" if len(data) else "-",
            'Q75': f"{data.quantile(0.75):.1f}" if len(data) else "-",
            'Cutoff': f"{cutoffs[col]:.1f}"
        })
    st.subheader("📈 Statistics")
    st.dataframe(pd.DataFrame(stats_data), use_container_width=True)

    # Histograms
    st.subheader("📉 Distributions vs Cutoffs")
    cols = st.columns(2)
    for i, col in enumerate(criteria):
        with cols[i % 2]:
            data = df[col].dropna()
            if len(data) == 0:
                continue
            fig = px.histogram(data, x=col, nbins=20, title=criteria_display[col],
                             color_discrete_sequence=['#1f77b4'])
            fig.add_vline(x=cutoffs[col], line_dash="dash", line_color="red", 
                         line_width=3, annotation_text=f"{cutoffs[col]:.1f}")
            fig.update_layout(height=300, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

def calculate_metrics(df, cutoffs):
    metrics = {}
    criteria = ['Final report score (Average)', 'Absorption rate (Average)', 
               'Progress report score', 'QS report score']
    
    for criterion in criteria:
        col_data = df[criterion].dropna()
        pass_count = (col_data >= cutoffs[criterion]).sum()
        fail_count = (col_data < cutoffs[criterion]).sum()
        no_data = len(df) - len(col_data)
        total = len(df)
        metrics[criterion] = {
            'pass': int(pass_count), 'fail': int(fail_count), 
            'no_data': int(no_data),
            'pass_pct': pass_count/total*100 if total>0 else 0,
            'fail_pct': fail_count/total*100 if total>0 else 0,
            'no_data_pct': no_data/total*100 if total>0 else 0
        }
    
    # Overall pass/fail
    overall_pass = overall_fail = 0
    for _, row in df.iterrows():
        applicable = [c for c in criteria if pd.notna(row[c])]
        if applicable:
            passes_all = all(row[c] >= cutoffs[c] for c in applicable)
            if passes_all: overall_pass += 1
            else: overall_fail += 1
    
    total_eval = overall_pass + overall_fail
    metrics['overall'] = {
        'pass': overall_pass, 'fail': overall_fail, 
        'total_evaluated': total_eval,
        'pass_pct': overall_pass/total_eval*100 if total_eval>0 else 0,
        'fail_pct': overall_fail/total_eval*100 if total_eval>0 else 0
    }
    return metrics

def create_pie_charts(metrics, criteria_display):
    fig = make_subplots(rows=2, cols=2, subplot_titles=list(criteria_display.values()),
                       specs=[[{"type": "pie"}, {"type": "pie"}], [{"type": "pie"}, {"type": "pie"}]])
    criteria_list = list(criteria_display.keys())
    colors = ['#4CAF50', '#F44336', '#FF9800']
    labels = ['✅ Pass', '❌ Fail', '📄 No Data']
    
    for i, criterion in enumerate(criteria_list):
        row, col = divmod(i, 2)
        row += 1; col += 1
        m = metrics[criterion]
        fig.add_trace(go.Pie(labels=labels, values=[m['pass'],m['fail'],m['no_data']],
                           marker=dict(colors=colors, line=dict(color='#000',width=1)),
                           textinfo='label+percent', showlegend=False),
                     row=row, col=col)
    fig.update_layout(height=700, title="📊 Results")
    return fig

# MAIN APP
st.title("🎯 Project Cutoff Analysis Tool")

uploaded_file = st.sidebar.file_uploader("📁 Upload Excel", type=['xlsx', 'xls'])

if uploaded_file is not None:
    df_full = load_data(uploaded_file.read())
    
    # Sector filter
    st.sidebar.header("📂 Sector Filter")
    sector_options = ['All'] + sorted(df_full['Sector'].dropna().unique().tolist())
    selected_sector = st.sidebar.selectbox("Sector", sector_options, index=0)
    
    df = df_full if selected_sector == 'All' else df_full[df_full['Sector'] == selected_sector]
    st.sidebar.info(f"📊 {len(df)} projects filtered")
    
    criteria_display = {
        'Final report score (Average)': 'Final Report',
        'Absorption rate (Average)': 'Absorption',
        'Progress report score': 'Progress Report',
        'QS report score': 'QS Report'
    }
    
    st.sidebar.header("🎯 Cutoffs")
    
    # FIXED Dual inputs
    cutoffs = {}
    cutoffs['Final report score (Average)'] = cutoff_input(
        "Final Report", 'final', 0.0, 100.0, df['Final report score (Average)'])
    cutoffs['Absorption rate (Average)'] = cutoff_input(
        "Absorption", 'absorb', 0.0, 100.0, df['Absorption rate (Average)'])
    cutoffs['Progress report score'] = cutoff_input(
        "Progress Report", 'progress', 0.0, 45.0, df['Progress report score'])
    cutoffs['QS report score'] = cutoff_input(
        "QS Report", 'qs', 0.0, 45.0, df['QS report score'])
    
    show_data_preview(df, cutoffs)
    
    metrics = calculate_metrics(df, cutoffs)
    
    col1, col2, col3 = st.columns(3)
    with col1: st.metric("🎉 Pass All", metrics['overall']['pass'], f"{metrics['overall']['pass_pct']:.1f}%")
    with col2: st.metric("❌ Fail Any", metrics['overall']['fail'], f"{metrics['overall']['fail_pct']:.1f}%")
    with col3: st.metric("📈 Total", metrics['overall']['total_evaluated'], len(df))
    
    summary_data = []
    for c in criteria_display:
        m = metrics[c]
        summary_data.append({
            'Criterion': criteria_display[c],
            'Cutoff': f"{cutoffs[c]:.1f}",
            '✅ Pass': f"{m['pass']} ({m['pass_pct']:.1f}%)",
            '❌ Fail': f"{m['fail']} ({m['fail_pct']:.1f}%)",
            '📄 No Data': f"{m['no_data']} ({m['no_data_pct']:.1f}%)"
        })
    st.subheader("📋 Results")
    st.dataframe(pd.DataFrame(summary_data))
    
    st.subheader("🥧 Charts")
    fig = create_pie_charts(metrics, criteria_display)
    st.plotly_chart(fig, use_container_width=True)
    
    csv = pd.DataFrame(summary_data).to_csv(index=False).encode()
    st.download_button("💾 Download", csv, "results.csv", "text/csv")
    
else:
    st.info("👈 Upload Excel with Sector column (SCH,VET,ADU)")

# In[ ]:




