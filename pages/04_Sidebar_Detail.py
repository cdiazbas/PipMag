"""Sidebar Detail Query page (Interactive, Cloud-safe).

Displays a table with single-row selection; shows a rich detail panel in the sidebar.
"""

import importlib.util
import sys
from datetime import time
from typing import Any

import pandas as pd
import streamlit as st

from theming import init_theme, setup_theme

# Import load_data from 01_Home.py
spec = importlib.util.spec_from_file_location("home_module", "pages/01_Home.py")
home_module = importlib.util.module_from_spec(spec)
sys.modules["home_module"] = home_module
spec.loader.exec_module(home_module)
load_data = home_module.load_data


def _normalize_lists(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "date_time" in out.columns:
        out["date_time"] = pd.to_datetime(out["date_time"], errors="coerce")
    if "time" not in out.columns and "date_time" in out.columns:
        out["time"] = out["date_time"].dt.time
    if "polarimetry" in out.columns:
        out["polarimetry"] = out["polarimetry"].astype(str).str.strip().str.capitalize()
    return out


def render_detail_panel(row: pd.Series):
    """Renderiza el panel de detalle en el sidebar."""
    st.subheader("🔍 Detalle Seleccionado")

    with st.container():
        st.caption("Fecha & Hora")
        dt = row.get("date_time")
        st.write(dt.strftime("%Y-%m-%d %H:%M:%S") if pd.notna(dt) else "N/A")

        st.caption("Target")
        target = row.get("target", "N/A")
        if isinstance(target, list):
            target = ", ".join(target)
        st.write(target)

        st.caption("Instrumentos")
        instruments = row.get("instruments", [])
        if isinstance(instruments, list):
            st.write(", ".join(instruments))
        else:
            st.write(instruments or "N/A")

        st.caption("Polarimetry")
        pol = row.get("polarimetry")
        st.write("✓ Sí" if str(pol) == "True" else "✗ No")

    st.markdown("---")

    if pd.notna(row.get("primary_image")):
        with st.container():
            st.subheader("🖼️ Imagen Principal")
            st.image(row["primary_image"], use_container_width=True)

    if pd.notna(row.get("primary_video")):
        with st.container():
            st.subheader("🎬 Video Principal")
            st.video(row["primary_video"])

    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        additional_images = row.get("additional_images", [])
        if additional_images:
            st.subheader(f"📷 Imágenes ({len(additional_images)})")
            for i, img_url in enumerate(additional_images[:5]):
                with st.expander(f"Img {i+1}"):
                    st.image(img_url, use_container_width=True)

    with col2:
        additional_movies = row.get("additional_movies", [])
        if additional_movies:
            st.subheader(f"🎥 Videos ({len(additional_movies)})")
            for i, vid_url in enumerate(additional_movies[:3]):
                with st.expander(f"Video {i+1}"):
                    st.video(vid_url)

    comments = row.get("comments")
    if pd.notna(comments):
        st.markdown("---")
        st.subheader("💬 Comentarios")
        st.info(str(comments))

    if st.button("❌ Cerrar Detalle", use_container_width=True, type="primary"):
        st.session_state["selected_row_id"] = None
        st.session_state.pop("selected_row_data", None)


@st.cache_data(show_spinner=False)
def _cached_load_data() -> pd.DataFrame:
    df = load_data()
    return df.copy()


@st.cache_data(show_spinner=False)
def _cached_normalize(df: pd.DataFrame) -> pd.DataFrame:
    return _normalize_lists(df)


def main():
    init_theme()

    # Hide default nav and style active item
    st.markdown(
        """
        <style>
        [data-testid='stSidebarNav'] { display: none !important; }
        [data-testid="stSidebar"] [aria-current="page"] {
            background: #ff4b4b !important; color: #fff !important;
            border-radius: 8px; font-weight: bold;
            box-shadow: 0 2px 8px rgba(255,75,75,0.18);
            border-left: 6px solid #ffa63a;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Initialize selection state
    st.session_state.setdefault("selected_row_id", None)

    # Sidebar with filters and detail
    with st.sidebar:
        st.page_link('streamlit_app.py', label='Home', icon='🔭')
        st.page_link('pages/02_Data_Query.py', label='Data Query', icon='🔎')
        st.page_link('pages/03_Modal_Query.py', label='Modal Query', icon='🪟')
        st.page_link('pages/04_Sidebar_Detail.py', label='Sidebar Detail', icon='📋')
        st.markdown('<hr style="border: none; border-top: 2px solid #444; margin: 12px 0;">', unsafe_allow_html=True)
        setup_theme()

        st.header("Filtros")

        # Compute date range from data (cached)
        df_temp = _cached_load_data()
        min_date = pd.Timestamp.now().date()
        max_date = pd.Timestamp.now().date()
        if not df_temp.empty:
            df_temp = _cached_normalize(df_temp)
            min_date = df_temp["date_time"].min().date()
            max_date = df_temp["date_time"].max().date()

        start_date = st.date_input("Desde", value=min_date, min_value=min_date, max_value=max_date)
        end_date = st.date_input("Hasta", value=max_date, min_value=min_date, max_value=max_date)

        keyword = st.text_input("🔍 Buscar", value="", placeholder="Ej: solar, prominence")
        pol_mode = st.selectbox("Polarimetry", options=["All", "True", "False"], index=0)

        st.markdown("---")
        if st.session_state.get("selected_row_data") is not None:
            render_detail_panel(st.session_state["selected_row_data"])

    # Main content
    st.title("🔎 Data Query - Modo Sidebar")

    df = _cached_load_data()
    if df.empty:
        st.stop()
    df = _cached_normalize(df)

    # Apply filters
    result_df = df.copy()
    if start_date:
        result_df = result_df[result_df["date_time"].dt.date >= start_date]
    if end_date:
        result_df = result_df[result_df["date_time"].dt.date <= end_date]

    if pol_mode != "All" and "polarimetry" in result_df.columns:
        result_df = result_df[result_df["polarimetry"].astype(str) == pol_mode]

    if keyword:
        kw = keyword.lower()
        mask = result_df.apply(lambda row: row.astype(str).str.lower().str.contains(kw).any(), axis=1)
        result_df = result_df[mask]

    # Media preparation
    def pick_primary(urls, exts):
        if isinstance(urls, list) and urls:
            matches = [u for u in urls if isinstance(u, str) and u.lower().endswith(exts)]
            return matches[0] if matches else None
        return None

    if "image_links" in result_df.columns:
        result_df["primary_image"] = result_df["image_links"].apply(lambda x: pick_primary(x, (".png", ".jpg", ".jpeg", ".gif")))
    if "video_links" in result_df.columns:
        result_df["primary_video"] = result_df["video_links"].apply(lambda x: pick_primary(x, (".mp4", ".webm", ".mov")))

    def collect_additional(row):
        p_img = row.get("primary_image")
        p_vid = row.get("primary_video")
        img_links = row.get("image_links", [])
        vid_links = row.get("video_links", [])
        additional_images = [u for u in img_links if isinstance(u, str) and u and u != p_img and u.lower().endswith((".png", ".jpg", ".jpeg", ".gif"))]
        additional_movies = [u for u in vid_links if isinstance(u, str) and u and u != p_vid and u.lower().endswith((".mp4", ".webm", ".mov"))]
        return pd.Series({"additional_images": additional_images, "additional_movies": additional_movies})

    result_df[["additional_images", "additional_movies"]] = result_df.apply(collect_additional, axis=1)

    if "date_time" in result_df.columns:
        result_df = result_df.sort_values("date_time", ascending=False)

    # Table
    st.subheader("📊 Selecciona una fila para ver detalles")

    display_df = result_df.copy()
    if "date_time" in display_df.columns:
        display_df["date_time"] = pd.to_datetime(display_df["date_time"], errors="coerce")
    if "instruments" in display_df.columns:
        display_df["instruments"] = display_df["instruments"].apply(lambda x: ", ".join(x) if isinstance(x, list) else ("" if pd.isna(x) else str(x)))
    if "polarimetry" in display_df.columns:
        display_df["polarimetry"] = display_df["polarimetry"].astype(str) == "True"

    show_cols = [c for c in ["date_time", "instruments", "target", "comments", "polarimetry", "primary_image", "primary_video"] if c in display_df.columns]

    column_config = {
        "date_time": st.column_config.DatetimeColumn("Date & Time", format="YYYY-MM-DD HH:mm:ss"),
        "primary_image": st.column_config.ImageColumn("Preview", width="small"),
        "primary_video": st.column_config.LinkColumn("Video", display_text="▶️ Play"),
        "instruments": st.column_config.TextColumn("Instruments", width="medium"),
        "target": st.column_config.TextColumn("Target", width="medium"),
        "comments": st.column_config.TextColumn("Comments", width="large"),
        "polarimetry": st.column_config.CheckboxColumn("Polarimetry", width="small"),
    }

    event = st.dataframe(
        display_df[show_cols],
        column_config=column_config,
        hide_index=True,
        use_container_width=True,
        on_select="rerun",
        selection_mode="single-row",
    )

    # Throttle selection updates: only change state when index actually changes; avoid manual reruns
    if event.selection.rows:
        selected_idx = event.selection.rows[0]
        if selected_idx != st.session_state.get("selected_row_id"):
            selected_row = result_df.iloc[selected_idx]
            st.session_state["selected_row_id"] = selected_idx
            st.session_state["selected_row_data"] = selected_row
    elif st.session_state.get("selected_row_id") is not None and not event.selection.rows:
        st.session_state["selected_row_id"] = None
        st.session_state.pop("selected_row_data", None)

    # Export
    st.markdown("---")
    try:
        export_df = result_df.drop(columns=["additional_images", "additional_movies"], errors="ignore")
        csv = export_df.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Exportar CSV", csv, "query_results.csv", "text/csv")
    except Exception as e:
        st.error(f"Error: {e}")


if __name__ == "__main__":
    main()
