from __future__ import annotations

ONES = ("", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten",
        "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen")
TENS = ("", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety")


def _under_thousand(number: int) -> str:
    parts: list[str] = []
    if number >= 100:
        parts.extend((ONES[number // 100], "Hundred")); number %= 100
    if number >= 20:
        parts.append(TENS[number // 10]); number %= 10
    if number:
        parts.append(ONES[number])
    return " ".join(parts)


def amount_to_words(amount: float) -> str:
    if amount < 0 or amount >= 1_000_000_000_000:
        raise ValueError("Amount must be between zero and one trillion.")
    rupees = int(amount); cents = round((amount - rupees) * 100)
    if cents == 100: rupees += 1; cents = 0
    if rupees == 0: words = "Zero"
    else:
        words, remaining = [], rupees
        for value, label in ((1_000_000_000, "Billion"), (1_000_000, "Million"), (1_000, "Thousand"), (1, "")):
            group, remaining = divmod(remaining, value)
            if group: words.append((_under_thousand(group) + " " + label).strip())
        words = " ".join(words)
    result = f"{words} Rupees"
    if cents: result += f" and {_under_thousand(cents)} Cents"
    return result + " Only"

