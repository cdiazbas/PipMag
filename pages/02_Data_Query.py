import html as htmlesc
from datetime import time
from typing import Any, List
import importlib.util
import sys

import pandas as pd
import streamlit as st

from theming import init_theme, setup_theme, is_dark

# Import load_data from 01_Home.py
spec = importlib.util.spec_from_file_location("home_module", "pages/01_Home.py")
home_module = importlib.util.module_from_spec(spec)
sys.modules["home_module"] = home_module
spec.loader.exec_module(home_module)
load_data = home_module.load_data


def _normalize_lists(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    # Ensure datetime parts exist
    if "date_time" in out.columns:
        out["date_time"] = pd.to_datetime(out["date_time"], errors="coerce")
    if "time" not in out.columns and "date_time" in out.columns:
        out["time"] = out["date_time"].dt.time
    # Normalize polarimetry textual form
    if "polarimetry" in out.columns:
        out["polarimetry"] = out["polarimetry"].astype(str).str.strip().str.capitalize()
    return out


def main():
    init_theme()
    # Hide Streamlit's default sidebar navigation and highlight active custom link in dark mode
    st.markdown("""
    <style>
    [data-testid='stSidebarNav'] { display: none !important; }
    [data-testid="stSidebar"] [aria-current="page"] {
        background: #ff4b4b !important;
        color: #fff !important;
        border-radius: 8px;
        font-weight: bold;
        box-shadow: 0 2px 8px rgba(255,75,75,0.18);
        border-left: 6px solid #ffa63a;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Custom sidebar navigation
    with st.sidebar:
        st.page_link('streamlit_app.py', label='Home', icon='🔭')
        st.page_link('pages/02_Data_Query.py', label='Data Query', icon='🔎')
        # Horizontal line for separation
        st.markdown('<hr style="border: none; border-top: 2px solid #444; margin: 12px 0;">', unsafe_allow_html=True)
    
    setup_theme()

    # st.title("🔎 Data Query")
    # st.caption("Filter observations with the styled HTML table from Home including lightweight preview thumbnails.")

    df = load_data()
    if df.empty:
        st.stop()

    df = _normalize_lists(df)

    # Sidebar filters (match 03 minus instruments per request)
    with st.sidebar:
        st.header("Query Filters")

        # Date range
        min_date = df["date_time"].min().date() if df["date_time"].notna().any() else None
        max_date = df["date_time"].max().date() if df["date_time"].notna().any() else None
        start_date = st.date_input("Start Date", value=min_date, min_value=min_date, max_value=max_date)
        end_date = st.date_input("End Date", value=max_date, min_value=min_date, max_value=max_date)

        # Time range
        col1, col2 = st.columns(2)
        with col1:
            start_time = st.time_input("Start Time", value=time(0, 0))
        with col2:
            end_time = st.time_input("End Time", value=time(23, 59))

        # Polarimetry
        pol_mode = st.selectbox("Polarimetry", options=["All", "True", "False"], index=0)

        keyword = st.text_input("Search in target/comments", value="")

        max_additional_sources = st.number_input(
            "Max additional sources", min_value=1, max_value=20, value=2, step=1,
            help="Show only the first X additional image/movie links per observation."
        )

    # Apply filters
    result_df = df.copy()

    if start_date:
        result_df = result_df[result_df["date_time"].dt.date >= start_date]
    if end_date:
        result_df = result_df[result_df["date_time"].dt.date <= end_date]

    if "time" in result_df.columns:
        result_df["time_obj"] = pd.to_datetime(result_df["time"].astype(str), format="%H:%M:%S", errors="coerce").dt.time
        result_df = result_df[(result_df["time_obj"] >= start_time) & (result_df["time_obj"] <= end_time)]

    if pol_mode != "All" and "polarimetry" in result_df.columns:
        result_df = result_df[result_df["polarimetry"].astype(str) == pol_mode]

    # Target selection (before keyword search)
    available_targets = set()
    if "target" in result_df.columns:
        for targets in result_df["target"].dropna():
            if isinstance(targets, str):
                for t in targets.split(","):
                    t = t.strip()
                    if t:
                        available_targets.add(t)
    available_targets = sorted(available_targets)
    st.subheader("Target Selection")
    selected_targets = st.multiselect("Target(s)", options=available_targets)

    if selected_targets:
        pattern = "|".join([t.replace("(", r"\(").replace(")", r"\)") for t in selected_targets])
        result_df = result_df[result_df["target"].fillna("").str.contains(pattern, case=False, na=False)]

    if keyword:
        kw = keyword.strip().lower()

        def text_has_kw(val: Any) -> bool:
            if pd.isna(val):
                return False
            # If value is a list, search within each element
            if isinstance(val, list):
                for v in val:
                    if pd.isna(v):
                        continue
                    if kw in str(v).lower():
                        return True
                return False
            return kw in str(val).lower()

        columns_to_search = [c for c in ["target", "comments"] if c in result_df.columns]
        if columns_to_search:
            mask = pd.Series(False, index=result_df.index)
            for col in columns_to_search:
                mask = mask | result_df[col].apply(text_has_kw)
            # Only apply filter if at least one match; otherwise keep all so user can refine
            if mask.any():
                result_df = result_df[mask]

    if result_df.empty:
        st.info("👆 Adjust the filters in the sidebar to see results")
        return

    # (Summary metrics removed per request)

    # Styled HTML table (exactly like Home)
    base_cols = [c for c in ["date_time", "instruments", "target", "comments", "polarimetry"] if c in result_df.columns]
    base_df = result_df.copy()

    # Helpers to select primary media and collect additional links
    def pick_primary_image(urls):
        if isinstance(urls, list) and urls:
            imgs = [u for u in urls if isinstance(u, str) and u.lower().endswith((".png",".jpg",".jpeg",".gif"))]
            return imgs[0] if imgs else None
        return None

    def pick_primary_video(urls):
        if isinstance(urls, list) and urls:
            vids = [u for u in urls if isinstance(u, str) and u.lower().endswith((".mp4",".webm",".mov"))]
            return vids[0] if vids else None
        return None

    def collect_additional_media(row):
        additional_images = []
        additional_movies = []
        img_links = row.get("image_links") if "image_links" in base_df.columns else None
        vid_links = row.get("video_links") if "video_links" in base_df.columns else None
        p_img = row.get("primary_image")
        p_vid = row.get("primary_video")
        # Add remaining image links
        if isinstance(img_links, list):
            for u in img_links:
                if isinstance(u, str) and u and u != p_img:
                    if u.lower().endswith((".png",".jpg",".jpeg",".gif")):
                        additional_images.append(u)
        # Add remaining video links
        if isinstance(vid_links, list):
            for u in vid_links:
                if isinstance(u, str) and u and u != p_vid:
                    if u.lower().endswith((".mp4",".webm",".mov")):
                        additional_movies.append(u)
        return pd.Series({"additional_images": additional_images, "additional_movies": additional_movies})

    # Derive primary media columns
    if "image_links" in base_df.columns:
        base_df["primary_image"] = base_df["image_links"].apply(pick_primary_image)
    else:
        base_df["primary_image"] = None

    if "video_links" in base_df.columns:
        base_df["primary_video"] = base_df["video_links"].apply(pick_primary_video)
    else:
        base_df["primary_video"] = None

    # Derive additional images/movies per row
    base_df[["additional_images", "additional_movies"]] = base_df.apply(collect_additional_media, axis=1)
    # Extend displayed columns (will reorder for display)
    base_cols.extend(["primary_image", "primary_video", "additional_images", "additional_movies"])

    # Sort by date_time desc when available
    if "date_time" in base_df.columns:
        base_df = base_df.sort_values("date_time", ascending=False)

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
        "primary_image": "Preview image",
        "primary_video": "Preview movie",
        "additional_images": "Additional images",
        "additional_movies": "Additional movies",
    }
    # Ensure preview image/movie first, additional images/movies last
    preview_first = ["primary_image", "primary_video"]
    other_cols = [c for c in base_cols if c in display_df.columns and c not in preview_first and c not in ["additional_images", "additional_movies"]]
    ordered_cols = preview_first + other_cols + [c for c in ["additional_images", "additional_movies"] if c in display_df.columns]
    header_cells = ''.join(f"<th>{htmlesc.escape(label_map.get(col, col))}</th>" for col in ordered_cols)

    rows_html_parts: List[str] = []
    for _, row in display_df.iterrows():
        tds = []
        for col in ordered_cols:
            val = row.get(col)
            if col == "primary_image":
                if isinstance(val, str) and val:
                    cell = f'<a href="{htmlesc.escape(val)}" target="_blank" rel="noopener noreferrer"><img loading="lazy" style="border-radius:4px;background:#000;width:80px;height:60px;object-fit:cover" src="{htmlesc.escape(val)}" alt="Preview image"></a>'
                else:
                    cell = ""
            elif col == "primary_video":
                if isinstance(val, str) and val:
                    play_icon = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI4MCIgaGVpZ2h0PSI2MCIgdmlld0JveD0iMCAwIDgwIDYwIj48cmVjdCB3aWR0aD0iODAiIGhlaWdodD0iNjAiIHJ4PSI4IiBmaWxsPSIjMDAwIi8+PHBvbHlnb24gcG9pbnRzPSIzMiwyMCAzMiw0MCA0OCwzMCIgZmlsbD0iI2ZmNGI0YiIvPjwvc3ZnPg=="
                    cell = f'<a href="{htmlesc.escape(val)}" target="_blank" rel="noopener noreferrer"><img loading="lazy" style="border-radius:4px;width:80px;height:60px;object-fit:cover" src="{play_icon}" alt="Preview movie"></a>'
                else:
                    cell = ""
            elif col == "additional_images":
                links = val if isinstance(val, list) else []
                if links:
                    parts = []
                    for u in links[:int(max_additional_sources)]:
                        parts.append(f'<a href="{htmlesc.escape(u)}" target="_blank" rel="noopener noreferrer">image</a>')
                    more = len(links) - len(parts)
                    cell = ", ".join(parts) + (f" (+{more} more)" if more > 0 else "")
                else:
                    cell = ""
            elif col == "additional_movies":
                links = val if isinstance(val, list) else []
                if links:
                    parts = []
                    for u in links[:int(max_additional_sources)]:
                        parts.append(f'<a href="{htmlesc.escape(u)}" target="_blank" rel="noopener noreferrer">movie</a>')
                    more = len(links) - len(parts)
                    cell = ", ".join(parts) + (f" (+{more} more)" if more > 0 else "")
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
        /* Column header row: orange titles on dark background */
        .modern-table thead { background: #1c1f26; }
        .modern-table thead th {
            color: #ff4b4b;
            padding: 14px 16px; text-align: left; font-weight: 600;
            text-transform: uppercase; font-size: 12px; letter-spacing: 0.5px;
            border-bottom: 2px solid #ff4b4b;
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

    # Export (match 03)
    st.subheader("Export Results")
    try:
        export_df = result_df.copy()
        for col in ["instruments", "target", "video_links", "image_links", "links"]:
            if col in export_df.columns:
                export_df[col] = export_df[col].apply(lambda x: ";".join(x) if isinstance(x, list) else x)
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


if __name__ == "__main__":
    main()
