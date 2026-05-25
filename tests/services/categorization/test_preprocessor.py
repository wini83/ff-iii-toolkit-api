from services.categorization.preprocessor import CategorizationTextPreprocessor


def test_preprocessor_normalizes_unicode_numbers_and_whitespace():
    preprocessor = CategorizationTextPreprocessor()

    result = preprocessor.normalize("  Płatność   123456789  Za kawę \n")

    assert result == "platnosc za kawe"
