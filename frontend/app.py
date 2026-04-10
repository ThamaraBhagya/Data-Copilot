import streamlit as st
import requests
import pandas as pd
import os

API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="Data Copilot", page_icon="📊", layout="wide")
st.title("LLM-Powered Data Analysis Copilot")

# --- Session State ---
defaults = {
    "session_id": None,
    "chat_history": [],
    "summary": None,
    "prefill_question": "",
    "multi_mode": False,
    "multi_session_ids": [],
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# --- Sidebar ---
with st.sidebar:
    st.header("🗄️ Data Copilot", divider="gray")

    # 1. UPLOAD SECTION (Hidden in an expander to save space)
    with st.expander("➕ Upload New CSV", expanded=False):
        uploaded_file = st.file_uploader("Choose a CSV file", type=["csv"], label_visibility="collapsed")
        if uploaded_file:
            with st.spinner("Saving..."):
                res = requests.post(
                    f"{API_URL}/upload",
                    files={"file": (uploaded_file.name, uploaded_file.getvalue(), "text/csv")}
                )
                if res.status_code == 200:
                    st.success("✅ Saved! Select it below.")
                else:
                    st.error("Upload failed.")

    # 2. DATASET SELECTION CARD
    with st.container(border=True):
        st.subheader("📂 Load Workspace")
        try:
            res = requests.get(f"{API_URL}/datasets")
            existing = res.json()
            if existing:
                options = {f"{d['session_id']} ({d['rows']} rows)": d["session_id"] for d in existing}

                # Multi-CSV mode toggle
                st.session_state.multi_mode = st.toggle("🔗 Multi-CSV Join Mode", value=st.session_state.multi_mode)

                if st.session_state.multi_mode:
                    st.caption("Select 2+ datasets to query together.")
                    selected_multi = st.multiselect("Select datasets", list(options.keys()), label_visibility="collapsed")
                    
                    if len(selected_multi) >= 2:
                        if st.button("Load Workspace", type="primary", use_container_width=True):
                            st.session_state.multi_session_ids = [options[s] for s in selected_multi]
                            st.session_state.session_id = None
                            st.session_state.chat_history = []
                            st.session_state.summary = None
                            st.success(f"Loaded {len(selected_multi)} datasets.")
                            st.rerun()
                else:
                    selected = st.selectbox("Pick a dataset", ["-- Select --"] + list(options.keys()), label_visibility="collapsed")
                    if selected != "-- Select --":
                        picked_id = options[selected]
                        if picked_id == st.session_state.session_id:
                            st.info("🟢 Currently Active")
                        else:
                            if st.button("Load Dataset", type="primary", use_container_width=True):
                                with st.spinner("Loading & summarizing..."):
                                    load_res = requests.post(f"{API_URL}/load", data={"session_id": picked_id})
                                    if load_res.status_code == 200:
                                        load_data = load_res.json()
                                        st.session_state.session_id = picked_id
                                        st.session_state.multi_session_ids = []
                                        st.session_state.chat_history = []
                                        st.session_state.summary = load_data.get("summary")
                                        st.rerun()
                                    else:
                                        st.error("Failed to load.")
            else:
                st.info("No datasets yet. Upload one above.")
        except Exception as e:
            st.error(f"Backend offline: {e}")

    # Active dataset actions
    active = st.session_state.session_id
    multi_active = st.session_state.multi_session_ids

    # 3. ACTIVE DATASET CONTROLS
    if active or multi_active:
        with st.container(border=True):
            if active:
                st.markdown(f"**🟢 Active:** `{active}`")
            else:
                st.markdown(f"**🟢 Active (Multi):** `{len(multi_active)} datasets`")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("🧹 Clear Chat", use_container_width=True):
                    if active:
                        requests.delete(f"{API_URL}/history/{active}")
                    st.session_state.chat_history = []
                    st.rerun()
            with col2:
                if st.button("🗑️ Delete", use_container_width=True):
                    if active:
                        requests.delete(f"{API_URL}/datasets/{active}")
                    st.session_state.session_id = None
                    st.session_state.chat_history = []
                    st.session_state.summary = None
                    st.rerun()

        # 4. HISTORY PANEL
        if active:
            with st.container(border=True):
                st.markdown("🕓 **Query History**")
                try:
                    hist_res = requests.get(f"{API_URL}/history/{active}")
                    history_items = hist_res.json()
                    if history_items:
                        for item in reversed(history_items[-5:]):  # Reduced to 5 to keep UI clean
                            # vertical_alignment aligns the button nicely with the text
                            col1, col2 = st.columns([5, 1], vertical_alignment="center") 
                            with col1:
                                st.caption(item["question"])
                            with col2:
                                if st.button("▶", key=f"replay_{item['question'][:20]}", help="Rerun query"):
                                    st.session_state.prefill_question = item["question"]
                                    st.rerun()
                    else:
                        st.caption("No history yet.")
                except:
                    st.caption("Could not load history.")

        # 5. FAVOURITES PANEL
        if active:
            with st.container(border=True):
                st.markdown("⭐ **Favourites**")
                try:
                    fav_res = requests.get(f"{API_URL}/favourites/{active}")
                    favs = fav_res.json()
                    if favs:
                        for fav in favs:
                            col1, col2, col3 = st.columns([5, 1, 1], vertical_alignment="center")
                            with col1:
                                st.caption(fav["question"])
                            with col2:
                                if st.button("▶", key=f"fav_run_{fav['question'][:20]}", help="Rerun query"):
                                    st.session_state.prefill_question = fav["question"]
                                    st.rerun()
                            with col3:
                                if st.button("✖", key=f"fav_del_{fav['question'][:20]}", help="Remove favourite"):
                                    requests.delete(
                                        f"{API_URL}/favourites/{active}",
                                        data={"question": fav["question"]}
                                    )
                                    st.rerun()
                    else:
                        st.caption("No favourites yet.")
                except:
                    st.caption("Could not load favourites.")

# --- Main Area ---

# Multi-CSV mode
if st.session_state.multi_session_ids and not st.session_state.session_id:
    ids = st.session_state.multi_session_ids
    st.caption(f"🔗 Multi-CSV mode: {len(ids)} datasets loaded")
    st.info(f"Datasets: {', '.join(ids)}")
    st.divider()

    for i, chat in enumerate(st.session_state.chat_history):
        with st.chat_message("user"):
            st.write(chat["question"])
        with st.chat_message("assistant"):
            if chat.get("result"):
                if isinstance(chat["result"], list):
                    result_df = pd.DataFrame(chat["result"])
                    st.dataframe(result_df)
                    st.download_button("⬇️ CSV", result_df.to_csv(index=False), f"result_{i}.csv", key=f"dl_{i}")
                else:
                    st.write(chat["result"])
            if chat.get("chart_bytes"):
                st.image(chat["chart_bytes"], width='stretch')
            if chat.get("friendly_error"):
                st.error(f"😕 {chat['friendly_error']}")
                with st.expander("🔧 Technical details"):
                    st.code(chat.get("technical_error", ""), language="python")
            with st.expander("🔍 Code"):
                st.code(chat.get("generated_code", ""), language="python")

    question = st.chat_input("Ask a question across all loaded datasets...")
    if question:
        with st.chat_message("user"):
            st.write(question)
        with st.chat_message("assistant"):
            with st.spinner("Joining and analyzing..."):
                res = requests.post(f"{API_URL}/query/multi", data={
                    "session_ids": ",".join(ids),
                    "question": question
                })
            if res.status_code == 200:
                data = res.json()

                # ✅ Show chart type badge if a chart was selected
                chart_type = data.get("chart_type", "none")
                if chart_type and chart_type != "none":
                    chart_labels = {
                        "bar": "📊 Bar Chart",
                        "line": "📈 Line Chart",
                        "scatter": "🔵 Scatter Plot",
                        "histogram": "📉 Histogram",
                        "heatmap": "🟥 Heatmap",
                        "pie": "🥧 Pie Chart",
                        "box": "📦 Box Plot",
                        "area": "🏔️ Area Chart",
                    }
                    label = chart_labels.get(chart_type, f"📊 {chart_type.title()} Chart")
                    st.caption(f"Chart type selected: **{label}**")


                # ✅ Show chart type badge if a chart was selected
                chart_type = data.get("chart_type", "none")
                if chart_type and chart_type != "none":
                    chart_labels = {
                        "bar": "📊 Bar Chart",
                        "line": "📈 Line Chart",
                        "scatter": "🔵 Scatter Plot",
                        "histogram": "📉 Histogram",
                        "heatmap": "🟥 Heatmap",
                        "pie": "🥧 Pie Chart",
                        "box": "📦 Box Plot",
                        "area": "🏔️ Area Chart",
                    }
                    label = chart_labels.get(chart_type, f"📊 {chart_type.title()} Chart")
                    st.caption(f"Chart type selected: **{label}**")

                chart_bytes = None
                if data.get("result"):
                    if isinstance(data["result"], list):
                        result_df = pd.DataFrame(data["result"])
                        st.dataframe(result_df)
                        st.download_button("⬇️ CSV", result_df.to_csv(index=False), "result.csv", key="dl_multi_new")
                    else:
                        st.write(data["result"])
                if data.get("has_chart"):
                    chart_res = requests.get(f"{API_URL}/chart")
                    if chart_res.status_code == 200:
                        chart_bytes = chart_res.content
                        st.image(chart_bytes, width='stretch')
                with st.expander("🔍 Code"):
                    st.code(data.get("generated_code", ""), language="python")
                st.session_state.chat_history.append({
                    "question": question,
                    "result": data.get("result"),
                    "chart_bytes": chart_bytes,
                    "generated_code": data.get("generated_code"),
                })
            else:
                err = res.json()
                st.error(f"😕 {err.get('friendly_error', 'Something went wrong.')}")
                with st.expander("🔧 Technical details"):
                    st.code(err.get("technical_error", ""), language="python")

# Single CSV mode
elif st.session_state.session_id:
    st.caption(f"🗂️ Active: `{st.session_state.session_id}`")

    # Summary
    if st.session_state.summary:
        summary = st.session_state.summary
        with st.expander("🧠 Dataset Summary", expanded=True):
            st.write(summary.get("description", ""))
            col1, col2 = st.columns(2)
            with col1:
                if summary.get("key_columns"):
                    st.markdown("**📌 Key Columns**")
                    for col, desc in summary["key_columns"].items():
                        st.markdown(f"- **{col}**: {desc}")
            with col2:
                if summary.get("data_quality"):
                    st.markdown("**🔍 Data Quality**")
                    for obs in summary["data_quality"]:
                        st.markdown(f"- {obs}")
            if summary.get("suggested_questions"):
                st.markdown("**💡 Suggested Questions:**")
                cols = st.columns(len(summary["suggested_questions"]))
                for i, q in enumerate(summary["suggested_questions"]):
                    with cols[i]:
                        if st.button(q, key=f"sq_{i}"):
                            st.session_state.prefill_question = q
                            st.rerun()

    st.divider()

    # Chat history display
    for i, chat in enumerate(st.session_state.chat_history):
        with st.chat_message("user"):
            st.write(chat["question"])
        with st.chat_message("assistant"):
            if chat.get("result"):
                if isinstance(chat["result"], list):
                    result_df = pd.DataFrame(chat["result"])
                    st.dataframe(result_df)
                    st.download_button("⬇️ CSV", result_df.to_csv(index=False), f"result_{i}.csv", mime="text/csv", key=f"dl_csv_{i}")
                else:
                    st.write(chat["result"])

            if chat.get("chart_bytes"):
                st.image(chat["chart_bytes"], width='stretch')
                st.download_button("⬇️ Chart", chat["chart_bytes"], f"chart_{i}.png", mime="image/png", key=f"dl_chart_{i}")

            # ✅ Friendly error display
            if chat.get("friendly_error"):
                st.error(f"😕 {chat['friendly_error']}")
                with st.expander("🔧 Technical details"):
                    st.code(chat.get("technical_error", ""), language="python")

            if chat.get("attempts", 1) > 1:
                st.caption(f"⚡ Fixed after {chat['attempts']} attempts")

            col1, col2 = st.columns([1, 5])
            with col1:
                # ✅ Star / favourite button
                if st.button("⭐", key=f"fav_{i}", help="Save to favourites"):
                    requests.post(
                        f"{API_URL}/favourites/{st.session_state.session_id}",
                        data={
                            "question": chat["question"],
                            "code": chat.get("generated_code", "")
                        }
                    )
                    st.toast("⭐ Added to favourites!")

            with st.expander("🔍 Generated Code"):
                st.code(chat.get("generated_code", ""), language="python")

    # Chat input
    prefill = st.session_state.prefill_question
    question = st.chat_input("Ask anything about your data...")
    active_question = prefill if prefill else question
    if prefill:
        st.session_state.prefill_question = ""

    if active_question:
        with st.chat_message("user"):
            st.write(active_question)
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                res = requests.post(f"{API_URL}/query", data={
                    "session_id": st.session_state.session_id,
                    "question": active_question
                })

            entry = {"question": active_question, "generated_code": "", "result": None, "chart_bytes": None}

            if res.status_code == 200:
                data = res.json()
                entry["generated_code"] = data.get("generated_code", "")
                entry["attempts"] = data.get("attempts", 1)

                if data.get("result"):
                    if isinstance(data["result"], list):
                        result_df = pd.DataFrame(data["result"])
                        st.dataframe(result_df)
                        st.download_button("⬇️ CSV", result_df.to_csv(index=False), "result.csv", mime="text/csv", key="dl_csv_new")
                        entry["result"] = data["result"]
                    else:
                        st.write(data["result"])
                        entry["result"] = data["result"]

                chart_bytes = None
                if data.get("has_chart"):
                    chart_res = requests.get(f"{API_URL}/chart")
                    if chart_res.status_code == 200:
                        chart_bytes = chart_res.content
                        st.image(chart_bytes, width='stretch')
                        st.download_button("⬇️ Chart", chart_bytes, "chart.png", mime="image/png", key="dl_chart_new")
                        entry["chart_bytes"] = chart_bytes

                if data.get("attempts", 1) > 1:
                    st.caption(f"⚡ Fixed after {data['attempts']} attempts")

                # ✅ Star button for new response
                if st.button("⭐ Save to favourites", key="fav_new"):
                    requests.post(
                        f"{API_URL}/favourites/{st.session_state.session_id}",
                        data={"question": active_question, "code": data.get("generated_code", "")}
                    )
                    st.toast("⭐ Added to favourites!")

                with st.expander("🔍 Generated Code"):
                    st.code(data.get("generated_code", ""), language="python")

            else:
                # ✅ Friendly error shown to user
                err = res.json()
                friendly = err.get("friendly_error", "Something went wrong.")
                technical = err.get("technical_error", "")
                st.error(f"😕 {friendly}")
                with st.expander("🔧 Technical details"):
                    st.code(technical, language="python")
                entry["friendly_error"] = friendly
                entry["technical_error"] = technical

            st.session_state.chat_history.append(entry)

else:
    st.info("👈 Upload a CSV above, then select and load it from the sidebar.")