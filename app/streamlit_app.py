"""
Minimal smoke-test app — TEMPORARY.

If this renders on Streamlit Cloud but the full app (streamlit_app_full.py)
does not, then the bug is in the full app's code. If even this minimal
version is blank, then the Streamlit Cloud deployment itself is broken
and needs to be deleted and recreated.

Once we've identified which side has the issue, the full app is restored
by `cp app/streamlit_app_full.py app/streamlit_app.py`.
"""

import streamlit as st

st.set_page_config(page_title="Pairs Trading — Smoke Test", layout="wide")

st.title("Streamlit Cloud Smoke Test")
st.write("If you can see this text, Streamlit Cloud is rendering correctly.")
st.success("Deployment is healthy.")
st.write("Build version: 2026-05-03 10:30 UTC — minimal app for diagnosis.")

st.divider()

st.subheader("Click counter (verifies WebSocket is bidirectional)")
if "count" not in st.session_state:
    st.session_state.count = 0

if st.button("Increment"):
    st.session_state.count += 1

st.metric("Clicks", st.session_state.count)
