"""Conservative, read-only salary projection. Never rewrite published snapshots."""
import re
import unicodedata
from dataclasses import dataclass, asdict
from decimal import Decimal, InvalidOperation
from functools import lru_cache

from app.display import display_text

PARSER_VERSION = "salary-v1"
CURRENCIES = {"USD", "JPY", "EUR", "GBP", "AUD", "CAD", "CNY", "KRW", "SGD", "CHF", "INR"}
PERIODS = {"hour", "day", "week", "month", "year"}
_PREFIX = r"(?:USD|JPY|EUR|GBP|AUD|CAD|CNY|KRW|SGD|CHF|INR|US\$|CA\$|AU\$|[$€£¥])?"
_SUFFIX = r"(?:USD|JPY|EUR|GBP|AUD|CAD|CNY|KRW|SGD|CHF|INR|円|元|ウォン)?"
_AMOUNT = rf"{_PREFIX}\s*(\d+(?:[,.]\d+)*(?:\s*[kKmM万](?![a-zA-Z]))?)(?!\d|[.,]\d)\s*{_SUFFIX}(?![a-zA-Z\d]|[.,]\d)"
_RANGE = re.compile(rf"(?<![a-zA-Z\d.,]){_AMOUNT}\s*(?:[-–—~〜～]|\bto\b)\s*{_AMOUNT}", re.I)
_SINGLE = re.compile(rf"(?<![a-zA-Z\d.,]){_AMOUNT}", re.I)
_MONEY_MARKER = re.compile(r"USD|JPY|EUR|GBP|AUD|CAD|CNY|KRW|SGD|CHF|INR|[$€£¥円元]", re.I)
_PERIOD_PATTERNS = {
    "year": r"annual(?:ly)?\b(?!\s+(?:corporate\s+)?(?:bonus|incentive|leave|review))|yearly|per[-\s]+(?:per[-\s]+)?year|/\s*(?:year|yr)\b|年収|年額",
    "month": r"monthly|per[-\s]+month|/\s*(?:month|mo)\b|月収|月額|月給",
    "hour": r"hourly|per[-\s]+hour|/\s*(?:hour|hr)\b|時給",
    "week": r"weekly|per[-\s]+week|/\s*(?:week|wk)\b",
    "day": r"daily|per[-\s]+day|/\s*day\b|日給",
}


@dataclass(frozen=True)
class Salary:
    minimum: float | None = None
    maximum: float | None = None
    currency: str | None = None
    period: str | None = None
    symbol: str | None = None
    status: str = "unparsed"
    reason: str = "No single reliable salary amount"
    version: str = PARSER_VERSION
    qualifier: str | None = None

    def to_api(self):
        return asdict(self)


def _number(value):
    value = value.strip().replace(" ", "")
    multiplier = Decimal(1)
    if value[-1:].lower() in {"k", "m"} or value.endswith("万"):
        multiplier = {"k": Decimal(1000), "m": Decimal(1000000), "万": Decimal(10000)}[value[-1].lower()]
        value = value[:-1]
    # 2,738.10 / 2.738,10 / 2738,10; reject ambiguous European thousands.
    if "," in value and "." in value:
        if value.rfind(",") > value.rfind("."):
            value = value.replace(".", "").replace(",", ".")
        else:
            value = value.replace(",", "")
    elif "," in value:
        if re.fullmatch(r"\d{1,3}(?:,\d{3})+", value):
            value = value.replace(",", "")
        elif re.fullmatch(r"\d+,\d{1,2}", value):
            value = value.replace(",", ".")
        else:
            raise ValueError("Ambiguous number")
    elif re.fullmatch(r"\d{1,3}(?:\.\d{3})+", value):
        raise ValueError("Ambiguous decimal/thousands separator")
    amount = Decimal(value) * multiplier
    if not amount.is_finite() or amount < 0 or amount > Decimal("9999999999999999.99"):
        raise ValueError("Invalid amount")
    return float(amount)


def _currency(text):
    codes = {code for code in CURRENCIES if re.search(rf"\b{code}\b", text, re.I)}
    for marker, code in [("US$", "USD"), ("CA$", "CAD"), ("AU$", "AUD"), ("€", "EUR"), ("£", "GBP"), ("円", "JPY"), ("元", "CNY")]:
        if marker in text: codes.add(code)
    return next(iter(codes)) if len(codes) == 1 else None, len(codes) > 1


def _period(text):
    periods = {period for period, pattern in _PERIOD_PATTERNS.items() if re.search(pattern, text, re.I)}
    return next(iter(periods)) if len(periods) == 1 else None, len(periods) > 1


@lru_cache(maxsize=8192)
def project_salary(raw, minimum=None, maximum=None, currency=None, period=None):
    """Prefer validated structured bounds; otherwise parse a primary source line.

    Bare $, ¥ and missing periods are deliberately not inferred from location.
    Multiple location/pay bands are excluded rather than collapsed to extremes.
    """
    try:
        if minimum is not None or maximum is not None:
            lo = _number(str(minimum)) if minimum is not None else None
            hi = _number(str(maximum)) if maximum is not None else None
            if lo is not None and hi is not None and hi < lo: raise ValueError("Reversed bounds")
            code = str(currency or "").upper()
            unit = str(period or "").lower()
            unit = {"annual": "year", "yearly": "year", "monthly": "month", "hourly": "hour"}.get(unit, unit)
            return Salary(lo, hi, code if code in CURRENCIES else None, unit if unit in PERIODS else None,
                          status="structured", reason="Existing structured salary fields")

        text = unicodedata.normalize("NFKC", display_text(raw) or "")
        if not text: return Salary(reason="No salary provided")
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        # Tier IV distinguishes estimated total monthly pay, base pay and overtime.
        primary = [line for line in lines if re.search(r"estimated monthly salary|想定月収", line, re.I)]
        selected = primary[0] if len(primary) == 1 else text
        code, conflicting_currency = _currency(selected)
        unit, conflicting_period = _period(selected)
        if conflicting_currency or conflicting_period:
            return Salary(reason="Multiple currencies or pay periods")
        symbol = next((s for s in ("$", "€", "£", "¥", "円") if s in selected), None)
        if not code and not symbol:
            return Salary(reason="No explicit currency or money symbol")
        ranges = list(_RANGE.finditer(selected))
        qualifier = None
        if len(ranges) > 1: return Salary(reason="Multiple salary ranges; retain source qualifications")
        if ranges:
            match = ranges[0]
            if not _MONEY_MARKER.search(match.group(0)):
                return Salary(reason="Numeric range is not explicitly marked as money")
            prefix = selected[:match.start()].strip().rstrip(":：").strip()
            if ":" in selected[:match.start()] and prefix and not re.search(r"salary|pay|compensation|wage|月収|月給|年収", prefix, re.I):
                qualifier = prefix
            lo, hi = _number(match.group(1)), _number(match.group(2))
            if hi < lo: return Salary(reason="Reversed salary range")
        else:
            candidates = list(_SINGLE.finditer(selected))
            # A lone amount may precede/follow its currency (e.g. 2738,10 EUR).
            # Reject multiple numbers, which may include hours, bonus percentages etc.
            if len(candidates) != 1: return Salary(reason="Ambiguous amount or additional numeric components")
            if not _MONEY_MARKER.search(candidates[0].group(0)):
                return Salary(reason="Amount is not explicitly marked as money")
            lo = hi = _number(candidates[0].group(1))
            if re.search(r"minimum|at least|\bfrom\b|starting|以上", selected, re.I): hi = None
            elif re.search(r"up to|maximum|以下", selected, re.I): lo = None
        return Salary(lo, hi, code, unit, symbol,
                      "parsed" if code and unit else "partial",
                      "Estimated monthly total; see source for base/overtime" if primary else
                      "Source amount; no currency/period inference or conversion", qualifier=qualifier)
    except (ValueError, InvalidOperation, TypeError):
        return Salary(reason="Invalid or ambiguous numeric salary")


def salary_from_row(row):
    return project_salary(row.get("salary_raw"), row.get("salary_min"), row.get("salary_max"),
                          row.get("salary_currency"), row.get("salary_period"))


def matches_salary(salary, *, currency=None, period=None, minimum=None, maximum=None):
    if salary.minimum is None and salary.maximum is None: return False
    if currency and salary.currency != currency: return False
    if period and salary.period != period: return False
    # Inclusive overlap, only when the relevant advertised bound is known.
    if minimum is not None and (salary.maximum is None or salary.maximum < minimum): return False
    if maximum is not None and (salary.minimum is None or salary.minimum > maximum): return False
    return True
