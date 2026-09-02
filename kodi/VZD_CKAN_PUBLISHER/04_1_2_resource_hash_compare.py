"""
===============================================================================
04_1_2_resource_hash_compare.py
===============================================================================

Mērķis
------
1. Nolasīt lokālo CSV datni.
2. Nolasīt pašreizējo CKAN resursu.
3. Lejupielādēt pašreiz publicēto resursa saturu.
4. Aprēķināt abu datņu SHA-256 kontrolsummas.
5. Salīdzināt datņu izmēru un saturu.

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

RESOURCE_SHOW_URL = f"{CKAN_BASE_URL}/api/3/action/resource_show"

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
    Aprēķina SHA-256 kontrolsummu datnes baitiem.
    """

    return hashlib.sha256(content).hexdigest()


def format_size(size_bytes: int) -> str:
    """
    Attēlo datnes izmēru baitos un KiB.
    """

    size_kib = size_bytes / 1024

    return f"{size_bytes} baiti ({size_kib:.2f} KiB)"


def get_response(url: str, **kwargs: Any) -> requests.Response:
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
    Nolasa vienu CKAN resursu ar resource_show.
    """

    response = get_response(
        RESOURCE_SHOW_URL,
        headers=API_HEADERS,
        params={"id": resource_id}
    )

    data = response.json()

    if not data.get("success"):
        raise RuntimeError(
            "CKAN resource_show atgrieza kļūdu:\n"
            + json.dumps(data, ensure_ascii=False, indent=4)
        )

    resource = data.get("result")

    if not isinstance(resource, dict):
        raise ValueError(
            "CKAN atbildē nav derīga result objekta."
        )

    return resource


def read_local_file(file_path: Path) -> bytes:
    """
    Nolasa lokālo datni un pārbauda tās pamatīpašības.
    """

    if not file_path.exists():
        raise FileNotFoundError(
            f"Lokālā datne nav atrasta:\n{file_path}"
        )

    if not file_path.is_file():
        raise ValueError(
            f"Norādītais ceļš nav datne:\n{file_path}"
        )

    content = file_path.read_bytes()

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
            "Lokālo CSV datni nevar korekti dekodēt kā UTF-8."
        ) from error

    return content


# =============================================================================
# Rezultātu attēlošana
# =============================================================================

def print_file_information(
    title: str,
    file_name: str,
    content: bytes,
    sha256: str
) -> None:
    """
    Izdrukā datnes pamatinformāciju.
    """

    print(f"\n{title}")
    print("-" * 80)
    print(f"Datnes nosaukums : {file_name}")
    print(f"Izmērs           : {format_size(len(content))}")
    print(f"SHA-256          : {sha256}")


def print_comparison(
    local_content: bytes,
    remote_content: bytes,
    local_hash: str,
    remote_hash: str
) -> None:
    """
    Izdrukā lokālās un publicētās datnes salīdzinājumu.
    """

    same_size = len(local_content) == len(remote_content)
    same_hash = local_hash == remote_hash

    print("\n" + "=" * 80)
    print("SALĪDZINĀŠANAS REZULTĀTS")
    print("=" * 80)

    if same_size:
        print("✅ Datņu izmēri sakrīt.")
    else:
        print("ℹ️ Datņu izmēri atšķiras.")
        print(f"   Lokālā datne  : {len(local_content)} baiti")
        print(f"   CKAN resurss  : {len(remote_content)} baiti")

    if same_hash:
        print("✅ SHA-256 kontrolsummas sakrīt.")
        print("✅ Datņu binārais saturs ir identisks.")
    else:
        print("ℹ️ SHA-256 kontrolsummas atšķiras.")
        print("ℹ️ Lokālā datne atšķiras no pašlaik publicētās datnes.")

    print("\n" + "-" * 80)

    if same_hash:
        print("SECINĀJUMS: resource_update nav nepieciešams.")
        print("Portālā jau ir publicēts identisks resursa saturs.")
    else:
        print("SECINĀJUMS: lokālajā datnē ir izmaiņas.")
        print("Datni var sagatavot resource_update darbībai.")

    print("-" * 80)


# =============================================================================
# Galvenā programma
# =============================================================================

def main() -> None:
    print("1. Nolasu lokālo CSV datni...")

    local_content = read_local_file(
        LOCAL_CSV_PATH
    )

    local_hash = calculate_sha256(
        local_content
    )

    print("✅ Lokālā CSV datne nolasīta.")
    print("✅ UTF-8 BOM pārbaude veiksmīga.")

    print("\n2. Nolasu CKAN resursa informāciju...")

    resource = get_resource(
        RESOURCE_ID
    )

    resource_url = resource.get("url")

    if not resource_url:
        raise ValueError(
            "CKAN resursam nav norādīts satura URL."
        )

    print("✅ CKAN resurss atrasts.")
    print(f"Nosaukums      : {resource.get('name')}")
    print(f"Resursa ID     : {resource.get('id')}")
    print(f"Formāts        : {resource.get('format')}")
    print(f"Mainīts        : {resource.get('last_modified')}")
    print(f"CKAN izmērs    : {resource.get('size')}")
    print(f"Resursa URL    : {resource_url}")

    print("\n3. Lejupielādēju pašreiz publicēto resursa saturu...")

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

    print("✅ Pašreiz publicētais resursa saturs lejupielādēts.")

    print_file_information(
        title="Lokālā CSV datne",
        file_name=LOCAL_CSV_PATH.name,
        content=local_content,
        sha256=local_hash
    )

    remote_file_name = (
        resource_url
        .split("?")[0]
        .rstrip("/")
        .split("/")[-1]
    )

    print_file_information(
        title="Pašreiz publicētais CKAN resurss",
        file_name=remote_file_name,
        content=remote_content,
        sha256=remote_hash
    )

    print_comparison(
        local_content=local_content,
        remote_content=remote_content,
        local_hash=local_hash,
        remote_hash=remote_hash
    )

    print("\nDrošības informācija")
    print("-" * 80)
    print("Resurss NETIKA atjaunināts.")
    print("Lokālā datne NETIKA nosūtīta uz CKAN.")


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

    except (
        ValueError,
        RuntimeError,
        KeyError,
        json.JSONDecodeError
    ) as error:
        print("\nPārbaudes kļūda:")
        print(error)
        raise SystemExit(1)

    except Exception as error:
        print("\nNezināma kļūda:")
        print(error)
        raise SystemExit(1)