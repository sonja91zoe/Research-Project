"""Deterministic policy retrieval baseline for Member 3 Week 5."""

import json
import re
from pathlib import Path

from src.evidence.models import RetrievedPolicy


DEFAULT_POLICY_KB = Path("data/policies/refund_policies.json")
TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> set[str]:
    return set(TOKEN_PATTERN.findall(text.lower()))


def retrieve_policies(
    query: str,
    filename: str | Path = DEFAULT_POLICY_KB,
    top_k: int = 3,
) -> list[RetrievedPolicy]:
    """Rank mock policies using query/keyword token overlap."""

    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string")
    if top_k < 1:
        raise ValueError("top_k must be at least 1")

    with Path(filename).open(encoding="utf-8") as policy_file:
        policies = json.load(policy_file)

    query_tokens = _tokens(query)
    ranked = []
    for policy in policies:
        policy_tokens = _tokens(
            " ".join(
                [
                    policy["title"],
                    policy["policy_text"],
                    *policy["keywords"],
                    *policy["eligible_damage_types"],
                ]
            )
        )
        overlap = len(query_tokens & policy_tokens)
        score = overlap / max(len(query_tokens), 1)
        ranked.append((score, policy))

    ranked.sort(key=lambda item: (-item[0], item[1]["policy_id"]))
    results = []
    for score, policy in ranked[:top_k]:
        results.append(
            RetrievedPolicy(
                policy_id=policy["policy_id"],
                title=policy["title"],
                policy_text=policy["policy_text"],
                policy_source=policy["policy_source"],
                policy_match=round(score, 2),
                refund_window_days=policy["refund_window_days"],
                requires_image=policy["requires_image"],
                eligible_damage_types=tuple(policy["eligible_damage_types"]),
            )
        )
    return results


def retrieve_best_policy(
    query: str,
    filename: str | Path = DEFAULT_POLICY_KB,
) -> RetrievedPolicy:
    """Return the highest-ranked policy for a query."""

    return retrieve_policies(query, filename, top_k=1)[0]
