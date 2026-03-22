from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from services.citi_import.models import ParsedCitiTransaction

MONTHS_PL = {
    "sty": 1,
    "lut": 2,
    "mar": 3,
    "kwi": 4,
    "maj": 5,
    "cze": 6,
    "lip": 7,
    "sie": 8,
    "wrz": 9,
    "paź": 10,
    "paz": 10,
    "lis": 11,
    "gru": 12,
}


@dataclass(slots=True)
class CitiParseResult:
    transactions: list[ParsedCitiTransaction]
    warnings: list[str]


class CitiTextParser:
    def parse(
        self,
        *,
        raw_text: str,
        include_positive: bool = False,
    ) -> CitiParseResult:
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        transactions: list[ParsedCitiTransaction] = []
        warnings: list[str] = []
        index = 0

        while index < len(lines):
            parsed_date = self._parse_polish_date(lines[index])
            if parsed_date is None:
                index += 1
                continue

            if index + 3 >= len(lines):
                warnings.append(
                    f"Incomplete transaction block starting at line {index + 1}"
                )
                break

            payee = lines[index + 1]
            amount_line = lines[index + 3]
            amount = self._parse_amount(amount_line)
            if amount is None:
                warnings.append(
                    f"Skipped transaction at line {index + 1}: invalid amount '{amount_line}'"
                )
                index += 4
                continue

            if not include_positive and amount.value > 0:
                index += 4
                continue

            transactions.append(
                ParsedCitiTransaction(
                    date=parsed_date,
                    payee=payee,
                    amount_text=amount_line,
                    amount_currency=amount.currency,
                    amount_value=amount.normalized_value,
                )
            )
            index += 4

        return CitiParseResult(transactions=transactions, warnings=warnings)

    def _parse_polish_date(self, value: str) -> date | None:
        parts = value.strip().split()
        if len(parts) != 3:
            return None

        day_str, month_str, year_str = parts
        try:
            day = int(day_str)
            year = int(year_str)
        except ValueError:
            return None

        month = MONTHS_PL.get(month_str[:3].lower())
        if month is None:
            return None

        try:
            return datetime(year, month, day).date()
        except ValueError:
            return None

    def _parse_amount(self, value: str) -> _ParsedAmount | None:
        compact = value.replace(" ", "").replace(",", ".")
        currency = "".join(ch for ch in compact if ch.isalpha()).upper() or "PLN"
        number = compact.removesuffix(currency)
        if not number:
            return None

        try:
            float(number)
        except ValueError:
            return None

        return _ParsedAmount(
            normalized_value=number, currency=currency, value=float(number)
        )


@dataclass(slots=True)
class _ParsedAmount:
    normalized_value: str
    currency: str
    value: float
