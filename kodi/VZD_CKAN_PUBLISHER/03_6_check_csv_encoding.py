"""
===============================================================================
03_6_check_csv_encoding.py
===============================================================================

Mērķis
------
1. Nolasīt konkrētu CKAN resursu.
2. Iegūt CSV faila URL un conformsTo metadatu URL.
3. Nolasīt CSVW metadatos deklarēto kodējumu.
4. Nolasīt CSV faila pirmos baitus.
5. Pārbaudīt, vai fails sākas ar BOM.
6. Salīdzināt deklarēto un faktiski konstatēto kodējuma pazīmi.

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

Drošības līmenis
----------------
Tikai lasa datus.
Neveic nekādas izmaiņas CKAN portālā.
===============================================================================
"""

import json
import requests

from config import CKAN_BASE_URL, CKAN_API_TOKEN


RESOURCE_ID = "8e4ee339-494c-4048-a21b-71e4a8c6c04e"

RESOURCE_SHOW_URL = f"{CKAN_BASE_URL}/api/3/action/resource_show"

HEADERS = {
    "Authorization": CKAN_API_TOKEN
}

TIMEOUT_SECONDS = 30


def get_json(url: str, **kwargs) -> dict:
    response = requests.get(
        url,
        timeout=TIMEOUT_SECONDS,
        **kwargs
    )

    print(f"HTTP statuss: {response.status_code}")
    response.raise_for_status()

    return response.json()


def detect_bom(content: bytes) -> tuple[str | None, bytes | None]:
    """
    Nosaka biežākos BOM variantus pēc faila sākuma baitiem.
    """

    bom_signatures = {
        b"\xef\xbb\xbf": "UTF-8 ar BOM",
        b"\xff\xfe\x00\x00": "UTF-32 LE ar BOM",
        b"\x00\x00\xfe\xff": "UTF-32 BE ar BOM",
        b"\xff\xfe": "UTF-16 LE ar BOM",
        b"\xfe\xff": "UTF-16 BE ar BOM",
    }

    for signature, encoding_name in bom_signatures.items():
        if content.startswith(signature):
            return encoding_name, signature

    return None, None


def format_bytes(data: bytes) -> str:
    """
    Attēlo baitus heksadecimālā formā.
    """

    return " ".join(f"{byte:02X}" for byte in data)


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
        raise ValueError("Resursam nav CSV satura URL.")

    if not conforms_to_url:
        raise ValueError("Resursam nav aizpildīts lauks 'conformsTo'.")

    print("\n2. Nolasu CSVW metadatus...")

    metadata = get_json(conforms_to_url)

    declared_encoding = (
        metadata
        .get("dialect", {})
        .get("encoding")
    )

    print("\nCSVW deklarētais kodējums")
    print("-" * 80)
    print(f"Encoding: {declared_encoding}")

    print("\n3. Nolasu CSV faila baitus...")

    csv_response = requests.get(
        csv_url,
        timeout=TIMEOUT_SECONDS
    )

    print(f"CSV HTTP statuss: {csv_response.status_code}")
    csv_response.raise_for_status()

    content = csv_response.content

    if not content:
        raise ValueError("CSV fails ir tukšs.")

    first_bytes = content[:16]

    print("\nCSV pirmie 16 baiti")
    print("-" * 80)
    print(format_bytes(first_bytes))

    detected_encoding, bom_signature = detect_bom(content)

    print("\nBOM pārbaude")
    print("-" * 80)

    if detected_encoding:
        print(f"Atrasts BOM       : Jā")
        print(f"BOM baiti         : {format_bytes(bom_signature)}")
        print(f"Konstatētais tips : {detected_encoding}")
    else:
        print("Atrasts BOM       : Nē")
        print("Konstatētais tips : nav nosakāms tikai pēc BOM")

    print("\nSalīdzinājums")
    print("=" * 80)

    if detected_encoding == "UTF-8 ar BOM":
        print("CSV fails sākas ar UTF-8 BOM.")

        if declared_encoding and declared_encoding.upper() == "ISO-8859-1":
            print(
                "❌ Neatbilstība: CSVW metadatos deklarēts ISO-8859-1, "
                "bet failā konstatēts UTF-8 BOM."
            )
        else:
            print(
                "ℹ️ Jāpārbauda, vai deklarētais kodējums atbilst UTF-8 ar BOM."
            )

    elif detected_encoding:
        print(
            f"CSV failā konstatēts {detected_encoding}. "
            "Salīdziniet to ar CSVW deklarēto kodējumu."
        )

    else:
        print(
            "BOM nav atrasts. Ar šo testu vien nepietiek, "
            "lai droši noteiktu faila kodējumu."
        )

    print("=" * 80)


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
        print("\nDatu pārbaudes kļūda:")
        print(error)

    except KeyError as error:
        print("\nCKAN atbildē nav sagaidītā lauka:")
        print(error)

    except Exception as error:
        print("\nNezināma kļūda:")
        print(error)