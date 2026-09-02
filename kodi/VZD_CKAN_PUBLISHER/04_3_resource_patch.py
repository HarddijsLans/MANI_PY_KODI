"""
===============================================================================
04_3_resource_patch.py
===============================================================================

Mērķis
------
Augšupielādēt jaunu CSV datnes versiju esošam CKAN resursam.

Programma:
1. pārbauda lokālo CSV datni;
2. pārbauda UTF-8 BOM;
3. nolasa mērķa CKAN resursu;
4. salīdzina lokālo un pašreiz publicēto datni ar SHA-256;
5. pieprasa nepārprotamu lietotāja apstiprinājumu;
6. izpilda CKAN resource_patch ar multipart/form-data;
7. pārbauda CKAN atbildes success lauku;
8. parāda atjauninātā resursa pamatinformāciju.

CKAN objekts
------------
Resurss

CKAN Action
-----------
resource_patch

HTTP metode
-----------
POST

Rakstošā darbība
----------------
JĀ — skripts reāli aizstāj esošā resursa datnes saturu.

Svarīgi
-------
Resursa ID paliek nemainīgs.
Tiek mainīts tikai resursa augšupielādētais saturs.
===============================================================================
"""

import hashlib
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
    """Aprēķina SHA-256 kontrolsummu."""

    return hashlib.sha256(content).hexdigest()


def format_size(size_bytes: int) -> str:
    """Attēlo datnes izmēru baitos un KiB."""

    return (
        f"{size_bytes} baiti "
        f"({size_bytes / 1024:.2f} KiB)"
    )


def get_response(
    url: str,
    **kwargs: Any
) -> requests.Response:
    """Izpilda HTTP GET pieprasījumu."""

    response = requests.get(
        url,
        timeout=TIMEOUT_SECONDS,
        **kwargs
    )

    response.raise_for_status()
    return response


def get_resource(resource_id: str) -> dict:
    """Nolasa vienu CKAN resursu ar resource_show."""

    response = get_response(
        RESOURCE_SHOW_URL,
        headers=API_HEADERS,
        params={"id": resource_id}
    )

    data = response.json()

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
            "konfigurācijā norādītajam ID."
        )

    return resource


def read_local_csv(csv_path: Path) -> bytes:
    """
    Nolasa lokālo CSV datni un pārbauda:
    - vai tā eksistē;
    - vai nav tukša;
    - vai sākas ar UTF-8 BOM;
    - vai ir derīgs UTF-8 saturs.
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
        content.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise ValueError(
            "Lokālo CSV datni nevar dekodēt kā UTF-8."
        ) from error

    return content


def request_confirmation(
    resource: dict,
    local_hash: str,
    remote_hash: str,
    local_size: int,
    remote_size: int
) -> bool:
    """
    Pieprasa nepārprotamu apstiprinājumu.

    Drošības nolūkā jāievada pilns vārds PUBLICĒT.
    """

    print("\n" + "=" * 80)
    print("UZMANĪBU — RAKSTOŠA CKAN DARBĪBA")
    print("=" * 80)

    print("\nTiks aizstāts šī resursa saturs:")
    print("-" * 80)
    print(f"Nosaukums     : {resource.get('name')}")
    print(f"Resursa ID    : {resource.get('id')}")
    print(f"Formāts       : {resource.get('format')}")
    print(f"Pašreiz URL   : {resource.get('url')}")

    print("\nLokālā datne:")
    print("-" * 80)
    print(f"Ceļš          : {LOCAL_CSV_PATH}")
    print(f"Izmērs        : {format_size(local_size)}")
    print(f"SHA-256       : {local_hash}")

    print("\nPašreiz publicētā datne:")
    print("-" * 80)
    print(f"Izmērs        : {format_size(remote_size)}")
    print(f"SHA-256       : {remote_hash}")

    print("\nŠī darbība reāli mainīs resursa saturu portālā.")
    print("Lai turpinātu, precīzi ievadiet: PUBLICĒT")

    answer = input("\nApstiprinājums: ")

    return answer.strip() == "PUBLICĒT"


def upload_resource(
    resource_id: str,
    csv_path: Path
) -> dict:
    """
    Izpilda CKAN resource_patch.

    requests automātiski izveido multipart/form-data Content-Type
    un nepieciešamo boundary.
    """

    form_data = {
        "id": resource_id
    }

    with csv_path.open("rb") as csv_file:
        files = {
            "upload": (
                csv_path.name,
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

    print(f"\nHTTP statuss: {response.status_code}")

    response.raise_for_status()

    try:
        data = response.json()
    except requests.exceptions.JSONDecodeError as error:
        raise ValueError(
            "CKAN atbilde nav derīgs JSON."
        ) from error

    # CKAN var atgriezt HTTP 200 arī tad, ja Action API darbība
    # nav izdevusies, tāpēc obligāti jāpārbauda success.
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
            "CKAN atbildē nav derīga result objekta."
        )

    return result


# =============================================================================
# Galvenā programma
# =============================================================================

def main() -> int:
    print("1. Pārbaudu lokālo CSV datni...")

    local_content = read_local_csv(
        LOCAL_CSV_PATH
    )

    local_hash = calculate_sha256(
        local_content
    )

    print("✅ Lokālā CSV datne atrasta.")
    print("✅ UTF-8 BOM atrasts.")
    print("✅ CSV datne ir derīgs UTF-8 saturs.")
    print(f"✅ Izmērs: {format_size(len(local_content))}")
    print(f"✅ SHA-256: {local_hash}")

    print("\n2. Nolasu mērķa CKAN resursu...")

    resource_before = get_resource(
        RESOURCE_ID
    )

    resource_url = resource_before.get("url")

    if not resource_url:
        raise ValueError(
            "Mērķa resursam nav norādīts satura URL."
        )

    print(f"✅ Atrasts resurss: {resource_before.get('name')}")
    print(f"✅ Resursa ID: {resource_before.get('id')}")

    print("\n3. Lejupielādēju pašreiz publicēto saturu...")

    remote_response = get_response(
        resource_url
    )

    remote_content = remote_response.content

    if not remote_content:
        raise ValueError(
            "Pašreiz publicētā resursa saturs ir tukšs."
        )

    remote_hash = calculate_sha256(
        remote_content
    )

    print(
        f"✅ Pašreizējais izmērs: "
        f"{format_size(len(remote_content))}"
    )
    print(f"✅ Pašreizējais SHA-256: {remote_hash}")

    if local_hash == remote_hash:
        print("\n" + "=" * 80)
        print("PUBLICĒŠANA NAV NEPIECIEŠAMA")
        print("=" * 80)
        print(
            "Lokālā un pašreiz publicētā datne ir identiskas."
        )
        print("Resurss netika mainīts.")

        return 0

    print("\n4. Datnes atšķiras — nepieciešams apstiprinājums.")

    confirmed = request_confirmation(
        resource=resource_before,
        local_hash=local_hash,
        remote_hash=remote_hash,
        local_size=len(local_content),
        remote_size=len(remote_content)
    )

    if not confirmed:
        print("\nPUBLICĒŠANA ATCELTA")
        print("Pareizs apstiprinājums netika ievadīts.")
        print("Resurss netika mainīts.")

        return 0

    print("\n5. Izpildu CKAN resource_patch...")
    print("Datne tiek nosūtīta uz Latvijas Atvērto datu portālu.")

    updated_resource = upload_resource(
        resource_id=RESOURCE_ID,
        csv_path=LOCAL_CSV_PATH
    )

    print("\n" + "=" * 80)
    print("CKAN RESOURCE_PATCH IZDEVĀS")
    print("=" * 80)

    print(f"Nosaukums     : {updated_resource.get('name')}")
    print(f"Resursa ID    : {updated_resource.get('id')}")
    print(f"Formāts       : {updated_resource.get('format')}")
    print(f"URL           : {updated_resource.get('url')}")
    print(f"Izmērs        : {updated_resource.get('size')}")
    print(f"Mainīts       : {updated_resource.get('last_modified')}")
    print(f"Metadati mainīti: {updated_resource.get('metadata_modified')}")

    if updated_resource.get("id") != RESOURCE_ID:
        raise RuntimeError(
            "Atjauninātā resursa ID neatbilst sagaidītajam ID."
        )

    print("\nResursa saturs ir atjaunināts.")
    print(
        "Nākamais solis: palaist "
        "04_4_verify_resource_update.py"
    )

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
        print(
            "Nav droši zināms, vai serveris pabeidza darbību. "
            "Pirms atkārtošanas pārbaudiet resursu portālā."
        )
        raise SystemExit(1)

    except requests.exceptions.ConnectionError as error:
        print("\nSavienojuma kļūda:")
        print(error)
        print(
            "Pirms atkārtotas palaišanas pārbaudiet, "
            "vai resurss tomēr netika atjaunināts."
        )
        raise SystemExit(1)

    except requests.exceptions.HTTPError as error:
        print("\nHTTP kļūda:")
        print(error)

        if error.response is not None:
            print("\nServera atbilde:")
            print(error.response.text[:2000])

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
        print("\nResource patch kļūda:")
        print(error)
        raise SystemExit(1)

    except KeyboardInterrupt:
        print("\n\nDarbību pārtrauca lietotājs.")
        print(
            "Ja pārtraukšana notika datnes augšupielādes laikā, "
            "pārbaudiet resursu portālā."
        )
        raise SystemExit(130)

    except Exception as error:
        print("\nNezināma kļūda:")
        print(error)
        raise SystemExit(1)