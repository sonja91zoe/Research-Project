"""Refund-risk bands for the Week 4 mock Agent."""

LOW_RISK_MAX = 50.0
MEDIUM_RISK_MAX = 200.0


def calculate_refund_risk(refund_amount):
    """Classify the financial risk of a proposed refund."""

    if refund_amount < 0:
        raise ValueError("refund_amount cannot be negative")

    if refund_amount <= LOW_RISK_MAX:
        return "LOW"

    if refund_amount <= MEDIUM_RISK_MAX:
        return "MEDIUM"

    return "HIGH"

