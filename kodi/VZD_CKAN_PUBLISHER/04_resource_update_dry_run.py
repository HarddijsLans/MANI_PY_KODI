"""
===============================================================================
04_1_resource_update_dry_run.py
===============================================================================

Mērķis
------
Sagatavot CKAN resursa atjaunināšanu izmēģinājuma jeb dry run režīmā.

Programma:
1. pārbauda lokālo CSV datni;
2. pārbauda UTF-8 BOM;
3. nolasa mērķa CKAN resursu;
4. pārbauda CSV galveni pret CSVW metadatiem;
5. parāda plānoto resource_update darbību;
6. neko neaugšupielādē un neko portālā nemaina.

CKAN objekts
------------
Resurss

CKAN Action
-----------
resource_show

Nākotnes Action
---------------
resource_update

Drošības līmenis
----------------
Tikai lasa un validē datus.
Neveic nekādas izmaiņas CKAN portālā.
===============================================================================
"""

import csv
import io
import json
from pathlib import Path
from typing import Any

import requests

from config import CKAN_BASE_URL, CKAN_API_TOKEN


# =============================================================================
# Konfigurācija
# =============================================================================

RESOURCE_ID = "8e4ee339-494c-4048-a21b-71e4a8c6c04e"

# Nomainiet uz faktiskās lokālās CSV datnes ceļu.
LOCAL_CSV_PATH = Path(
    r"C:\Users\hardijslans\Desktop\VISUAL STUDIO CODE\ATSAVINAMAS ZEMES\Datnes_publicesanai\parveidots_1_pielikums.csv"
)

RESOURCE_SHOW_URL = f"{CKAN_BASE_URL}/api/3/action/resource_show"
RESOURCE_UPDATE_URL = f"{CKAN_BASE_URL}/api/3/action/resource_update"

TIMEOUT_SECONDS = 30
UTF8_BOM = b"\xef\xbb\xbf"

API_HEADERS = {
    "Authorization": CKAN_API_TOKEN
}


# =============================================================================
# HTTP funkcijas
# =============================================================================

def get_response(url: str, **kwargs: Any) -> requests.Response:
    """Izpilda HTTP GET pieprasījumu."""

    response = requests.get(
        url,
        timeout=TIMEOUT_SECONDS,
        **kwargs
    )

    response.raise_for_status()
    return response


def get_json(url: str, **kwargs: Any) -> dict:
    """Izpilda HTTP GET pieprasījumu un atgriež JSON."""

    response = get_response(url, **kwargs)

    try:
        return response.json()
    except requests.exceptions.JSONDecodeError as error:
        raise ValueError(
            f"No adreses nav saņemts derīgs JSON: {url}"
        ) from error


# =============================================================================
# CKAN nolasīšana
# =============================================================================

def get_resource(resource_id: str) -> dict:
    """Nolasa vienu CKAN resursu ar resource_show."""

    data = get_json(
        RESOURCE_SHOW_URL,
        headers=API_HEADERS,
        params={"id": resource_id}
    )

    if not data.get("success"):
        raise RuntimeError(
            "CKAN resource_show atgrieza kļūdu:\n"
            + json.dumps(data, ensure_ascii=False, indent=4)
        )

    resource = data.get("result")

    if not isinstance(resource, dict):
        raise ValueError("CKAN atbildē nav derīga result objekta.")

    return resource


# =============================================================================
# Lokālās CSV datnes pārbaude
# =============================================================================

def read_local_csv(csv_path: Path) -> tuple[bytes, str]:
    """
    Nolasa lokālo CSV datni.

    Atgriež:
    - datnes baitus;
    - tekstu, dekodētu kā UTF-8 ar BOM.
    """

    if not csv_path.exists():
        raise FileNotFoundError(
            f"Lokālā CSV datne nav atrasta:\n{csv_path}"
        )

    if not csv_path.is_file():
        raise ValueError(
            f"Norādītais ceļš nav datne:\n{csv_path}"
        )

    content = csv_path.read_bytes()

    if not content:
        raise ValueError("Lokālā CSV datne ir tukša.")

    if not content.startswith(UTF8_BOM):
        raise ValueError(
            "Lokālā CSV datne nesākas ar UTF-8 BOM "
            "(gaidīti baiti EF BB BF)."
        )

    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise ValueError(
            "Lokālo CSV datni nevar dekodēt kā UTF-8 ar BOM."
        ) from error

    return content, text


def get_csvw_parameters(
    metadata: dict
) -> tuple[str, str, list[str]]:
    """
    No CSVW metadatiem nolasa:
    - delimiter;
    - quoteChar;
    - deklarētās kolonnas.
    """

    dialect = metadata.get("dialect", {})

    delimiter = str(dialect.get("delimiter", ","))
    quote_char = str(dialect.get("quoteChar", '"'))

    if len(delimiter) != 1:
        raise ValueError(
            f"Nederīgs CSVW delimiter: {delimiter!r}"
        )

    if len(quote_char) != 1:
        raise ValueError(
            f"Nederīgs CSVW quoteChar: {quote_char!r}"
        )

    columns = (
        metadata
        .get("tableSchema", {})
        .get("columns", [])
    )

    if not isinstance(columns, list) or not columns:
        raise ValueError(
            "CSVW metadati nesatur tableSchema.columns."
        )

    declared_columns: list[str] = []

    for index, column in enumerate(columns, start=1):
        column_name = column.get("name")

        if not column_name:
            raise ValueError(
                f"{index}. CSVW kolonnai nav lauka name."
            )

        declared_columns.append(str(column_name).strip())

    return delimiter, quote_char, declared_columns


def read_csv_rows(
    csv_text: str,
    delimiter: str,
    quote_char: str
) -> list[list[str]]:
    """Nolasa CSV rindas."""

    csv_stream = io.StringIO(csv_text, newline="")

    reader = csv.reader(
        csv_stream,
        delimiter=delimiter,
        quotechar=quote_char
    )

    return list(reader)


def validate_csv_structure(
    rows: list[list[str]],
    declared_columns: list[str]
) -> tuple[list[str], int]:
    """
    Pārbauda CSV galveni un datu rindu kolonnu skaitu.

    Atgriež:
    - faktiskās kolonnas;
    - datu rindu skaitu.
    """

    if not rows:
        raise ValueError("CSV datne nesatur nevienu rindu.")

    actual_columns = [
        value.lstrip("\ufeff").strip()
        for value in rows[0]
    ]

    if actual_columns != declared_columns:
        raise ValueError(
            "CSV galvene neatbilst CSVW metadatiem.\n\n"
            f"CSVW kolonnas:\n{declared_columns}\n\n"
            f"CSV kolonnas:\n{actual_columns}"
        )

    expected_count = len(actual_columns)
    invalid_rows: list[tuple[int, int]] = []

    for row_number, row in enumerate(rows[1:], start=2):
        if len(row) != expected_count:
            invalid_rows.append((row_number, len(row)))

    if invalid_rows:
        details = "\n".join(
            (
                f"CSV {row_number}. rindā ir {column_count} "
                f"kolonnas; sagaidītas {expected_count}."
            )
            for row_number, column_count in invalid_rows[:20]
        )

        raise ValueError(
            "CSV datnē atrastas rindas ar nepareizu "
            f"kolonnu skaitu:\n{details}"
        )

    return actual_columns, len(rows) - 1


# =============================================================================
# Dry run rezultāts
# =============================================================================

def print_dry_run_plan(
    resource: dict,
    csv_path: Path,
    file_size: int,
    columns: list[str],
    data_row_count: int
) -> None:
    """Parāda plānoto resource_update darbību."""

    print("\n" + "=" * 80)
    print("RESOURCE_UPDATE — DRY RUN")
    print("=" * 80)

    print("\nMērķa CKAN resurss")
    print("-" * 80)
    print(f"Nosaukums       : {resource.get('name')}")
    print(f"Resursa ID      : {resource.get('id')}")
    print(f"Pašreizējais URL: {resource.get('url')}")
    print(f"Formāts         : {resource.get('format')}")
    print(f"Pašreiz mainīts : {resource.get('last_modified')}")

    print("\nLokālā datne")
    print("-" * 80)
    print(f"Ceļš            : {csv_path}")
    print(f"Datnes nosaukums: {csv_path.name}")
    print(f"Izmērs          : {file_size} baiti")
    print("Kodējums        : UTF-8 ar BOM")
    print(f"Kolonnu skaits  : {len(columns)}")
    print(f"Datu rindu skaits: {data_row_count}")

    print("\nPlānotais CKAN pieprasījums")
    print("-" * 80)
    print("HTTP metode : POST")
    print(f"Action URL  : {RESOURCE_UPDATE_URL}")
    print(f"Resursa ID  : {RESOURCE_ID}")
    print(f"Augšupielāde: {csv_path.name}")

    print("\n" + "-" * 80)
    print("DRY RUN REZULTĀTS: VEIKSMĪGS")
    print("Resurss NETIKA atjaunināts.")
    print("Datne NETIKA nosūtīta uz CKAN.")
    print("-" * 80)


# =============================================================================
# Galvenā programma
# =============================================================================

def main() -> None:
    print("1. Pārbaudu lokālo CSV datni...")

    csv_content, csv_text = read_local_csv(
        LOCAL_CSV_PATH
    )

    print("✅ Lokālā CSV datne ir atrasta.")
    print("✅ UTF-8 BOM ir atrasts.")
    print("✅ CSV datne veiksmīgi dekodēta kā UTF-8.")

    print("\n2. Nolasu mērķa CKAN resursu...")

    resource = get_resource(RESOURCE_ID)

    print(f"✅ Atrasts resurss: {resource.get('name')}")

    conforms_to_url = resource.get("conformsTo")

    if not conforms_to_url:
        raise ValueError(
            "Mērķa resursam nav aizpildīts lauks conformsTo."
        )

    print("\n3. Nolasu CSVW metadatus...")

    metadata = get_json(conforms_to_url)

    delimiter, quote_char, declared_columns = (
        get_csvw_parameters(metadata)
    )

    print("✅ CSVW metadati nolasīti.")

    print("\n4. Validēju lokālās CSV datnes struktūru...")

    rows = read_csv_rows(
        csv_text,
        delimiter,
        quote_char
    )

    actual_columns, data_row_count = validate_csv_structure(
        rows,
        declared_columns
    )

    print("✅ CSV galvene atbilst CSVW metadatiem.")
    print("✅ Visām rindām ir pareizs kolonnu skaits.")

    print_dry_run_plan(
        resource=resource,
        csv_path=LOCAL_CSV_PATH,
        file_size=len(csv_content),
        columns=actual_columns,
        data_row_count=data_row_count
    )


if __name__ == "__main__":
    try:
        main()

    except FileNotFoundError as error:
        print("\nDatnes kļūda:")
        print(error)
        raise SystemExit(1)

    except requests.exceptions.Timeout:
        print(
            "\nKļūda: HTTP pieprasījums pārsniedza "
            f"{TIMEOUT_SECONDS} sekunžu gaidīšanas laiku."
        )
        raise SystemExit(1)

    except requests.exceptions.ConnectionError as error:
        print("\nSavienojuma kļūda:")
        print(error)
        raise SystemExit(1)

    except requests.exceptions.HTTPError as error:
        print("\nHTTP kļūda:")
        print(error)
        raise SystemExit(1)

    except requests.exceptions.RequestException as error:
        print("\nHTTP pieprasījuma kļūda:")
        print(error)
        raise SystemExit(1)

    except (ValueError, RuntimeError, KeyError) as error:
        print("\nDry run pārbaudes kļūda:")
        print(error)
        raise SystemExit(1)

    except Exception as error:
        print("\nNezināma kļūda:")
        print(error)
        raise SystemExit(1)