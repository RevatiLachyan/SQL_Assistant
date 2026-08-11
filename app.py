 
import streamlit as st
import plotly.express as px
import pandas as pd

from nl_to_sql import generate_sql_retry
from intent_classifier import classify_intent
from db_runner import run_query

st.set_page_config(
    page_title="PropQuery",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
)
 
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');
 
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
 
#MainMenu { visibility: hidden; }
footer    { visibility: hidden; }
header    { visibility: hidden; }
 
.stApp {
    background-color: #0f1117;
    color: #e2e8f0;
}
 
.app-header {
    padding: 2rem 0 1.5rem 0;
    border-bottom: 1px solid #1e2533;
    margin-bottom: 2rem;
}
.app-title {
    font-size: 1.5rem;
    font-weight: 600;
    color: #f8fafc;
    letter-spacing: -0.02em;
    margin: 0;
}
.app-subtitle {
    font-size: 0.85rem;
    color: #64748b;
    margin: 0.25rem 0 0 0;
}
 
.stTextInput > div > div > input {
    background-color: #1a1f2e !important;
    border: 1px solid #2d3748 !important;
    border-radius: 8px !important;
    color: #e2e8f0 !important;
    font-size: 0.95rem !important;
    padding: 0.75rem 1rem !important;
    font-family: 'Inter', sans-serif !important;
}
.stTextInput > div > div > input:focus {
    border-color: #3b82f6 !important;
    box-shadow: 0 0 0 3px rgba(59,130,246,0.15) !important;
}
.stTextInput > div > div > input::placeholder {
    color: #475569 !important;
}
 
.stButton > button {
    background-color: #1a1f2e;
    color: #94a3b8;
    border: 1px solid #2d3748;
    border-radius: 6px;
    font-size: 0.78rem;
    font-family: 'Inter', sans-serif;
    padding: 0.4rem 0.75rem;
    width: 100%;
    text-align: left;
    transition: all 0.15s ease;
    white-space: normal;
    height: auto;
    line-height: 1.4;
}
.stButton > button:hover {
    background-color: #1e2840;
    border-color: #3b82f6;
    color: #e2e8f0;
}
 
.intent-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    background-color: #1a1f2e;
    border: 1px solid #2d3748;
    border-radius: 20px;
    padding: 0.3rem 0.9rem;
    font-size: 0.78rem;
    font-weight: 500;
    color: #94a3b8;
    margin-bottom: 1.25rem;
}
 
.streamlit-expanderHeader {
    background-color: #1a1f2e !important;
    border: 1px solid #2d3748 !important;
    border-radius: 8px !important;
    color: #64748b !important;
    font-size: 0.82rem !important;
}
.streamlit-expanderContent {
    background-color: #141820 !important;
    border: 1px solid #2d3748 !important;
    border-top: none !important;
}
code, pre, .stCodeBlock {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.82rem !important;
}
 
.meta-row {
    display: flex;
    gap: 1.5rem;
    margin: 0.5rem 0 1.25rem 0;
}
.meta-chip {
    font-size: 0.75rem;
    color: #475569;
    font-family: 'JetBrains Mono', monospace;
}
 
.error-box {
    background-color: #1c1017;
    border: 1px solid #7f1d1d;
    border-radius: 8px;
    padding: 1rem 1.25rem;
    color: #fca5a5;
    font-size: 0.85rem;
    margin-top: 1rem;
}
 
.section-label {
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #475569;
    margin-bottom: 0.6rem;
}
 
[data-testid="stSidebar"] {
    background-color: #0d1017;
    border-right: 1px solid #1e2533;
}
.sidebar-col {
    font-size: 0.73rem;
    color: #64748b;
    font-family: 'JetBrains Mono', monospace;
    padding: 0.1rem 0;
    border-left: 2px solid #1e2533;
    padding-left: 0.6rem;
    margin-left: 0.3rem;
}
</style>
""", unsafe_allow_html=True)

EXAMPLE_QUESTIONS = [
    "Which tenants have outstanding balances over $500?",
    "Show vacancy rate by property",
    "What is the late payment trend by month?",
    "Top 5 most expensive maintenance repairs",
    "Compare collected vs billed revenue by property",
    "Which active leases expire in the next 90 days?",
]


SCHEMA = {
    "property": [
        ("property_id", "INTEGER PK"), ("property_name", "VARCHAR(100)"),
        ("address", "VARCHAR(200)"), ("city", "VARCHAR(50)"),
        ("state", "CHAR(2)"), ("zip_code", "CHAR(5)"),
        ("units_count", "INTEGER"), ("property_type", "VARCHAR(30)"),
        ("year_built", "INTEGER"), ("monthly_hoa_fee", "DECIMAL(10,2)"),
    ],
    "unit": [
        ("unit_id", "INTEGER PK"), ("property_id", "INTEGER FK→property"),
        ("unit_number", "VARCHAR(10)"), ("bedrooms", "INTEGER"),
        ("bathrooms", "DECIMAL(3,1)"), ("sq_footage", "INTEGER"),
        ("floor_number", "INTEGER"), ("unit_type", "VARCHAR(20)"),
        ("market_rent", "DECIMAL(10,2)"), ("is_available", "BOOLEAN"),
    ],
    "tenant": [
        ("tenant_id", "INTEGER PK"), ("first_name", "VARCHAR(50)"),
        ("last_name", "VARCHAR(50)"), ("email", "VARCHAR(100)"),
        ("phone", "VARCHAR(20)"), ("date_of_birth", "DATE"),
        ("ssn_last4", "CHAR(4)"), ("credit_score", "INTEGER"),
        ("move_in_date", "DATE"), ("emergency_contact_name", "VARCHAR(100)"),
        ("emergency_contact_phone", "VARCHAR(20)"),
    ],
    "lease": [
        ("lease_id", "INTEGER PK"), ("tenant_id", "INTEGER FK→tenant"),
        ("unit_id", "INTEGER FK→unit"), ("property_id", "INTEGER FK→property"),
        ("lease_start", "DATE"), ("lease_end", "DATE"),
        ("monthly_rent", "DECIMAL(10,2)"), ("security_deposit", "DECIMAL(10,2)"),
        ("lease_status", "VARCHAR(20)"), ("lease_type", "VARCHAR(20)"),
        ("late_fee_pct", "DECIMAL(5,2)"), ("grace_period_days", "INTEGER"),
        ("signed_date", "DATE"), ("renewal_count", "INTEGER"),
    ],
    "payment": [
        ("payment_id", "INTEGER PK"), ("lease_id", "INTEGER FK→lease"),
        ("tenant_id", "INTEGER FK→tenant"), ("payment_date", "DATE"),
        ("due_date", "DATE"), ("amount_due", "DECIMAL(10,2)"),
        ("amount_paid", "DECIMAL(10,2)"), ("payment_method", "VARCHAR(30)"),
        ("payment_type", "VARCHAR(30)"), ("is_late", "BOOLEAN"),
        ("days_late", "INTEGER"), ("transaction_ref", "VARCHAR(50)"),
        ("notes", "VARCHAR(500)"),
    ],
    "invoice": [
        ("invoice_id", "INTEGER PK"), ("lease_id", "INTEGER FK→lease"),
        ("tenant_id", "INTEGER FK→tenant"), ("invoice_date", "DATE"),
        ("due_date", "DATE"), ("invoice_type", "VARCHAR(50)"),
        ("amount", "DECIMAL(10,2)"), ("amount_paid", "DECIMAL(10,2)"),
        ("balance_due", "DECIMAL(10,2)"), ("invoice_status", "VARCHAR(20)"),
        ("description", "VARCHAR(500)"),
    ],
    "maintenance_request": [
        ("request_id", "INTEGER PK"), ("unit_id", "INTEGER FK→unit"),
        ("tenant_id", "INTEGER FK→tenant"), ("property_id", "INTEGER FK→property"),
        ("request_date", "DATE"), ("category", "VARCHAR(50)"),
        ("priority", "VARCHAR(20)"), ("description", "VARCHAR(1000)"),
        ("status", "VARCHAR(20)"), ("resolved_date", "DATE"),
        ("repair_cost", "DECIMAL(10,2)"), ("vendor_name", "VARCHAR(100)"),
        ("days_to_resolve", "INTEGER"),
    ],
}

def build_chart(df: pd.DataFrame, chart_type: str):
    if df.shape[1] < 2:
        return None
 
    label_col = df.columns[0]
    numeric_cols = [c for c in df.columns[1:] if pd.api.types.is_numeric_dtype(df[c])]
    if not numeric_cols:
        return None
 
    if chart_type == "line":
        fig = px.line(df, x=label_col, y=numeric_cols, markers=True)
    elif chart_type == "bar_horizontal":
        value_col = numeric_cols[0]
        plot_df = df[[label_col, value_col]].sort_values(value_col, ascending=True)
        fig = px.bar(plot_df, x=value_col, y=label_col, orientation="h")
    elif chart_type == "bar_grouped":
        melted = df.melt(id_vars=label_col, value_vars=numeric_cols,
                          var_name="metric", value_name="value")
        fig = px.bar(melted, x=label_col, y="value", color="metric", barmode="group")
    elif chart_type == "bar":
        fig = px.bar(df, x=label_col, y=numeric_cols[0])
    else:
        return None
 
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0f1117",
        plot_bgcolor="#0f1117",
        font=dict(family="Inter, sans-serif", color="#e2e8f0"),
        margin=dict(l=10, r=10, t=30, b=10),
    )
    return fig

st.markdown("""
<div class="app-header">
    <p class="app-title">Questions related to property:</p>
    <p class="app-subtitle">Ask questions about your property portfolio in plain English</p>
</div>
""", unsafe_allow_html=True)


if "question" not in st.session_state:
    st.session_state.question = ""
if "run_query" not in st.session_state:
    st.session_state.run_query = False


def use_example(q: str):
    st.session_state.question = q
    st.session_state.run_query = True

def clear_button():
    st.session_state.question = ""
    st.session_state.run_query = False
 
def trigger_run():
    st.session_state.run_query = True

st.text_input(
    "Ask a question",
    key="question",
    placeholder="e.g. Which tenants have outstanding balances over $500?",
    label_visibility="collapsed",
    on_change=trigger_run,
)

if st.session_state.run_query:
    if not st.session_state.question.strip():
        st.session_state.run_query = False
        st.warning("Type a question first")
    else:
        question = st.session_state.question.strip()
        st.session_state.run_query = False
 
        try:
            with st.spinner("Generating SQL..."):
                sql_result = generate_sql_retry(question)
        except Exception:
            sql_result = {
                "sql": None, "success": False, "retried": False,
                "error": "Something went wrong generating SQL. Please try again.",
            }
        print(sql_result)

        st.button("Clear", on_click=clear_button)


        try:
                intent_result = classify_intent(question)
        except Exception:
                intent_result = {"intent": "lookup", "chart_type": "table", "raw": None}

        if not sql_result["success"]:
            st.markdown(
                f'<div class="error-box">⚠️ {sql_result["error"]}</div>',
                unsafe_allow_html=True,
            )
        else:
            sql=sql_result["sql"]

            intent = intent_result["intent"]
            chart_type = intent_result["chart_type"]

            print(intent_result)
            if sql_result["retried"]:
                st.caption("First attempt failed validation — this SQL was auto-corrected on retry.")
            with st.expander("Generated SQL"):
                    st.code(sql, language="sql")
    
            with st.spinner("Running query..."):
                    query_result = run_query(sql)
    
            if not query_result.success:
                    st.markdown(
                        f'<div class="error-box">⚠️ {query_result.error_message}</div>',
                        unsafe_allow_html=True,
                    )
            else:
                    df = query_result.df
                    if df.empty:
                        st.info("Query ran successfully but returned no rows.")
                    else:
                        st.dataframe(df, use_container_width=True)

                    if chart_type != "table":
                            chart = build_chart(df, chart_type)
                            if chart is not None:
                                st.plotly_chart(chart, use_container_width=True)
                            else:
                                st.caption("No chart available for this result shape.")
    
            meta_html = (
                    '<div class="meta-row">'
                    f'<span class="meta-chip">{query_result.row_count} rows</span>'
                    f'<span class="meta-chip">{query_result.execution_time} ms</span>'
                )
            if query_result.truncated:
                        meta_html += '<span class="meta-chip">truncated to 1000 rows</span>'
            meta_html += "</div>"
            st.markdown(meta_html, unsafe_allow_html=True)