import mlflow
import os
from dotenv import load_dotenv

load_dotenv()
mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000"))
mlflow.set_experiment("data-copilot")

def log_query(question: str, generated_code: str, success: bool, error: str = None, attempts: int = 1):
    with mlflow.start_run():
        mlflow.log_param("question", question[:250])
        mlflow.log_param("success", success)
        mlflow.log_param("attempts", attempts)        # ← new
        mlflow.log_text(generated_code, "generated_code.py")
        if error:
            mlflow.log_text(error, "error.txt")