#!/usr/bin/env python
# coding: utf-8

# In[1]:
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import io

st.markdown("""
<style>
.metric-card {background: linear-gradient(135deg,#f5f7fa 0%,#c3cfe2 100%);padding:1rem;border-radius:10px;border-left:5px solid #1f77b4;}
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data(file_bytes):
    df = pd.read_excel(io.BytesIO(file_bytes))
    # ADDED: 'Project ID' and 'Organization name' to required columns
    required_cols = [
        'Project ID', 'Organization name', 'Sector',
        'Final report score (Average)', 'Absorption rate (Average)',
        'Progress report score', 'QS report score'
    ]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        st.error(f"❌ Missing columns: {', '.join(missing)}")
        st.stop()
    return df

def show_data_preview(df, cutoffs):
    st.header("📊 Data Distribution & Statistics")
    criteria = ['Final report score (Average)','Absorption rate (Average)','Progress report score','QS report score']
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
            fig = px.histogram(data, x=col, nbins=20, title=criteria_display[col],
                             color_discrete_sequence=['#1f77b4'])
            fig.add_vline(x=cutoffs[col], line_dash="dash", line_color="red",
                         line_width=3, annotation_text=f"Cutoff: {cutoffs[col]:.1f}",
                         annotation_position="top right")
            fig.update_layout(height=300, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

def calculate_metrics(df, cutoffs, overall_mode="all_data"):
    metrics = {}
    criteria = ['Final report score (Average)','Absorption rate (Average)',
                'Progress report score','QS report score']

    # Per-criterion metrics
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

    # Overall metrics
    overall_pass = 0
    overall_fail = 0
    overall_no_data_all = 0
    failed_projects_data = [] # NEW: tracking list for failed projects

    for _, row in df.iterrows():
        has_all_data  = all(pd.notna(row[c]) for c in criteria)
        applicable    = [c for c in criteria if pd.notna(row[c])]

        if overall_mode == "all_data":
            if has_all_data:
                failed_crits = [c for c in criteria if row[c] < cutoffs[c]]
                if not failed_crits:
                    overall_pass += 1
                else:
                    overall_fail += 1
                    # Record the failure details
                    failed_projects_data.append({
                        'Project ID': row['Project ID'],
                        'Sector': row['Sector'],
                        'Organization name': row['Organization name'],
                        'Failed Criteria Raw': failed_crits
                    })

        elif overall_mode == "all_projects":
            if not applicable:
                overall_no_data_all += 1
            else:
                failed_crits = [c for c in applicable if row[c] < cutoffs[c]]
                if not failed_crits:
                    overall_pass += 1
                else:
                    overall_fail += 1
                    # Record the failure details
                    failed_projects_data.append({
                        'Project ID': row['Project ID'],
                        'Sector': row['Sector'],
                        'Organization name': row['Organization name'],
                        'Failed Criteria Raw': failed_crits
                    })

    total_projects = len(df)

    if overall_mode == "all_data":
        total_complete = overall_pass + overall_fail
        excluded = total_projects - total_complete
        metrics['overall'] = {
            'pass': overall_pass,
            'fail': overall_fail,
            'no_data_all': excluded,
            'total_complete': total_complete,
            'total_projects': total_projects,
            'pass_pct': overall_pass / total_complete * 100 if total_complete > 0 else 0,
            'fail_pct': overall_fail / total_complete * 100 if total_complete > 0 else 0,
            'no_data_all_pct': excluded / total_projects * 100 if total_projects > 0 else 0,
        }
    else:
        metrics['overall'] = {
            'pass': overall_pass,
            'fail': overall_fail,
            'no_data_all': overall_no_data_all,
            'total_complete': overall_pass + overall_fail,
            'total_projects': total_projects,
            'pass_pct': overall_pass / total_projects * 100 if total_projects > 0 else 0,
            'fail_pct': overall_fail / total_projects * 100 if total_projects > 0 else 0,
            'no_data_all_pct': overall_no_data_all / total_projects * 100 if total_projects > 0 else 0,
        }
        
    metrics['failed_projects'] = failed_projects_data # Add the list to our metrics dictionary

    return metrics

def create_overall_pie(overall, overall_mode):
    if overall_mode == "all_data":
        labels = ['✅ Pass', '❌ Fail']
        values = [overall['pass'], overall['fail']]
        colors = ['#4CAF50', '#F44336']
        title = "Overall (projects with ALL criteria filled)"
    else:
        labels = ['✅ Pass', '❌ Fail', '📄 No Data']
        values = [overall['pass'], overall['fail'], overall['no_data_all']]
        colors = ['#4CAF50', '#F44336', '#FF9800']
        title = "Overall (all projects)"

    fig = go.Figure(go.Pie(
        labels=labels, values=values,
        marker=dict(colors=colors, line=dict(color='#000', width=1)),
        textinfo='label+percent', showlegend=True,
        hovertemplate='<b>%{label}</b><br>Projects: %{value}<br>Share: %{percent}<extra></extra>'
    ))
    fig.update_layout(height=400, title=title)
    return fig

def create_pie_charts(metrics, criteria_display):
    fig = make_subplots(
        rows=2, cols=2,
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
            row=row, col=col,
        )
    fig.update_layout(height=700, title="📊 Per-Criterion Distribution")
    return fig

# ── MAIN APP ──────────────────────────────────────────────────────────────────
st.title("🎯 Project Cutoff Analysis Tool")

uploaded_file = st.sidebar.file_uploader("📁 Upload Excel", type=['xlsx', 'xls'])

if uploaded_file is not None:
    df_full = load_data(uploaded_file.read())

    st.sidebar.header("📂 Sector Filter")
    sector_options = ['All'] + sorted(df_full['Sector'].dropna().unique().tolist())
    selected_sector = st.sidebar.selectbox("Sector", sector_options, index=0)
    df = df_full.copy() if selected_sector == 'All' else df_full[df_full['Sector'] == selected_sector].copy()
    st.sidebar.caption(f"📊 {len(df)} / {len(df_full)} projects")

    st.sidebar.header("🎛 Overall Analysis Mode")
    mode_label = st.sidebar.radio(
        "Pass/Fail calculation:",
        [
            "1. Projects with ALL criteria filled (pass / fail)",
            "2. All projects (pass / fail / no data for any criterion)",
        ],
        index=0,
    )
    overall_mode = "all_data" if "1." in mode_label else "all_projects"

    if overall_mode == "all_data":
        st.sidebar.caption("✏️ Only projects with all 4 scores filled are evaluated.")
    else:
        st.sidebar.caption("✏️ Every project is classified. Pass = meets cutoff on all criteria where data exists.")

    st.sidebar.header("🎯 Cutoff Thresholds")

    def safe_quantile(series, q, fallback):
        series = series.dropna()
        if len(series) > 0:
            val = series.quantile(q)
            return float(val) if not pd.isna(val) else fallback
        return fallback

    def sync_slider(key):
        st.session_state[f"num_{key}"] = st.session_state[f"slider_{key}"]

    def sync_num(key):
        st.session_state[f"slider_{key}"] = st.session_state[f"num_{key}"]

    def cutoff_widget(label, col_key, min_val, max_val, default):
        clamped_default = max(min_val, min(float(default), max_val))
        
        if f"slider_{col_key}" not in st.session_state:
            st.session_state[f"slider_{col_key}"] = clamped_default
            st.session_state[f"num_{col_key}"] = clamped_default
            
        st.sidebar.markdown(f"**{label}**")
        c1, c2 = st.sidebar.columns([3, 1])
        with c1:
            st.slider(" ", min_value=min_val, max_value=max_val,
                      key=f"slider_{col_key}", step=0.5, 
                      on_change=sync_slider, args=(col_key,),
                      label_visibility="collapsed")
        with c2:
            st.number_input(" ", min_value=min_val, max_value=max_val,
                            key=f"num_{col_key}", step=0.5, format="%.1f",
                            on_change=sync_num, args=(col_key,),
                            label_visibility="collapsed")
            
        return st.session_state[f"num_{col_key}"]

    cutoffs = {}
    cutoffs['Final report score (Average)'] = cutoff_widget(
        "Final Report Score", "final", 0.0, 100.0,
        safe_quantile(df['Final report score (Average)'], 0.75, 75.0))
    cutoffs['Absorption rate (Average)'] = cutoff_widget(
        "Absorption Rate", "absorb", 0.0, 100.0,
        safe_quantile(df['Absorption rate (Average)'], 0.75, 75.0))
    cutoffs['Progress report score'] = cutoff_widget(
        "Progress Report", "progress", 0.0, 45.0,
        safe_quantile(df['Progress report score'], 0.75, 30.0))
    cutoffs['QS report score'] = cutoff_widget(
        "QS Report", "qs", 0.0, 45.0,
        safe_quantile(df['QS report score'], 0.75, 30.0))

    criteria_display = {
        'Final report score (Average)': 'Final Report Score',
        'Absorption rate (Average)': 'Absorption Rate',
        'Progress report score': 'Progress Report',
        'QS report score': 'QS Report',
    }

    show_data_preview(df, cutoffs)

    st.header("🎯 Overall Pass/Fail Analysis")
    metrics = calculate_metrics(df, cutoffs, overall_mode)
    overall = metrics['overall']

    if overall_mode == "all_data":
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("🎉 Pass (all criteria)", f"{overall['pass']:,}",
                     f"{overall['pass_pct']:.1f}% of complete")
        with col2:
            st.metric("❌ Fail (any criterion)", f"{overall['fail']:,}",
                     f"{overall['fail_pct']:.1f}% of complete")
        with col3:
            st.metric("📊 Complete / Total",
                     f"{overall['total_complete']:,} / {overall['total_projects']:,}",
                     f"{overall['no_data_all_pct']:.1f}% excluded (missing data)")
    else:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("🎉 Pass (applicable criteria)", f"{overall['pass']:,}",
                     f"{overall['pass_pct']:.1f}% of all projects")
        with col2:
            st.metric("❌ Fail (any applicable criterion)", f"{overall['fail']:,}",
                     f"{overall['fail_pct']:.1f}% of all projects")
        with col3:
            st.metric("📄 No Data (all criteria missing)", f"{overall['no_data_all']:,}",
                     f"{overall['no_data_all_pct']:.1f}% of all projects")

    st.plotly_chart(create_overall_pie(overall, overall_mode), use_container_width=True)

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

    st.subheader("🥧 Per-Criterion Visuals")
    fig = create_pie_charts(metrics, criteria_display)
    st.plotly_chart(fig, use_container_width=True)

    # ── NEW FEATURE: Failed Projects Table ──────────────────────────────────────
    st.markdown("---")
    st.header("⚠️ Failed Projects List")
    st.write("List of projects that failed the selected overall criteria logic.")
    
    failed_projects_raw = metrics['failed_projects']
    if failed_projects_raw:
        # Convert raw criteria names to nice display names
        display_failed = []
        for fp in failed_projects_raw:
            mapped_crits = [criteria_display[c] for c in fp['Failed Criteria Raw']]
            display_failed.append({
                'Project ID': fp['Project ID'],
                'Sector': fp['Sector'],
                'Organization name': fp['Organization name'],
                'Failed Criteria': ", ".join(mapped_crits)
            })
            
        failed_df = pd.DataFrame(display_failed)
        st.dataframe(failed_df, use_container_width=True, hide_index=True)
        
        # Adding a download button for just the failed list
        csv_failed = failed_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            "💾 Download Failed Projects CSV", 
            csv_failed,
            f"failed_projects_{selected_sector}_{overall_mode}.csv", 
            "text/csv"
        )
    else:
        st.success("🎉 No projects failed the current criteria!")

    # ── Master Summary Download ─────────────────────────────────────────────────
    st.markdown("---")
    csv_data = pd.DataFrame(summary_data).to_csv(index=False).encode('utf-8')
    st.download_button("💾 Download Master Summary CSV", csv_data,
                      f"analysis_summary_{selected_sector}_{overall_mode}.csv", "text/csv")

else:
    st.info(
        "👈 Upload Excel file\n\n"
        "**Required columns:**\n"
        "• `Project ID`\n"
        "• `Organization name`\n"
        "• `Sector` (SCH, VET, ADU)\n"
        "• `Final report score (Average)`\n"
        "• `Absorption rate (Average)`\n"
        "• `Progress report score`\n"
        "• `QS report score`"
    )
# In[ ]:
