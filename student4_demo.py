"""Run a demonstration of the Student 4 Week 5 Agent."""

import json
from pathlib import Path

from src.agent.agent import run_agent
from src.common.schemas import (
    Member1Output,
    Member2Output,
    Member3Output,
)


PROJECT_ROOT = Path(__file__).resolve().parent

CASE_PATH = (
    PROJECT_ROOT
    / "data"
    / "test_cases"
    / "student4_auto_refund.json"
)


def load_demo_case():
    """Load the Student 4 demonstration case."""

    with CASE_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        raw_data = json.load(file)

    member1 = Member1Output(**raw_data["member1"])
    member2 = Member2Output(**raw_data["member2"])
    member3 = Member3Output(**raw_data["member3"])

    return member1, member2, member3


def main():
    """Run the Agent and display the final decision."""

    member1, member2, member3 = load_demo_case()

    result = run_agent(
        member1,
        member2,
        member3,
    )

    print("Student 4 Week 5 Decision")
    print("-------------------------")
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()