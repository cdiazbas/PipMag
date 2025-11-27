from __future__ import annotations

import configparser
import os
from dataclasses import dataclass
from typing import Dict, List, Optional
import datetime as dt

import pandas as pd
import requests
import streamlit as st

from theming import init_theme, render_theme_toggle, apply_theme_css
from home import load_data


ADS_ENDPOINT = "https://api.adsabs.harvard.edu/v1/search/query"


@dataclass
class ADSPaper:
    title: str
    bibcode: str
    first_author: str
    year: str
    url: str


class ADSSearch:
    def __init__(self):
        token = os.environ.get("ADS_DEV_KEY")
        if not token:
            cfg = configparser.ConfigParser()
            cfg.read("config.ini")
            token = cfg.get("DEFAULT", "ADS_DEV_KEY", fallback=None)
        if not token:
            raise ValueError(
                "ADS API key not found. Set ADS_DEV_KEY in env or config.ini"
            )
        self.token = token

    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}

    def search(self, terms: List[str], rows: int = 100) -> List[ADSPaper]:
        query_terms = " AND ".join([f'full:"{t}"' for t in terms if str(t).strip()])
        params = {
            "q": query_terms,
            "fl": "id,title,bibcode,author,year",
            "rows": rows,
            "sort": "date desc",
        }
        r = requests.get(ADS_ENDPOINT, headers=self._headers(), params=params, timeout=30)
        if r.status_code == 401:
            raise PermissionError("Unauthorized (401). Check your ADS API token.")
        r.raise_for_status()
        data = r.json()
        docs = data.get("response", {}).get("docs", [])
        out: List[ADSPaper] = []
        for p in docs:
            title = (p.get("title") or [""])[0]
            bibcode = p.get("bibcode", "")
            authors = p.get("author") or [""]
            first = authors[0] if authors else ""
            year = str(p.get("year", ""))
            url = f"https://ui.adsabs.harvard.edu/abs/{bibcode}"
            out.append(ADSPaper(title, bibcode, first, year, url))
        return out

    def search_advanced(self, query: str, rows: int = 100, sort: str = "date desc") -> List[ADSPaper]:
        params = {
            "q": query,
            "fl": "id,title,bibcode,author,year",
            "rows": rows,
            "sort": sort,
        }
        r = requests.get(ADS_ENDPOINT, headers=self._headers(), params=params, timeout=30)
        if r.status_code == 401:
            raise PermissionError("Unauthorized (401). Check your ADS API token.")
        r.raise_for_status()
        data = r.json()
        docs = data.get("response", {}).get("docs", [])
        out: List[ADSPaper] = []
        for p in docs:
            title = (p.get("title") or [""])[0]
            bibcode = p.get("bibcode", "")
            authors = p.get("author") or [""]
            first = authors[0] if authors else ""
            year = str(p.get("year", ""))
            url = f"https://ui.adsabs.harvard.edu/abs/{bibcode}"
            out.append(ADSPaper(title, bibcode, first, year, url))
        return out


def human_date(d: pd.Timestamp) -> str:
    if pd.isna(d):
        return ""
    d = pd.to_datetime(d)
    return f"{d.day} {d.strftime('%B %Y')}"


def build_terms_from_observation(date: Optional[pd.Timestamp], instruments: List[str]) -> List[str]:
    terms: List[str] = []
    # Always include SST like the notebook examples
    terms.append("SST")
    # Add instruments
    terms.extend([i for i in instruments if i])
    # Add formatted date
    if date is not None:
        terms.append(human_date(date))
    return terms


def main():
    init_theme()
    render_theme_toggle(position="header")
    apply_theme_css()

    st.title("📚 ADS Search")
    st.write("Search NASA/SAO ADS for publications using simple terms or an advanced query. API key is read from the ADS_DEV_KEY environment variable or config.ini.")

    df = load_data()

    # Left: inputs. Right: results
    left, right = st.columns([1, 2])

    with left:
        st.subheader("Build Search Terms")

        # Observation-driven helpers
        with st.expander("From Observation", expanded=True):
            if df.empty or "date_time" not in df.columns:
                st.info("No observation data available to prefill terms.")
                selected_date = None
                selected_instr: List[str] = []
            else:
                unique_dates = sorted({d.date() for d in df["date_time"].dropna()})
                # Default example date: 25 May 2017 if available
                if unique_dates:
                    default_dt = dt.date(2017, 5, 25)
                    default_idx = unique_dates.index(default_dt) if default_dt in unique_dates else 0
                    date_val = st.selectbox("Date", options=unique_dates, index=default_idx)
                else:
                    date_val = st.selectbox("Date", options=[None])
                selected_date = pd.Timestamp(date_val) if date_val else None

                all_instr = sorted({i for row in df.get("instruments", []) for i in (row or [])})
                # Default example instrument: CRISP if available
                default_instr = ["CRISP"] if "CRISP" in all_instr else []
                selected_instr = st.multiselect(
                    "Instrument(s)", options=all_instr, default=default_instr, help="Add one or more instruments"
                )

            terms_from_obs = build_terms_from_observation(selected_date, selected_instr)
            st.caption(f"Terms from observation: {', '.join(terms_from_obs) if terms_from_obs else '—'}")

        # Manual terms
        with st.expander("Manual Terms", expanded=False):
            # Default example terms per notebook: SST, CRISP, 25 May 2017
            manual_terms_str = st.text_input("Comma-separated terms", value="SST, CRISP, 25 May 2017")
            manual_terms = [t.strip() for t in manual_terms_str.split(",") if t.strip()]

        # Advanced query
        with st.expander("Advanced Query (optional)", expanded=False):
            st.caption("Provide a full ADS query (overrides terms above when used). Example: full:\"SST\" AND full:\"CRISP\" AND year:2017")
            advanced_query = st.text_area("ADS query string", value="", height=80)
            rows = st.number_input("Rows", value=100, min_value=1, max_value=500)
            sort = st.text_input("Sort", value="date desc")

        st.divider()
        run = st.button("🔎 Run Search", type="primary", use_container_width=True)

    with right:
        st.subheader("Results")
        try:
            ads = ADSSearch()
        except Exception as e:
            st.warning("ADS API key missing. Set ADS_DEV_KEY or create config.ini. See docs/Setting-up-configuration-file.md")
            st.stop()

        results: List[ADSPaper] = []
        if run:
            try:
                if advanced_query.strip():
                    results = ads.search_advanced(advanced_query.strip(), rows=rows, sort=sort)
                else:
                    terms = (terms_from_obs or []) + manual_terms
                    results = ads.search(terms, rows=rows)
            except PermissionError as pe:
                st.error(str(pe))
            except requests.HTTPError as he:
                st.error(f"ADS error: {he}")
            except Exception as e:
                st.error(f"Unexpected error: {e}")

        if results:
            # Format DataFrame
            data = [
                {
                    "#": idx + 1,
                    "Title": r.title,
                    "First Author": r.first_author,
                    "Year": r.year,
                    "Bibcode": r.bibcode,
                    "URL": r.url,
                }
                for idx, r in enumerate(results)
            ]
            res_df = pd.DataFrame(data)

            # Interactive grid with clickable link
            colcfg = {
                "URL": st.column_config.LinkColumn("URL", display_text="Open in ADS"),
            }
            st.data_editor(
                res_df,
                column_config=colcfg,
                disabled=True,
                hide_index=True,
                width="stretch",
            )

            # Download
            csv_bytes = res_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="⬇️ Download Results CSV",
                data=csv_bytes,
                file_name="ads_search_results.csv",
                mime="text/csv",
                use_container_width=True,
            )
        else:
            st.info("Run a search to see results.")


if __name__ == "__main__":
    main()
