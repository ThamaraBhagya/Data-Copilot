import streamlit as st
import requests
import pandas as pd

API_URL = "http://localhost:8000"

st.set_page_config(page_title="📊 Data Copilot", page_icon="📊", layout="wide")
st.title("📊 LLM-Powered Data Analysis Copilot")

if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# --- Sidebar ---
with st.sidebar:
    st.header("📁 Dataset")

    # ✅ Show previously stored datasets
    st.subheader("Previously Uploaded")
    try:
        res = requests.get(f"{API_URL}/datasets")
        existing = res.json()
        if existing:
            options = {f"{d['session_id']} ({d['rows']} rows)": d["session_id"] for d in existing}
            selected = st.selectbox("Pick an existing dataset", ["-- Select --"] + list(options.keys()))
            if selected != "-- Select --":
                picked_id = options[selected]
                if st.button("Load this dataset"):
                    st.session_state.session_id = picked_id
                    st.session_state.chat_history = []
                    st.success(f"✅ Loaded: {picked_id}")
        else:
            st.info("No datasets stored yet.")
    except:
        st.warning("Could not reach backend.")

    st.divider()

    # ✅ Upload new CSV
    st.subheader("Upload New CSV")
    uploaded_file = st.file_uploader("Choose a CSV file", type=["csv"])
    if uploaded_file:
        with st.spinner("Uploading..."):
            res = requests.post(
                f"{API_URL}/upload",
                files={"file": (uploaded_file.name, uploaded_file.getvalue(), "text/csv")}
            )
            if res.status_code == 200:
                data = res.json()
                st.session_state.session_id = data["session_id"]
                st.session_state.chat_history = []
                cached = data.get("cached", False)
                st.success(f"{'📦 Reusing cached' if cached else '✅ Uploaded'}: {data['shape'][0]} rows × {data['shape'][1]} cols")
            else:
                st.error("Upload failed.")

    st.divider()

    # ✅ Delete dataset option
    if st.session_state.session_id:
        if st.button("🗑️ Delete current dataset", type="secondary"):
            requests.delete(f"{API_URL}/datasets/{st.session_state.session_id}")
            st.session_state.session_id = None
            st.session_state.chat_history = []
            st.rerun()

    st.markdown("**Example Questions:**")
    st.markdown("- Show a bar chart of sales by category")
    st.markdown("- What is the average price per product?")
    st.markdown("- Show correlation heatmap")
    st.markdown("- Top 10 customers by total spend")

# --- Chat ---
if st.session_state.session_id:
    st.caption(f"🗂️ Active dataset: `{st.session_state.session_id}`")
    st.divider()

    for chat in st.session_state.chat_history:
        with st.chat_message("user"):
            st.write(chat["question"])
        with st.chat_message("assistant"):
            if chat.get("result"):
                if isinstance(chat["result"], list):
                    st.dataframe(pd.DataFrame(chat["result"]))
                else:
                    st.write(chat["result"])
            if chat.get("chart_bytes"):
                st.image(chat["chart_bytes"], width="stretch")
            if chat.get("error"):
                st.error(chat["error"])
            with st.expander("🔍 Generated Code"):
                st.code(chat.get("generated_code", ""), language="python")

    question = st.chat_input("Ask anything about your data...")

    if question:
        with st.chat_message("user"):
            st.write(question)
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                res = requests.post(f"{API_URL}/query", data={
                    "session_id": st.session_state.session_id,
                    "question": question
                })

            if res.status_code == 200:
                data = res.json()
                # Show result table
                if data.get("result"):
                    result_data = data["result"]
                    if isinstance(result_data, list):
                        st.dataframe(pd.DataFrame(result_data))
                    else:
                        st.write(result_data)
                chart_bytes = None
                if data.get("has_chart"):
                    chart_res = requests.get(f"{API_URL}/chart")
                    if chart_res.status_code == 200:
                        chart_bytes = chart_res.content
                        st.image(chart_bytes, width="stretch")

                if data.get("attempts", 1) > 1:
                    st.caption(f"⚡ Fixed after {data['attempts']} attempts")

                with st.expander("🔍 Generated Code"):
                    st.code(data.get("generated_code", ""), language="python")

                st.session_state.chat_history.append({
                    "question": question,
                    "result": data.get("result"),
                    "chart_bytes": chart_bytes,
                    "generated_code": data.get("generated_code"),
                    "error": None
                })
            else:
                err = res.json()
                st.error(err.get("error"))
                with st.expander("Generated Code (failed)"):
                    st.code(err.get("generated_code", ""), language="python")
else:
    st.info("👈 Upload a CSV or pick an existing dataset from the sidebar.")