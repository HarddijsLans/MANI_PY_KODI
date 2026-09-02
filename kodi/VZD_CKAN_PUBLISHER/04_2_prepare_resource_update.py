"""
===============================================================================
04_2_prepare_resource_update.py
===============================================================================

Mērķis
------
Sagatavot CKAN resursa atjaunināšanu:

1. nolasīt un validēt lokālo CSV datni;
2. pārbaudīt UTF-8 BOM;
3. nolasīt CKAN resursu;
4. nolasīt CSVW metadatus;
5. pārbaudīt CSV galveni un rindu struktūru;
6. salīdzināt lokālo datni ar pašlaik publicēto datni;
7. parādīt publicēšanas plānu;
8. pieprasīt lietotāja apstiprinājumu.

Svarīgi
-------
Šis skripts NEIZPILDA resource_update.
Tas neko nemaina Latvijas Atvērto datu portālā.

CKAN objekts
------------
Resurss

CKAN Action
-----------
resource_show

Drošības līmenis
----------------
Tikai lasa, validē un sagatavo publicēšanu.
===============================================================================
"""

import csv
import hashlib
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

LOCAL_CSV_PATH = Path(
    r"C:\Users\hardijslans\Desktop\VISUAL STUDIO CODE"
    r"\ATSAVINAMAS ZEMES\Datnes_publicesanai"
    r"\parveidots_1_pielikums.csv"
)

RESOURCE_SHOW_URL = (
    f"{CKAN_BASE_URL}/api/3/action/resource_show"
)

NEXT_SCRIPT_NAME = "04_3_resource_update.py"

TIMEOUT_SECONDS = 60
UTF8_BOM = b"\xef\xbb\xbf"

API_HEADERS = {
    "Authorization": CKAN_API_TOKEN
}


# =============================================================================
# Vispārīgas palīgfunkcijas
# =============================================================================

def calculate_sha256(content: bytes) -> str:
    """
    Aprēķina datnes SHA-256 kontrolsummu.
    """

    return hashlib.sha256(content).hexdigest()


def format_size(size_bytes: int) -> str:
    """
    Attēlo datnes izmēru baitos un KiB.
    """

    size_kib = size_bytes / 1024

    return f"{size_bytes} baiti ({size_kib:.2f} KiB)"


def get_response(
    url: str,
    **kwargs: Any
) -> requests.Response:
    """
    Izpilda HTTP GET pieprasījumu.
    """

    response = requests.get(
        url,
        timeout=TIMEOUT_SECONDS,
        **kwargs
    )

    response.raise_for_status()

    return response


def get_json(
    url: str,
    **kwargs: Any
) -> dict:
    """
    Izpilda HTTP GET pieprasījumu un atgriež JSON.
    """

    response = get_response(
        url,
        **kwargs
    )

    try:
        data = response.json()
    except requests.exceptions.JSONDecodeError as error:
        raise ValueError(
            f"No adreses nav saņemts derīgs JSON:\n{url}"
        ) from error

    if not isinstance(data, dict):
        raise ValueError(
            f"No adreses saņemtais JSON nav objekts:\n{url}"
        )

    return data


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
            "CKAN resource_show atgrieza kļūdu:\n"
            + json.dumps(
                data,
                ensure_ascii=False,
                indent=4
            )
        )

    resource = data.get("result")

    if not isinstance(resource, dict):
        raise ValueError(
            "CKAN atbildē nav derīga result objekta."
        )

    returned_resource_id = resource.get("id")

    if returned_resource_id != resource_id:
        raise ValueError(
            "CKAN atgrieztais resursa ID neatbilst "
            "konfigurācijā norādītajam ID."
        )

    return resource


# =============================================================================
# Lokālās CSV datnes pārbaude
# =============================================================================

def read_local_csv(
    csv_path: Path
) -> tuple[bytes, str]:
    """
    Nolasa lokālo CSV datni.

    Atgriež:
    - datnes bināro saturu;
    - tekstu, dekodētu ar utf-8-sig.
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
        raise ValueError(
            "Lokālā CSV datne ir tukša."
        )

    if not content.startswith(UTF8_BOM):
        raise ValueError(
            "Lokālā CSV datne nesākas ar UTF-8 BOM "
            "(EF BB BF)."
        )

    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise ValueError(
            "Lokālo CSV datni nevar dekodēt kā UTF-8."
        ) from error

    return content, text


# =============================================================================
# CSVW metadatu apstrāde
# =============================================================================

def get_csvw_parameters(
    metadata: dict
) -> tuple[str, str, list[str]]:
    """
    No CSVW metadatiem nolasa:
    - delimiter;
    - quoteChar;
    - deklarētos kolonnu tehniskos nosaukumus.
    """

    dialect = metadata.get("dialect", {})

    if not isinstance(dialect, dict):
        dialect = {}

    delimiter = str(
        dialect.get("delimiter", ",")
    )

    quote_char = str(
        dialect.get("quoteChar", '"')
    )

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

    for index, column in enumerate(
        columns,
        start=1
    ):
        if not isinstance(column, dict):
            raise ValueError(
                f"{index}. CSVW kolonnas apraksts "
                "nav JSON objekts."
            )

        column_name = column.get("name")

        if not column_name:
            raise ValueError(
                f"{index}. CSVW kolonnai nav lauka name."
            )

        declared_columns.append(
            str(column_name).strip()
        )

    return delimiter, quote_char, declared_columns


# =============================================================================
# CSV struktūras validācija
# =============================================================================

def read_csv_rows(
    csv_text: str,
    delimiter: str,
    quote_char: str
) -> list[list[str]]:
    """
    Nolasa visas CSV rindas.
    """

    csv_stream = io.StringIO(
        csv_text,
        newline=""
    )

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
    Validē:
    - CSV galveni;
    - kolonnu secību;
    - katras rindas kolonnu skaitu.

    Atgriež:
    - faktiskos kolonnu nosaukumus;
    - datu rindu skaitu.
    """

    if not rows:
        raise ValueError(
            "CSV datne nesatur nevienu rindu."
        )

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

    expected_column_count = len(
        declared_columns
    )

    invalid_rows: list[tuple[int, int]] = []

    for row_number, row in enumerate(
        rows[1:],
        start=2
    ):
        if len(row) != expected_column_count:
            invalid_rows.append(
                (row_number, len(row))
            )

    if invalid_rows:
        details = "\n".join(
            (
                f"CSV {row_number}. rindā ir "
                f"{column_count} kolonnas; "
                f"sagaidītas {expected_column_count}."
            )
            for row_number, column_count
            in invalid_rows[:20]
        )

        additional_count = (
            len(invalid_rows) - 20
        )

        if additional_count > 0:
            details += (
                "\n"
                f"Vēl nav parādītas "
                f"{additional_count} kļūdainas rindas."
            )

        raise ValueError(
            "CSV datnē atrastas rindas ar nepareizu "
            f"kolonnu skaitu:\n{details}"
        )

    data_row_count = len(rows) - 1

    return actual_columns, data_row_count


# =============================================================================
# Sagatavošanas plāna attēlošana
# =============================================================================

def print_preparation_plan(
    resource: dict,
    local_content: bytes,
    remote_content: bytes,
    local_hash: str,
    remote_hash: str,
    columns: list[str],
    data_row_count: int
) -> None:
    """
    Parāda visu informāciju pirms lietotāja apstiprinājuma.
    """

    print("\n" + "=" * 80)
    print("RESURSA ATJAUNINĀŠANAS SAGATAVOŠANA")
    print("=" * 80)

    print("\nMērķa CKAN resurss")
    print("-" * 80)
    print(
        f"Nosaukums          : {resource.get('name')}"
    )
    print(
        f"Resursa ID         : {resource.get('id')}"
    )
    print(
        f"Formāts            : {resource.get('format')}"
    )
    print(
        f"Pašreizējais URL   : {resource.get('url')}"
    )
    print(
        f"Pašreiz mainīts    : "
        f"{resource.get('last_modified')}"
    )
    print(
        f"CKAN norādītais izmērs: "
        f"{resource.get('size')}"
    )

    print("\nLokālā datne")
    print("-" * 80)
    print(
        f"Ceļš               : {LOCAL_CSV_PATH}"
    )
    print(
        f"Datnes nosaukums   : {LOCAL_CSV_PATH.name}"
    )
    print(
        f"Izmērs             : "
        f"{format_size(len(local_content))}"
    )
    print(
        f"SHA-256            : {local_hash}"
    )
    print(
        "Kodējums           : UTF-8 ar BOM"
    )
    print(
        f"Kolonnu skaits     : {len(columns)}"
    )
    print(
        f"Datu rindu skaits  : {data_row_count}"
    )

    print("\nPašreiz publicētais saturs")
    print("-" * 80)
    print(
        f"Izmērs             : "
        f"{format_size(len(remote_content))}"
    )
    print(
        f"SHA-256            : {remote_hash}"
    )

    print("\nSalīdzinājums")
    print("-" * 80)

    if len(local_content) == len(remote_content):
        print("Datņu izmēri       : sakrīt")
    else:
        print("Datņu izmēri       : atšķiras")

    if local_hash == remote_hash:
        print("SHA-256            : sakrīt")
    else:
        print("SHA-256            : atšķiras")

    print("\nPlānotā darbība")
    print("-" * 80)
    print("HTTP metode        : POST")
    print("CKAN Action        : resource_update")
    print(
        f"Mērķa resursa ID   : {RESOURCE_ID}"
    )
    print(
        f"Augšupielādējamā datne: "
        f"{LOCAL_CSV_PATH.name}"
    )

    print("\n" + "=" * 80)


# =============================================================================
# Lietotāja apstiprinājums
# =============================================================================

def request_confirmation() -> bool:
    """
    Pieprasa nepārprotamu lietotāja apstiprinājumu.

    Tikai atbilde y vai yes tiek uzskatīta par apstiprinājumu.
    """

    print(
        "Vai sagatavot šo datni publicēšanai?"
    )
    answer = input(
        "Ievadiet y, lai apstiprinātu [y/N]: "
    )

    normalized_answer = answer.strip().lower()

    return normalized_answer in {
        "y",
        "yes"
    }


# =============================================================================
# Galvenā programma
# =============================================================================

def main() -> int:
    print("1. Nolasu un pārbaudu lokālo CSV datni...")

    local_content, csv_text = read_local_csv(
        LOCAL_CSV_PATH
    )

    local_hash = calculate_sha256(
        local_content
    )

    print("✅ Lokālā CSV datne atrasta.")
    print("✅ UTF-8 BOM atrasts.")
    print("✅ CSV datne dekodēta kā UTF-8.")

    print("\n2. Nolasu mērķa CKAN resursu...")

    resource = get_resource(
        RESOURCE_ID
    )

    resource_url = resource.get("url")
    conforms_to_url = resource.get(
        "conformsTo"
    )

    if not resource_url:
        raise ValueError(
            "Mērķa resursam nav norādīts satura URL."
        )

    if not conforms_to_url:
        raise ValueError(
            "Mērķa resursam nav aizpildīts "
            "lauks conformsTo."
        )

    print(
        f"✅ Atrasts resurss: {resource.get('name')}"
    )

    print("\n3. Nolasu CSVW metadatus...")

    metadata = get_json(
        conforms_to_url
    )

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

    actual_columns, data_row_count = (
        validate_csv_structure(
            rows,
            declared_columns
        )
    )

    print(
        "✅ CSV galvene atbilst CSVW metadatiem."
    )
    print(
        "✅ Visām rindām ir pareizs kolonnu skaits."
    )

    print(
        "\n5. Lejupielādēju pašreiz publicēto resursa saturu..."
    )

    remote_response = get_response(
        resource_url
    )

    remote_content = remote_response.content

    if not remote_content:
        raise ValueError(
            "Pašreiz publicētais resursa saturs ir tukšs."
        )

    remote_hash = calculate_sha256(
        remote_content
    )

    print(
        "✅ Pašreiz publicētais saturs lejupielādēts."
    )

    if local_hash == remote_hash:
        print("\n" + "=" * 80)
        print("PUBLICĒŠANA NAV NEPIECIEŠAMA")
        print("=" * 80)
        print(
            "Lokālās un publicētās datnes "
            "SHA-256 kontrolsummas sakrīt."
        )
        print(
            "Datņu binārais saturs ir identisks."
        )
        print(
            "Resurss NETIKA atjaunināts."
        )

        return 0

    print_preparation_plan(
        resource=resource,
        local_content=local_content,
        remote_content=remote_content,
        local_hash=local_hash,
        remote_hash=remote_hash,
        columns=actual_columns,
        data_row_count=data_row_count
    )

    confirmed = request_confirmation()

    print("\n" + "-" * 80)

    if not confirmed:
        print("PUBLICĒŠANA ATCELTA")
        print("Apstiprinājums netika saņemts.")
        print("Resurss NETIKA atjaunināts.")
        print("Datne NETIKA nosūtīta uz CKAN.")

        return 0

    print("APSTIPRINĀJUMS SAŅEMTS")
    print()
    print(
        "Šis sagatavošanas skripts neveic "
        "resource_update."
    )
    print(
        "Resurss vēl NAV atjaunināts."
    )
    print()
    print("Nākamais solis:")
    print(
        f"python {NEXT_SCRIPT_NAME}"
    )
    print("-" * 80)

    return 0


# =============================================================================
# Programmas starts un kļūdu apstrāde
# =============================================================================

if __name__ == "__main__":
    try:
        raise SystemExit(main())

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

    except (
        ValueError,
        RuntimeError,
        KeyError,
        json.JSONDecodeError
    ) as error:
        print("\nSagatavošanas kļūda:")
        print(error)
        raise SystemExit(1)

    except KeyboardInterrupt:
        print("\n\nDarbību pārtrauca lietotājs.")
        print("Resurss NETIKA atjaunināts.")
        raise SystemExit(130)

    except Exception as error:
        print("\nNezināma kļūda:")
        print(error)
        raise SystemExit(1)