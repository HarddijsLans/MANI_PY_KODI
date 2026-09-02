"""
===============================================================================
03_5_validate_csv_header.py
===============================================================================

Mērķis
------
1. Nolasīt konkrētu CKAN resursu.
2. Iegūt CSV faila URL un conformsTo metadatu URL.
3. No CSVW metadatiem nolasīt deklarētos kolonnu tehniskos nosaukumus.
4. No CSV faila nolasīt faktisko galvenes rindu.
5. Salīdzināt kolonnu nosaukumus, skaitu un secību.

CKAN objekts
------------
Resurss

CKAN Action
-----------
resource_show

HTTP metodes
------------
1. GET uz CKAN Action API.
2. GET uz conformsTo JSON URL.
3. GET uz CSV faila URL.

Rezultāts
---------
Terminālī tiek parādīts:
- deklarēto kolonnu saraksts;
- faktisko CSV kolonnu saraksts;
- salīdzināšanas rezultāts;
- trūkstošās, liekās vai nepareizā secībā esošās kolonnas.

Drošības līmenis
----------------
Tikai lasa datus.
Neveic nekādas izmaiņas CKAN portālā.
===============================================================================
"""

import csv
import io
import json
from typing import Any

import requests

from config import CKAN_BASE_URL, CKAN_API_TOKEN


# -----------------------------------------------------------------------------
# 1. Izvēlētais CSV resurss
# -----------------------------------------------------------------------------

RESOURCE_ID = "8e4ee339-494c-4048-a21b-71e4a8c6c04e"

RESOURCE_SHOW_URL = f"{CKAN_BASE_URL}/api/3/action/resource_show"

HEADERS = {
    "Authorization": CKAN_API_TOKEN
}

TIMEOUT_SECONDS = 30


def get_json(url: str, **request_kwargs: Any) -> dict:
    """
    Izpilda GET pieprasījumu un atgriež JSON kā Python vārdnīcu.
    """

    response = requests.get(
        url,
        timeout=TIMEOUT_SECONDS,
        **request_kwargs
    )

    print(f"HTTP statuss: {response.status_code}")
    response.raise_for_status()

    return response.json()


def normalize_encoding(encoding: str | None) -> str:
    """
    Normalizē CSVW metadatos norādīto kodējuma nosaukumu.

    Ja kodējums nav norādīts, izmanto UTF-8.
    """

    if not encoding:
        return "utf-8-sig"

    normalized = encoding.strip().lower()

    encoding_aliases = {
        "utf-8": "utf-8-sig",
        "utf8": "utf-8-sig",
        "iso-8859-1": "iso-8859-1",
        "latin-1": "iso-8859-1",
        "latin1": "iso-8859-1",
        "windows-1252": "cp1252",
        "windows-1257": "cp1257"
    }

    return encoding_aliases.get(normalized, normalized)


def get_declared_columns(metadata: dict) -> list[str]:
    """
    No CSVW tableSchema.columns iegūst kolonnu tehniskos nosaukumus.
    """

    columns = (
        metadata
        .get("tableSchema", {})
        .get("columns", [])
    )

    if not columns:
        raise ValueError(
            "CSVW metadati nesatur 'tableSchema.columns'."
        )

    declared_columns: list[str] = []

    for index, column in enumerate(columns, start=1):
        column_name = column.get("name")

        if not column_name:
            raise ValueError(
                f"{index}. kolonnai CSVW metadatos nav lauka 'name'."
            )

        declared_columns.append(str(column_name).strip())

    return declared_columns


def get_csv_dialect(metadata: dict) -> tuple[str, str, str]:
    """
    No CSVW metadatiem iegūst:
    - kolonnu atdalītāju;
    - pēdiņu simbolu;
    - faila kodējumu.
    """

    dialect = metadata.get("dialect", {})

    delimiter = dialect.get("delimiter", ",")
    quote_char = dialect.get("quoteChar", '"')
    encoding = normalize_encoding(dialect.get("encoding"))

    if len(delimiter) != 1:
        raise ValueError(
            f"Nederīgs CSV atdalītājs: {delimiter!r}"
        )

    if len(quote_char) != 1:
        raise ValueError(
            f"Nederīgs CSV pēdiņu simbols: {quote_char!r}"
        )

    return delimiter, quote_char, encoding


def get_actual_csv_header(
    csv_url: str,
    delimiter: str,
    quote_char: str,
    encoding: str
) -> list[str]:
    """
    Lejupielādē CSV failu un nolasa tikai pirmo — galvenes — rindu.
    """

    response = requests.get(
        csv_url,
        timeout=TIMEOUT_SECONDS
    )

    print(f"CSV HTTP statuss: {response.status_code}")
    response.raise_for_status()

    try:
        csv_text = response.content.decode(encoding)
    except UnicodeDecodeError as error:
        raise ValueError(
            f"CSV failu nevar dekodēt ar kodējumu {encoding!r}."
        ) from error

    csv_stream = io.StringIO(csv_text, newline="")

    reader = csv.reader(
        csv_stream,
        delimiter=delimiter,
        quotechar=quote_char
    )

    try:
        header = next(reader)
    except StopIteration as error:
        raise ValueError("CSV fails ir tukšs.") from error

    # Noņemam iespējamo BOM un nevajadzīgas ārējās atstarpes.
    return [
        value.lstrip("\ufeff").strip()
        for value in header
    ]


def print_columns(title: str, columns: list[str]) -> None:
    """
    Izdrukā kolonnu sarakstu ar numerāciju.
    """

    print(f"\n{title}")
    print("-" * 80)

    for index, column_name in enumerate(columns, start=1):
        print(f"{index:>2}. {column_name}")


def compare_columns(
    declared_columns: list[str],
    actual_columns: list[str]
) -> bool:
    """
    Salīdzina deklarētās un faktiskās kolonnas.

    Pārbauda:
    - kolonnu skaitu;
    - kolonnu nosaukumus;
    - kolonnu secību.
    """

    print("\nSalīdzināšanas rezultāts")
    print("=" * 80)

    exact_match = declared_columns == actual_columns

    if exact_match:
        print("✅ CSV galvene pilnībā atbilst CSVW metadatiem.")
        print("✅ Kolonnu skaits ir vienāds.")
        print("✅ Kolonnu nosaukumi ir vienādi.")
        print("✅ Kolonnu secība ir vienāda.")
        return True

    print("❌ CSV galvene pilnībā neatbilst CSVW metadatiem.")

    print(
        f"\nDeklarēto kolonnu skaits : {len(declared_columns)}"
    )
    print(
        f"Faktisko CSV kolonnu skaits: {len(actual_columns)}"
    )

    declared_set = set(declared_columns)
    actual_set = set(actual_columns)

    missing_columns = [
        column
        for column in declared_columns
        if column not in actual_set
    ]

    extra_columns = [
        column
        for column in actual_columns
        if column not in declared_set
    ]

    if missing_columns:
        print("\nCSV failā trūkst šādu deklarēto kolonnu:")

        for column in missing_columns:
            print(f"  - {column}")

    if extra_columns:
        print("\nCSV failā ir metadatos nedeklarētas kolonnas:")

        for column in extra_columns:
            print(f"  - {column}")

    common_count = min(
        len(declared_columns),
        len(actual_columns)
    )

    position_differences: list[tuple[int, str, str]] = []

    for index in range(common_count):
        declared = declared_columns[index]
        actual = actual_columns[index]

        if declared != actual:
            position_differences.append(
                (index + 1, declared, actual)
            )

    if position_differences:
        print("\nKolonnu pozīciju atšķirības:")

        for position, declared, actual in position_differences:
            print(
                f"  {position}. pozīcija:"
                f" deklarēts={declared!r},"
                f" CSV={actual!r}"
            )

    return False


def main() -> None:
    print("1. Nolasu resursu no CKAN...")

    ckan_response = get_json(
        RESOURCE_SHOW_URL,
        headers=HEADERS,
        params={"id": RESOURCE_ID}
    )

    if not ckan_response.get("success"):
        print("\nCKAN atgrieza kļūdu:")
        print(
            json.dumps(
                ckan_response,
                ensure_ascii=False,
                indent=4
            )
        )
        raise SystemExit(1)

    resource = ckan_response["result"]

    print("\nResurss")
    print("-" * 80)
    print(f"Nosaukums  : {resource.get('name')}")
    print(f"Resursa ID : {resource.get('id')}")
    print(f"Formāts    : {resource.get('format')}")

    csv_url = resource.get("url")
    conforms_to_url = resource.get("conformsTo")

    if not csv_url:
        raise ValueError(
            "Resursam nav norādīts CSV satura URL."
        )

    if not conforms_to_url:
        raise ValueError(
            "Resursam nav aizpildīts lauks 'conformsTo'."
        )

    print("\n2. Nolasu CSVW metadatus...")

    metadata = get_json(conforms_to_url)

    declared_columns = get_declared_columns(metadata)

    delimiter, quote_char, encoding = get_csv_dialect(metadata)

    print("\nCSV tehniskie parametri")
    print("-" * 80)
    print(f"Atdalītājs : {delimiter!r}")
    print(f"Pēdiņas    : {quote_char!r}")
    print(f"Kodējums   : {encoding}")

    print("\n3. Nolasu faktiskā CSV faila galveni...")

    actual_columns = get_actual_csv_header(
        csv_url=csv_url,
        delimiter=delimiter,
        quote_char=quote_char,
        encoding=encoding
    )

    print_columns(
        "CSVW metadatos deklarētās kolonnas",
        declared_columns
    )

    print_columns(
        "CSV faila faktiskās kolonnas",
        actual_columns
    )

    is_valid = compare_columns(
        declared_columns,
        actual_columns
    )

    print("\n" + "=" * 80)

    if is_valid:
        print("Validācijas rezultāts: VEIKSMĪGS")
    else:
        print("Validācijas rezultāts: NEVEIKSMĪGS")
        raise SystemExit(1)


if __name__ == "__main__":
    try:
        main()

    except requests.exceptions.Timeout:
        print(
            "\nKļūda: pieprasījums pārsniedza "
            f"{TIMEOUT_SECONDS} sekunžu gaidīšanas laiku."
        )

    except requests.exceptions.ConnectionError as error:
        print("\nSavienojuma kļūda:")
        print(error)

    except requests.exceptions.HTTPError as error:
        print("\nHTTP kļūda:")
        print(error)

    except requests.exceptions.RequestException as error:
        print("\nHTTP pieprasījuma kļūda:")
        print(error)

    except json.JSONDecodeError as error:
        print("\nSaņemtais saturs nav derīgs JSON:")
        print(error)

    except ValueError as error:
        print("\nDatu validācijas kļūda:")
        print(error)

    except KeyError as error:
        print("\nCKAN atbildē nav sagaidītā lauka:")
        print(error)

    except Exception as error:
        print("\nNezināma kļūda:")
        print(error)