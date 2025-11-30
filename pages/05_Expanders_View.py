"""Expanders View page (Interactive, Cloud-safe).

Renders observations as individual expanders with rich media and metadata.
Limits results for performance and uses native components only.
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
    """Normaliza datos del CSV"""
    out = df.copy()
    if "date_time" in out.columns:
        out["date_time"] = pd.to_datetime(out["date_time"], errors="coerce")
    if "time" not in out.columns and "date_time" in out.columns:
        out["time"] = out["date_time"].dt.time
    if "polarimetry" in out.columns:
        out["polarimetry"] = out["polarimetry"].astype(str).str.strip().str.capitalize()
    return out


def create_expander_header(row: pd.Series) -> str:
    """Crea un header informativo para cada expander"""
    date = row["date_time"].strftime("%Y-%m-%d %H:%M") if pd.notna(row["date_time"]) else "N/A"
    target = row.get("target", "N/A")
    if isinstance(target, list):
        target = ", ".join(target)
    has_image = "🖼️" if pd.notna(row.get("primary_image")) else ""
    has_video = "🎬" if pd.notna(row.get("primary_video")) else ""
    img_count = len(row.get("additional_images", []))
    vid_count = len(row.get("additional_movies", []))
    return f"{date} | {target} {has_image}{has_video} ({img_count}+{vid_count})"


def render_media_content(row: pd.Series):
    """Renderiza el contenido multimedia dentro del expander"""
    col1, col2 = st.columns(2)
    with col1:
        if pd.notna(row.get("primary_image")):
            st.image(row["primary_image"], use_container_width=True, caption="Imagen Principal")
        additional_images = row.get("additional_images", [])
        if additional_images:
            with st.expander(f"📷 Imágenes Adicionales ({len(additional_images)})"):
                cols = st.columns(3)
                for i, img_url in enumerate(additional_images):
                    with cols[i % 3]:
                        st.image(img_url, use_container_width=True, caption=f"Img {i+1}")
    with col2:
        if pd.notna(row.get("primary_video")):
            st.video(row["primary_video"])
        additional_movies = row.get("additional_movies", [])
        if additional_movies:
            with st.expander(f"🎥 Videos Adicionales ({len(additional_movies)})"):
                for i, vid_url in enumerate(additional_movies):
                    st.video(vid_url)
                    st.caption(f"Video {i+1}")


def render_metadata(row: pd.Series):
    """Renderiza metadatos en formato compacto"""
    metadata_cols = ["date_time", "instruments", "target", "comments", "polarimetry"]
    # Robust not-null check that handles lists/arrays without raising ambiguity
    def _is_present(v):
        if v is None:
            return False
        if isinstance(v, float):
            return not pd.isna(v)
        return True
    meta = {k: v for k, v in row.items() if k in metadata_cols and _is_present(v)}
    if "date_time" in meta:
        meta["date_time"] = meta["date_time"].strftime("%Y-%m-%d %H:%M:%S")
    if "instruments" in meta and isinstance(meta["instruments"], list):
        meta["instruments"] = ", ".join(meta["instruments"])
    st.dataframe(pd.DataFrame([meta]), hide_index=True, width='stretch')


def main():
    init_theme()

    # Hide default nav
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

    with st.sidebar:
        st.page_link('streamlit_app.py', label='Home', icon='🔭')
        st.page_link('pages/02_Data_Query.py', label='Data Query', icon='🔎')
        st.page_link('pages/03_Modal_Query.py', label='Modal Query', icon='🪟')
        st.page_link('pages/04_Sidebar_Detail.py', label='Sidebar Detail', icon='📋')
        st.page_link('pages/05_Expanders_View.py', label='Expanders View', icon='📂')
        st.markdown('<hr style="border: none; border-top: 2px solid #444; margin: 12px 0;">', unsafe_allow_html=True)
        setup_theme()

    st.title("📂 Data Query - Modo Expansor")

    df = load_data()
    if df.empty:
        st.stop()
    df = _normalize_lists(df)

    # Filters (simplified)
    with st.sidebar:
        st.header("Filtros")
        min_date = df["date_time"].min().date() if df["date_time"].notna().any() else None
        max_date = df["date_time"].max().date() if df["date_time"].notna().any() else None
        start_date = st.date_input("Desde", value=min_date, min_value=min_date, max_value=max_date)
        end_date = st.date_input("Hasta", value=max_date, min_value=min_date, max_value=max_date)
        keyword = st.text_input("🔍 Buscar en target/comments", value="", placeholder="Ej: Sun, Venus, prom12")
        pol_mode = st.selectbox("Polarimetry", options=["All", "True", "False"], index=0)
        max_items = st.slider("Máx. resultados visibles", 5, 200, 50)

    result_df = df.copy()
    if start_date:
        result_df = result_df[result_df["date_time"].dt.date >= start_date]
    if end_date:
        result_df = result_df[result_df["date_time"].dt.date <= end_date]
    if pol_mode != "All":
        result_df = result_df[result_df["polarimetry"].astype(str) == pol_mode]
    if keyword:
        kw = keyword.lower()
        mask = result_df.apply(lambda row: row.astype(str).str.lower().str.contains(kw).any(), axis=1)
        result_df = result_df[mask]

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

    result_df = result_df.head(max_items)

    st.subheader(f"📋 Resultados ({len(result_df)} observaciones)")

    if result_df.empty:
        st.info("No hay resultados. Ajusta los filtros.")
        return

    progress_bar = st.progress(0)
    for idx, (_, row) in enumerate(result_df.iterrows()):
        progress_bar.progress((idx + 1) / len(result_df))
        with st.expander(create_expander_header(row), expanded=False):
            render_media_content(row)
            with st.expander("ℹ️ Metadatos", expanded=True):
                render_metadata(row)
    progress_bar.empty()

    with st.sidebar:
        st.markdown("---")
        st.subheader("Exportar")
        try:
            export_df = result_df.drop(columns=["additional_images", "additional_movies"], errors="ignore")
            csv = export_df.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Descargar CSV", csv, "query_results.csv", "text/csv")
        except Exception as e:
            st.error(f"Error: {e}")


if __name__ == "__main__":
    main()
