from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class DecisionResult:
    action: str
    confidence: float
    approved: bool
    reasons: list[str]
    thresholds: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CouncilVote:
    module: str
    direction: str
    weight: float
    strength: float
    evidence_count: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_MODULE_RULES: dict[str, tuple[tuple[str, ...], float]] = {
    "technical": (
        ("ema", "macd", "rsi", "divergence"),
        1.00,
    ),
    "market_structure": (
        ("bos", "choch", "swing", "structure"),
        1.25,
    ),
    "price_action": (
        ("engulf", "pin bar", "inside bar", "breakout", "retest", "wick"),
        1.10,
    ),
    "smart_money": (
        (
            "liquidity",
            "order-block",
            "order block",
            "fair value gap",
            "fvg",
            "premium",
            "discount",
        ),
        1.25,
    ),
    "volume": (
        ("volume profile", "point of control", "poc", "vah", "val"),
        0.70,
    ),
    "ict": (
        ("ict", "kill zone", "ote", "judas"),
        0.85,
    ),
    "wyckoff": (
        (
            "wyckoff",
            "spring",
            "upthrust",
            "sign of strength",
            "sign of weakness",
        ),
        0.65,
    ),
    "elliott": (
        ("elliott", "impulse wave", "corrective wave"),
        0.45,
    ),
}

_BUY_WORDS = (
    "bullish",
    "buy",
    "discount",
    "sell-side sweep",
    "above",
    "support",
    "spring",
    "sign of strength",
    "bullish ote",
)

_SELL_WORDS = (
    "bearish",
    "sell",
    "premium",
    "buy-side sweep",
    "below",
    "resistance",
    "upthrust",
    "sign of weakness",
    "bearish ote",
)


def _direction_for_text(text: str) -> str:
    lowered = text.lower()

    buy_hits = sum(term in lowered for term in _BUY_WORDS)
    sell_hits = sum(term in lowered for term in _SELL_WORDS)

    if buy_hits > sell_hits:
        return "BUY"

    if sell_hits > buy_hits:
        return "SELL"

    return "NEUTRAL"


def _build_council(evidence: list[str]) -> list[CouncilVote]:
    votes: list[CouncilVote] = []
    normalized = [(item, item.lower()) for item in evidence]

    for module, (keywords, weight) in _MODULE_RULES.items():
        matched = [
            original
            for original, lowered in normalized
            if any(keyword in lowered for keyword in keywords)
        ]

        if not matched:
            continue

        buy_count = sum(
            _direction_for_text(item) == "BUY"
            for item in matched
        )

        sell_count = sum(
            _direction_for_text(item) == "SELL"
            for item in matched
        )

        directional_count = buy_count + sell_count

        if buy_count > sell_count:
            direction = "BUY"
        elif sell_count > buy_count:
            direction = "SELL"
        else:
            direction = "NEUTRAL"

        if directional_count == 0:
            strength = 0.0
        else:
            strength = round(
                100.0
                * max(buy_count, sell_count)
                / directional_count,
                2,
            )

        votes.append(
            CouncilVote(
                module=module,
                direction=direction,
                weight=weight,
                strength=strength,
                evidence_count=len(matched),
            )
        )

    return votes


def _infer_regime(evidence: list[str]) -> str:
    lowered = " | ".join(evidence).lower()

    if (
        "ema 20/50/200 bullish alignment" in lowered
        or "ema 20/50/200 bearish alignment" in lowered
    ):
        return "TREND"

    if "bos" in lowered or "choch" in lowered:
        return "STRUCTURE_BREAK"

    return "RANGE"


def _adaptive_thresholds(
    regime: str,
    min_score: float,
    min_confidence: float,
    min_edge: float,
) -> tuple[float, float, float, int]:
    if regime == "TREND":
        return (
            max(55.0, min_score - 5.0),
            max(60.0, min_confidence - 5.0),
            min_edge,
            2,
        )

    if regime == "STRUCTURE_BREAK":
        return (
            min_score,
            min_confidence,
            max(12.0, min_edge - 3.0),
            3,
        )

    return (
        max(65.0, min_score + 5.0),
        max(70.0, min_confidence + 5.0),
        max(18.0, min_edge + 3.0),
        3,
    )


def make_decision(
    *,
    buy_score: float,
    sell_score: float,
    evidence: list[str],
    min_score: float = 60.0,
    min_confidence: float = 65.0,
    min_edge: float = 15.0,
) -> DecisionResult:
    """Create the final HAYA-ZAID Supervisor V2 decision.

    The public signature remains unchanged so existing callers,
    tests, backtests, journaling, risk planning and MT5 execution
    remain compatible.

    Council agreement is required only when recognizable council
    evidence is available. Legacy calls containing no council
    evidence continue to use the score, confidence and edge gates.
    """

    buy_score_value = float(buy_score)
    sell_score_value = float(sell_score)
    total = buy_score_value + sell_score_value

    regime = _infer_regime(evidence)

    (
        score_threshold,
        confidence_threshold,
        edge_threshold,
        min_agreement,
    ) = _adaptive_thresholds(
        regime,
        min_score,
        min_confidence,
        min_edge,
    )

    council = _build_council(evidence)
    has_council = bool(council)

    if total <= 0:
        return DecisionResult(
            action="HOLD",
            confidence=0.0,
            approved=False,
            reasons=["No directional evidence"],
            thresholds={
                "supervisor_version": "2.0",
                "regime": regime,
                "min_score": score_threshold,
                "min_confidence": confidence_threshold,
                "min_edge": edge_threshold,
                "min_agreement": min_agreement,
                "council_required": has_council,
                "agreement_passed": not has_council,
                "council": [
                    vote.to_dict()
                    for vote in council
                ],
            },
        )

    if buy_score_value > sell_score_value:
        raw_action = "BUY"
    elif sell_score_value > buy_score_value:
        raw_action = "SELL"
    else:
        raw_action = "HOLD"

    leading_score = max(
        buy_score_value,
        sell_score_value,
    )

    edge = abs(
        buy_score_value
        - sell_score_value
    )

    raw_confidence = (
        100.0
        * leading_score
        / total
    )

    supporters = [
        vote
        for vote in council
        if vote.direction == raw_action
    ]

    opponents = [
        vote
        for vote in council
        if vote.direction not in (
            raw_action,
            "NEUTRAL",
        )
    ]

    supporter_weight = sum(
        vote.weight
        * (vote.strength / 100.0)
        for vote in supporters
    )

    opponent_weight = sum(
        vote.weight
        * (vote.strength / 100.0)
        for vote in opponents
    )

    agreement = len(supporters)

    # Reward broad independent agreement and penalize contradiction.
    council_adjustment = (
        min(8.0, supporter_weight * 2.0)
        - min(12.0, opponent_weight * 3.0)
    )

    confidence = round(
        max(
            0.0,
            min(
                100.0,
                raw_confidence
                + council_adjustment,
            ),
        ),
        2,
    )

    strong_core_opposition = any(
        vote.module
        in {
            "market_structure",
            "smart_money",
            "price_action",
        }
        and (
            vote.weight
            * vote.strength
            / 100.0
        )
        >= 0.75
        for vote in opponents
    )

    # Backward compatibility:
    # Council agreement is mandatory only when council evidence exists.
    agreement_passed = (
        agreement >= min_agreement
        if has_council
        else True
    )

    approved = (
        raw_action != "HOLD"
        and leading_score >= score_threshold
        and confidence >= confidence_threshold
        and edge >= edge_threshold
        and agreement_passed
        and not strong_core_opposition
    )

    reasons = list(evidence[-12:])

    if supporters:
        reasons.append(
            "HAYA Supervisor support: "
            + ", ".join(
                f"{vote.module}({vote.strength:.0f}%)"
                for vote in supporters
            )
        )

    if opponents:
        reasons.append(
            "HAYA Supervisor opposition: "
            + ", ".join(
                f"{vote.module}({vote.strength:.0f}%)"
                for vote in opponents
            )
        )

    if strong_core_opposition:
        reasons.append(
            "A core analysis module strongly contradicts "
            "the leading direction"
        )

    if has_council and not agreement_passed:
        reasons.append(
            "Council agreement is below the required minimum"
        )

    if not approved:
        reasons.append(
            "Signal did not pass HAYA Supervisor V2 "
            "adaptive approval rules"
        )

    return DecisionResult(
        action=raw_action if approved else "HOLD",
        confidence=confidence,
        approved=approved,
        reasons=reasons,
        thresholds={
            "supervisor_version": "2.0",
            "regime": regime,
            "min_score": score_threshold,
            "min_confidence": confidence_threshold,
            "min_edge": edge_threshold,
            "min_agreement": min_agreement,
            "leading_score": round(
                leading_score,
                4,
            ),
            "edge": round(
                edge,
                4,
            ),
            "raw_confidence": round(
                raw_confidence,
                2,
            ),
            "council_adjustment": round(
                council_adjustment,
                2,
            ),
            "council_required": has_council,
            "agreement_passed": agreement_passed,
            "agreement": agreement,
            "supporter_weight": round(
                supporter_weight,
                4,
            ),
            "opponent_weight": round(
                opponent_weight,
                4,
            ),
            "strong_core_opposition": strong_core_opposition,
            "council": [
                vote.to_dict()
                for vote in council
            ],
        },
    )