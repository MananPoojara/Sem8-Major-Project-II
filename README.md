# Sem8-Major-Project-II
# Multi-Agent Cold Case Intelligence (Review 1)

## Goal
Implement a single CrimePatternAnalyzer agent in both LangChain and CrewAI (shim), compare their extraction quality on crime case PDFs, and present results in a Streamlit dashboard.
This project compares two AI frameworks LangChain and CrewAI —for building multi-agent systems that help in investigating unsolved criminal (cold) cases. The system collects and processes data from various sources like reports, news, and public records using ETL pipelines.We test how each framework performs in terms of automation, coordination, and real-time reasoning. The goal is to find which framework works better for handling complex investigation tasks.Overall, the project shows how AI agents can support digital investigation and highlights the strengths and differences between LangChain’s flexible design and CrewAI’s teamwork approach

## Quickstart
1. Copy `.env.example` to `.env` and fill keys.
2. `python -m venv .venv && source .venv/bin/activate`
3. `pip install -r requirements.txt`
4. Put sample PDFs in `data/samples/` and ground_truth.csv in `data/`.
5. `streamlit run src/app.py`

## Structure
... (same as project structure above) ...
