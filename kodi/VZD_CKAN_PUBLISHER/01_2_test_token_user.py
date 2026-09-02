import json
import requests

from config import CKAN_BASE_URL, CKAN_API_TOKEN


url = f"{CKAN_BASE_URL}/api/3/action/user_show"

headers = {
    "Authorization": CKAN_API_TOKEN
}

params = {
    "id": "hardijslans"
}

print("Pārbaudu API tokena lietotāju...")

response = requests.get(
    url,
    headers=headers,
    params=params,
    timeout=30
)

print(f"HTTP statuss: {response.status_code}")

try:
    data = response.json()
except ValueError:
    print("Servera atbilde nav JSON:")
    print(response.text)
    raise SystemExit(1)

if not data.get("success"):
    print("CKAN kļūda:")
    print(json.dumps(data, ensure_ascii=False, indent=4))
    raise SystemExit(1)

user = data["result"]

print("\nAPI tokens identificē lietotāju:")
print(f"Lietotājvārds : {user.get('name')}")
print(f"Pilnais vārds : {user.get('fullname')}")
print(f"E-pasts       : {user.get('email')}")
print(f"Sysadmin      : {user.get('sysadmin')}")