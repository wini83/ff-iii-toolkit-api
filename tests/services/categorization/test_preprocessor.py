from services.categorization.preprocessor import CategorizationTextPreprocessor


def test_preprocessor_normalizes_unicode_numbers_and_whitespace():
    preprocessor = CategorizationTextPreprocessor()

    result = preprocessor.normalize("  Płatność   123456789  Za kawę \n")

    assert result == "platnosc za kawe"


def test_preprocessor_handles_empty_inputs_and_tokens():
    preprocessor = CategorizationTextPreprocessor()

    assert preprocessor.normalize(None) == ""
    assert preprocessor.normalize("   ") == ""
    assert preprocessor.normalize("Order 1234567   Nr 89") == "order nr 89"
    assert preprocessor.tokens(None) == set()
    assert preprocessor.tokens("   ") == set()
