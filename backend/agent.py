from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
import os

load_dotenv()

llm = ChatGroq(
    api_key=os.getenv("GROQ_API_KEY"),
    model_name="llama-3.3-70b-versatile",
    temperature=0
)

SYSTEM_PROMPT = """
You are a Python data analysis expert.
Given a pandas DataFrame called `df` and a user question, write Python code to answer it.

Rules:
- Always use `df` as the variable name
- For charts: use matplotlib/seaborn, always end with plt.savefig('output_chart.png') and plt.close()
- For data/stats: store final result in a variable called `result`
- Never use input() or any user interaction
- Never use print() — just store data in the `result` variable
- Only return the Python code, nothing else, no explanations

Available columns will be provided. Use only those columns.
"""

FIX_PROMPT = """
You are a Python data analysis expert.
The code you previously generated threw an error. Fix it.

Original question: {question}

DataFrame schema:
{schema}

Previously generated code:
{bad_code}

Error received:
{error}

Rules for the fixed code:
- Store output in `result` variable
- Never use print() — just assign to `result`
- Never use input()
- For charts: end with plt.savefig('output_chart.png') and plt.close()
- Return ONLY the fixed Python code, nothing else
"""

generate_prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", "DataFrame columns and dtypes:\n{schema}\n\nUser question: {question}")
])

fix_prompt = ChatPromptTemplate.from_messages([
    ("human", FIX_PROMPT)
])

generate_chain = generate_prompt | llm
fix_chain = fix_prompt | llm


def clean_code(raw: str) -> str:
    """Strip markdown code fences if LLM adds them."""
    return raw.replace("```python", "").replace("```", "").strip()


def generate_code(schema: str, question: str) -> str:
    response = generate_chain.invoke({
        "schema": schema,
        "question": question
    })
    return clean_code(response.content)


def fix_code(schema: str, question: str, bad_code: str, error: str) -> str:
    """Ask the LLM to fix broken code by passing the error back."""
    response = fix_chain.invoke({
        "question": question,
        "schema": schema,
        "bad_code": bad_code,
        "error": error
    })
    return clean_code(response.content)