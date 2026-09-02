"""
===============================================================================
03_7_validate_csv.py
===============================================================================

Mērķis
------
Validēt CKAN resursam pievienoto CSV datni pirms automatizētas publicēšanas.

Pārbaudes
---------
1. CKAN resurss ir pieejams.
2. Resurss satur CSV URL un conformsTo URL.
3. CSV datne sākas ar UTF-8 BOM.
4. CSV datni var dekodēt kā UTF-8 ar BOM.
5. CSV galvene atbilst CSVW tableSchema.columns.
6. Kolonnu secība atbilst CSVW metadatiem.
7. Visām CSV rindām ir vienāds kolonnu skaits.
8. CSVW encoding vērtība tiek salīdzināta ar faktisko kodējumu.

CKAN objekts
------------
Resurss

CKAN Action
-----------
resource_show

Drošības līmenis
----------------
Tikai lasa un validē datus.
Neveic nekādas izmaiņas CKAN portālā.
===============================================================================
"""

import csv
import io
import json
from dataclasses import dataclass, field
from typing import Any

import requests

from config import CKAN_BASE_URL, CKAN_API_TOKEN


# =============================================================================
# Konfigurācija
# =============================================================================

RESOURCE_ID = "8e4ee339-494c-4048-a21b-71e4a8c6c04e"

RESOURCE_SHOW_URL = f"{CKAN_BASE_URL}/api/3/action/resource_show"

TIMEOUT_SECONDS = 30

API_HEADERS = {
    "Authorization": CKAN_API_TOKEN
}

UTF8_BOM = b"\xef\xbb\xbf"


# =============================================================================
# Validācijas rezultāts
# =============================================================================

@dataclass
class ValidationResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    information: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.errors

    def add_error(self, message: str) -> None:
        self.errors.append(message)

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)

    def add_information(self, message: str) -> None:
        self.information.append(message)


# =============================================================================
# HTTP palīgfunkcijas
# =============================================================================

def get_response(url: str, **kwargs: Any) -> requests.Response:
    """
    Izpilda HTTP GET pieprasījumu un pārbauda HTTP statusu.
    """

    response = requests.get(
        url,
        timeout=TIMEOUT_SECONDS,
        **kwargs
    )

    response.raise_for_status()
    return response


def get_json(url: str, **kwargs: Any) -> dict:
    """
    Izpilda HTTP GET pieprasījumu un atgriež JSON objektu.
    """

    response = get_response(url, **kwargs)

    try:
        return response.json()
    except requests.exceptions.JSONDecodeError as error:
        raise ValueError(
            f"No adreses nav saņemts derīgs JSON: {url}"
        ) from error


# =============================================================================
# CKAN resursa nolasīšana
# =============================================================================

def get_resource(resource_id: str) -> dict:
    """
    Nolasa vienu CKAN resursu ar resource_show.
    """

    data = get_json(
        RESOURCE_SHOW_URL,
        headers=API_HEADERS,
        params={"id": resource_id}
    )

    if not data.get("success"):
        raise RuntimeError(
            "CKAN resource_show darbība atgrieza kļūdu:\n"
            + json.dumps(data, ensure_ascii=False, indent=4)
        )

    result = data.get("result")

    if not isinstance(result, dict):
        raise ValueError("CKAN atbildē nav derīga result objekta.")

    return result


# =============================================================================
# CSVW metadatu apstrāde
# =============================================================================

def get_declared_columns(metadata: dict) -> list[str]:
    """
    Nolasa CSVW tableSchema.columns[*].name vērtības.
    """

    columns = (
        metadata
        .get("tableSchema", {})
        .get("columns", [])
    )

    if not isinstance(columns, list) or not columns:
        raise ValueError(
            "CSVW metadati nesatur tableSchema.columns."
        )

    result: list[str] = []

    for index, column in enumerate(columns, start=1):
        if not isinstance(column, dict):
            raise ValueError(
                f"{index}. kolonnas apraksts nav JSON objekts."
            )

        column_name = column.get("name")

        if not column_name:
            raise ValueError(
                f"{index}. kolonnai CSVW metadatos nav lauka name."
            )

        result.append(str(column_name).strip())

    return result


def get_csv_parameters(metadata: dict) -> tuple[str, str, str | None]:
    """
    Nolasa CSVW dialect parametrus:
    - delimiter;
    - quoteChar;
    - encoding.
    """

    dialect = metadata.get("dialect", {})

    if not isinstance(dialect, dict):
        dialect = {}

    delimiter = str(dialect.get("delimiter", ","))
    quote_char = str(dialect.get("quoteChar", '"'))
    declared_encoding = dialect.get("encoding")

    if len(delimiter) != 1:
        raise ValueError(
            f"CSVW norādīts nederīgs delimiter: {delimiter!r}"
        )

    if len(quote_char) != 1:
        raise ValueError(
            f"CSVW norādīts nederīgs quoteChar: {quote_char!r}"
        )

    if declared_encoding is not None:
        declared_encoding = str(declared_encoding).strip()

    return delimiter, quote_char, declared_encoding


# =============================================================================
# CSV validācija
# =============================================================================

def decode_csv(
    content: bytes,
    validation: ValidationResult
) -> str:
    """
    Pārbauda UTF-8 BOM un dekodē CSV kā utf-8-sig.
    """

    if content.startswith(UTF8_BOM):
        validation.add_information(
            "CSV datne sākas ar UTF-8 BOM (EF BB BF)."
        )
    else:
        validation.add_error(
            "CSV datne nesākas ar UTF-8 BOM (EF BB BF)."
        )

    try:
        return content.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        validation.add_error(
            "CSV datni nevar dekodēt kā UTF-8 ar BOM: "
            f"{error}"
        )
        return ""


def read_csv_rows(
    csv_text: str,
    delimiter: str,
    quote_char: str
) -> list[list[str]]:
    """
    Nolasa visas CSV rindas.
    """

    csv_stream = io.StringIO(csv_text, newline="")

    reader = csv.reader(
        csv_stream,
        delimiter=delimiter,
        quotechar=quote_char
    )

    return list(reader)


def normalize_header(header: list[str]) -> list[str]:
    """
    Noņem BOM atlikumu un ārējās atstarpes no galvenes laukiem.
    """

    return [
        value.lstrip("\ufeff").strip()
        for value in header
    ]


def validate_header(
    actual_columns: list[str],
    declared_columns: list[str],
    validation: ValidationResult
) -> None:
    """
    Salīdzina faktiskās un deklarētās CSV kolonnas.
    """

    if len(actual_columns) != len(declared_columns):
        validation.add_error(
            "Kolonnu skaits neatbilst: "
            f"CSV={len(actual_columns)}, "
            f"CSVW={len(declared_columns)}."
        )
    else:
        validation.add_information(
            f"Kolonnu skaits atbilst: {len(actual_columns)}."
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
        validation.add_error(
            "CSV datnē trūkst kolonnu: "
            + ", ".join(missing_columns)
        )

    if extra_columns:
        validation.add_error(
            "CSV datnē ir CSVW metadatos nedeklarētas kolonnas: "
            + ", ".join(extra_columns)
        )

    if actual_columns == declared_columns:
        validation.add_information(
            "CSV kolonnu nosaukumi un secība pilnībā atbilst CSVW metadatiem."
        )
    elif not missing_columns and not extra_columns:
        validation.add_error(
            "CSV kolonnu nosaukumi sakrīt, bet to secība neatbilst CSVW metadatiem."
        )

        for index, (declared, actual) in enumerate(
            zip(declared_columns, actual_columns),
            start=1
        ):
            if declared != actual:
                validation.add_error(
                    f"{index}. pozīcija: "
                    f"CSVW={declared!r}, CSV={actual!r}."
                )


def validate_row_widths(
    rows: list[list[str]],
    expected_column_count: int,
    validation: ValidationResult
) -> None:
    """
    Pārbauda, vai katrai datu rindai ir sagaidāmais kolonnu skaits.
    """

    invalid_rows: list[tuple[int, int]] = []

    # Pirmā rinda ir galvene, tāpēc sākam ar 2. CSV rindas numuru.
    for row_number, row in enumerate(rows[1:], start=2):
        if len(row) != expected_column_count:
            invalid_rows.append((row_number, len(row)))

    if not invalid_rows:
        validation.add_information(
            "Visām CSV datu rindām ir pareizs kolonnu skaits."
        )
        return

    validation.add_error(
        f"Atrastas {len(invalid_rows)} rindas ar nepareizu kolonnu skaitu."
    )

    # Terminālī parādām ne vairāk kā pirmās 20 kļūdainās rindas.
    for row_number, column_count in invalid_rows[:20]:
        validation.add_error(
            f"CSV {row_number}. rindā ir {column_count} kolonnas; "
            f"sagaidītas {expected_column_count}."
        )

    if len(invalid_rows) > 20:
        validation.add_error(
            f"Vēl nav parādītas {len(invalid_rows) - 20} kļūdainas rindas."
        )


def validate_declared_encoding(
    declared_encoding: str | None,
    validation: ValidationResult
) -> None:
    """
    Salīdzina CSVW deklarēto kodējumu ar VZD datnes faktisko prasību.
    """

    if not declared_encoding:
        validation.add_warning(
            "CSVW metadatos nav norādīts dialect.encoding."
        )
        return

    normalized = declared_encoding.lower().replace("_", "-")

    accepted_values = {
        "utf-8",
        "utf8",
        "utf-8-sig"
    }

    if normalized in accepted_values:
        validation.add_information(
            f"CSVW kodējuma metadati atbilst UTF-8: {declared_encoding}."
        )
    else:
        validation.add_warning(
            "CSV datne ir UTF-8 ar BOM, bet CSVW metadatos "
            f"dialect.encoding ir norādīts {declared_encoding!r}."
        )


# =============================================================================
# Rezultātu attēlošana
# =============================================================================

def print_columns(title: str, columns: list[str]) -> None:
    print(f"\n{title}")
    print("-" * 80)

    for index, column in enumerate(columns, start=1):
        print(f"{index:>2}. {column}")


def print_validation_result(validation: ValidationResult) -> None:
    print("\n" + "=" * 80)
    print("VALIDĀCIJAS REZULTĀTS")
    print("=" * 80)

    if validation.information:
        print("\nInformācija")

        for message in validation.information:
            print(f"✅ {message}")

    if validation.warnings:
        print("\nBrīdinājumi")

        for message in validation.warnings:
            print(f"⚠️  {message}")

    if validation.errors:
        print("\nKļūdas")

        for message in validation.errors:
            print(f"❌ {message}")

    print("\n" + "-" * 80)

    if validation.is_valid:
        print("Kopējais rezultāts: VEIKSMĪGS")
        print("CSV datnes struktūra ir derīga.")
    else:
        print("Kopējais rezultāts: NEVEIKSMĪGS")
        print("CSV datni nedrīkst publicēt, kamēr kļūdas nav novērstas.")

    if validation.warnings and validation.is_valid:
        print(
            "CSV datne ir derīga, bet ir metadatu vai kvalitātes brīdinājumi."
        )


# =============================================================================
# Galvenā programma
# =============================================================================

def main() -> int:
    validation = ValidationResult()

    print("1. Nolasu CKAN resursu...")

    resource = get_resource(RESOURCE_ID)

    print("\nResurss")
    print("-" * 80)
    print(f"Nosaukums  : {resource.get('name')}")
    print(f"Resursa ID : {resource.get('id')}")
    print(f"Formāts    : {resource.get('format')}")

    csv_url = resource.get("url")
    conforms_to_url = resource.get("conformsTo")

    if not csv_url:
        raise ValueError("Resursam nav norādīts CSV datnes URL.")

    if not conforms_to_url:
        raise ValueError("Resursam nav aizpildīts lauks conformsTo.")

    print("\n2. Nolasu CSVW metadatus...")

    metadata = get_json(conforms_to_url)

    declared_columns = get_declared_columns(metadata)

    delimiter, quote_char, declared_encoding = get_csv_parameters(
        metadata
    )

    print("\nCSV tehniskie parametri")
    print("-" * 80)
    print(f"Atdalītājs               : {delimiter!r}")
    print(f"Pēdiņu simbols           : {quote_char!r}")
    print(f"CSVW deklarētais kodējums: {declared_encoding}")

    validate_declared_encoding(
        declared_encoding,
        validation
    )

    print("\n3. Lejupielādēju CSV datni...")

    csv_response = get_response(csv_url)
    csv_content = csv_response.content

    if not csv_content:
        validation.add_error("CSV datne ir tukša.")
        print_validation_result(validation)
        return 1

    print(f"CSV datnes izmērs: {len(csv_content)} baiti")

    print("\n4. Pārbaudu kodējumu...")

    csv_text = decode_csv(
        csv_content,
        validation
    )

    if not csv_text:
        print_validation_result(validation)
        return 1

    print("\n5. Nolasu CSV struktūru...")

    rows = read_csv_rows(
        csv_text,
        delimiter,
        quote_char
    )

    if not rows:
        validation.add_error("CSV datne nesatur nevienu rindu.")
        print_validation_result(validation)
        return 1

    actual_columns = normalize_header(rows[0])

    print_columns(
        "CSVW deklarētās kolonnas",
        declared_columns
    )

    print_columns(
        "CSV faktiskās kolonnas",
        actual_columns
    )

    print("\n6. Validēju CSV galveni...")

    validate_header(
        actual_columns,
        declared_columns,
        validation
    )

    print("\n7. Validēju CSV datu rindu struktūru...")

    validate_row_widths(
        rows,
        len(actual_columns),
        validation
    )

    validation.add_information(
        f"CSV datu rindu skaits bez galvenes: {max(len(rows) - 1, 0)}."
    )

    print_validation_result(validation)

    return 0 if validation.is_valid else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())

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
        print("\nValidācijas procesa kļūda:")
        print(error)
        raise SystemExit(1)

    except Exception as error:
        print("\nNezināma kļūda:")
        print(error)
        raise SystemExit(1)