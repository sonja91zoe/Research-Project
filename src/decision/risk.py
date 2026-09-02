"""Rule-based refund-risk classification for Student 4 Week 5."""

LOW_RISK_MAX = 50.0
MEDIUM_RISK_MAX = 200.0


def calculate_refund_risk(refund_amount: float) -> str:
    """Classify financial risk using the requested refund amount."""

    if refund_amount < 0:
        raise ValueError("refund_amount cannot be negative")

    if refund_amount <= LOW_RISK_MAX:
        return "LOW"

    if refund_amount <= MEDIUM_RISK_MAX:
        return "MEDIUM"

    return "HIGH"
