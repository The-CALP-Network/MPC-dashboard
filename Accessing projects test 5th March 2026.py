import requests
import json

project_id = "209282"

url = f"https://api.hpc.tools/v2/public/project/{project_id}"

response = requests.get(url, timeout=30)

print("Status code:", response.status_code)
print("URL:", url)

try:
    data = response.json()

    with open(f"project_{project_id}.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Saved to project_{project_id}.json")

except Exception as e:
    print("Could not parse JSON.")
    print("Error:", e)
    print(response.text[:2000])