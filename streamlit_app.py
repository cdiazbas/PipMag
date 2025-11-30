import streamlit as st
import importlib.util
import sys

# Import from numbered module
spec = importlib.util.spec_from_file_location("home_module", "pages/01_Home.py")
home_module = importlib.util.module_from_spec(spec)
sys.modules["home_module"] = home_module
spec.loader.exec_module(home_module)
home_main = home_module.main


def main() -> None:
    # Configure the app so the sidebar header shows "Home"
    st.set_page_config(page_title="Home", page_icon="🔭", layout="wide", initial_sidebar_state="expanded")
    
    # Custom sidebar navigation
    with st.sidebar:
        st.page_link('streamlit_app.py', label='Home', icon='🔭')
        st.page_link('pages/02_Data_Query.py', label='Data Query', icon='🔎')

        # Horizontal line for separation
        st.markdown('<hr style="border: none; border-top: 2px solid #444; margin: 12px 0;">', unsafe_allow_html=True)
    
    # Delegate to the Home implementation
    home_main()


if __name__ == "__main__":
    main()
