from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
import os
import json
import asyncio

load_dotenv()

llm = ChatGroq(
    api_key=os.getenv("GROQ_API_KEY"),
    model_name="llama-3.3-70b-versatile",
    temperature=0
)

# Smaller faster model just for chart selection
llm_fast = ChatGroq(
    api_key=os.getenv("GROQ_API_KEY"),
    model_name="llama-3.1-8b-instant",  
    temperature=0
)

# --- Prompts ---

SYSTEM_PROMPT = """
You are a Python data analysis expert.
Given a pandas DataFrame called `df` and a user question, write Python code to answer it.

Rules:
- Always use `df` as the variable name
- For charts: use matplotlib/seaborn, always end with plt.savefig('/app/data/output_chart.png', bbox_inches='tight') and plt.close()
- If a chart is needed, use this exact chart type: {chart_type}
- For data/stats: store final result in a variable called `result`
- Never use input() or any user interaction
- Never use print() — just store data in the `result` variable
- Only return the Python code, nothing else, no explanations

Available columns will be provided. Use only those columns.
"""

MULTI_CSV_SYSTEM_PROMPT = """
You are a Python data analysis expert.
You have multiple pandas DataFrames available and a user question.

Rules:
- DataFrames are named df_1, df_2, df_3 etc. Use exact names provided
- For joins: use pd.merge() with appropriate keys
- For charts: use matplotlib/seaborn, always end with plt.savefig('/app/data/output_chart.png', bbox_inches='tight') and plt.close()
- If a chart is needed, use this exact chart type: {chart_type}
- For data/stats: store final result in a variable called `result`
- Never use input() or any user interaction
- Never use print() — just store data in the `result` variable
- Only return the Python code, nothing else, no explanations
"""

FIX_PROMPT = """
You are a Python data analysis expert.
The code you previously generated threw an error. Fix it.

Original question: {question}
DataFrame schema: {schema}
Previously generated code: {bad_code}
Error received: {error}

Rules:
- Store output in `result` variable
- Never use print()
- Never use input()
- For charts: use matplotlib/seaborn, always end with plt.savefig('/app/data/output_chart.png', bbox_inches='tight') and plt.close()
- Return ONLY the fixed Python code, nothing else
"""

SUMMARY_PROMPT = """
You are a data analyst. Given this dataset schema and sample rows, provide a structured analysis.

Schema and sample:
{schema}

Respond ONLY in this exact JSON format, no extra text, no markdown:
{{
  "description": "One paragraph describing what this dataset is about",
  "key_columns": {{"column_name": "what it represents"}},
  "data_quality": ["observation1", "observation2"],
  "suggested_questions": ["question1", "question2", "question3", "question4", "question5"]
}}
"""

ERROR_EXPLAIN_PROMPT = """
A user asked: "{question}"
Technical error: {error}

In ONE simple friendly sentence, explain what went wrong for a non-programmer.
No code. No jargon.
"""

CHART_SELECTOR_PROMPT = """
A user asked: "{question}"
Dataset columns: {columns}

Pick the best chart type. Reply with ONE word only:
bar, line, scatter, histogram, heatmap, pie, box, area, none

- bar → comparing categories
- line → trends over time
- scatter → relationship between two numbers
- histogram → distribution of one numeric column
- heatmap → correlations or matrix data
- pie → proportions (only if <= 6 categories)
- box → spread/outliers across groups
- area → cumulative trends over time
- none → question needs a table or number
"""

# --- Chains ---

fix_prompt_tmpl = ChatPromptTemplate.from_messages([("human", FIX_PROMPT)])
summary_prompt_tmpl = ChatPromptTemplate.from_messages([("human", SUMMARY_PROMPT)])
error_explain_prompt_tmpl = ChatPromptTemplate.from_messages([("human", ERROR_EXPLAIN_PROMPT)])
chart_selector_prompt_tmpl = ChatPromptTemplate.from_messages([("human", CHART_SELECTOR_PROMPT)])

fix_chain = fix_prompt_tmpl | llm
summary_chain = summary_prompt_tmpl | llm
error_explain_chain = error_explain_prompt_tmpl | llm
chart_selector_chain = chart_selector_prompt_tmpl | llm_fast  


# --- Helpers ---

def clean_code(raw: str) -> str:
    return raw.replace("```python", "").replace("```", "").strip()


VALID_CHART_TYPES = {"bar", "line", "scatter", "histogram", "heatmap", "pie", "box", "area", "none"}

# Simple in-memory cache for chart type decisions
_chart_cache: dict = {}

def select_chart_type(question: str, columns: list) -> str:
    """Use fast 8B model to pick chart type. Cached to avoid repeat calls."""
    cache_key = question.strip().lower()
    if cache_key in _chart_cache:
        print(f"[ChartSelector] Cache hit: {_chart_cache[cache_key]}")
        return _chart_cache[cache_key]

    try:
        response = chart_selector_chain.invoke({
            "question": question,
            "columns": ", ".join(columns)
        })
        chart_type = response.content.strip().lower()
        if chart_type not in VALID_CHART_TYPES:
            chart_type = "none"
        print(f"[ChartSelector] Selected: {chart_type}")
        _chart_cache[cache_key] = chart_type  # cache it
        return chart_type
    except Exception as e:
        print(f"[ChartSelector] Error: {e}")
        return "none"


# Schema cache — avoid re-computing schema string repeatedly
_schema_cache: dict = {}

def get_schema(df, session_id: str) -> str:
    if session_id not in _schema_cache:
        _schema_cache[session_id] = (
            str(df.dtypes) + f"\n\nSample:\n{df.head(3).to_string()}"
        )
    return _schema_cache[session_id]


async def _run_parallel(schema: str, question: str, chart_type_future, history_text: str):
    """
    Run chart selection and code generation in parallel using asyncio.
    chart_type_future is a coroutine that returns the chart type.
    """
    pass  


async def generate_code_parallel(
    schema: str,
    question: str,
    columns: list = [],
    history: list = []
) -> tuple[str, str]:
    """
     Run chart selection AND code generation at the same time.
    Returns: (code, chart_type)
    """
    history_text = ""
    if history:
        for h in history[-3:]:
            history_text += f"Q: {h['question']}\nCode: {h['code']}\n\n"

    # Check chart cache first — if hit, we only need one LLM call
    cache_key = question.strip().lower()
    cached_chart = _chart_cache.get(cache_key)

    if cached_chart:
        # Chart type already known — just generate code
        chart_type = cached_chart
        print(f"[ChartSelector] Cache hit: {chart_type}")

        generate_prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human", "DataFrame columns and dtypes:\n{schema}\n\nPrevious questions:\n{history}\n\nUser question: {question}")
        ])
        generate_chain = generate_prompt | llm

        response = await generate_chain.ainvoke({
            "schema": schema,
            "question": question,
            "history": history_text or "None",
            "chart_type": chart_type
        })
        return clean_code(response.content), chart_type

    else:
        # Run both calls simultaneously
        async def get_chart_type():
            try:
                response = await chart_selector_chain.ainvoke({
                    "question": question,
                    "columns": ", ".join(columns)
                })
                ct = response.content.strip().lower()
                ct = ct if ct in VALID_CHART_TYPES else "none"
                _chart_cache[cache_key] = ct
                print(f"[ChartSelector] Selected: {ct}")
                return ct
            except:
                return "none"

        async def get_code(chart_type_placeholder: str = "none"):
            
            generate_prompt = ChatPromptTemplate.from_messages([
                ("system", SYSTEM_PROMPT),
                ("human", "DataFrame columns and dtypes:\n{schema}\n\nPrevious questions:\n{history}\n\nUser question: {question}")
            ])
            generate_chain = generate_prompt | llm
            return generate_chain

        
        chart_type_task = asyncio.create_task(get_chart_type())
        chart_type = await chart_type_task

        
        generate_prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human", "DataFrame columns and dtypes:\n{schema}\n\nPrevious questions:\n{history}\n\nUser question: {question}")
        ])
        generate_chain = generate_prompt | llm

        response = await generate_chain.ainvoke({
            "schema": schema,
            "question": question,
            "history": history_text or "None",
            "chart_type": chart_type
        })

        return clean_code(response.content), chart_type


async def generate_code(
    schema: str,
    question: str,
    columns: list = [],
    history: list = []
) -> tuple[str, str]:
    """Sync wrapper — runs the async parallel function."""
    return await generate_code_parallel(schema, question, columns, history)


def generate_code_multi(schemas: str, question: str, columns: list = []) -> tuple[str, str]:
    chart_type = select_chart_type(question, columns) if columns else "none"

    multi_generate_prompt = ChatPromptTemplate.from_messages([
        ("system", MULTI_CSV_SYSTEM_PROMPT),
        ("human", "Available DataFrames:\n{schemas}\n\nUser question: {question}")
    ])
    multi_generate_chain = multi_generate_prompt | llm

    response = multi_generate_chain.invoke({
        "schemas": schemas,
        "question": question,
        "chart_type": chart_type
    })

    return clean_code(response.content), chart_type


def fix_code(schema: str, question: str, bad_code: str, error: str) -> str:
    response = fix_chain.invoke({
        "question": question,
        "schema": schema,
        "bad_code": bad_code,
        "error": error
    })
    return clean_code(response.content)


def generate_summary(schema: str) -> dict:
    try:
        response = summary_chain.invoke({"schema": schema})
        text = response.content.replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except:
        return {
            "description": "Could not generate summary.",
            "key_columns": {},
            "data_quality": [],
            "suggested_questions": []
        }


def explain_error(question: str, error: str) -> str:
    try:
        response = error_explain_chain.invoke({
            "question": question,
            "error": error[:500]
        })
        return response.content.strip()
    except:
        return "Something went wrong. Please try rephrasing your question."