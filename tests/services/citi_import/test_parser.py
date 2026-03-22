from services.citi_import.parser import CitiTextParser


def test_parse_skips_positive_transactions_by_default():
    parser = CitiTextParser()

    result = parser.parse(
        raw_text="\n".join(
            [
                "16 sty 2025",
                "Test Shop",
                "Test Shop",
                "-42,00PLN",
                "17 sty 2025",
                "Salary",
                "Salary",
                "100,00PLN",
            ]
        )
    )

    assert len(result.transactions) == 1
    assert result.transactions[0].payee == "Test Shop"
    assert result.transactions[0].amount_value == "-42.00"
    assert result.warnings == []


def test_parse_collects_warning_for_invalid_amount():
    parser = CitiTextParser()

    result = parser.parse(
        raw_text="\n".join(
            [
                "16 sty 2025",
                "Test Shop",
                "Test Shop",
                "invalid",
            ]
        )
    )

    assert result.transactions == []
    assert result.warnings == [
        "Skipped transaction at line 1: invalid amount 'invalid'"
    ]


def test_parse_includes_positive_when_requested():
    parser = CitiTextParser()

    result = parser.parse(
        raw_text="\n".join(
            [
                "17 sty 2025",
                "Salary",
                "Salary",
                "100,00PLN",
            ]
        ),
        include_positive=True,
    )

    assert len(result.transactions) == 1
    assert result.transactions[0].amount_value == "100.00"
