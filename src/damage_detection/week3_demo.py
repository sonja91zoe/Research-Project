"""Run an offline contract fixture; image inference is supplied by Week2."""
import argparse
import json
from pathlib import Path
from src.common.schemas import CaseInput, Member1Output, Member2Output
from src.damage_detection.verification import HandoffContext, verify_claim, recommend_handoff


def run(payload):
    result = verify_claim(CaseInput.model_validate(payload["case"]),
                          Member1Output.model_validate(payload["member1"]),
                          Member2Output.model_validate(payload["member2"]))
    handoff = recommend_handoff(result, HandoffContext.model_validate(payload["context"]))
    return {"verification": result.model_dump(), "handoff": handoff.model_dump()}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", type=Path)
    args = parser.parse_args()
    print(json.dumps(run(json.loads(args.case.read_text(encoding="utf-8"))), indent=2))
