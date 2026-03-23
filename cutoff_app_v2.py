#!/usr/bin/env python
# coding: utf-8

# In[1]:
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import io

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
    required_cols = [
        'Sector',
        'Final report score (Average)',
        'Absorption rate (Average)',
        'Progress report score',
        'QS report score'
    ]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        st.error(f"❌ Missing columns: {', '.join(missing)}")
        st.stop()
    return df

def show_data_preview(df, cutoffs):
    st.header("📊 Data Distribution & Statistics (Filtered)")
    criteria = [
        'Final report score (Average)',
        'Absorption rate (Average)',
        'Progress report score',
        'QS report score'
    ]
    criteria_display = {
        'Final report score (Average)': 'Final Report Score',
        'Absorption rate (Average)': 'Absorption Rate',
        'Progress report score': 'Progress Report',
        'QS report score': 'QS Report'
    }

    stats_data = []
    for col in criteria:
        data = df[col].dropna()
        stats_data.append({
            'Criterion': criteria_display[col],
            'Valid': len(data),
            'Missing': len(df) - len(data),
            'Min': f"{data.min():.1f}" if len(data) else "-",
            'Max': f"{data.max():.1f}" if len(data) else "-",
            'Mean': f"{data.mean():.1f}" if len(data) else "-",
            'Median': f"{data.median():.1f}" if len(data) else "-",
            'Cutoff': f"{cutoffs[col]:.1f}"
        })
    st.subheader("📈 Statistics & Current Cutoffs")
    st.dataframe(pd.DataFrame(stats_data), use_container_width=True)

    st.subheader("📉 Distribution vs Cutoff Lines")
    st.markdown("🔴 Red dashed line = current cutoff value.")

    cols = st.columns(2)
    for i, col in enumerate(criteria):
        with cols[i % 2]:
            data = df[col].dropna()
            if len(data) == 0:
                st.info(f"No data for {criteria_display[col]}.")
                continue
            fig = px.histogram(
                data,
                x=col,
                nbins=20,
                title=criteria_display[col],
                labels={'value': criteria_display[col]},
                color_discrete_sequence=['#1f77b4']
            )
            fig.add_vline(
                x=cutoffs[col],
                line_dash="dash",
                line_color="red",
                line_width=3,
                annotation_text=f"Cutoff: {cutoffs[col]:.1f}",
                annotation_position="top right"
            )
            fig.update_layout(height=300, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

def calculate_metrics(df, cutoffs, overall_mode="all_data"):
    """
    overall_mode:
    - 'all_data': Mode 1 - Only projects with ALL criteria filled (pass/fail only)
    - 'all_projects': Mode 2 - All projects (pass / fail / no data for ALL criteria)
    """
    metrics = {}
    criteria = [
        'Final report score (Average)',
        'Absorption rate (Average)',
        'Progress report score',
        'QS report score'
    ]

    # Per-criterion metrics (unchanged)
    for criterion in criteria:
        col_data = df[criterion].dropna()
        pass_count = (col_data >= cutoffs[criterion]).sum()
        fail_count = (col_data < cutoffs[criterion]).sum()
        no_data = len(df) - len(col_data)
        total = len(df)
        metrics[criterion] = {
            'pass': int(pass_count),
            'fail': int(fail_count),
            'no_data': int(no_data),
            'pass_pct': pass_count / total * 100 if total > 0 else 0,
            'fail_pct': fail_count / total * 100 if total > 0 else 0,
            'no_data_pct': no_data / total * 100 if total > 0 else 0,
        }

    # Overall analysis - CORRECTED LOGIC
    overall_pass = 0
    overall_fail = 0
    overall_no_data_all = 0

    for _, row in df.iterrows():
        has_all_data = all(pd.notna(row[c]) for c in criteria)
        no_data_all = all(pd.isna(row[c]) for c in criteria)

        if overall_mode == "all_data":
            # Mode 1: ONLY projects with ALL criteria filled
            if has_all_data:
                passes_all = all(row[c] >= cutoffs[c] for c in criteria)
                if passes_all:
                    overall_pass += 1
                else:
                    overall_fail += 1

        elif overall_mode == "all_projects":
            # Mode 2: ALL projects
            if no_data_all:
                overall_no_data_all += 1
            elif has_all_data:
                # All data filled - pass/fail
                passes_all = all(row[c] >= cutoffs[c] for c in criteria)
                if passes_all:
                    overall_pass += 1
                else:
                    overall_fail += 1
            else:
                # Partial data - fail (doesn't pass ALL applicable)
                overall_fail += 1

    total_all = len(df)
    total_complete = overall_pass + overall_fail

    if overall_mode == "all_data":
        metrics['overall'] = {
            'pass': overall_pass,
            'fail': overall_fail,
            'no_data_all': total_all - total_complete,
            'total_complete': total_complete,
            'total_projects': total_all,
            'pass_pct': overall_pass / total_complete * 100 if total_complete > 0 else 0,
            'fail_pct': overall_fail / total_complete * 100 if total_complete > 0 else 0,
        }
    else:  # all_projects
        metrics['overall'] = {
            'pass': overall_pass,
            'fail': overall_fail,
            'no_data_all': overall_no_data_all,
            'total_complete': total_complete,
            'total_projects': total_all,
            'pass_pct': overall_pass / total_all * 100,
            'fail_pct': overall_fail / total_all * 100,
            'no_data_all_pct': overall_no_data_all / total_all * 100,
        }

    return metrics

def create_pie_charts(metrics, criteria_display):
    fig = make_subplots(
        rows=2,
        cols=2,
        subplot_titles=list(criteria_display.values()),
        specs=[[{"type": "pie"}, {"type": "pie"}], [{"type": "pie"}, {"type": "pie"}]],
    )
    criteria_list = list(criteria_display.keys())
    colors = ['#4CAF50', '#F44336', '#FF9800']
    labels = ['✅ Pass', '❌ Fail', '📄 No Data']

    for i, criterion in enumerate(criteria_list):
        row = 1 if i < 2 else 2
        col = 1 if i % 2 == 0 else 2
        m = metrics[criterion]
        fig.add_trace(
            go.Pie(
                labels=labels,
                values=[m['pass'], m['fail'], m['no_data']],
                marker=dict(colors=colors, line=dict(color='#000', width=1)),
                textinfo='label+percent',
                showlegend=False,
            ),
            row=row,
            col=col,
        )

    fig.update_layout(height=700, title="📊 Per-Criterion Distribution")
    return fig

# MAIN APP
st.title("🎯 Project Cutoff Analysis Tool")

uploaded_file = st.sidebar.file_uploader("📁 Upload Excel", type=['xlsx', 'xls'])

if uploaded_file is not None:
    df_full = load_data(uploaded_file.read())

    st.sidebar.header("📂 Sector Filter")
    sector_options = ['All'] + sorted(df_full['Sector'].dropna().unique().tolist())
    selected_sector = st.sidebar.selectbox("Sector", sector_options, index=0)

    df = df_full.copy() if selected_sector == 'All' else df_full[df_full['Sector'] == selected_sector].copy()
    st.sidebar.caption(f"📊 {len(df)} projects")

    # NEW: Overall mode switch
    st.sidebar.header("🎛 Overall Analysis Mode")
    overall_mode = st.sidebar.radio(
        "Pass/Fail calculation:",
        [
            "1. Only projects with ALL criteria filled",
            "2. All projects (incl. no data for all criteria)"
        ],
        index=0,
        help="Mode 1: Strict - requires all 4 criteria filled.\nMode 2: Complete - classifies every project."
    )
    overall_mode = "all_data" if "1. Only" in overall_mode else "all_projects"

    criteria_display = {
        'Final report score (Average)': 'Final Report Score',
        'Absorption rate (Average)': 'Absorption Rate',
        'Progress report score': 'Progress Report',
        'QS report score': 'QS Report',
    }

    st.sidebar.header("🎯 Cutoff Thresholds")
    def safe_quantile(series, q, fallback):
        series = series.dropna()
        return float(series.quantile(q)) if len(series) > 0 else fallback

    cutoffs = {}
    cutoffs['Final report score (Average)'] = st.sidebar.slider(
        "Final Report Score", 0.0, 100.0,
        safe_quantile(df['Final report score (Average)'], 0.75, 75.0), 0.5)
    cutoffs['Absorption rate (Average)'] = st.sidebar.slider(
        "Absorption Rate", 0.0, 100.0,
        safe_quantile(df['Absorption rate (Average)'], 0.75, 75.0), 0.5)
    cutoffs['Progress report score'] = st.sidebar.slider(
        "Progress Report", 0.0, 45.0,
        safe_quantile(df['Progress report score'], 0.75, 30.0), 0.5)
    cutoffs['QS report score'] = st.sidebar.slider(
        "QS Report", 0.0, 45.0,
        safe_quantile(df['QS report score'], 0.75, 30.0), 0.5)

    show_data_preview(df, cutoffs)

    st.header("🎯 Overall Pass/Fail Analysis")
    metrics = calculate_metrics(df, cutoffs, overall_mode)

    overall = metrics['overall']

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("🎉 Pass All Criteria", f"{overall['pass']:,}", f"{overall['pass_pct']:.1f}%")
    with col2:
        st.metric("❌ Fail Any Criteria", f"{overall['fail']:,}", f"{overall['fail_pct']:.1f}%")
    
    if overall_mode == "all_data":
        with col3:
            st.metric("📊 Projects with Complete Data", f"{overall['total_complete']:,}", 
                     f"({overall['total_complete']/len(df)*100:.1f}% of total)")
    else:
        with col3:
            st.metric("📄 No Data (All Criteria)", f"{overall['no_data_all']:,}", 
                     f"{overall['no_data_all']/len(df)*100:.1f}%")

    st.subheader("📋 Per-Criterion Results")
    summary_data = []
    for c in criteria_display:
        m = metrics[c]
        summary_data.append({
            'Criterion': criteria_display[c],
            'Cutoff': f"{cutoffs[c]:.1f}",
            '✅ Pass': f"{m['pass']:,} ({m['pass_pct']:.1f}%)",
            '❌ Fail': f"{m['fail']:,} ({m['fail_pct']:.1f}%)",
            '📄 No Data': f"{m['no_data']:,} ({m['no_data_pct']:.1f}%)",
        })
    st.dataframe(pd.DataFrame(summary_data), use_container_width=True)

    st.subheader("🥧 Visuals")
    fig = create_pie_charts(metrics, criteria_display)
    st.plotly_chart(fig, use_container_width=True)

    csv_data = pd.DataFrame(summary_data).to_csv(index=False).encode('utf-8')
    st.download_button(
        "💾 Download CSV",
        csv_data,
        f"analysis_{selected_sector}_{overall_mode}.csv",
        "text/csv"
    )

else:
    st.info(
        "👈 Upload Excel file\n\n"
        "**Required columns:**\n"
        "• `Sector` (SCH, VET, ADU)\n"
        "• `Final report score (Average)`\n"
        "• `Absorption rate (Average)`\n"
        "• `Progress report score`\n"
        "• `QS report score`"
    )
# In[ ]:
