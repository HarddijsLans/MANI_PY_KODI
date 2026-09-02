import requests
from config import CKAN_BASE_URL, CKAN_API_TOKEN

url = f"{CKAN_BASE_URL}/api/3/action/status_show"

headers = {
    "Authorization": CKAN_API_TOKEN
}

print("Pieslēdzos CKAN API...")

try:
    response = requests.get(url, headers=headers, timeout=30)

    print(f"HTTP statuss: {response.status_code}")

    data = response.json()

    if data.get("success"):
        print("✅ Savienojums izdevās!")
        print(f"CKAN versija: {data['result']['ckan_version']}")
        print(f"Vietnes nosaukums: {data['result']['site_title']}")
    else:
        print("❌ CKAN atgrieza kļūdu:")
        print(data)

except Exception as e:
    print("❌ Kļūda:")
    print(e)