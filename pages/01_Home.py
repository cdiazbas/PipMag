import ast
import html as htmlesc
from typing import List, Any

import altair as alt
import pandas as pd
import streamlit as st


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
    # Page-scoped styling
    st.markdown("""
    <style>
    /* Reduce space above titles */
    .stMainBlockContainer {
    padding-left: 1rem;
    padding-right: 1rem;
    padding-top: 2rem;
    padding-bottom: 1rem;
    }
    /* Accent underline for main title */
    h1:after {content: ""; display: block; width: 64px; height: 4px; background: #ff4b4b; margin-top: 8px; border-radius: 2px;}
    /* Card-like metrics */
    [data-testid="stMetric"] {
        border-left: 4px solid #ff4b4b; 
        border-radius: 8px; 
        padding: 8px 12px; 
    }
    /* Hide Streamlit's default sidebar navigation */
    [data-testid="stSidebarNav"] { display: none !important; }
    /* Highlight active custom link */
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
    st.title("🔭 SST Observations (La Palma)")
    # st.caption("Explore observations, filter quickly, and visualize counts over time.")

    if df.empty:
        st.stop()

    # Sidebar filters
    with st.sidebar:
        st.header("Filters")
        y_min = int(pd.to_numeric(df["year"], errors="coerce").min()) if df["year"].notna().any() else 2000
        y_max = int(pd.to_numeric(df["year"], errors="coerce").max()) if df["year"].notna().any() else 2025
        years = st.slider("Years", y_min, y_max, (y_min, y_max))

        # Collect instrument options robustly (handle NaN/non-list entries)
        def as_list(x):
            if isinstance(x, list):
                return x
            if pd.isna(x) or x is None:
                return []
            if isinstance(x, str):
                return [x]
            return []
        if "instruments" in df.columns:
            all_instr = sorted({i for row in df["instruments"].apply(as_list) for i in row})
        else:
            all_instr = []

        default_instr = [x for x in ["CRISP", "CHROMIS", "IRIS"] if x in all_instr] or all_instr[:3]
        selected_instr = st.multiselect("Instruments", options=all_instr, default=default_instr)


    # Apply filters
    df_f = df.copy()
    df_f = df_f[df_f["year"].between(years[0], years[1], inclusive="both")]

    if selected_instr and "instruments" in df_f.columns:
        sel_set = set(selected_instr)
        df_f = df_f[df_f["instruments"].apply(lambda xs: bool(sel_set.intersection(xs if isinstance(xs, list) else [])))]
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
        # After exploding, restrict to selected instruments so the plot matches the filter
        if selected_instr:
            df_exp = df_exp[df_exp["instruments"].isin(selected_instr)]
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
        st.altair_chart(chart, width='stretch', theme="streamlit")
    else:
        st.info("No instrument data available for charting.")


    # Heatmap: observations distribution by year vs month/day
    st.subheader("Observations heatmap")
    if not df_f.empty:
        df_dates = df_f[["date_time"]].dropna().copy()
        df_dates["year"] = df_dates["date_time"].dt.year
        df_dates["month"] = df_dates["date_time"].dt.month
        # Month abbreviations for cleaner y-axis
        df_dates["month_abbr"] = df_dates["date_time"].dt.strftime('%b')
        df_heat = (
            df_dates.groupby(["year", "month_abbr"], dropna=True)
            .size()
            .reset_index(name="count")
        )

        # GitHub-like green palette from low → high activity
        # Orange-forward palette (light → strong) aligned with app's main orange
        # Automatic thresholds from data distribution (quantiles)
        counts = df_heat["count"].astype(float)
        if len(counts) > 0:
            q = counts.quantile([0.10, 0.30, 0.50, 0.70, 0.99]).tolist()
            # Build bin edges from 0 to max with quantiles as interior points
            min_edge = 0.0
            max_edge = float(counts.max()) if counts.max() > 0 else 1.0
            edges = [min_edge]
            for v in q:
                v = float(v)
                if v <= edges[-1]:
                    v = edges[-1] + 1.0
                if v < max_edge:
                    edges.append(v)
            edges.append(max_edge)
        else:
            edges = [0, 1, 3, 7, 12, 25, 50]

        # Color scale: two-stop gradient from light → strong #FF4B4B
        light_orange = "#ffeadf"
        strong_orange = "#FF4B4B"

        # Continuous color scale: map min non-zero → light, max → strong orange
        min_nonzero = float(counts[counts > 0].min()) if (counts > 0).any() else 1.0
        max_val = float(counts.max()) if len(counts) else 1.0

        heatmap = (
            alt.Chart(df_heat)
            .mark_square(size=700)
            .encode(
                x=alt.X("year:O", title="Year", sort="ascending", axis=alt.Axis(labelAngle=0)),
                y=alt.Y("month_abbr:O", title="Month", sort=["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]),
                color=alt.Color(
                    "count:Q",
                    title="Observations",
                    scale=alt.Scale(domain=[min_nonzero, max_val], range=[light_orange, strong_orange], clamp=True, interpolate='rgb'),
                    legend=alt.Legend(orient='right', direction='vertical', gradientLength=160)
                ),
                tooltip=[alt.Tooltip("year:O", title="Year"), alt.Tooltip("month_abbr:O", title="Month"), alt.Tooltip("count:Q", title="Observations")],
            )
            .properties(height=260)
        )

        st.altair_chart(heatmap, width='stretch', theme="streamlit")



def main():
    df = load_data()
    build_ui(df)


if __name__ == "__main__":
    main()
