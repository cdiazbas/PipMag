from __future__ import annotations

import streamlit as st
from streamlit import components as _components


THEME_STATE_KEY = "ui_theme"

# Modern Color Palette
COLORS = {
    "light": {
        "bg_primary": "#FAFBFC",
        "bg_secondary": "#F6F8FA",
        "accent_primary": "#0969DA",
        "accent_secondary": "#8250DF",
        "success": "#1A7F37",
        "warning": "#BF8700",
        "text_primary": "#1F2328",
        "text_secondary": "#656D76",
        "border": "#D1D9E0",
    },
    "dark": {
        "bg_primary": "#0D1117",
        "bg_secondary": "#161B22",
        "accent_primary": "#58A6FF",
        "accent_secondary": "#A371F7",
        "success": "#3FB950",
        "warning": "#D29922",
        "text_primary": "#E6EDF3",
        "text_secondary": "#7D8590",
        "border": "#30363D",
    }
}


def init_theme(default: str | None = None) -> None:
    """Initialize theme state from session or Streamlit config.

    default: override default base ("light" or "dark"). If None, read from config.
    """
    if THEME_STATE_KEY not in st.session_state:
        # Prefer explicit default, else Streamlit config, else dark as global default
        base = "dark"
        st.session_state[THEME_STATE_KEY] = base.lower()


def is_dark() -> bool:
    val = st.session_state.get(THEME_STATE_KEY, "light")
    return str(val).lower() == "dark"


def get_colors() -> dict:
    """Get current theme colors."""
    theme = "dark" if is_dark() else "light"
    return COLORS[theme]


def render_theme_toggle(position: str = "header") -> None:
    """Render a simple theme toggle (Light/Dark).

    position: "header" places it in a right-aligned column at the top.
    """
    init_theme()

    def set_theme(dark: bool):
        st.session_state[THEME_STATE_KEY] = "dark" if dark else "light"

    if position == "header":
        # Reduced spacer to bring content closer to top while keeping toggle clickable.
        cols = st.columns([1, 1, 1, 1, 1])
        with cols[-1]:
            st.markdown("<div style='height:0.0rem'></div>", unsafe_allow_html=True)
            st.toggle(
                "Dark mode",
                value=is_dark(),
                on_change=lambda: set_theme(not is_dark()),
                help="Toggle between light and dark mode",
            )
    else:
        # Add a small spacer to move the inline toggle down
        st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)
        st.toggle(
            "Dark mode",
            value=is_dark(),
            on_change=lambda: set_theme(not is_dark()),
            help="Toggle between light and dark mode",
        )

def render_theme_toggle_sidebar() -> None:
    """Render the dark mode toggle inside the Streamlit sidebar."""
    init_theme()

    def set_theme(dark: bool):
        st.session_state[THEME_STATE_KEY] = "dark" if dark else "light"

    with st.sidebar:
        # st.markdown("### Appearance")
        st.toggle(
            "Dark mode",
            value=is_dark(),
            on_change=lambda: set_theme(not is_dark()),
            help="Toggle between light and dark mode",
        )

def render_theme_toggle_floating(top: str = "2rem", right: str = "2rem") -> None:
    """Render a dark mode toggle that is fixed-positioned and does not affect layout flow.

    top/right: CSS offsets from viewport edges.
    This avoids column/layout shifts by absolutely positioning a wrapper.
    """
    init_theme()

    def set_theme(dark: bool):
        st.session_state[THEME_STATE_KEY] = "dark" if dark else "light"

        # True floating toggle rendered via HTML component that does not affect layout flow
        current_dark = is_dark()
        bg = "rgba(0,0,0,0.35)" if current_dark else "rgba(255,255,255,0.65)"
        border = "rgba(255,255,255,0.25)" if current_dark else "rgba(0,0,0,0.15)"
        text_color = "#E6EDF3" if current_dark else "#1F2328"
        checked_attr = "checked" if current_dark else ""
        html = """
        <div id=\"floating-theme-toggle\" style=\"position: fixed; top: {top}; right: {right}; z-index: 10000;\">
            <label style=\"display:flex; align-items:center; gap:6px; padding:6px 10px; border-radius:24px; backdrop-filter: blur(6px); background: {bg}; border: 1px solid {border}; color: {text_color}; font-size: 0.8rem;\">
                <input id=\"toggle-input\" type=\"checkbox\" {checked_attr} style=\"transform: scale(1.1);\"/>
                <span>Dark mode</span>
            </label>
            <script>
                const input = document.getElementById('toggle-input');
                input.addEventListener('change', () => {
                    const value = input.checked ? 'dark' : 'light';
                    if (window.Streamlit && window.Streamlit.setComponentValue) {
                        window.Streamlit.setComponentValue(value);
                    }
                });
            </script>
        </div>
        """.format(top=top, right=right, bg=bg, border=border, text_color=text_color, checked_attr=checked_attr)
        # Render with minimal height; content is fixed-positioned and won't affect layout.
        value = _components.v1.html(html, height=1, width=0)
        if isinstance(value, str) and value in ("dark", "light"):
                st.session_state[THEME_STATE_KEY] = value


def apply_theme_css() -> None:
    """Inject comprehensive CSS to adapt all UI elements to the selected theme."""
    init_theme()
    if is_dark():
        css = """
        <style>
        /* Ultra-tight top spacing */
        [data-testid="stAppViewContainer"] > .main, .block-container {
            padding-top: 0.0rem !important;
        }
        h1 { margin-top: 0.05rem !important; margin-bottom: 0.25rem !important; }
        h2 { margin-top: 0.05rem !important; margin-bottom: 0.25rem !important; }
        /* Remove default top gap occasionally injected */
        div[data-testid="stToolbar"] + div:empty { display: none !important; }
        /* Base backgrounds and text */
        html, body, [data-testid="stAppViewContainer"], .main, .block-container {
            background-color: #0e1117 !important;
            color: #fafafa !important;
        }
        [data-testid="stHeader"] {
            background: transparent !important;
        }
        
        /* Sidebar - all variations */
        [data-testid="stSidebar"], 
        section[data-testid="stSidebar"] > div,
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
        [data-testid="stSidebar"] .element-container {
            background-color: #262730 !important;
            color: #fafafa !important;
        }
        /* Reduce sidebar top padding to bring content closer to top */
        section[data-testid="stSidebar"] > div {
            padding-top: 0.5rem !important;
        }
        
        /* Text elements - comprehensive */
        h1, h2, h3, h4, h5, h6, p, span, div, label, .stMarkdown {
            color: #fafafa !important;
        }
        
        /* Markdown text specifically */
        [data-testid="stMarkdownContainer"] p,
        [data-testid="stMarkdownContainer"] span,
        [data-testid="stMarkdownContainer"] div {
            color: #fafafa !important;
        }
        
        /* Links */
        a { 
            color: #58a6ff !important; 
        }
        a:hover { 
            color: #79b8ff !important; 
        }
        
        /* Widgets - inputs, selects, textareas */
        input, select, textarea, 
        .stTextInput input, 
        .stSelectbox select, 
        .stMultiSelect, 
        .stSlider, 
        .stNumberInput input,
        [data-baseweb="input"] input {
            background-color: #1c1e26 !important;
            color: #fafafa !important;
            border-color: #30363d !important;
        }
        
        /* Dropdown menus and popovers */
        [data-baseweb="select"] > div, 
        [data-baseweb="popover"],
        [data-baseweb="menu"],
        [role="listbox"],
        [role="option"] {
            background-color: #1c1e26 !important;
            color: #fafafa !important;
        }
        
        /* Multi-select tags - SAME RED AS LIGHT MODE */
        [data-baseweb="tag"],
        .stMultiSelect [data-baseweb="tag"],
        span[data-baseweb="tag"] {
            background-color: #ff4b4b !important;
            color: #ffffff !important;
        }
        
        /* Tag close button */
        [data-baseweb="tag"] svg,
        [data-baseweb="tag"] path {
            fill: #ffffff !important;
        }
        
        /* Dataframes and tables - VISIBLE WITH CONTRAST */
        .dataframe, 
        .stDataFrame, 
        [data-testid="stDataFrame"] {
            background-color: #1c1f26 !important;
        }
        
        /* DataFrame table structure */
        [data-testid="stDataFrame"] table,
        table {
            background-color: #1c1f26 !important;
            border: 1px solid #30363d !important;
        }
        
        /* DataFrame header row */
        [data-testid="stDataFrame"] thead,
        [data-testid="stDataFrame"] thead th,
        th.col_heading,
        thead th {
            background-color: #262c36 !important;
            color: #ffffff !important;
            font-weight: 600 !important;
            border: 1px solid #30363d !important;
        }
        
        /* DataFrame body and cells */
        [data-testid="stDataFrame"] tbody,
        tbody {
            background-color: #1c1f26 !important;
        }
        
        [data-testid="stDataFrame"] td,
        td.data,
        tbody td {
            background-color: #1c1f26 !important;
            color: #e6edf3 !important;
            border: 1px solid #30363d !important;
        }
        
        /* DataFrame alternating rows */
        [data-testid="stDataFrame"] tr:nth-child(even) td,
        tbody tr:nth-child(even) td {
            background-color: #22252e !important;
        }
        
        /* DataFrame hover */
        [data-testid="stDataFrame"] tr:hover td,
        tbody tr:hover td {
            background-color: #2d333b !important;
        }
        
        /* Expander */
        .streamlit-expanderHeader, 
        [data-testid="stExpander"],
        [data-testid="stExpander"] summary,
        details[data-testid="stExpander"] {
            background-color: #161b22 !important;
            color: #fafafa !important;
            border-color: #30363d !important;
        }
        
        /* Expander content */
        [data-testid="stExpander"] > div:last-child {
            background-color: #0d1117 !important;
        }
        
        /* Metrics */
        [data-testid="stMetric"], 
        [data-testid="stMetricLabel"],
        [data-testid="stMetricValue"], 
        [data-testid="stMetricDelta"],
        [data-testid="stMetric"] label,
        [data-testid="stMetric"] div {
            color: #fafafa !important;
        }
        
        /* Buttons */
        .stButton button, 
        button,
        [data-testid="baseButton-secondary"],
        [kind="secondary"] {
            background-color: #21262d !important;
            color: #fafafa !important;
            border: 1px solid #30363d !important;
        }
        .stButton button:hover, 
        button:hover {
            background-color: #30363d !important;
            border-color: #58a6ff !important;
        }
        
        /* Toggle/checkbox */
        .stCheckbox label, 
        .stRadio label,
        [data-testid="stWidgetLabel"] {
            color: #fafafa !important;
        }
        
        /* Code blocks */
        code, pre, .stCodeBlock,
        [data-testid="stCodeBlock"] {
            background-color: #161b22 !important;
            color: #fafafa !important;
            border-color: #30363d !important;
        }
        
        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {
            background-color: #0e1117 !important;
        }
        .stTabs [data-baseweb="tab"],
        button[role="tab"] {
            color: #fafafa !important;
        }
        
        /* Slider labels and values */
        .stSlider label, 
        .stSlider div,
        [data-testid="stSlider"] {
            color: #fafafa !important;
        }
        
        /* Caption text */
        .caption, 
        small, 
        [data-testid="stCaption"],
        [data-testid="stImageCaption"] {
            color: #8b949e !important;
        }
        
        /* Info/warning/error boxes */
        .stAlert, 
        [data-testid="stAlert"],
        [data-testid="stNotification"] {
            background-color: #161b22 !important;
            color: #fafafa !important;
            border-color: #30363d !important;
        }
        
        /* Video captions */
        [data-testid="stVideo"] + div,
        figcaption {
            color: #8b949e !important;
        }
        
        /* Column config text */
        [data-testid="column_config_editor"] {
            background-color: #161b22 !important;
            color: #fafafa !important;
        }
        
        /* Selectbox dropdown text */
        .stSelectbox label,
        .stMultiSelect label,
        [data-baseweb="select"] span {
            color: #fafafa !important;
        }
        
        /* Prevent white backgrounds on nested divs */
        div[style*="background-color: rgb(255, 255, 255)"],
        div[style*="background-color: white"],
        div[style*="background: rgb(255, 255, 255)"],
        div[style*="background: white"] {
            background-color: #0e1117 !important;
        }
        </style>
        """
    else:
        css = """
        <style>
        /* Ultra-tight top spacing */
        [data-testid="stAppViewContainer"] > .main, .block-container {
            padding-top: 0.25rem !important;
        }
        h1 { margin-top: 0.05rem !important; margin-bottom: 0.25rem !important; }
        h2 { margin-top: 0.40rem !important; margin-bottom: 0.25rem !important; }
        div[data-testid="stToolbar"] + div:empty { display: none !important; }
        /* Base backgrounds and text */
        html, body, [data-testid="stAppViewContainer"], .main {
            background-color: #ffffff !important;
            color: #262730 !important;
        }
        [data-testid="stHeader"] {background: transparent;}
        
        /* Sidebar */
        [data-testid="stSidebar"], section[data-testid="stSidebar"] > div {
            background-color: #f0f2f6 !important;
            color: #262730 !important;
        }
        /* Reduce sidebar top padding to bring content closer to top */
        section[data-testid="stSidebar"] > div {
            padding-top: 0.5rem !important;
        }
        
        /* Links */
        a { color: #0066cc !important; }
        a:hover { color: #0052a3 !important; }
        </style>
        """
    st.markdown(css, unsafe_allow_html=True)


def setup_theme(floating: bool = False, top: str = "1rem", right: str = "1rem", location: str = "sidebar") -> None:
    """Convenience helper to initialize theme, apply CSS, and render toggle.

    floating: if True, use floating toggle; else use header toggle.
    top/right: offsets for floating toggle.
    """
    init_theme()
    apply_theme_css()
    if floating:
        render_theme_toggle_floating(top=top, right=right)
    else:
        if location == "sidebar":
            render_theme_toggle_sidebar()
        elif location == "header":
            render_theme_toggle(position="header")
        else:
            render_theme_toggle(position=None)
