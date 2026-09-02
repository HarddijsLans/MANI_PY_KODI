import requests
from config import CKAN_BASE_URL, CKAN_API_TOKEN

DATASET_NAME = "atsavinamo-zemju-vertibas"

url = f"{CKAN_BASE_URL}/api/3/action/package_show"

headers = {
    "Authorization": CKAN_API_TOKEN
}

params = {
    "id": DATASET_NAME
}

print("Nolasu datu kopu no CKAN...")

try:
    response = requests.get(
        url,
        headers=headers,
        params=params,
        timeout=30
    )

    print(f"HTTP statuss: {response.status_code}")
    response.raise_for_status()

    data = response.json()

    if not data.get("success"):
        print("CKAN atgrieza kļūdu:")
        print(data)
        raise SystemExit

    dataset = data["result"]

    print("\nDatu kopa")
    print("-" * 60)
    print(f"Nosaukums : {dataset.get('title')}")
    print(f"ID        : {dataset.get('id')}")
    print(f"Name      : {dataset.get('name')}")
    print(f"Resursi kopā: {len(dataset.get('resources', []))}")

    print("\nCSV resursi")
    print("-" * 60)

    csv_count = 0

    for resource in dataset.get("resources", []):
        resource_format = resource.get("format", "").upper()

        if resource_format != "CSV":
            continue

        csv_count += 1

        print(f"{csv_count}. {resource.get('name')}")
        print(f"ID      : {resource.get('id')}")
        print(f"Formāts : {resource.get('format')}")
        print(f"URL     : {resource.get('url')}")
        print("-" * 60)

    print(f"\nAtrasti CSV resursi: {csv_count}")

except requests.exceptions.RequestException as e:
    print("Kļūda HTTP pieprasījumā:")
    print(e)

except Exception as e:
    print("Kļūda:")
    print(e)