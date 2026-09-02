"""
===============================================================================
05_3_compare_publications.py
===============================================================================

Mērķis
------
Nolasīt publications.json un visām ieslēgtajām publikācijām:

1. nolasīt lokālo CSV datni;
2. aprēķināt lokālās datnes SHA-256;
3. nolasīt CKAN resursu ar resource_show;
4. lejupielādēt pašreiz publicēto resursa saturu;
5. aprēķināt publicētās datnes SHA-256;
6. salīdzināt datņu izmērus un SHA-256;
7. noteikt, vai publicēšana ir nepieciešama.

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

PUBLICATIONS_FILE = (
    Path(__file__).parent / "publications.json"
)

RESOURCE_SHOW_URL = (
    f"{CKAN_BASE_URL}/api/3/action/resource_show"
)

TIMEOUT_SECONDS = 60

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
    Nolasa vienu CKAN resursu ar resource_show.
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
            "publications.json norādītajam ID."
        )

    return resource


def read_local_file(
    file_path: Path
) -> bytes:
    """
    Nolasa lokālo datni.
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
            f"Lokālā datne ir tukša:\n{file_path}"
        )

    return content


# =============================================================================
# Vienas publikācijas salīdzināšana
# =============================================================================

def compare_publication(
    publication: dict,
    index: int
) -> bool:
    """
    Salīdzina vienu lokālo datni ar CKAN publicēto resursu.

    Atgriež:
    True  -> datnes atšķiras, publicēšana nepieciešama
    False -> datnes identiskas
    """

    name = publication.get("name")
    resource_id = publication.get("resource_id")
    local_file_value = publication.get("local_file")

    print("\n" + "=" * 80)
    print(f"{index}. PUBLIKĀCIJA")
    print("=" * 80)

    print(f"Nosaukums  : {name}")
    print(f"Resursa ID : {resource_id}")
    print(f"Datne      : {local_file_value}")

    if not resource_id:
        raise ValueError(
            "Nav norādīts resource_id."
        )

    if not local_file_value:
        raise ValueError(
            "Nav norādīts local_file."
        )

    local_file = Path(local_file_value)

    # -------------------------------------------------------------------------
    # Lokālā datne
    # -------------------------------------------------------------------------

    print("\n1. Nolasu lokālo datni...")

    local_content = read_local_file(
        local_file
    )

    local_hash = calculate_sha256(
        local_content
    )

    print("✅ Lokālā datne nolasīta.")
    print(
        f"   Izmērs  : "
        f"{format_size(len(local_content))}"
    )
    print(
        f"   SHA-256 : {local_hash}"
    )

    # -------------------------------------------------------------------------
    # CKAN resurss
    # -------------------------------------------------------------------------

    print("\n2. Nolasu CKAN resursu...")

    resource = get_resource(
        resource_id
    )

    resource_url = resource.get("url")

    if not resource_url:
        raise ValueError(
            "CKAN resursam nav norādīts satura URL."
        )

    print(
        f"✅ CKAN resurss atrasts: "
        f"{resource.get('name')}"
    )
    print(
        f"   Mainīts : "
        f"{resource.get('last_modified')}"
    )
    print(
        f"   CKAN size: "
        f"{resource.get('size')}"
    )

    # -------------------------------------------------------------------------
    # Publicētā datne
    # -------------------------------------------------------------------------

    print(
        "\n3. Lejupielādēju pašreiz publicēto resursa saturu..."
    )

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

    print(
        "✅ Pašreiz publicētais resursa saturs lejupielādēts."
    )
    print(
        f"   Izmērs  : "
        f"{format_size(len(remote_content))}"
    )
    print(
        f"   SHA-256 : {remote_hash}"
    )

    # -------------------------------------------------------------------------
    # Salīdzinājums
    # -------------------------------------------------------------------------

    same_size = (
        len(local_content)
        == len(remote_content)
    )

    same_hash = (
        local_hash
        == remote_hash
    )

    print("\n4. Salīdzinu datnes...")
    print("-" * 80)

    if same_size:
        print("✅ Datņu izmēri sakrīt.")
    else:
        print("ℹ️ Datņu izmēri atšķiras.")

    if same_hash:
        print("✅ SHA-256 kontrolsummas sakrīt.")
    else:
        print("ℹ️ SHA-256 kontrolsummas atšķiras.")

    print("\nRezultāts")
    print("-" * 80)

    if same_hash:
        print(
            "IDENTISKS — publicēšana nav nepieciešama."
        )
        return False

    print(
        "ATŠĶIRAS — publicēšana ir nepieciešama."
    )
    return True


# =============================================================================
# Galvenā programma
# =============================================================================

def main() -> int:
    publications = load_publications()

    print(
        f"Atrasti konfigurētie resursi: "
        f"{len(publications)}"
    )

    total_enabled = 0
    total_changed = 0
    total_identical = 0
    total_failed = 0
    total_skipped = 0

    for index, publication in enumerate(
        publications,
        start=1
    ):
        enabled = publication.get(
            "enabled",
            False
        )

        if not enabled:
            total_skipped += 1

            print("\n" + "=" * 80)
            print(f"{index}. PUBLIKĀCIJA")
            print("=" * 80)

            print(
                f"Nosaukums: "
                f"{publication.get('name')}"
            )
            print(
                "⏭️ Izlaista — enabled = false."
            )

            continue

        total_enabled += 1

        try:
            changed = compare_publication(
                publication,
                index
            )

            if changed:
                total_changed += 1
            else:
                total_identical += 1

        except Exception as error:
            total_failed += 1

            print("\n❌ SALĪDZINĀŠANAS KĻŪDA")
            print(error)

    print("\n" + "=" * 80)
    print("KOPĒJAIS SALĪDZINĀŠANAS REZULTĀTS")
    print("=" * 80)

    print(
        f"Konfigurēti resursi : "
        f"{len(publications)}"
    )
    print(
        f"Ieslēgti            : "
        f"{total_enabled}"
    )
    print(
        f"Atšķiras            : "
        f"{total_changed}"
    )
    print(
        f"Identiski           : "
        f"{total_identical}"
    )
    print(
        f"Kļūdas              : "
        f"{total_failed}"
    )
    print(
        f"Izlaisti             : "
        f"{total_skipped}"
    )

    print("\n" + "-" * 80)

    if total_failed > 0:
        print(
            "KOPĒJAIS REZULTĀTS: NEVEIKSMĪGS"
        )
        print(
            "Vismaz vienam resursam salīdzināšana neizdevās."
        )

        return 1

    if total_changed == 0:
        print(
            "KOPĒJAIS REZULTĀTS: IZMAIŅU NAV"
        )
        print(
            "Nevienam resursam publicēšana nav nepieciešama."
        )

        return 0

    print(
        "KOPĒJAIS REZULTĀTS: ATRASTAS IZMAIŅAS"
    )
    print(
        f"Publicēšana nepieciešama "
        f"{total_changed} resursam(-iem)."
    )

    return 0


# =============================================================================
# Programmas starts
# =============================================================================

if __name__ == "__main__":
    try:
        raise SystemExit(main())

    except (
        FileNotFoundError,
        ValueError,
        RuntimeError,
        json.JSONDecodeError
    ) as error:
        print("\nProgrammas kļūda:")
        print(error)
        raise SystemExit(1)

    except requests.exceptions.Timeout:
        print(
            "\nHTTP pieprasījums pārsniedza "
            f"{TIMEOUT_SECONDS} sekunžu gaidīšanas laiku."
        )
        raise SystemExit(1)

    except requests.exceptions.RequestException as error:
        print("\nHTTP pieprasījuma kļūda:")
        print(error)
        raise SystemExit(1)

    except KeyboardInterrupt:
        print("\n\nDarbību pārtrauca lietotājs.")
        raise SystemExit(130)

    except Exception as error:
        print("\nNezināma kļūda:")
        print(error)
        raise SystemExit(1)