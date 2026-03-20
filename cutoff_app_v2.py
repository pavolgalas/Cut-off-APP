#!/usr/bin/env python
# coding: utf-8

# In[1]:


import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import io

# CSS
st.markdown("""
<style>
.metric-card {background: linear-gradient(135deg,#f5f7fa 0%,#c3cfe2 100%);padding:1rem;border-radius:10px;border-left:5px solid #1f77b4;}
.stMetric > label {font-size:1.2rem!important;color:#1f1f1f!important;}
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data(file_bytes):
    df = pd.read_excel(io.BytesIO(file_bytes))
    required_cols = ['Final report score (Average)', 'Absorption rate (Average)', 'Progress report score', 'QS report score']
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        st.error(f"❌ Missing columns: {', '.join(missing)}")
        st.stop()
    return df

def show_data_preview(df):
    """NEW: Show histograms + stats after upload"""
    st.header("📊 Data Distribution & Statistics")

    criteria = ['Final report score (Average)', 'Absorption rate (Average)', 'Progress report score', 'QS report score']
    criteria_display = {
        'Final report score (Average)': 'Final Report Score',
        'Absorption rate (Average)': 'Absorption Rate',
        'Progress report score': 'Progress Report',
        'QS report score': 'QS Report'
    }

    # Stats table
    stats_data = []
    for col in criteria:
        data = df[col].dropna()
        stats_data.append({
            'Criterion': criteria_display[col],
            'Valid': len(data),
            'Missing': len(df) - len(data),
            'Min': f"{data.min():.1f}",
            'Max': f"{data.max():.1f}",
            'Mean': f"{data.mean():.1f}",
            'Median': f"{data.median():.1f}",
            'Q75': f"{data.quantile(0.75):.1f}"
        })

    st.subheader("📈 Basic Statistics")
    stats_df = pd.DataFrame(stats_data)
    st.dataframe(stats_df, use_container_width=True)

    # Histograms
    st.subheader("📉 Distribution Histograms")
    cols = st.columns(2)

    for i, col in enumerate(criteria):
        with cols[i % 2]:
            data = df[col].dropna()
            fig = px.histogram(data, x=col, nbins=20, 
                             title=criteria_display[col],
                             labels={'value': criteria_display[col]},
                             color_discrete_sequence=['#1f77b4'])
            fig.update_layout(height=300, showlegend=False, 
                            xaxis_title="Score", yaxis_title="Projects")
            fig.add_vline(x=data.quantile(0.75), line_dash="dash", 
                         line_color="red", annotation_text="Q75")
            st.plotly_chart(fig, use_container_width=True)

def calculate_metrics(df, cutoffs):
    metrics = {}
    criteria = ['Final report score (Average)', 'Absorption rate (Average)', 'Progress report score', 'QS report score']

    for criterion in criteria:
        col_data = df[criterion].dropna()
        pass_count = (col_data >= cutoffs[criterion]).sum()
        fail_count = (col_data < cutoffs[criterion]).sum()
        no_data = len(df) - len(col_data)

        total = len(df)
        metrics[criterion] = {
            'pass': int(pass_count), 'fail': int(fail_count), 'no_data': int(no_data),
            'pass_pct': pass_count/total*100 if total > 0 else 0,
            'fail_pct': fail_count/total*100 if total > 0 else 0, 
            'no_data_pct': no_data/total*100 if total > 0 else 0
        }

    # Overall
    overall_pass = overall_fail = 0
    for _, row in df.iterrows():
        applicable = [c for c in criteria if pd.notna(row[c])]
        if applicable:
            passes_all = all(row[c] >= cutoffs[c] for c in applicable)
            if passes_all: overall_pass += 1
            else: overall_fail += 1

    total_eval = overall_pass + overall_fail
    metrics['overall'] = {
        'pass': overall_pass, 'fail': overall_fail, 'total_evaluated': total_eval,
        'pass_pct': overall_pass/total_eval*100 if total_eval > 0 else 0,
        'fail_pct': overall_fail/total_eval*100 if total_eval > 0 else 0
    }
    return metrics

def create_pie_charts(metrics, criteria_display):
    fig = make_subplots(rows=2, cols=2, subplot_titles=list(criteria_display.values()),
                       specs=[[{"type": "pie"}, {"type": "pie"}], [{"type": "pie"}, {"type": "pie"}]])

    criteria_list = list(criteria_display.keys())
    colors = ['#4CAF50', '#F44336', '#FF9800']
    labels = ['✅ Pass', '❌ Fail', '📄 No Data']

    for i, criterion in enumerate(criteria_list):
        row = 1 if i < 2 else 2
        col = 1 if i % 2 == 0 else 2
        m = metrics[criterion]

        fig.add_trace(go.Pie(labels=labels, values=[m['pass'],m['fail'],m['no_data']],
                           marker=dict(colors=colors, line=dict(color='#000',width=1)),
                           textinfo='label+percent', showlegend=False,
                           hovertemplate='<b>%{label}</b><br>Projects: %{value}<extra></extra>'),
                     row=row, col=col)

    fig.update_layout(height=700, title="📊 Performance Distribution")
    return fig

# MAIN APP
st.title("🎯 Project Cutoff Analysis Tool")
st.markdown("**Upload → Explore data → Set cutoffs → Analyze**")

# Sidebar upload
uploaded_file = st.sidebar.file_uploader("📁 Upload Excel", type=['xlsx','xls'])

if uploaded_file is not None:
    df = load_data(uploaded_file.read())
    st.sidebar.success(f"✅ {len(df):,} projects loaded")

    # NEW: Show data preview FIRST
    show_data_preview(df)

    # Cutoff sliders (now better informed by stats above)
    st.sidebar.header("🎯 Set Cutoffs")
    criteria_display = {
        'Final report score (Average)': 'Final Report Score',
        'Absorption rate (Average)': 'Absorption Rate',
        'Progress report score': 'Progress Report',
        'QS report score': 'QS Report'
    }

    cutoffs = {}
    for col, name in criteria_display.items():
        default = float(df[col].quantile(0.75))
        cutoffs[col] = st.sidebar.slider(name, 0.0, 100.0, default, 0.5)

    # ANALYSIS SECTION
    st.header("🎯 Analysis Results")
    metrics = calculate_metrics(df, cutoffs)

    # Key metrics
    col1, col2, col3 = st.columns(3)
    with col1: st.metric("🎉 Pass ALL", f"{metrics['overall']['pass']:,}", f"{metrics['overall']['pass_pct']:.1f}%")
    with col2: st.metric("❌ Fail ANY", f"{metrics['overall']['fail']:,}", f"{metrics['overall']['fail_pct']:.1f}%")
    with col3: st.metric("📈 Evaluated", f"{metrics['overall']['total_evaluated']:,}", f"{len(df):,} total")

    # Summary table
    st.subheader("📋 Breakdown")
    summary_data = []
    for c in criteria_display:
        m = metrics[c]
        summary_data.append({
            'Criterion': criteria_display[c],
            'Cutoff': f"{cutoffs[c]:.1f}",
            '✅ Pass': f"{m['pass']:,} ({m['pass_pct']:.1f}%)",
            '❌ Fail': f"{m['fail']:,} ({m['fail_pct']:.1f}%)",
            '📄 No Data': f"{m['no_data']:,} ({m['no_data_pct']:.1f}%)"
        })
    st.dataframe(pd.DataFrame(summary_data), use_container_width=True)

    # Pie charts
    st.subheader("🥧 Visuals")
    fig = create_pie_charts(metrics, criteria_display)
    st.plotly_chart(fig, use_container_width=True)

    # Download
    csv_data = pd.DataFrame(summary_data).to_csv(index=False).encode('utf-8')
    st.download_button("💾 Download Results", csv_data, "analysis.csv", "text/csv")

else:
    st.info("""
    **👈 Upload Excel file to begin**

    **Required columns:**
    • `Final report score (Average)`
    • `Absorption rate (Average)`
    • `Progress report score`
    • `QS report score`
    """)


# In[ ]:




