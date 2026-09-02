"""
===============================================================================
04_4_verify_resource_update.py
===============================================================================

Mērķis
------
Pārbaudīt, vai pēc resource_patch publicētais CKAN resursa saturs
precīzi sakrīt ar lokālo CSV datni.

Programma:
1. nolasa lokālo CSV datni;
2. aprēķina tās SHA-256;
3. nolasa CKAN resursu ar resource_show;
4. lejupielādē publicēto resursa saturu;
5. aprēķina publicētās datnes SHA-256;
6. salīdzina datņu izmērus un SHA-256;
7. parāda verifikācijas rezultātu.

CKAN objekts
------------
Resurss

CKAN Action
-----------
resource_show

Drošības līmenis
----------------
Tikai lasa un salīdzina datus.
Neveic nekādas izmaiņas CKAN portālā.
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

TIMEOUT_SECONDS = 60
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


def get_resource(resource_id: str) -> dict:
    """
    Nolasa CKAN resursu ar resource_show.
    """

    response = get_response(
        RESOURCE_SHOW_URL,
        headers=API_HEADERS,
        params={"id": resource_id}
    )

    try:
        data = response.json()
    except requests.exceptions.JSONDecodeError as error:
        raise ValueError(
            "CKAN resource_show atbilde nav derīgs JSON."
        ) from error

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
            "sagaidītajam resursa ID."
        )

    return resource


def read_local_csv(csv_path: Path) -> bytes:
    """
    Nolasa lokālo CSV datni un pārbauda UTF-8 BOM.
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


# =============================================================================
# Rezultātu attēlošana
# =============================================================================

def print_verification_result(
    resource: dict,
    local_content: bytes,
    remote_content: bytes,
    local_hash: str,
    remote_hash: str
) -> bool:
    """
    Parāda verifikācijas rezultātu.

    Atgriež True, ja datnes ir identiskas.
    """

    same_size = len(local_content) == len(remote_content)
    same_hash = local_hash == remote_hash

    print("\n" + "=" * 80)
    print("RESOURCE_UPDATE VERIFIKĀCIJA")
    print("=" * 80)

    print("\nCKAN resurss")
    print("-" * 80)
    print(f"Nosaukums       : {resource.get('name')}")
    print(f"Resursa ID      : {resource.get('id')}")
    print(f"Formāts         : {resource.get('format')}")
    print(f"URL             : {resource.get('url')}")
    print(f"Mainīts         : {resource.get('last_modified')}")
    print(f"Metadati mainīti: {resource.get('metadata_modified')}")
    print(f"CKAN izmērs     : {resource.get('size')}")

    print("\nLokālā datne")
    print("-" * 80)
    print(f"Ceļš            : {LOCAL_CSV_PATH}")
    print(f"Izmērs          : {format_size(len(local_content))}")
    print(f"SHA-256         : {local_hash}")

    print("\nPublicētā datne")
    print("-" * 80)
    print(f"Izmērs          : {format_size(len(remote_content))}")
    print(f"SHA-256         : {remote_hash}")

    print("\nSalīdzinājums")
    print("-" * 80)

    if same_size:
        print("✅ Datņu izmēri sakrīt.")
    else:
        print("❌ Datņu izmēri atšķiras.")

    if same_hash:
        print("✅ SHA-256 kontrolsummas sakrīt.")
        print("✅ Datņu binārais saturs ir identisks.")
    else:
        print("❌ SHA-256 kontrolsummas atšķiras.")
        print("❌ Publicētā datne nav identiska lokālajai datnei.")

    print("\n" + "-" * 80)

    if same_size and same_hash:
        print("VERIFIKĀCIJAS REZULTĀTS: VEIKSMĪGS")
        print(
            "CKAN portālā publicētā datne precīzi sakrīt "
            "ar lokālo CSV datni."
        )
        return True

    print("VERIFIKĀCIJAS REZULTĀTS: NEVEIKSMĪGS")
    print(
        "Pirms turpmākām darbībām jāpārbauda "
        "publicētais resurss."
    )
    return False


# =============================================================================
# Galvenā programma
# =============================================================================

def main() -> int:
    print("1. Nolasu lokālo CSV datni...")

    local_content = read_local_csv(
        LOCAL_CSV_PATH
    )

    local_hash = calculate_sha256(
        local_content
    )

    print("✅ Lokālā CSV datne nolasīta.")
    print(f"✅ Izmērs: {format_size(len(local_content))}")
    print(f"✅ SHA-256: {local_hash}")

    print("\n2. Nolasu CKAN resursa informāciju...")

    resource = get_resource(
        RESOURCE_ID
    )

    resource_url = resource.get("url")

    if not resource_url:
        raise ValueError(
            "CKAN resursam nav norādīts satura URL."
        )

    print(f"✅ Atrasts resurss: {resource.get('name')}")
    print(f"✅ Resursa ID: {resource.get('id')}")
    print(f"✅ Mainīts: {resource.get('last_modified')}")

    print("\n3. Lejupielādēju publicēto resursa saturu...")

    remote_response = get_response(
        resource_url
    )

    remote_content = remote_response.content

    if not remote_content:
        raise ValueError(
            "No CKAN lejupielādētais resursa saturs ir tukšs."
        )

    remote_hash = calculate_sha256(
        remote_content
    )

    print("✅ Publicētais resursa saturs lejupielādēts.")

    verified = print_verification_result(
        resource=resource,
        local_content=local_content,
        remote_content=remote_content,
        local_hash=local_hash,
        remote_hash=remote_hash
    )

    return 0 if verified else 1


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
        print("\nVerifikācijas kļūda:")
        print(error)
        raise SystemExit(1)

    except Exception as error:
        print("\nNezināma kļūda:")
        print(error)
        raise SystemExit(1)