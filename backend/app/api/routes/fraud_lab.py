from typing import Any

from fastapi import APIRouter

from app.api.deps import CurrentUser
from app.domain.fraud_lab import run_fraud_lab_benchmark

router = APIRouter(prefix="/fraud-lab", tags=["fraud-lab"])


@router.get("/metrics")
def get_fraud_lab_metrics(_current_user: CurrentUser) -> dict[str, Any]:
    """Return synthetic fraud lab benchmark metrics (TP, FP, FN, TN, precision, recall, accuracy).

    Strictly synthetic data only.
    """
    return run_fraud_lab_benchmark()
