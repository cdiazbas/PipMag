import streamlit as st
from home import main as home_main


def main() -> None:
    # Configure the app so the sidebar header shows "Home"
    st.set_page_config(page_title="Home", page_icon="🔭", layout="wide", initial_sidebar_state="expanded")
    # Delegate to the Home implementation
    home_main()


if __name__ == "__main__":
    main()
