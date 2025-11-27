import ast
import html as htmlesc
from typing import List, Any

import altair as alt
import pandas as pd
import streamlit as st
from theming import render_theme_toggle, apply_theme_css, is_dark, init_theme


@st.cache_data(show_spinner=True)
def load_data(csv_path: str = "data/la_palma_obs_data.csv") -> pd.DataFrame:
    try:
        df = pd.read_csv(csv_path, low_memory=False)
    except FileNotFoundError:
        st.error(
            f"Could not find '{csv_path}'. Make sure you've generated the database (see docs)"
        )
        return pd.DataFrame()

    # Parse datetime and ensure date parts exist
    if "date_time" in df.columns:
        df["date_time"] = pd.to_datetime(df["date_time"], errors="coerce")
    else:
        df["date_time"] = pd.NaT

    if "year" not in df.columns:
        df["year"] = df["date_time"].dt.year
    if "month" not in df.columns:
        df["month"] = df["date_time"].dt.month
    if "day" not in df.columns:
        df["day"] = df["date_time"].dt.day
    if "time" not in df.columns:
        df["time"] = df["date_time"].dt.time

    # Normalize polarimetry as string ("True"/"False")
    if "polarimetry" in df.columns:
        df["polarimetry"] = (
            df["polarimetry"].astype(str).str.strip().str.capitalize().replace({"Nan": "False"})
        )
    else:
        df["polarimetry"] = "False"

    # Columns that often store list-like content as strings
    list_like_cols = [
        col for col in ["instruments", "video_links", "image_links", "links"] if col in df.columns
    ]

    def to_list(val: Any) -> List[Any]:
        if isinstance(val, list):
            return val
        if pd.isna(val):
            return []
        if isinstance(val, str):
            s = val.strip()
            # Try to parse Python-literal lists like "['CRISP','IRIS']"
            if (s.startswith("[") and s.endswith("]")) or (s.startswith("(") and s.endswith(")")) or (
                s.startswith("{") and s.endswith("}")
            ):
                try:
                    parsed = ast.literal_eval(s)
                    if isinstance(parsed, list):
                        return parsed
                    if isinstance(parsed, dict):
                        return list(parsed.values())
                    return [parsed]
                except Exception:
                    pass
            # Fallback: split by comma/semicolon
            if ";" in s:
                return [x.strip() for x in s.split(";") if x.strip()]
            if "," in s:
                return [x.strip() for x in s.split(",") if x.strip()]
            if s:
                return [s]
        return []

    for col in list_like_cols:
        df[col] = df[col].apply(to_list)

    # Normalize instruments to simple uppercased tags where possible
    if "instruments" in df.columns:
        def normalize_instr(vals: List[Any]) -> List[str]:
            out = []
            for v in vals:
                if isinstance(v, str):
                    tag = v.strip().upper()
                    # Map common variants
                    if "CRISP" in tag:
                        out.append("CRISP")
                    elif "CHROMIS" in tag:
                        out.append("CHROMIS")
                    elif "IRIS" in tag:
                        out.append("IRIS")
                    else:
                        # Keep non-empty tokens
                        if tag:
                            out.append(tag)
                elif pd.notna(v):
                    out.append(str(v))
            # Deduplicate preserving order
            seen = set()
            uniq = []
            for x in out:
                if x not in seen:
                    seen.add(x)
                    uniq.append(x)
            return uniq

        df["instruments"] = df["instruments"].apply(normalize_instr)

    return df


def build_ui(df: pd.DataFrame) -> None:
    init_theme()
    # Render a small header toolbar with a theme toggle
    render_theme_toggle(position="header")
    apply_theme_css()
    
    # Page-scoped modern styling with theme awareness
    if is_dark():
        page_css = """
        <style>
        /* Accent underline for main title */
        h1:after {content: ""; display: block; width: 64px; height: 4px; background: #ff4b4b; margin-top: 8px; border-radius: 2px;}
        /* Card-like metrics - DARK MODE */
        [data-testid="stMetric"] div, [data-testid="stMetric"] label {
            color: #fafafa !important;
        }
        [data-testid="stMetric"] {
            background: #1c1f26 !important; 
            border: 1px solid #30363d !important; 
            border-left: 4px solid #ff4b4b !important; 
            border-radius: 8px; 
            padding: 8px 12px; 
            box-shadow: 0 1px 4px rgba(0,0,0,0.3) !important;
        }
        /* Dataframe header accent */
        [data-testid="stDataFrame"] thead { background: #ff4b4b !important; }
        [data-testid="stDataFrame"] thead th { color: #ffffff !important; }
        /* Section subtitles - DARK MODE */
        .section-title { font-weight: 600; font-size: 1rem; margin: 0 0 6px 0; color: #fafafa !important; }
        .section-sub { color: #8b949e !important; margin-bottom: 12px; }
        /* Force first nav item (main page) label to lowercase 'home' */
        [data-testid="stSidebarNav"] li:first-child a, 
        [data-testid="stSidebarNav"] li:first-child a span { 
            text-transform: lowercase !important; 
        }
        </style>
        """
    else:
        page_css = """
        <style>
        /* Accent underline for main title */
        h1:after {content: ""; display: block; width: 64px; height: 4px; background: #ff4b4b; margin-top: 8px; border-radius: 2px;}
        /* Card-like metrics - LIGHT MODE */
        [data-testid="stMetric"] div, [data-testid="stMetric"] label {
            color: inherit !important;
        }
        [data-testid="stMetric"] {
            background: #ffffff; 
            border: 1px solid #eaeaea; 
            border-left: 4px solid #ff4b4b; 
            border-radius: 8px; 
            padding: 8px 12px; 
            box-shadow: 0 1px 4px rgba(0,0,0,0.04);
        }
        /* Dataframe header accent */
        [data-testid="stDataFrame"] thead { background: #ff4b4b !important; }
        [data-testid="stDataFrame"] thead th { color: #ffffff !important; }
        /* Section subtitles - LIGHT MODE */
        .section-title { font-weight: 600; font-size: 1rem; margin: 0 0 6px 0; color: #333; }
        .section-sub { color: #666; margin-bottom: 12px; }
        /* Force first nav item (main page) label to lowercase 'home' */
        [data-testid="stSidebarNav"] li:first-child a, 
        [data-testid="stSidebarNav"] li:first-child a span { 
            text-transform: lowercase !important; 
        }
        </style>
        """
    
    st.markdown(page_css, unsafe_allow_html=True)
    st.title("🔭 SST Observations (La Palma)")
    st.caption("Explore observations, filter quickly, and visualize counts over time.")

    if df.empty:
        st.stop()

    # Sidebar filters
    with st.sidebar:
        st.header("Filters")
        y_min = int(pd.to_numeric(df["year"], errors="coerce").min()) if df["year"].notna().any() else 2000
        y_max = int(pd.to_numeric(df["year"], errors="coerce").max()) if df["year"].notna().any() else 2025
        years = st.slider("Years", y_min, y_max, (y_min, y_max))

        # Collect instrument options
        if "instruments" in df.columns:
            all_instr = sorted({i for row in df["instruments"] for i in (row or [])})
        else:
            all_instr = []

        default_instr = [x for x in ["CRISP", "CHROMIS", "IRIS"] if x in all_instr] or all_instr[:3]
        selected_instr = st.multiselect("Instruments", options=all_instr, default=default_instr)

        pol_opts = ["Any", "True", "False"]
        pol_choice = st.selectbox("Polarimetry", pol_opts, index=0)

        keyword = st.text_input("Search in target/comments", value="")

    # Apply filters
    df_f = df.copy()
    df_f = df_f[df_f["year"].between(years[0], years[1], inclusive="both")]

    if selected_instr and "instruments" in df_f.columns:
        sel_set = set(selected_instr)
        df_f = df_f[df_f["instruments"].apply(lambda xs: bool(sel_set.intersection(xs)))]

    if pol_choice != "Any" and "polarimetry" in df_f.columns:
        df_f = df_f[df_f["polarimetry"].astype(str) == pol_choice]

    if keyword:
        kw = keyword.strip().lower()
        def text_has_kw(val: Any) -> bool:
            if pd.isna(val):
                return False
            return kw in str(val).lower()
        mask = False
        if "target" in df_f.columns:
            mask = mask | df_f["target"].apply(text_has_kw)
        if "comments" in df_f.columns:
            mask = mask | df_f["comments"].apply(text_has_kw)
        df_f = df_f[mask]

    # Summary stats (card style)
    st.subheader("Summary")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Observations", len(df_f))
    with c2:
        st.metric("Years covered", len(df_f["year"].dropna().unique()))
    with c3:
        st.metric("Unique instruments", len({i for row in df_f.get("instruments", []) for i in (row or [])}))

    # Chart: observations per year by instrument
    st.subheader("Observations per year by instrument")
    if not df_f.empty and "instruments" in df_f.columns:
        df_exp = df_f[["year", "instruments"]].explode("instruments")
        df_exp = df_exp.dropna(subset=["instruments", "year"]).copy()
        df_counts = (
            df_exp.groupby(["year", "instruments"], dropna=True).size().reset_index(name="count")
        )
        # Orange-forward palette
        palette = ["#ff4b4b", "#ff7a59", "#ff9f80", "#ffa63a", "#ffbd2e", "#ff8c42", "#ff6f61"]
        chart = (
            alt.Chart(df_counts)
            .mark_line(point=True)
            .encode(
                x=alt.X("year:N", title="Year", sort="ascending"),
                y=alt.Y("count:Q", title="Observations"),
                color=alt.Color("instruments:N", title="Instrument", scale=alt.Scale(range=palette)),
                tooltip=["year:N", "instruments:N", "count:Q"],
            )
            .properties(height=320)
        )
        # Adapt Altair styling to the current Streamlit theme
        if is_dark():
            chart = (
                chart
                .configure(background="#0e1117")
                .configure_axis(labelColor="#fafafa", titleColor="#fafafa", gridColor="#333333")
                .configure_legend(labelColor="#fafafa", titleColor="#fafafa")
                .configure_title(color="#fafafa")
            )
        else:
            chart = (chart
                     .configure(background="#ffffff")
                     .configure_axis(gridColor="#eaeaea")
            )
        st.altair_chart(chart, width='stretch')
    else:
        st.info("No instrument data available for charting.")

    # Data table (Interactive or Styled)
    st.subheader("Filtered observations")
    view_mode = st.radio("Table display", ["Interactive", "Styled"], index=1, horizontal=True)

    # Build a lean display similar to Data Query
    base_cols = [c for c in ["date_time", "instruments", "target", "comments", "polarimetry"] if c in df_f.columns]
    base_df = df_f.copy()
    # Derive a single preferred video link if present
    if "video_links" in base_df.columns:
        def pick_preferred_link(urls):
            if isinstance(urls, list) and urls:
                mp4s = [u for u in urls if isinstance(u, str) and u.lower().endswith(".mp4")]
                return mp4s[0] if mp4s else (urls[0] if isinstance(urls[0], str) else None)
            return None
        base_df["video_link"] = base_df["video_links"].apply(pick_preferred_link)
        base_cols.append("video_link")

    # Sort by date_time desc when available
    if "date_time" in base_df.columns:
        base_df = base_df.sort_values("date_time", ascending=False)

    if view_mode == "Interactive":
        interactive_df = base_df[base_cols].copy()
        # Prepare types
        if "date_time" in interactive_df.columns:
            interactive_df["date_time"] = pd.to_datetime(interactive_df["date_time"], errors="coerce")
        if "instruments" in interactive_df.columns:
            interactive_df["instruments"] = interactive_df["instruments"].apply(lambda x: ", ".join(x) if isinstance(x, list) else ("" if pd.isna(x) else str(x)))
        if "polarimetry" in interactive_df.columns:
            interactive_df["polarimetry"] = interactive_df["polarimetry"].astype(str) == "True"
        if "video_link" in interactive_df.columns:
            interactive_df["video_link"] = interactive_df["video_link"].fillna("")

        column_config = {}
        if "date_time" in base_cols:
            column_config["date_time"] = st.column_config.DatetimeColumn("Date & Time", format="YYYY-MM-DD HH:mm:ss")
        if "instruments" in base_cols:
            column_config["instruments"] = st.column_config.TextColumn("Instruments", width="medium")
        if "target" in base_cols:
            column_config["target"] = st.column_config.TextColumn("Target", width="medium")
        if "comments" in base_cols:
            column_config["comments"] = st.column_config.TextColumn("Comments", width="large")
        if "polarimetry" in base_cols:
            column_config["polarimetry"] = st.column_config.CheckboxColumn("Polarimetry", width="small")
        if "video_link" in base_cols:
            column_config["video_link"] = st.column_config.LinkColumn("Video Link", display_text="🎬 Watch")

        # Compact styling and first-row highlight to match Data Query
        if is_dark():
            grid_css = """
            <style>
            [data-testid="stDataFrame"] td,
            [data-testid="stDataFrame"] th,
            [data-testid="stDataFrame"] [role="gridcell"],
            [data-testid="stDataFrame"] [role="columnheader"] {
                padding: 6px 8px !important;
                font-size: 13px !important;
                line-height: 1.2 !important;
            }
            [data-testid="stDataFrame"] tr:nth-child(even) td { 
                background-color: #1c1f26 !important; 
            }
            [data-testid="stDataFrame"] tbody tr:first-child td {
                background-color: rgba(255, 75, 75, 0.18) !important;
            }
            </style>
            """
        else:
            grid_css = """
            <style>
            [data-testid="stDataFrame"] td,
            [data-testid="stDataFrame"] th,
            [data-testid="stDataFrame"] [role="gridcell"],
            [data-testid="stDataFrame"] [role="columnheader"] {
                padding: 6px 8px !important;
                font-size: 13px !important;
                line-height: 1.2 !important;
            }
            [data-testid="stDataFrame"] tr:nth-child(even) td { 
                background-color: #ffffff !important; 
            }
            [data-testid="stDataFrame"] tbody tr:first-child td {
                background-color: rgba(255, 75, 75, 0.08) !important;
            }
            </style>
            """
        st.markdown(grid_css, unsafe_allow_html=True)

        rows = len(interactive_df)
        row_h = 28
        header_h = 44
        height = min(720, header_h + rows * row_h)
        st.data_editor(
            interactive_df,
            column_config=column_config,
            hide_index=True,
            disabled=True,
            width='stretch',
            height=height,
        )
    else:
        # Styled HTML table
        display_df = base_df[base_cols].copy()
        if "date_time" in display_df.columns:
            display_df["date_time"] = pd.to_datetime(display_df["date_time"], errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S")
        if "instruments" in display_df.columns:
            display_df["instruments"] = display_df["instruments"].apply(lambda x: ", ".join(x) if isinstance(x, list) else ("" if pd.isna(x) else str(x)))
        if "polarimetry" in display_df.columns:
            display_df["polarimetry"] = display_df["polarimetry"].apply(lambda x: "✓" if str(x) == "True" else "✗")

        label_map = {
            "date_time": "Date & Time",
            "instruments": "Instruments",
            "target": "Target",
            "comments": "Comments",
            "polarimetry": "Polarimetry",
            "video_link": "Video Link",
        }
        ordered_cols = [c for c in base_cols if c in display_df.columns]
        header_cells = ''.join(f"<th>{htmlesc.escape(label_map.get(col, col))}</th>" for col in ordered_cols)

        rows_html_parts = []
        for _, row in display_df.iterrows():
            tds = []
            for col in ordered_cols:
                val = row.get(col)
                if col == "video_link":
                    if isinstance(val, str) and val:
                        cell = f'<a href="{htmlesc.escape(val)}" target="_blank" rel="noopener noreferrer">🎬 Watch</a>'
                    else:
                        cell = ""
                else:
                    cell = htmlesc.escape("" if pd.isna(val) else str(val))
                tds.append(f"<td>{cell}</td>")
            rows_html_parts.append(f"<tr>{''.join(tds)}</tr>")

        table_html = f"<table class='modern-table'><thead><tr>{header_cells}</tr></thead><tbody>{''.join(rows_html_parts)}</tbody></table>"

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
            .modern-table thead { background: #ff4b4b; color: #ffffff; }
            .modern-table thead th {
                padding: 14px 16px; text-align: left; font-weight: 600;
                text-transform: uppercase; font-size: 12px; letter-spacing: 0.5px;
                border-bottom: 1px solid #30363d;
            }
            .modern-table tbody tr { border-bottom: 1px solid #30363d; transition: background-color 0.2s ease; }
            .modern-table tbody tr:hover { background-color: rgba(255, 75, 75, 0.18); }
            .modern-table tbody td { padding: 12px 16px; border-bottom: 1px solid #30363d; }
            .modern-table tbody tr:nth-child(even) td { background-color: #2a1d1d; }
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
            .modern-table thead { background: #ff4b4b; color: #ffffff; }
            .modern-table thead th {
                padding: 14px 16px; text-align: left; font-weight: 600;
                text-transform: uppercase; font-size: 12px; letter-spacing: 0.5px;
            }
            .modern-table tbody tr { border-bottom: 1px solid #e0e0e0; transition: background-color 0.2s ease; }
            .modern-table tbody tr:hover { background-color: rgba(255, 75, 75, 0.08); }
            .modern-table tbody td { padding: 12px 16px; }
            .modern-table tbody tr:nth-child(even) td { background-color: #fff7f5; }
            .modern-table a { color: #ff4b4b; text-decoration: none; font-weight: 500; }
            .modern-table a:hover { text-decoration: underline; }
            </style>
            """

        st.markdown(table_css, unsafe_allow_html=True)
        st.markdown(table_html, unsafe_allow_html=True)


def main():
    df = load_data()
    build_ui(df)


if __name__ == "__main__":
    main()
