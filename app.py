# app.py
import streamlit as st
import pandas as pd
import os
import plotly.express as px

from langchain_ingest import run_langchain_ingest
from crewai_ingest_shim import run_crewai_ingest
from src.eval.compare_ingest import compare_batches

# ----------------- CONFIG -----------------
st.set_page_config(layout="wide", page_title="CrimeLake Ingestion Dashboard", page_icon="🕵️‍♂️")
st.title("CrimeLake Intelligence Ingestion Agent")

# ----------------- DATA ANALYTICS SECTION -----------------
st.subheader("📊 Crime Data Overview (From NCRB Dataset)")

DATA_PATH = "NCRB_CII_2017_State_Table-18A.8.csv"
try:
    df = pd.read_csv(DATA_PATH)
    df.columns = df.columns.str.strip()

    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    category_cols = df.select_dtypes(exclude=['number']).columns.tolist()

    with st.expander("Explore How Many Cases Are Pending!!"):
        col1, col2 = st.columns(2)
        x_col = col1.selectbox("X-Axis", category_cols, index=0)
        y_col = col2.selectbox("Y-Axis", numeric_cols, index=0)
        chart = px.bar(df, x=x_col, y=y_col, color=x_col, title=f"{y_col} by {x_col}", height=400)
        st.plotly_chart(chart, use_container_width=True)


except Exception as e:
    st.error(f"Could not load or parse dataset (Try Again): {e}")

st.markdown("---")

# ----------------- MODE SELECTION -----------------
st.subheader("Ingestion Agent Comparison (Langchain Vs CrewAI)")

mode = st.radio("Choose Mode", ["Topic Search", "Famous Cold Case Mode"], horizontal=True)

lc_results, cr_results = [], []

# ----------------- CASE MODE -----------------
if mode == "Famous Cold Case Mode":
    st.markdown("### 🕵️ Famous Unsolved Murder Cases")
    cases = {
        "Aarushi Talwar – 2017": "https://timesofindia.indiatimes.com/city/aarushi-hemraj-murder-case-talwars-acquitted/photostory/61046942.cms?picid=61054355",
        "Sheena Bora – 2015": "https://timesofindia.indiatimes.com/city/mumbai/sheena-bora-murder-case-rahul-mukerjea-refused-help-for-lodging-missing-report-witness-tells-court/articleshow/124009745.cms",
        "Nitish Katara – 2002": "https://theprint.in/ground-reports/nitish-katara-murder-witness-battles-37-cases-bullets-poison-ajay-katara-a-cautionary-tale/2269160/",
        "J Dey – 2011": "https://timesofindia.indiatimes.com/city/mumbai/j-dey-verdict-all-you-need-to-know/articleshow/63997333.cms",
    }

    selected_cases = st.multiselect("Select cases to ingest", options=list(cases.keys()), default=list(cases.keys())[:2])
    selected_urls = [cases[c] for c in selected_cases]

    st.write(f"🧾 {len(selected_urls)} URLs selected:")
    for u in selected_urls:
        st.markdown(f"- [{u}]({u})")

    col_a, col_b, col_c = st.columns(3)
    run_lc = col_a.button("Run LangChain Ingest :)")
    run_cr = col_b.button("Run CrewAI Ingest :)")
    run_both = col_c.button("Run Both (Recommended) ⚡")

    if run_both or run_lc or run_cr:
        if not selected_urls:
            st.warning("Please select at least one case.")
        else:
            if run_both or run_lc:
                with st.spinner("Running LangChain ingestion..."):
                    try:
                        lc_results = run_langchain_ingest(selected_urls, max_items=len(selected_urls))
                        st.success("LangChain ingestion complete!!! :0")
                    except Exception as e:
                        st.error(f"LangChain ingest failed :( : {e}")

            if run_both or run_cr:
                with st.spinner("Running CrewAI ingestion..."):
                    try:
                        cr_results = run_crewai_ingest(selected_urls, max_items=len(selected_urls))
                        st.success("CrewAI ingestion complete!!! :0")
                    except Exception as e:
                        st.error(f"CrewAI ingest failed :( : {e}")

            if lc_results or cr_results:
                try:
                    df_result = compare_batches(lc_results, cr_results)
                    st.subheader("📈 Comparison Summary")
                    st.json(df_result)
                except Exception as e:
                    st.error(f"Comparison failed :( (Try Again) {e}")

            # Results
            def show_results(label, results):
                st.markdown(f"### {label} Outputs")
                if not results:
                    st.write("No outputs available.")
                    return
                for r in results:
                    st.markdown(f"**📰 {r.get('title', 'Untitled')[:120]}**")
                    img_path = r.get("image_path")
                    if img_path and os.path.exists(img_path):
                        st.image(img_path, width=300)
                    st.markdown(f"- 📄 PDF: `{r.get('pdf_path')}`")
                    st.markdown(f"- 🧾 Text length: {r.get('text_length', 0)}, Bytes: {r.get('pdf_bytes', 0)}, ⏱ {r.get('time_seconds', 0)}s")
                    st.divider()

            if lc_results:
                show_results("LangChain", lc_results)
            if cr_results:
                show_results("CrewAI", cr_results)

# ----------------- TOPIC MODE (same as before) -----------------
else:
    topic = st.text_input("Topic:", value="murder case")
    site_choice = "times_of_india"
    max_articles = st.slider("Max articles per framework", 1, 4, 2)

    col_a, col_b, col_c = st.columns(3)
    run_lc = col_a.button("Run LangChain Ingest ")
    run_cr = col_b.button("Run CrewAI Ingest")
    run_both = col_c.button("Run Both (Recommended)")

    def gather_seed_urls(topic: str, site_pref: str, max_items: int):
        topic = topic.strip()
        dash_topic = topic.replace(" ", "-")
        return [f"https://timesofindia.indiatimes.com/topic/{dash_topic}?page={i}" for i in range(1, max_items + 1)]

    if run_both or run_lc or run_cr:
        seeds = gather_seed_urls(topic, site_choice, max_articles)
        st.write(f"Generated {len(seeds)} seed URLs")
        st.code(seeds, language="python")

        if run_both or run_lc:
            with st.spinner("Running LangChain ingestion (Hang in There)..."):
                try:
                    lc_results = run_langchain_ingest(topic, max_items=max_articles)
                    st.success("LangChain ingestion complete!!! :)")
                except Exception as e:
                    st.error(f"LangChain ingest failed :( (Try Again) {e}")

        if run_both or run_cr:
            with st.spinner("Running CrewAI ingestion (Hang in There)..."):
                try:
                    cr_results = run_crewai_ingest(seeds, max_items=max_articles)
                    st.success("CrewAI ingestion complete!!! :)")
                except Exception as e:
                    st.error(f"CrewAI ingest failed :( (Try Again) {e}")

        if lc_results or cr_results:
            try:
                df_result = compare_batches(lc_results, cr_results)
                st.subheader("Comparison Summary")
                st.json(df_result)
            except Exception as e:
                st.error(f"Comparison failed :( (Sorry) {e}")

