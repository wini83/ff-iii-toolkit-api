from __future__ import annotations

import re
import unicodedata


class CategorizationTextPreprocessor:
    _long_number_pattern = re.compile(r"\d{6,}")
    _whitespace_pattern = re.compile(r"\s+")
    _diacritic_translation = str.maketrans(
        {
            "ą": "a",
            "ć": "c",
            "ę": "e",
            "ł": "l",
            "ń": "n",
            "ó": "o",
            "ś": "s",
            "ż": "z",
            "ź": "z",
            "Ą": "A",
            "Ć": "C",
            "Ę": "E",
            "Ł": "L",
            "Ń": "N",
            "Ó": "O",
            "Ś": "S",
            "Ż": "Z",
            "Ź": "Z",
        }
    )

    def normalize(self, value: str | None) -> str:
        if value is None:
            return ""

        text = value.strip()
        if not text:
            return ""

        text = unicodedata.normalize("NFKD", text)
        text = text.translate(self._diacritic_translation)
        text = text.encode("ascii", "ignore").decode("ascii")
        text = self._long_number_pattern.sub(" ", text)
        text = text.lower()
        text = self._whitespace_pattern.sub(" ", text)
        return text.strip()

    def tokens(self, value: str | None) -> set[str]:
        normalized = self.normalize(value)
        if not normalized:
            return set()
        return set(normalized.split(" "))
