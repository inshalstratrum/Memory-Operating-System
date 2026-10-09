import streamlit as st
from orchestrator import process_input
from automation import run_task

st.set_page_config(page_title="Memory OS v5", layout="wide")

st.title("🧠 Memory OS v5 - AI System")

mode = st.sidebar.selectbox("Mode", ["Chat", "Automation"])

if "history" not in st.session_state:
    st.session_state.history = []

user_input = st.text_input("Enter command")

if user_input:

    if mode == "Automation":
        result = run_task(user_input)
        output = f"⚙️ {result}"

    else:
        output = process_input(user_input)

    st.session_state.history.append((user_input, output))

    st.subheader("Response")
    st.write(output)

st.sidebar.subheader("📜 Chat History")

for i, (q, a) in enumerate(reversed(st.session_state.history[-10:])):
    st.sidebar.write(f"**Q:** {q}")
    st.sidebar.write(f"**A:** {a}")
    st.sidebar.markdown("---")
