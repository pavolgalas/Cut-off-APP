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

@st.cache_data
def load_data(file_bytes):
    df = pd.read_excel(io.BytesIO(file_bytes))
    required_cols = ['Sector', 'Final report score (Average)', 'Absorption rate (Average)', 
                    'Progress report score', 'QS report score']
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        st.error(f"❌ Missing: {', '.join(missing)}")
        st.stop()
    return df

def safe_default(series, q=0.75, fallback=75.0):
    data = series.dropna()
    if len(data) == 0:
        return fallback
    val = data.quantile(q)
    return float(val) if not pd.isna(val) else fallback

def cutoff_row(label, min_val, max_val, df_col):
    st.markdown(f"**{label}**")
    col1, col2 = st.columns([3,1])
    with col1:
        slider_val = st.slider("", min_value=min_val, max_value=max_val,
                             value=safe_default(df_col), step=0.5,
                             key=f"slider_{label.replace(' ','_')}")
    with col2:
        num_val = st.number_input("", min_value=min_val, max_value=max_val,
                                value=slider_val, step=0.5,
                                key=f"num_{label.replace(' ','_')}", format="%.1f")
    return num_val

def show_data_preview(df, cutoffs):
    st.header("📊 Data Preview")
    criteria = ['Final report score (Average)', 'Absorption rate (Average)', 
               'Progress report score', 'QS report score']
    display_names = {'Final report score (Average)': 'Final', 'Absorption rate (Average)': 'Absorption', 
                    'Progress report score': 'Progress', 'QS report score': 'QS'}
    
    stats = []
    for col in criteria:
        data = df[col].dropna()
        stats.append({
            'Metric': display_names[col],
            'N': len(data),
            'Min': f"{data.min():.1f}" if len(data)>0 else "-",
            'Max': f"{data.max():.1f}" if len(data)>0 else "-",
            'Mean': f"{data.mean():.1f}" if len(data)>0 else "-",
            'Q75': f"{data.quantile(0.75):.1f}" if len(data)>0 else "-",
            'Cutoff': f"{cutoffs[col]:.1f}"
        })
    st.dataframe(pd.DataFrame(stats))
    
    st.subheader("📉 Histograms")
    cols = st.columns(2)
    for i, col in enumerate(criteria):
        with cols[i%2]:
            data = df[col].dropna()
            if len(data) == 0: continue
            fig = px.histogram(data, x=col, nbins=20, title=display_names[col])
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
        no_data_count = len(df) - len(col_data)
        total = len(df)
        metrics[criterion] = {
            'pass': int(pass_count), 'fail': int(fail_count),
            'no_data': int(no_data_count),
            'pass_pct': pass_count/total*100 if total>0 else 0,
            'fail_pct': fail_count/total*100 if total>0 else 0,
            'no_data_pct': no_data_count/total*100 if total>0 else 0
        }
    
    # FIXED: Proper if/else instead of conditional assignment
    overall_pass = 0
    overall_fail = 0
    for _, row in df.iterrows():
        applicable = [c for c in criteria if pd.notna(row[c])]
        if applicable:
            passes_all = all(row[c] >= cutoffs[c] for c in applicable)
            if passes_all:
                overall_pass += 1
            else:
                overall_fail += 1
    
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
    
    for i, criterion in enumerate(criteria_list):
        row, col = divmod(i, 2)
        row += 1; col += 1
        m = metrics[criterion]
        fig.add_trace(go.Pie(labels=['✅ Pass','❌ Fail','📄 No Data'], 
                           values=[m['pass'],m['fail'],m['no_data']],
                           marker=dict(colors=colors, line=dict(color='#000',width=1)),
                           textinfo='label+percent', showlegend=False),
                     row=row, col=col)
    fig.update_layout(height=700)
    return fig

# MAIN APP
st.title("🎯 Cutoff Analysis Tool")

uploaded_file = st.sidebar.file_uploader("📁 Upload Excel", type=['xlsx','xls'])

if uploaded_file is not None:
    df_full = load_data(uploaded_file.read())
    
    st.sidebar.header("📂 Filter")
    sectors = ['All'] + sorted(df_full['Sector'].dropna().unique().tolist())
    sector = st.sidebar.selectbox("Sector", sectors)
    df = df_full if sector == 'All' else df_full[df_full['Sector'] == sector]
    
    st.sidebar.markdown("---")
    st.sidebar.info(f"📊 {len(df)} projects")
    
    st.sidebar.header("🎯 Cutoffs")
    
    criteria_display = {
        'Final report score (Average)': 'Final Report',
        'Absorption rate (Average)': 'Absorption',
        'Progress report score': 'Progress',
        'QS report score': 'QS'
    }
    
    cutoffs = {}
    cutoffs['Final report score (Average)'] = cutoff_row("Final Report", 0.0, 100.0, df['Final report score (Average)'])
    cutoffs['Absorption rate (Average)'] = cutoff_row("Absorption", 0.0, 100.0, df['Absorption rate (Average)'])
    cutoffs['Progress report score'] = cutoff_row("Progress", 0.0, 45.0, df['Progress report score'])
    cutoffs['QS report score'] = cutoff_row("QS", 0.0, 45.0, df['QS report score'])
    
    show_data_preview(df, cutoffs)
    
    metrics = calculate_metrics(df, cutoffs)
    
    col1, col2, col3 = st.columns(3)
    with col1: st.metric("🎉 Pass All", metrics['overall']['pass'], f"{metrics['overall']['pass_pct']:.1f}%")
    with col2: st.metric("❌ Fail Any", metrics['overall']['fail'], f"{metrics['overall']['fail_pct']:.1f}%")
    with col3: st.metric("📈 Total", metrics['overall']['total_evaluated'])
    
    summary_data = [{
        'Criterion': k,
        'Cutoff': f"{cutoffs[k]:.1f}",
        '✅ Pass': f"{metrics[k]['pass']} ({metrics[k]['pass_pct']:.1f}%)",
        '❌ Fail': f"{metrics[k]['fail']} ({metrics[k]['fail_pct']:.1f}%)",
        '📄 No Data': f"{metrics[k]['no_data']} ({metrics[k]['no_data_pct']:.1f}%)"
    } for k in criteria_display]
    
    st.subheader("📋 Summary")
    st.dataframe(pd.DataFrame(summary_data))
    
    st.subheader("🥧 Charts")
    fig = create_pie_charts(metrics, criteria_display)
    st.plotly_chart(fig, use_container_width=True)
    
    csv = pd.DataFrame(summary_data).to_csv(index=False).encode('utf-8')
    st.download_button("💾 Download CSV", csv, f"results_{sector.lower()}.csv", "text/csv")
    
else:
    st.info("👈 Upload Excel with Sector column")

# In[ ]:




