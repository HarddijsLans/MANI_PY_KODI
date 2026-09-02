"""
===============================================================================
05_4_publish_publications.py
===============================================================================

Mērķis
------
Publicēt visus publications.json ierakstus, kuriem:

    "enabled": true

Svarīgs biznesa noteikums
-------------------------
Katras publicēšanas reizē tiek publicēti VISI ieslēgtie resursi.

SHA-256 salīdzinājums NAV kritērijs, pēc kura tiek pieņemts lēmums publicēt
vai nepublicēt.

Programma:
1. nolasa publications.json;
2. validē VISAS ieslēgtās lokālās CSV datnes;
3. pārbauda atbilstošos CKAN resursus;
4. pārbauda CSVW struktūru;
5. ja kaut viena datne nav derīga, publicēšana netiek sākta;
6. parāda publicēšanas plānu;
7. pieprasa vienu nepārprotamu apstiprinājumu;
8. secīgi publicē visus ieslēgtos resursus ar resource_patch;
9. parāda publicēšanas rezultātu.

CKAN objekts
------------
Resurss

CKAN Actions
------------
resource_show
resource_patch

HTTP metodes
------------
GET
POST

Drošības līmenis
----------------
RAKSTOŠA DARBĪBA.

Pēc apstiprinājuma PUBLICĒT skripts reāli aizstāj CKAN resursu CSV saturu.
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

PUBLICATIONS_FILE = (
    Path(__file__).parent / "publications.json"
)

RESOURCE_SHOW_URL = (
    f"{CKAN_BASE_URL}/api/3/action/resource_show"
)

RESOURCE_PATCH_URL = (
    f"{CKAN_BASE_URL}/api/3/action/resource_patch"
)

TIMEOUT_SECONDS = 120

UTF8_BOM = b"\xef\xbb\xbf"

API_HEADERS = {
    "Authorization": CKAN_API_TOKEN
}


# =============================================================================
# Palīgfunkcijas
# =============================================================================

def calculate_sha256(content: bytes) -> str:
    """
    Aprēķina SHA-256 kontrolsummu.
    """

    return hashlib.sha256(content).hexdigest()


def format_size(size_bytes: int) -> str:
    """
    Attēlo datnes izmēru baitos un KiB.
    """

    return (
        f"{size_bytes} baiti "
        f"({size_bytes / 1024:.2f} KiB)"
    )


# =============================================================================
# publications.json
# =============================================================================

def load_publications() -> list[dict]:
    """
    Nolasa publications.json.
    """

    if not PUBLICATIONS_FILE.exists():
        raise FileNotFoundError(
            f"Konfigurācijas fails nav atrasts:\n"
            f"{PUBLICATIONS_FILE}"
        )

    with PUBLICATIONS_FILE.open(
        "r",
        encoding="utf-8"
    ) as file:
        config = json.load(file)

    publications = config.get("publications")

    if not isinstance(publications, list):
        raise ValueError(
            "publications.json nesatur sarakstu 'publications'."
        )

    return publications


# =============================================================================
# HTTP
# =============================================================================

def get_response(
    url: str,
    **kwargs: Any
) -> requests.Response:
    """
    Izpilda HTTP GET.
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
    Izpilda HTTP GET un atgriež JSON.
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
            f"Saņemtais JSON nav objekts:\n{url}"
        )

    return data


# =============================================================================
# CKAN resurss
# =============================================================================

def get_resource(resource_id: str) -> dict:
    """
    Nolasa CKAN resursu ar resource_show.
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

    if resource.get("id") != resource_id:
        raise ValueError(
            "CKAN atgrieztais resursa ID neatbilst "
            "publications.json norādītajam ID."
        )

    return resource


# =============================================================================
# Lokālā CSV
# =============================================================================

def read_local_csv(
    file_path: Path
) -> tuple[bytes, str]:
    """
    Nolasa un pārbauda lokālo CSV.
    """

    if not file_path.exists():
        raise FileNotFoundError(
            f"CSV datne nav atrasta:\n{file_path}"
        )

    if not file_path.is_file():
        raise ValueError(
            f"Norādītais ceļš nav datne:\n{file_path}"
        )

    content = file_path.read_bytes()

    if not content:
        raise ValueError(
            f"CSV datne ir tukša:\n{file_path}"
        )

    if not content.startswith(UTF8_BOM):
        raise ValueError(
            f"CSV datnei nav UTF-8 BOM:\n{file_path}"
        )

    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise ValueError(
            f"CSV datni nevar dekodēt kā UTF-8:\n{file_path}"
        ) from error

    return content, text


# =============================================================================
# CSVW
# =============================================================================

def get_csvw_parameters(
    metadata: dict
) -> tuple[str, str, list[str]]:
    """
    Nolasa CSVW parametrus.
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
            f"Nederīgs delimiter: {delimiter!r}"
        )

    if len(quote_char) != 1:
        raise ValueError(
            f"Nederīgs quoteChar: {quote_char!r}"
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

    declared_columns = []

    for index, column in enumerate(
        columns,
        start=1
    ):
        if not isinstance(column, dict):
            raise ValueError(
                f"{index}. CSVW kolonnas apraksts nav objekts."
            )

        name = column.get("name")

        if not name:
            raise ValueError(
                f"{index}. CSVW kolonnai nav lauka name."
            )

        declared_columns.append(
            str(name).strip()
        )

    return (
        delimiter,
        quote_char,
        declared_columns
    )


# =============================================================================
# CSV validācija
# =============================================================================

def validate_csv_structure(
    csv_text: str,
    delimiter: str,
    quote_char: str,
    declared_columns: list[str]
) -> tuple[int, int]:
    """
    Validē CSV galveni un rindu struktūru.
    """

    stream = io.StringIO(
        csv_text,
        newline=""
    )

    reader = csv.reader(
        stream,
        delimiter=delimiter,
        quotechar=quote_char
    )

    rows = list(reader)

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
            f"CSVW:\n{declared_columns}\n\n"
            f"CSV:\n{actual_columns}"
        )

    expected_count = len(
        declared_columns
    )

    invalid_rows = []

    for row_number, row in enumerate(
        rows[1:],
        start=2
    ):
        if len(row) != expected_count:
            invalid_rows.append(
                (row_number, len(row))
            )

    if invalid_rows:
        details = "\n".join(
            (
                f"{row_number}. rindā ir "
                f"{column_count} kolonnas; "
                f"sagaidītas {expected_count}."
            )
            for row_number, column_count
            in invalid_rows[:20]
        )

        raise ValueError(
            "Atrastas rindas ar nepareizu "
            f"kolonnu skaitu:\n{details}"
        )

    return (
        expected_count,
        len(rows) - 1
    )


# =============================================================================
# Preflight — pārbaudām visu PIRMS pirmā POST
# =============================================================================

def prepare_publication(
    publication: dict,
    index: int
) -> dict:
    """
    Pilnībā validē vienu publikāciju.

    Šeit nekas netiek publicēts.
    """

    name = publication.get("name")
    resource_id = publication.get(
        "resource_id"
    )
    local_file_value = publication.get(
        "local_file"
    )

    if not resource_id:
        raise ValueError(
            f"{index}. publikācijai nav resource_id."
        )

    if not local_file_value:
        raise ValueError(
            f"{index}. publikācijai nav local_file."
        )

    local_file = Path(
        local_file_value
    )

    print("\n" + "=" * 80)
    print(f"{index}. RESURSA SAGATAVOŠANA")
    print("=" * 80)

    print(f"Nosaukums  : {name}")
    print(f"Resursa ID : {resource_id}")
    print(f"Datne      : {local_file}")

    print("\n1. Validēju lokālo CSV...")

    content, csv_text = read_local_csv(
        local_file
    )

    print("✅ CSV datne atrasta.")
    print("✅ UTF-8 BOM atrasts.")
    print("✅ UTF-8 dekodēšana veiksmīga.")

    print("\n2. Nolasu CKAN resursu...")

    resource = get_resource(
        resource_id
    )

    print(
        f"✅ Atrasts CKAN resurss: "
        f"{resource.get('name')}"
    )

    conforms_to_url = resource.get(
        "conformsTo"
    )

    if not conforms_to_url:
        raise ValueError(
            "Resursam nav conformsTo."
        )

    print("\n3. Nolasu CSVW metadatus...")

    metadata = get_json(
        conforms_to_url
    )

    (
        delimiter,
        quote_char,
        declared_columns
    ) = get_csvw_parameters(
        metadata
    )

    print("✅ CSVW metadati nolasīti.")

    print("\n4. Validēju CSV struktūru...")

    (
        column_count,
        row_count
    ) = validate_csv_structure(
        csv_text,
        delimiter,
        quote_char,
        declared_columns
    )

    sha256 = calculate_sha256(
        content
    )

    print("✅ CSV galvene atbilst.")
    print("✅ Kolonnu secība atbilst.")
    print("✅ Visu rindu struktūra atbilst.")
    print(f"✅ Kolonnas   : {column_count}")
    print(f"✅ Datu rindas: {row_count}")
    print(f"✅ Izmērs     : {format_size(len(content))}")
    print(f"✅ SHA-256    : {sha256}")

    return {
        "index": index,
        "name": name,
        "resource_id": resource_id,
        "local_file": local_file,
        "file_size": len(content),
        "sha256": sha256,
        "column_count": column_count,
        "row_count": row_count,
        "resource": resource
    }


# =============================================================================
# Apstiprinājums
# =============================================================================

def request_confirmation(
    prepared: list[dict]
) -> bool:
    """
    Parāda visu publicēšanas plānu un prasa vienu apstiprinājumu.
    """

    print("\n" + "=" * 80)
    print("PUBLICĒŠANAS PLĀNS")
    print("=" * 80)

    print(
        f"\nTiks publicēti resursi: {len(prepared)}"
    )

    for item in prepared:
        print("\n" + "-" * 80)
        print(
            f"{item['index']}. {item['name']}"
        )
        print(
            f"Resursa ID : {item['resource_id']}"
        )
        print(
            f"Datne      : {item['local_file'].name}"
        )
        print(
            f"Izmērs     : {format_size(item['file_size'])}"
        )
        print(
            f"SHA-256    : {item['sha256']}"
        )

    print("\n" + "=" * 80)
    print("UZMANĪBU — RAKSTOŠA CKAN DARBĪBA")
    print("=" * 80)

    print(
        "\nVisi iepriekš uzskaitītie resursi tiks atjaunināti."
    )

    print(
        "Lai turpinātu, precīzi ievadiet:"
    )

    print("\nPUBLICĒT")

    answer = input(
        "\nApstiprinājums: "
    )

    return (
        answer.strip()
        == "PUBLICĒT"
    )


# =============================================================================
# resource_patch
# =============================================================================

def publish_resource(
    item: dict
) -> dict:
    """
    Publicē vienu CSV ar CKAN resource_patch.
    """

    resource_id = item[
        "resource_id"
    ]

    local_file = item[
        "local_file"
    ]

    form_data = {
        "id": resource_id
    }

    with local_file.open(
        "rb"
    ) as csv_file:

        files = {
            "upload": (
                local_file.name,
                csv_file,
                "text/csv"
            )
        }

        response = requests.post(
            RESOURCE_PATCH_URL,
            headers=API_HEADERS,
            data=form_data,
            files=files,
            timeout=TIMEOUT_SECONDS
        )

    print(
        f"HTTP statuss: "
        f"{response.status_code}"
    )

    response.raise_for_status()

    try:
        data = response.json()
    except requests.exceptions.JSONDecodeError as error:
        raise ValueError(
            "CKAN atbilde nav derīgs JSON."
        ) from error

    if not data.get("success"):
        raise RuntimeError(
            "CKAN resource_patch atgrieza kļūdu:\n"
            + json.dumps(
                data.get("error", data),
                ensure_ascii=False,
                indent=4
            )
        )

    result = data.get("result")

    if not isinstance(result, dict):
        raise ValueError(
            "CKAN atbildē nav result objekta."
        )

    if result.get("id") != resource_id:
        raise RuntimeError(
            "Atjauninātā resursa ID neatbilst "
            "sagaidītajam ID."
        )

    return result


# =============================================================================
# Galvenā programma
# =============================================================================

def main() -> int:

    publications = load_publications()

    enabled_publications = [
        publication
        for publication in publications
        if publication.get(
            "enabled",
            False
        )
    ]

    print(
        f"Konfigurēti resursi : "
        f"{len(publications)}"
    )

    print(
        f"Publicēšanai ieslēgti: "
        f"{len(enabled_publications)}"
    )

    if not enabled_publications:
        print(
            "\nNav neviena enabled=true resursa."
        )
        return 0

    # =========================================================================
    # PRE-FLIGHT
    # =========================================================================

    print("\n" + "#" * 80)
    print("1. POSMS — PIRMSPUBLICĒŠANAS VALIDĀCIJA")
    print("#" * 80)

    prepared = []

    for index, publication in enumerate(
        publications,
        start=1
    ):
        if not publication.get(
            "enabled",
            False
        ):
            continue

        item = prepare_publication(
            publication,
            index
        )

        prepared.append(
            item
        )

    print("\n" + "=" * 80)
    print("VISU RESURSU VALIDĀCIJA VEIKSMĪGA")
    print("=" * 80)

    print(
        "Neviena datne vēl NAV nosūtīta uz CKAN."
    )

    # =========================================================================
    # APSTIPRINĀJUMS
    # =========================================================================

    if not request_confirmation(
        prepared
    ):
        print("\nPUBLICĒŠANA ATCELTA")
        print(
            "Pareizs apstiprinājums netika ievadīts."
        )
        print(
            "Neviens resurss netika mainīts."
        )
        return 0

    # =========================================================================
    # PUBLICĒŠANA
    # =========================================================================

    print("\n" + "#" * 80)
    print("2. POSMS — RESURSU PUBLICĒŠANA")
    print("#" * 80)

    success_count = 0
    failed_count = 0

    results = []

    for item in prepared:

        print("\n" + "=" * 80)
        print(
            f"PUBLICĒJU: "
            f"{item['name']}"
        )
        print("=" * 80)

        try:

            result = publish_resource(
                item
            )

            success_count += 1

            results.append({
                "name": item["name"],
                "resource_id": item["resource_id"],
                "status": "VEIKSMĪGS",
                "last_modified": result.get(
                    "last_modified"
                ),
                "size": result.get(
                    "size"
                )
            })

            print(
                "✅ RESOURCE_PATCH IZDEVĀS"
            )

            print(
                f"Resursa ID : "
                f"{result.get('id')}"
            )

            print(
                f"Izmērs     : "
                f"{result.get('size')}"
            )

            print(
                f"Mainīts    : "
                f"{result.get('last_modified')}"
            )

        except Exception as error:

            failed_count += 1

            results.append({
                "name": item["name"],
                "resource_id": item["resource_id"],
                "status": "NEVEIKSMĪGS",
                "error": str(error)
            })

            print(
                "❌ PUBLICĒŠANA NEIZDEVĀS"
            )

            print(error)

    # =========================================================================
    # KOPSAVILKUMS
    # =========================================================================

    print("\n" + "=" * 80)
    print("PUBLICĒŠANAS KOPSAVILKUMS")
    print("=" * 80)

    for result in results:

        print("\n" + "-" * 80)

        print(
            f"Nosaukums  : "
            f"{result['name']}"
        )

        print(
            f"Resursa ID : "
            f"{result['resource_id']}"
        )

        print(
            f"Rezultāts  : "
            f"{result['status']}"
        )

        if result[
            "status"
        ] == "VEIKSMĪGS":

            print(
                f"Izmērs     : "
                f"{result.get('size')}"
            )

            print(
                f"Mainīts    : "
                f"{result.get('last_modified')}"
            )

        else:

            print(
                f"Kļūda      : "
                f"{result.get('error')}"
            )

    print("\n" + "=" * 80)

    print(
        f"Veiksmīgi publicēti : "
        f"{success_count}"
    )

    print(
        f"Neveiksmīgi         : "
        f"{failed_count}"
    )

    if failed_count == 0:

        print(
            "\nKOPĒJAIS REZULTĀTS: VEIKSMĪGS"
        )

        print(
            "Visi ieslēgtie resursi ir publicēti."
        )

        print(
            "\nNākamais solis:"
        )

        print(
            "05_5_verify_publications.py"
        )

        return 0

    print(
        "\nKOPĒJAIS REZULTĀTS: DAĻĒJI NEVEIKSMĪGS"
    )

    print(
        "Jāpārbauda katra resursa rezultāts atsevišķi."
    )

    return 1


# =============================================================================
# Programmas starts
# =============================================================================

if __name__ == "__main__":
    try:

        raise SystemExit(
            main()
        )

    except (
        FileNotFoundError,
        ValueError,
        RuntimeError,
        KeyError,
        json.JSONDecodeError
    ) as error:

        print(
            "\nPUBLICĒŠANAS SAGATAVOŠANAS KĻŪDA:"
        )

        print(error)

        print(
            "\nPublicēšana netika sākta."
        )

        raise SystemExit(1)

    except requests.exceptions.Timeout:

        print(
            "\nHTTP pieprasījuma taimauts."
        )

        print(
            "Pirms atkārtotas palaišanas "
            "pārbaudiet resursus portālā."
        )

        raise SystemExit(1)

    except requests.exceptions.RequestException as error:

        print(
            "\nHTTP pieprasījuma kļūda:"
        )

        print(error)

        raise SystemExit(1)

    except KeyboardInterrupt:

        print(
            "\n\nDarbību pārtrauca lietotājs."
        )

        print(
            "Ja pārtraukšana notika publicēšanas laikā, "
            "pārbaudiet abu resursu stāvokli portālā."
        )

        raise SystemExit(130)

    except Exception as error:

        print(
            "\nNezināma kļūda:"
        )

        print(error)

        raise SystemExit(1)