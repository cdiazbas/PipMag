"""Modal-based Data Query page (Interactive only, Cloud-safe).

Provides single-row selection with a high-resolution media modal.
"""

from datetime import time
from typing import Any
import importlib.util
import sys

import pandas as pd
import streamlit as st

from theming import init_theme, setup_theme

# Import load_data from 01_Home.py dynamically to avoid circular import issues
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


def show_media_modal(row: pd.Series):
    """Modal con contenido en alta resolución de la observación seleccionada."""
    @st.dialog(f"Detalle: {row.get('target', 'N/A')}", width="large")
    def modal():
        col1, col2 = st.columns(2)

        # Columna izquierda: imágenes
        with col1:
            st.subheader("🖼️ Imagen Principal")
            if row.get("primary_image"):
                st.image(row["primary_image"], use_container_width=True)
            additional_images = row.get("additional_images", [])
            if additional_images:
                st.subheader(f"📷 Imágenes Adicionales ({len(additional_images)})")
                for i, img_url in enumerate(additional_images[:5], 1):
                    with st.expander(f"Imagen {i}"):
                        st.image(img_url, use_container_width=True)

        # Columna derecha: videos
        with col2:
            st.subheader("🎬 Video Principal")
            if row.get("primary_video"):
                st.video(row["primary_video"])
            additional_movies = row.get("additional_movies", [])
            if additional_movies:
                st.subheader(f"🎥 Videos Adicionales ({len(additional_movies)})")
                for i, vid_url in enumerate(additional_movies[:3], 1):
                    with st.expander(f"Video {i}"):
                        st.video(vid_url)

        # Metadatos (limpiamos urls para no saturar el JSON)
        with st.expander("📋 Metadatos Completos"):
            metadata = row.to_dict()
            for k in ["primary_image", "primary_video", "additional_images", "additional_movies"]:
                metadata.pop(k, None)
            st.json(metadata)

    modal()


def main():
    init_theme()

    # Ocultar navegación por defecto
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

    # Sidebar personalizado
    with st.sidebar:
        st.page_link('streamlit_app.py', label='Home', icon='🔭')
        st.page_link('pages/02_Data_Query.py', label='Data Query', icon='🔎')
        st.page_link('pages/03_Modal_Query.py', label='Modal Query', icon='🪟')
        st.markdown('<hr style="border: none; border-top: 2px solid #444; margin: 12px 0;">', unsafe_allow_html=True)
        setup_theme()

    st.title("🪟 Modal Query")
    st.caption("Explora y abre un modal con imágenes y videos en alta resolución.")

    df = load_data()
    if df.empty:
        st.stop()
    df = _normalize_lists(df)

    # ===== FILTROS =====
    with st.sidebar:
        st.header("Query Filters")
        min_date = df["date_time"].min().date() if df["date_time"].notna().any() else None
        max_date = df["date_time"].max().date() if df["date_time"].notna().any() else None
        start_date = st.date_input("Start Date", value=min_date, min_value=min_date, max_value=max_date)
        end_date = st.date_input("End Date", value=max_date, min_value=min_date, max_value=max_date)

        col1, col2 = st.columns(2)
        with col1:
            start_time = st.time_input("Start Time", value=time(0, 0))
        with col2:
            end_time = st.time_input("End Time", value=time(23, 59))

        pol_mode = st.selectbox("Polarimetry", options=["All", "True", "False"], index=0)
        keyword = st.text_input("Search in target/comments", value="")
        max_additional_sources = st.number_input("Max additional sources", min_value=1, max_value=20, value=2, step=1)

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

    if "target" in result_df.columns:
        available_targets = sorted(set([t.strip() for targets in result_df["target"].dropna() for t in str(targets).split(",") if t.strip()]))
        selected_targets = st.sidebar.multiselect("Target(s)", options=available_targets)
        if selected_targets:
            pattern = "|".join([t.replace("(", r"\(").replace(")", r"\)") for t in selected_targets])
            result_df = result_df[result_df["target"].fillna("").str.contains(pattern, case=False, na=False)]

    if keyword:
        kw = keyword.strip().lower()

        def text_has_kw(val: Any) -> bool:
            if pd.isna(val):
                return False
            if isinstance(val, list):
                return any(kw in str(v).lower() for v in val if not pd.isna(v))
            return kw in str(val).lower()

        columns_to_search = [c for c in ["target", "comments"] if c in result_df.columns]
        if columns_to_search:
            mask = pd.Series(False, index=result_df.index)
            for col in columns_to_search:
                mask = mask | result_df[col].apply(text_has_kw)
            if mask.any():
                result_df = result_df[mask]

    if result_df.empty:
        st.info("👆 Ajusta los filtros para ver resultados")
        return

    # ===== PREPARACIÓN DE MEDIOS =====
    def pick_primary(urls, extensions):
        if isinstance(urls, list) and urls:
            matches = [u for u in urls if isinstance(u, str) and u.lower().endswith(extensions)]
            return matches[0] if matches else None
        return None

    def collect_additional(row):
        p_img = row.get("primary_image")
        p_vid = row.get("primary_video")
        img_links = row.get("image_links", [])
        vid_links = row.get("video_links", [])
        additional_images = [u for u in img_links if isinstance(u, str) and u and u != p_img and u.lower().endswith((".png", ".jpg", ".jpeg", ".gif"))]
        additional_movies = [u for u in vid_links if isinstance(u, str) and u and u != p_vid and u.lower().endswith((".mp4", ".webm", ".mov"))]
        return pd.Series({"additional_images": additional_images, "additional_movies": additional_movies})

    if "image_links" in result_df.columns:
        result_df["primary_image"] = result_df["image_links"].apply(lambda x: pick_primary(x, (".png", ".jpg", ".jpeg", ".gif")))
    else:
        result_df["primary_image"] = None
    if "video_links" in result_df.columns:
        result_df["primary_video"] = result_df["video_links"].apply(lambda x: pick_primary(x, (".mp4", ".webm", ".mov")))
    else:
        result_df["primary_video"] = None

    result_df[["additional_images", "additional_movies"]] = result_df.apply(collect_additional, axis=1)

    if "date_time" in result_df.columns:
        result_df = result_df.sort_values("date_time", ascending=False)

    # ===== TABLA INTERACTIVA =====
    st.subheader("📊 Resultados")

    display_df = result_df.copy()
    if "date_time" in display_df.columns:
        display_df["date_time"] = pd.to_datetime(display_df["date_time"], errors="coerce")
    if "instruments" in display_df.columns:
        display_df["instruments"] = display_df["instruments"].apply(lambda x: ", ".join(x) if isinstance(x, list) else ("" if pd.isna(x) else str(x)))
    if "polarimetry" in display_df.columns:
        display_df["polarimetry"] = display_df["polarimetry"].astype(str) == "True"
    if "comments" in display_df.columns:
        display_df["comments"] = display_df["comments"].apply(lambda x: str(x)[:100] + "..." if len(str(x)) > 100 else str(x))
    if "primary_image" in display_df.columns:
        display_df["primary_image"] = display_df["primary_image"].fillna("")
    if "primary_video" in display_df.columns:
        display_df["primary_video"] = display_df["primary_video"].fillna("")

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

    if event.selection.rows:
        selected_idx = event.selection.rows[0]
        selected_row = result_df.iloc[selected_idx]
        show_media_modal(selected_row)

    # ===== EXPORTAR =====
    st.subheader("⬇️ Exportar")
    try:
        export_df = result_df.drop(columns=["time_obj"], errors="ignore").copy()
        for col in ["instruments", "target", "video_links", "image_links", "links"]:
            if col in export_df.columns:
                export_df[col] = export_df[col].apply(lambda x: ";".join(x) if isinstance(x, list) else x)
        csv_bytes = export_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Descargar CSV",
            data=csv_bytes,
            file_name="la_palma_query.csv",
            mime="text/csv",
            use_container_width=True,
        )
    except Exception as e:
        st.error(f"❌ Error preparando descarga: {e}")


if __name__ == "__main__":
    main()
