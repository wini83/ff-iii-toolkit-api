# py_firefly_iii_tools

Narzędzia pomocnicze do importu i przetwarzania transakcji bankowych (CSV) do Firefly III / innych narzędzi finansowych.

## Najważniejsze funkcje
- Parsowanie plików CSV banku (separator `;`, kodowanie UTF-8).
- Obsługa polskiego formatu dat (`DD-MM-YYYY`) i formatów kwot (przecinek jako separator dziesiętny, spacje jako separatory grup).
- Mapowanie wierszy CSV na obiekt `SimplifiedRecord`.

## Instalacja
Załóż wirtualne środowisko i zainstaluj zależności:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Uruchamianie
Jeśli aplikacja ma punkt wejścia ASGI/fastapi (np. `app.main:app`), można użyć `uvicorn`. Jeżeli używasz polecenia `uv` jako aliasu do `uvicorn`, poniższe przykłady będą działać także z `uv` zamiast `uvicorn`.

PowerShell / CMD:
```powershell
uvicorn app.main:app --reload --port 8000
# lub, jeśli masz alias `uv`:
uv app.main:app --reload --port 8000
```

## Szybkie użycie parsera CSV
Przykład użycia czytnika CSV w kodzie:
```python
from app.services.csv_reader import BankCSVReader

reader = BankCSVReader(r"C:\path\to\Historia_Operacji.csv")
records = reader.parse()
for r in records[:10]:
    print(r)
```

## Format CSV oczekiwany przez reader
Plik powinien zawierać nagłówek i kolumny:
- Data transakcji
- Data księgowania
- Nazwa nadawcy
- Nazwa odbiorcy
- Szczegóły transakcji
- Kwota operacji
- Waluta operacji
- Kwota w walucie rachunku
- Waluta rachunku
- Numer rachunku nadawcy
- Numer rachunku odbiorcy

Separator: `;`, kodowanie: `utf-8`.

## Testy i rozwój
Uruchamiaj testy lokalnie (jeśli są): `pytest`. Rozszerzyć walidację i obsługę błędów w parserze według potrzeb.

## License
Dodać plik `LICENSE` (np. MIT).