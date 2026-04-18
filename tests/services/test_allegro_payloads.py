from services.allegro.payloads import OrderPayload


def test_fill_total_cost_currency_handles_non_dict_and_missing_shapes():
    non_dict = ["not", "a", "dict"]
    assert OrderPayload._fill_total_cost_currency(non_dict) is non_dict

    already_normalized = {
        "totalCost": {"amount": "1.23", "currency": "PLN"},
        "payment": {"amount": {"amount": "1.23", "currency": "PLN"}},
    }
    assert (
        OrderPayload._fill_total_cost_currency(already_normalized) is already_normalized
    )

    missing_payment = {"totalCost": {"amount": "1.23"}}
    assert OrderPayload._fill_total_cost_currency(missing_payment) is missing_payment

    missing_amount = {
        "totalCost": {"amount": "1.23"},
        "payment": {"provider": "PAYU"},
    }
    assert OrderPayload._fill_total_cost_currency(missing_amount) is missing_amount

    missing_currency = {
        "totalCost": {"amount": "1.23"},
        "payment": {"amount": {"amount": "1.23"}},
    }
    assert OrderPayload._fill_total_cost_currency(missing_currency) is missing_currency


def test_fill_total_cost_currency_infers_currency_from_payment_amount():
    payload = {
        "totalCost": {"amount": "1.23"},
        "payment": {"amount": {"amount": "1.23", "currency": "EUR"}},
    }

    normalized = OrderPayload._fill_total_cost_currency(payload)

    assert normalized is not payload
    assert normalized["totalCost"]["currency"] == "EUR"
    assert payload["totalCost"] == {"amount": "1.23"}
