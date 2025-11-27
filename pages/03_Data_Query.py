from typing import Any, List
import html as htmlesc
from datetime import time

import pandas as pd
import streamlit as st

from theming import render_theme_toggle, apply_theme_css, init_theme, is_dark
from home import load_data


def main():
    init_theme()
    render_theme_toggle(position="header")
    apply_theme_css()
    
    st.title("🔎 Data Query")
    st.write(
        """
        Build custom queries to filter SST observations. Select instruments, date ranges, 
        polarimetry mode, and targets to find exactly what you need. Export results to CSV.
        """
    )

    df = load_data()
    if df.empty:
        st.stop()

    # Live results: we'll compute results on every change (no button needed)

    # Sidebar filters
    with st.sidebar:
        st.header("Query Filters")
        
        # Instruments (multi-select)
        if "instruments" in df.columns:
            all_instr = sorted({i for row in df["instruments"] for i in (row or [])})
        else:
            all_instr = []
        
        selected_instruments = st.multiselect(
            "Instrument(s)",
            options=all_instr,
            help="Select one or more instruments. All selected must be present."
        )
        
        # Date range
        st.subheader("Date Range")
        min_date = df["date_time"].min().date() if df["date_time"].notna().any() else None
        max_date = df["date_time"].max().date() if df["date_time"].notna().any() else None
        
        start_date = st.date_input(
            "Start Date",
            value=min_date,
            min_value=min_date,
            max_value=max_date
        )
        
        end_date = st.date_input(
            "End Date",
            value=max_date,
            min_value=min_date,
            max_value=max_date
        )
        
        # Time range
        st.subheader("Time Range")
        col1, col2 = st.columns(2)
        with col1:
            start_time = st.time_input("Start Time", value=time(0, 0))
        with col2:
            end_time = st.time_input("End Time", value=time(23, 59))
        
        # Polarimetry mode
        pol_mode = st.selectbox(
            "Polarimetry",
            options=["All", "True", "False"],
            index=0
        )
        
        # Target options update is automatic; no button needed

    # Main area - Target selection and results
    
    # Apply initial filters to get available targets
    filtered_for_targets = df.copy()
    
    # Filter by instruments
    if selected_instruments:
        sel_set = set(selected_instruments)
        filtered_for_targets = filtered_for_targets[
            filtered_for_targets["instruments"].apply(
                lambda xs: sel_set.issubset(set(xs)) if xs else False
            )
        ]
    
    # Filter by date range
    if start_date:
        filtered_for_targets = filtered_for_targets[
            filtered_for_targets["date_time"].dt.date >= start_date
        ]
    if end_date:
        filtered_for_targets = filtered_for_targets[
            filtered_for_targets["date_time"].dt.date <= end_date
        ]
    
    # Filter by time range
    if "time" in filtered_for_targets.columns:
        filtered_for_targets["time_obj"] = pd.to_datetime(
            filtered_for_targets["time"].astype(str), format="%H:%M:%S", errors="coerce"
        ).dt.time
        filtered_for_targets = filtered_for_targets[
            (filtered_for_targets["time_obj"] >= start_time) &
            (filtered_for_targets["time_obj"] <= end_time)
        ]
    
    # Filter by polarimetry
    if pol_mode != "All" and "polarimetry" in filtered_for_targets.columns:
        filtered_for_targets = filtered_for_targets[
            filtered_for_targets["polarimetry"].astype(str) == pol_mode
        ]
    
    # Get available targets from filtered data
    available_targets = set()
    if "target" in filtered_for_targets.columns:
        for targets in filtered_for_targets["target"].dropna():
            if isinstance(targets, str):
                # Split by comma and strip whitespace
                for t in targets.split(","):
                    t = t.strip()
                    if t:
                        available_targets.add(t)
    
    available_targets = sorted(available_targets)
    
    # Target selection
    st.subheader("Target Selection")
    selected_targets = st.multiselect(
        "Target(s)",
        options=available_targets,
        help="Select one or more targets to filter observations"
    )
    
    # Compute results live on any widget change
    result_df = filtered_for_targets.copy()
    if selected_targets:
        target_pattern = "|".join([t.replace("(", r"\(").replace(")", r"\)") for t in selected_targets])
        result_df = result_df[
            result_df["target"].fillna("").str.contains(target_pattern, case=False, na=False)
        ]

    # Display results
    if result_df is not None and not result_df.empty:
        st.subheader("Query Results")
        
        # Metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Observations", len(result_df))
        with col2:
            st.metric("Date Range", f"{len(result_df['date_time'].dt.date.unique())} days")
        with col3:
            unique_instr = {i for row in result_df.get("instruments", []) for i in (row or [])}
            st.metric("Instruments", len(unique_instr))
        with col4:
            pol_count = result_df[result_df["polarimetry"].astype(str) == "True"].shape[0]
            st.metric("With Polarimetry", pol_count)
        
        # Display table with key columns
        display_cols = [
            c for c in [
                "date_time", "instruments", "target", "comments", "polarimetry"
            ] if c in result_df.columns
        ]
        
        # Create display dataframe
        display_df = result_df[display_cols].copy()
        
        # Format instruments as comma-separated string
        if "instruments" in display_df.columns:
            display_df["instruments"] = display_df["instruments"].apply(
                lambda x: ", ".join(x) if isinstance(x, list) else str(x)
            )
        
        # Add video link column
        if "video_links" in result_df.columns:
            display_df["video_link"] = result_df["video_links"].apply(
                lambda x: x[0] if isinstance(x, list) and len(x) > 0 and x[0] else None
            )
        
        # Sort by date_time descending when available
        if "date_time" in display_df.columns:
            display_df = display_df.sort_values("date_time", ascending=False).reset_index(drop=True)
        else:
            display_df = display_df.reset_index(drop=True)
        
        # Toggle between Interactive (sortable) and Styled (static) table
        view_mode = st.radio("Table display", ["Interactive", "Styled"], index=1, horizontal=True)

        # Column visibility selector
        available_cols = display_df.columns.tolist() + (["video_link"] if "video_link" in display_df.columns else [])
        # Ensure unique and preserve order
        available_cols = [c for c in ["date_time", "instruments", "target", "comments", "polarimetry", "video_link"] if c in available_cols]
        selected_cols = st.multiselect("Visible columns", options=available_cols, default=available_cols)

        # Build interactive dataframe with proper types
        interactive_df = display_df.copy()
        if "date_time" in interactive_df.columns:
            interactive_df["date_time"] = pd.to_datetime(interactive_df["date_time"], errors="coerce")
        if "video_link" in interactive_df.columns:
            # Keep raw URL for LinkColumn
            interactive_df["video_link"] = interactive_df["video_link"].fillna("")

        if view_mode == "Interactive":
            # Use Streamlit's interactive data editor for sorting by clicking headers
            column_config = {}
            if "date_time" in selected_cols:
                column_config["date_time"] = st.column_config.DatetimeColumn("Date & Time", format="YYYY-MM-DD HH:mm:ss")
            if "instruments" in selected_cols:
                column_config["instruments"] = st.column_config.TextColumn("Instruments", width="medium")
            if "target" in selected_cols:
                column_config["target"] = st.column_config.TextColumn("Target", width="medium")
            if "comments" in selected_cols:
                column_config["comments"] = st.column_config.TextColumn("Comments", width="large")
            if "polarimetry" in selected_cols:
                column_config["polarimetry"] = st.column_config.CheckboxColumn("Polarimetry", width="small")
            if "video_link" in selected_cols:
                column_config["video_link"] = st.column_config.LinkColumn("Video Link", display_text="🎬 Watch")
            # Page-scoped CSS: first-row highlight, no zebra stripes, compact rows
            if is_dark():
                grid_css = """
                <style>
                /* Compact cells */
                [data-testid="stDataFrame"] td,
                [data-testid="stDataFrame"] th,
                [data-testid="stDataFrame"] [role="gridcell"],
                [data-testid="stDataFrame"] [role="columnheader"] {
                    padding: 6px 8px !important;
                    font-size: 13px !important;
                    line-height: 1.2 !important;
                }
                /* Remove zebra stripes specifically for interactive tables */
                [data-testid="stDataFrame"] tr:nth-child(even) td { 
                    background-color: #1c1f26 !important; 
                }
                /* First row subtle highlight */
                [data-testid="stDataFrame"] tbody tr:first-child td {
                    background-color: rgba(255, 75, 75, 0.18) !important;
                }
                </style>
                """
            else:
                grid_css = """
                <style>
                /* Compact cells */
                [data-testid="stDataFrame"] td,
                [data-testid="stDataFrame"] th,
                [data-testid="stDataFrame"] [role="gridcell"],
                [data-testid="stDataFrame"] [role="columnheader"] {
                    padding: 6px 8px !important;
                    font-size: 13px !important;
                    line-height: 1.2 !important;
                }
                /* Remove zebra stripes specifically for interactive tables */
                [data-testid="stDataFrame"] tr:nth-child(even) td { 
                    background-color: #ffffff !important; 
                }
                /* First row subtle highlight */
                [data-testid="stDataFrame"] tbody tr:first-child td {
                    background-color: rgba(255, 75, 75, 0.08) !important;
                }
                </style>
                """
            st.markdown(grid_css, unsafe_allow_html=True)

            # Dynamic height so the table fits better in viewport
            rows = len(interactive_df)
            row_h = 28
            header_h = 44
            height = min(720, header_h + rows * row_h)
            st.data_editor(
                interactive_df[selected_cols],
                column_config=column_config,
                hide_index=True,
                disabled=True,
                width='stretch',
                height=height,
            )
        else:
            # Styled static HTML table (manually built for robust markup)
            html_df = display_df.copy()

            def pick_preferred_link(url_or_list):
                if isinstance(url_or_list, list):
                    mp4s = [u for u in url_or_list if isinstance(u, str) and u.lower().endswith(".mp4")]
                    if mp4s:
                        return mp4s[0]
                    return url_or_list[0] if url_or_list else None
                return url_or_list

            # Prepare a working copy with formatted values but without HTML in data yet
            if "date_time" in html_df.columns:
                html_df["date_time"] = pd.to_datetime(html_df["date_time"], errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S")
            if "polarimetry" in html_df.columns:
                html_df["polarimetry"] = html_df["polarimetry"].apply(lambda x: "✓" if str(x) == "True" else "✗")
            # Keep raw link for now

            # Reorder columns as per user selection
            ordered_cols = [c for c in selected_cols if c in html_df.columns]

            # Column labels
            label_map = {
                "date_time": "Date & Time",
                "instruments": "Instruments",
                "target": "Target",
                "comments": "Comments",
                "polarimetry": "Polarimetry",
                "video_link": "Video Link",
            }

            # Build HTML table safely
            header_cells = ''.join(f"<th>{htmlesc.escape(label_map.get(col, col))}</th>" for col in ordered_cols)
            rows_html_parts = []
            for _, row in html_df.iterrows():
                tds = []
                for col in ordered_cols:
                    val = row.get(col)
                    if col == "video_link":
                        url = pick_preferred_link(val)
                        if isinstance(url, str) and url:
                            cell = f'<a href="{htmlesc.escape(url)}" target="_blank" rel="noopener noreferrer">🎬 Watch</a>'
                        else:
                            cell = ""
                    else:
                        cell = htmlesc.escape( 
                            ", ".join(val) if isinstance(val, list) else ("" if pd.isna(val) else str(val))
                        )
                    tds.append(f"<td>{cell}</td>")
                rows_html_parts.append(f"<tr>{''.join(tds)}</tr>")

            table_html = f"<table class='modern-table'><thead><tr>{header_cells}</tr></thead><tbody>{''.join(rows_html_parts)}</tbody></table>"

            # Modern styled HTML table with dynamic light/dark theme
            if is_dark():
                table_css = """
                <style>
                .modern-table {
                    width: 100%;
                    border-collapse: collapse;
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                    font-size: 14px;
                    border-radius: 8px;
                    overflow: hidden;
                    background: #1c1f26;
                    color: #e6edf3;
                    border: 1px solid #30363d;
                }
                .modern-table thead {
                    background: #ff4b4b;
                    color: #ffffff;
                }
                .modern-table thead th {
                    padding: 14px 16px;
                    text-align: left;
                    font-weight: 600;
                    text-transform: uppercase;
                    font-size: 12px;
                    letter-spacing: 0.5px;
                    border-bottom: 1px solid #30363d;
                }
                .modern-table tbody tr {
                    border-bottom: 1px solid #30363d;
                    transition: background-color 0.2s ease;
                }
                .modern-table tbody tr:hover {
                    background-color: rgba(255, 75, 75, 0.18);
                }
                .modern-table tbody td {
                    padding: 12px 16px;
                    border-bottom: 1px solid #30363d;
                }
                .modern-table tbody tr:nth-child(even) td {
                    background-color: #2a1d1d;
                }
                .modern-table a { color: #ff4b4b; text-decoration: none; }
                .modern-table a:hover { text-decoration: underline; }
                </style>
                """
            else:
                table_css = """
                <style>
                .modern-table {
                    width: 100%;
                    border-collapse: collapse;
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                    font-size: 14px;
                    border-radius: 8px;
                    overflow: hidden;
                    background: #ffffff;
                    color: #262730;
                    border: 1px solid #e0e0e0;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
                }
                .modern-table thead {
                    background: #ff4b4b;
                    color: #ffffff;
                }
                .modern-table thead th {
                    padding: 14px 16px;
                    text-align: left;
                    font-weight: 600;
                    text-transform: uppercase;
                    font-size: 12px;
                    letter-spacing: 0.5px;
                }
                .modern-table tbody tr {
                    border-bottom: 1px solid #e0e0e0;
                    transition: background-color 0.2s ease;
                }
                .modern-table tbody tr:hover {
                    background-color: rgba(255, 75, 75, 0.08);
                }
                .modern-table tbody td {
                    padding: 12px 16px;
                }
                .modern-table tbody tr:nth-child(even) td {
                    background-color: #fff7f5;
                }
                .modern-table a { color: #ff4b4b; text-decoration: none; font-weight: 500; }
                .modern-table a:hover { text-decoration: underline; }
                </style>
                """

            # Inject CSS first, then the table HTML separately for reliability
            st.markdown(table_css, unsafe_allow_html=True)
            st.markdown(table_html, unsafe_allow_html=True)
        
        # Export functionality
        st.subheader("Export Results")
        try:
            export_df = result_df.copy()
            for col in ["instruments", "target", "video_links", "image_links", "links"]:
                if col in export_df.columns:
                    export_df[col] = export_df[col].apply(
                        lambda x: ";".join(x) if isinstance(x, list) else x
                    )
            csv_bytes = export_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="⬇️ Download CSV",
                data=csv_bytes,
                file_name="la_palma_query.csv",
                mime="text/csv",
                use_container_width=True,
            )
        except Exception as e:
            st.error(f"❌ Error preparing download: {e}")
    else:
        st.info("👆 Adjust the filters in the sidebar to see results")


if __name__ == "__main__":
    main()
