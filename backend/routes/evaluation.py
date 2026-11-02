import os
import json
import subprocess
import sys
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter(prefix="/evaluation", tags=["Evaluation"])

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RESULTS_DIR = os.path.join(BASE_DIR, "results")
EVAL_SCRIPT = os.path.join(BASE_DIR, "evaluation", "evaluate.py")
PYTHON_EXE = os.path.join(BASE_DIR, "venv", "Scripts", "python.exe")
if not os.path.exists(PYTHON_EXE):
    PYTHON_EXE = sys.executable


@router.get("/metrics")
def get_metrics():
    """Retrieve the latest evaluation metrics and sample predictions."""
    metrics_path = os.path.join(RESULTS_DIR, "evaluation_metrics.json")
    preds_path = os.path.join(RESULTS_DIR, "predictions.csv")

    metrics_data = None
    if os.path.exists(metrics_path):
        try:
            with open(metrics_path, "r") as f:
                metrics_data = json.load(f)
        except Exception:
            pass

    predictions = []
    if os.path.exists(preds_path):
        import csv
        with open(preds_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            predictions = list(reader)

    return {
        "metrics": metrics_data,
        "predictions": predictions[:20],  # sample predictions
        "has_confusion_matrix": os.path.exists(os.path.join(RESULTS_DIR, "confusion_matrix.png")),
    }


@router.get("/confusion-matrix")
def get_confusion_matrix():
    """Serve the generated confusion matrix image."""
    cm_path = os.path.join(RESULTS_DIR, "confusion_matrix.png")
    if not os.path.exists(cm_path):
        raise HTTPException(status_code=404, detail="Confusion matrix image not yet generated.")
    return FileResponse(cm_path, media_type="image/png")


@router.post("/run")
def run_evaluation_endpoint():
    """Trigger the evaluation script synchronously and return metrics."""
    try:
        proc = subprocess.run(
            [PYTHON_EXE, EVAL_SCRIPT],
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            timeout=120,
        )
        return {
            "exit_code": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "success": proc.returncode == 0,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

