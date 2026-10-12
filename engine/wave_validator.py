"""
engine/wave_validator.py
------------------------
Layer 2 — Wave Validation Engine

Translates the three non-negotiable impulse wave rules from the course notes
into strict Python boolean logic, operating on six consecutive price pivot
points P0–P5 that represent a complete 5-wave impulse structure:

    P0 --> P1     Wave 1  (impulse leg, motive direction)
    P1 --> P2     Wave 2  (corrective retracement)
    P2 --> P3     Wave 3  (impulse leg - longest / most powerful)
    P3 --> P4     Wave 4  (corrective retracement)
    P4 --> P5     Wave 5  (final impulse leg)

                   P3
           P1      /|    P5
           /|     / |   /
          / |    /  |  /
    P0   /  |   /   | /
          |  P2   |
           | (Wave 2 retracement)

Rules implemented (source: course notes pages 5-8):

  Rule 1 — Wave 2 retracement bound (p.6, rule 2):
      Wave 2 NEVER retraces beyond the origin of Wave 1.
      → P2 must NOT go past P0.

  Rule 2 — Wave 3 length constraint (p.5, rule "03" and p.6, rule 5):
      Wave 3 is NEVER the shortest among Wave 1, Wave 3, and Wave 5.
      → |P3-P2| must be > min(|P1-P0|, |P5-P4|).

  Rule 3 — Wave 4 / Wave 1 no-overlap (p.6, rule 7):
      Wave 4 must NOT overlap into Wave 1 price territory.
      → P4 must NOT cross beyond P1.

  Confluence check (bonus, from p.9 "best entry points"):
      is_valid_impulse() also verifies Fibonacci-level adherence for W2 and W4.
      This is surfaced as a non-blocking FibConformance result attached to the
      ValidationResult, so callers can decide how strict to be.

Public API
----------
    from engine.wave_validator import WaveValidator, WavePivots

    pivots = WavePivots(P0=10000, P1=13500, P2=11800, P3=18200,
                        P4=16000, P5=20000)
    wv     = WaveValidator(pivots)

    result = wv.is_valid_impulse()
    print(result.is_valid)      # True / False
    print(result.summary())     # human-readable report
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, Optional

from engine.fibonacci import (
    RETRACEMENT_RATIOS,
    FibHitResult,
    FibonacciChecker,
    FibonacciLevels,
)
from utils.logger import fmt_price, get_logger

log = get_logger(__name__)


# ── Pivot container ────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class WavePivots:
    """
    Six consecutive price pivot points defining a complete 5-wave impulse.

    All values are *closing prices* (or pivot highs/lows) in quote currency.
    The direction of the impulse is inferred: if P1 > P0 it is bullish,
    if P1 < P0 it is bearish.

    Parameters
    ----------
    P0 : float  — Wave 0 / start of Wave 1 (origin)
    P1 : float  — Top of Wave 1 (bottom of Wave 2)
    P2 : float  — Bottom of Wave 2 (start of Wave 3)
    P3 : float  — Top of Wave 3 (bottom of Wave 4)
    P4 : float  — Bottom of Wave 4 (start of Wave 5)
    P5 : float  — Top of Wave 5 (end of the impulse)

    Raises
    ------
    ValueError  — if any price is non-positive, or if P0 == P1
                  (zero-length Wave 1 is undefined).
    """

    P0: float
    P1: float
    P2: float
    P3: float
    P4: float
    P5: float

    def __post_init__(self) -> None:
        for name, val in self.as_dict().items():
            if val <= 0:
                raise ValueError(
                    f"Pivot {name}={val} is non-positive. "
                    "All pivot prices must be > 0."
                )
        if math.isclose(self.P0, self.P1, rel_tol=1e-9):
            raise ValueError(
                f"P0={self.P0} and P1={self.P1} are equal — "
                "Wave 1 has zero length, cannot validate."
            )

    # ── Derived wave lengths ───────────────────────────────────────────────

    @property
    def wave1_length(self) -> float:
        """Absolute price length of Wave 1 (P0 → P1)."""
        return abs(self.P1 - self.P0)

    @property
    def wave2_length(self) -> float:
        """Absolute price length of Wave 2 (P1 → P2)."""
        return abs(self.P2 - self.P1)

    @property
    def wave3_length(self) -> float:
        """Absolute price length of Wave 3 (P2 → P3)."""
        return abs(self.P3 - self.P2)

    @property
    def wave4_length(self) -> float:
        """Absolute price length of Wave 4 (P3 → P4)."""
        return abs(self.P4 - self.P3)

    @property
    def wave5_length(self) -> float:
        """Absolute price length of Wave 5 (P4 → P5)."""
        return abs(self.P5 - self.P4)

    @property
    def is_bullish(self) -> bool:
        """True when the impulse moves upward (P1 > P0)."""
        return self.P1 > self.P0

    def as_dict(self) -> Dict[str, float]:
        """Return pivots as an ordered dict {name: price}."""
        return {
            "P0": self.P0, "P1": self.P1, "P2": self.P2,
            "P3": self.P3, "P4": self.P4, "P5": self.P5,
        }

    def __repr__(self) -> str:  # pragma: no cover
        direction = "BULL" if self.is_bullish else "BEAR"
        return (
            f"WavePivots({direction} "
            f"P0={self.P0} P1={self.P1} P2={self.P2} "
            f"P3={self.P3} P4={self.P4} P5={self.P5})"
        )


# ── Rule result containers ─────────────────────────────────────────────────────

@dataclass
class RuleResult:
    """Outcome of a single Elliott Wave rule check."""
    rule_name:   str
    passed:      bool
    description: str
    detail:      str = ""   # Optional quantitative detail (e.g. "W2 retrace = 61.8%")

    def __str__(self) -> str:
        status = "✅ PASS" if self.passed else "❌ FAIL"
        parts = [f"{status}  [{self.rule_name}]  {self.description}"]
        if self.detail:
            parts.append(f"         → {self.detail}")
        return "\n".join(parts)


@dataclass
class FibConformance:
    """Fibonacci-level conformance for Wave 2 and Wave 4 retracements."""
    wave2_fib_result: FibHitResult
    wave4_fib_result: FibHitResult
    wave2_retrace_pct: float    # e.g. 0.618 means 61.8% retracement
    wave4_retrace_pct: float

    @property
    def wave2_in_zone(self) -> bool:
        """True when Wave 2 retraces within the key 38.2%–61.8% zone."""
        return 0.382 <= self.wave2_retrace_pct <= 0.886

    @property
    def wave4_in_zone(self) -> bool:
        """True when Wave 4 retraces within the key 23.6%–50.0% zone."""
        return 0.236 <= self.wave4_retrace_pct <= 0.500

    def summary(self) -> str:
        w2_pct = f"{self.wave2_retrace_pct * 100:.1f}%"
        w4_pct = f"{self.wave4_retrace_pct * 100:.1f}%"
        w2_zone = "✅ in zone" if self.wave2_in_zone else "⚠️  outside zone"
        w4_zone = "✅ in zone" if self.wave4_in_zone else "⚠️  outside zone"
        return (
            f"  Wave 2 retracement : {w2_pct}  nearest Fib={self.wave2_fib_result.nearest_ratio}  {w2_zone}\n"
            f"  Wave 4 retracement : {w4_pct}  nearest Fib={self.wave4_fib_result.nearest_ratio}  {w4_zone}"
        )


@dataclass
class ValidationResult:
    """
    Complete result of WaveValidator.is_valid_impulse().

    Aggregates all rule results, the overall pass/fail flag, and optional
    Fibonacci conformance data.
    """
    is_valid:      bool
    rules:         Dict[str, RuleResult] = field(default_factory=dict)
    fib:           Optional[FibConformance] = None
    pivots:        Optional[WavePivots] = None

    def failed_rules(self) -> list[RuleResult]:
        """Return only the rules that failed."""
        return [r for r in self.rules.values() if not r.passed]

    def summary(self) -> str:
        """Human-readable multi-line validation report."""
        lines = [
            "═" * 56,
            "  Elliott Wave Impulse Validation",
            f"  Overall: {'✅ VALID' if self.is_valid else '❌ INVALID'}",
            "─" * 56,
        ]
        if self.pivots:
            d = self.pivots.as_dict()
            lines.append(
                "  Pivots: "
                + "  ".join(f"{k}={v:.2f}" for k, v in d.items())
            )
            lines.append(
                f"  Lengths — W1={self.pivots.wave1_length:.2f}  "
                f"W2={self.pivots.wave2_length:.2f}  "
                f"W3={self.pivots.wave3_length:.2f}  "
                f"W4={self.pivots.wave4_length:.2f}  "
                f"W5={self.pivots.wave5_length:.2f}"
            )
            lines.append("─" * 56)
        for rule in self.rules.values():
            lines.append(str(rule))
        if self.fib:
            lines.append("─" * 56)
            lines.append("  Fibonacci Conformance (informational):")
            lines.append(self.fib.summary())
        lines.append("═" * 56)
        return "\n".join(lines)


# ── WaveValidator ──────────────────────────────────────────────────────────────

class WaveValidator:
    """
    Validates a set of six price pivots against the three non-negotiable
    Elliott Wave impulse rules from the course notes (pages 5-8).

    Parameters
    ----------
    pivots : WavePivots
        The six pivot prices P0-P5 defining the impulse candidate.
    fib_tolerance_pct : float
        Percentage tolerance for Fibonacci proximity checks (default ±0.5%).
        This only affects the *informational* FibConformance result; it does
        NOT affect the core three hard rules.

    Quick Usage
    -----------
        wv     = WaveValidator(pivots)
        result = wv.is_valid_impulse()
        if result.is_valid:
            print("Valid impulse — proceed to execution layer")
        else:
            for r in result.failed_rules():
                print(r)
    """

    def __init__(
        self,
        pivots: WavePivots,
        fib_tolerance_pct: float = 0.5,
    ) -> None:
        self.pivots = pivots
        self.fib_tolerance_pct = fib_tolerance_pct
        log.debug("WaveValidator initialised: %r", pivots)

    # ═══════════════════════════════════════════════════════════════════════
    # Rule 1 — Wave 2 retracement bound
    # Source: course notes p.6, rule 2: "Wave two — wave one's origin cannot
    #         be broken" (i.e. P2 must not pass P0).
    # ═══════════════════════════════════════════════════════════════════════

    def check_wave_2_retracement(self) -> RuleResult:
        """
        Rule 1 — Wave 2 must NOT retrace past the origin of Wave 1 (P0).

        Bullish impulse : P2 must be strictly ABOVE P0.
        Bearish impulse : P2 must be strictly BELOW P0.

        A Wave 2 that closes at exactly P0 is treated as a violation because
        that would imply 100% retracement, invalidating the impulse count.

        Returns
        -------
        RuleResult
            .passed = True  → rule satisfied, impulse count remains valid.
            .passed = False → impulse is invalid; this is a corrective move
                              or a misidentified pivot.
        """
        p = self.pivots
        rule_name = "Rule-1: W2 Retracement Bound"

        # Compute actual retracement percentage for reporting
        w2_retrace_pct = abs(p.P2 - p.P1) / p.wave1_length if p.wave1_length else 0.0

        if p.is_bullish:
            # Bullish: Wave 2 low (P2) must stay above Wave 1 origin (P0)
            passed = p.P2 > p.P0
            description = (
                f"Wave 2 low (P2={fmt_price(p.P2)}) must be > Wave 1 origin (P0={fmt_price(p.P0)})"
            )
            detail = (
                f"P2 {'>' if passed else '<='} P0  |  "
                f"W2 retraced {w2_retrace_pct * 100:.1f}% of W1"
            )
        else:
            # Bearish: Wave 2 high (P2) must stay below Wave 1 origin (P0)
            passed = p.P2 < p.P0
            description = (
                f"Wave 2 high (P2={fmt_price(p.P2)}) must be < Wave 1 origin (P0={fmt_price(p.P0)})"
            )
            detail = (
                f"P2 {'<' if passed else '>='} P0  |  "
                f"W2 retraced {w2_retrace_pct * 100:.1f}% of W1"
            )

        if not passed:
            log.warning(
                "[Rule-1 FAIL] W2 retracement violation: P2=%.4f crossed P0=%.4f "
                "(%.1f%% retrace). Impulse count invalidated.",
                p.P2, p.P0, w2_retrace_pct * 100,
            )
        else:
            log.debug("[Rule-1 PASS] P2=%s P0=%s retrace=%.1f%%",
                      fmt_price(p.P2), fmt_price(p.P0), w2_retrace_pct * 100)

        return RuleResult(
            rule_name=rule_name,
            passed=passed,
            description=description,
            detail=detail,
        )

    # ═══════════════════════════════════════════════════════════════════════
    # Rule 2 — Wave 3 length constraint
    # Source: course notes p.5 rule "03": "Wave 1 cannot look like Wave 5"
    #         and p.6 rule 5: "Wave 3 breaks Wave 1 high."
    #         Also: "Wave 3 is never the shortest" (classic EW rule).
    # ═══════════════════════════════════════════════════════════════════════

    def check_wave_3_length(self) -> RuleResult:
        """
        Rule 2 — Wave 3 must NOT be the shortest wave among W1, W3, and W5.

        Specifically: Wave 3 length must be strictly greater than the
        MINIMUM of (Wave 1 length, Wave 5 length).

        This ensures Wave 3 is never the shortest impulse leg, which is one
        of the most fundamental constraints in Elliott Wave theory.

        A common complementary check (from p.6, rule 5) is that Wave 3's
        high must break above Wave 1's high (for a bullish impulse). This is
        also verified here and reported in detail.

        Returns
        -------
        RuleResult
            .passed = True  → Wave 3 is not the shortest.
            .passed = False → Wave 3 is the shortest; count is invalid.
        """
        p = self.pivots
        rule_name = "Rule-2: W3 Not Shortest"

        w1 = p.wave1_length
        w3 = p.wave3_length
        w5 = p.wave5_length
        shortest_of_w1_w5 = min(w1, w5)

        # Core rule: W3 must not be the shortest
        w3_not_shortest = w3 > shortest_of_w1_w5

        # Supplementary: W3 high must break beyond W1 high (bullish) / low (bearish)
        if p.is_bullish:
            w3_breaks_w1 = p.P3 > p.P1
        else:
            w3_breaks_w1 = p.P3 < p.P1

        passed = w3_not_shortest and w3_breaks_w1

        description = (
            f"W3 length ({fmt_price(w3)}) must be > min(W1={fmt_price(w1)}, W5={fmt_price(w5)}) "
            f"and W3 must break beyond W1 extreme"
        )
        detail = (
            f"W1={fmt_price(w1)}  W3={fmt_price(w3)}  W5={fmt_price(w5)}  "
            f"min(W1,W5)={fmt_price(shortest_of_w1_w5)}  "
            f"W3>min={'Yes' if w3_not_shortest else 'No'}  "
            f"W3_breaks_W1={'Yes' if w3_breaks_w1 else 'No'}"
        )

        if not passed:
            log.warning(
                "[Rule-2 FAIL] W3 length constraint: W1=%s W3=%s W5=%s. "
                "W3_not_shortest=%s  W3_breaks_W1=%s",
                fmt_price(w1), fmt_price(w3), fmt_price(w5), w3_not_shortest, w3_breaks_w1,
            )
        else:
            log.debug("[Rule-2 PASS] W1=%s W3=%s W5=%s", fmt_price(w1), fmt_price(w3), fmt_price(w5))

        return RuleResult(
            rule_name=rule_name,
            passed=passed,
            description=description,
            detail=detail,
        )

    # ═══════════════════════════════════════════════════════════════════════
    # Rule 3 — Wave 4 / Wave 1 no-overlap
    # Source: course notes p.6, rule 7: "Wave four — wave one's territory
    #         cannot be overlapped."
    # ═══════════════════════════════════════════════════════════════════════

    def check_wave_4_overlap(self) -> RuleResult:
        """
        Rule 3 — Wave 4 must NOT enter Wave 1 price territory.

        Wave 1 price territory is defined as all prices between P0 and P1.
        Wave 4's corrective extreme (P4) must not cross into that zone.

        Bullish impulse : P4 must remain strictly ABOVE P1.
        Bearish impulse : P4 must remain strictly BELOW P1.

        Note on Modern Elliott Wave (p.8):
          The Modern EW interpretation allows a brief intra-candle overlap
          ("spike" overlap), but for clean signal generation this validator
          uses the strict classical rule by default.

        Returns
        -------
        RuleResult
            .passed = True  → no overlap, impulse count valid.
            .passed = False → overlap detected; likely a diagonal or
                              misidentified impulse.
        """
        p = self.pivots
        rule_name = "Rule-3: W4 No Overlap with W1"

        # How far did P4 penetrate relative to P1?
        overlap_amount = p.P1 - p.P4 if p.is_bullish else p.P4 - p.P1
        # Positive overlap_amount means there IS an overlap
        has_overlap = overlap_amount > 0

        if p.is_bullish:
            passed = p.P4 > p.P1
            description = (
                f"Wave 4 low (P4={fmt_price(p.P4)}) must be > Wave 1 top (P1={fmt_price(p.P1)})"
            )
        else:
            passed = p.P4 < p.P1
            description = (
                f"Wave 4 high (P4={fmt_price(p.P4)}) must be < Wave 1 bottom (P1={fmt_price(p.P1)})"
            )

        overlap_pct = (
            overlap_amount / p.wave1_length * 100
            if p.wave1_length and has_overlap
            else 0.0
        )
        detail = (
            f"Overlap = {'YES' if has_overlap else 'NO'}  "
            f"{'Penetration=' + fmt_price(overlap_amount) if has_overlap else ''}"
            f"  ({overlap_pct:.1f}% of W1 length)"
            if has_overlap
            else f"P4 clear of W1 territory by {fmt_price(abs(overlap_amount))}"
        )

        if not passed:
            log.warning(
                "[Rule-3 FAIL] W4 overlap with W1: P4=%s crossed P1=%s "
                "(penetration=%s, %.1f%% of W1).",
                fmt_price(p.P4), fmt_price(p.P1), fmt_price(overlap_amount), overlap_pct,
            )
        else:
            log.debug("[Rule-3 PASS] P4=%s P1=%s no overlap.", fmt_price(p.P4), fmt_price(p.P1))

        return RuleResult(
            rule_name=rule_name,
            passed=passed,
            description=description,
            detail=detail,
        )

    # ═══════════════════════════════════════════════════════════════════════
    # Fibonacci Conformance (informational — does NOT affect is_valid_impulse)
    # Source: course notes p.9-11: preferred entry zones for W2 and W4.
    # ═══════════════════════════════════════════════════════════════════════

    def check_fibonacci_conformance(self) -> FibConformance:
        """
        Informational check: are Wave 2 and Wave 4 landing near key Fib levels?

        Wave 2 ideal zone : 38.2%–61.8% retracement of Wave 1 (p.11 starred)
        Wave 4 ideal zone : 23.6%–38.2% retracement of Wave 3 (p.10 starred)

        This method does NOT affect is_valid_impulse(). It enriches the
        ValidationResult with confluence data for the execution layer.

        Returns
        -------
        FibConformance dataclass with hit results for W2 and W4.
        """
        p = self.pivots

        # ── Wave 2 Fibonacci check ─────────────────────────────────────
        # Reference swing: P0 → P1 (Wave 1 full move)
        fib_w1 = FibonacciLevels(swing_start=p.P0, swing_end=p.P1)
        checker_w1 = FibonacciChecker(fib_w1, self.fib_tolerance_pct)
        w2_fib_result = checker_w1.is_at_retracement(
            price=p.P2, ratios=RETRACEMENT_RATIOS
        )
        w2_retrace_pct = checker_w1.retracement_pct(p.P2)

        # ── Wave 4 Fibonacci check ─────────────────────────────────────
        # Reference swing: P2 → P3 (Wave 3 full move)
        fib_w3 = FibonacciLevels(swing_start=p.P2, swing_end=p.P3)
        checker_w3 = FibonacciChecker(fib_w3, self.fib_tolerance_pct)
        w4_fib_result = checker_w3.is_at_retracement(
            price=p.P4, ratios=RETRACEMENT_RATIOS
        )
        w4_retrace_pct = checker_w3.retracement_pct(p.P4)

        log.debug(
            "Fib conformance: W2_retrace=%.1f%% (at_fib=%s)  "
            "W4_retrace=%.1f%% (at_fib=%s)",
            w2_retrace_pct * 100, w2_fib_result.hit,
            w4_retrace_pct * 100, w4_fib_result.hit,
        )

        return FibConformance(
            wave2_fib_result=w2_fib_result,
            wave4_fib_result=w4_fib_result,
            wave2_retrace_pct=w2_retrace_pct,
            wave4_retrace_pct=w4_retrace_pct,
        )

    # ═══════════════════════════════════════════════════════════════════════
    # Master validation
    # ═══════════════════════════════════════════════════════════════════════

    def is_valid_impulse(self) -> ValidationResult:
        """
        Run all three hard rules and return a ValidationResult.

        The overall ``is_valid`` flag is True ONLY when all three rules pass:
          1. Wave 2 does not retrace past P0
          2. Wave 3 is not the shortest
          3. Wave 4 does not overlap Wave 1

        Fibonacci conformance is always computed and attached to the result
        but does NOT affect the is_valid flag.

        Returns
        -------
        ValidationResult
            .is_valid   — bool
            .rules      — dict of RuleResult for each of the 3 rules
            .fib        — FibConformance (informational, always present)
            .pivots     — the WavePivots that were evaluated

        Example
        -------
            pivots = WavePivots(P0=10000, P1=13500, P2=11800,
                                P3=18200, P4=16000, P5=20000)
            wv     = WaveValidator(pivots)
            result = wv.is_valid_impulse()
            print(result.summary())
        """
        log.info(
            "Starting impulse validation for pivots: %s",
            self.pivots.as_dict(),
        )

        # ── Execute the three hard rules ───────────────────────────────────
        r1 = self.check_wave_2_retracement()
        r2 = self.check_wave_3_length()
        r3 = self.check_wave_4_overlap()

        rules = {
            r1.rule_name: r1,
            r2.rule_name: r2,
            r3.rule_name: r3,
        }
        is_valid = r1.passed and r2.passed and r3.passed

        # ── Fibonacci conformance (informational) ──────────────────────────
        fib_conformance: Optional[FibConformance] = None
        try:
            fib_conformance = self.check_fibonacci_conformance()
        except Exception as exc:   # pragma: no cover
            log.warning("Fibonacci conformance check failed: %s", exc)

        result = ValidationResult(
            is_valid=is_valid,
            rules=rules,
            fib=fib_conformance,
            pivots=self.pivots,
        )

        log.info(
            "Impulse validation complete: %s  (%d/%d rules passed)",
            "VALID ✅" if is_valid else "INVALID ❌",
            sum(r.passed for r in rules.values()),
            len(rules),
        )
        return result


# ── Convenience factory ────────────────────────────────────────────────────────

def validate_impulse(
    P0: float, P1: float, P2: float,
    P3: float, P4: float, P5: float,
    fib_tolerance_pct: float = 0.5,
) -> ValidationResult:
    """
    One-liner factory to validate a set of six pivot prices.

    Equivalent to:
        WaveValidator(WavePivots(P0, P1, P2, P3, P4, P5)).is_valid_impulse()

    Example
    -------
        from engine.wave_validator import validate_impulse
        result = validate_impulse(10000, 13500, 11800, 18200, 16000, 20000)
        print(result.summary())
    """
    pivots = WavePivots(P0=P0, P1=P1, P2=P2, P3=P3, P4=P4, P5=P5)
    return WaveValidator(pivots, fib_tolerance_pct).is_valid_impulse()
