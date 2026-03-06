import requests
import json

tests = [
    "https://api.hpc.tools/v2/public/project/search?planId=1514",
    "https://api.hpc.tools/v2/public/project/search?projectCode=HSDN24-NUT-209282-1",
    "https://api.hpc.tools/v2/public/project/search?code=HSDN24-NUT-209282-1",
    "https://api.hpc.tools/v2/public/project/search?id=209282",
    "https://api.hpc.tools/v2/public/project/search?projectId=209282",
]

for url in tests:
    print("\n" + "=" * 80)
    print("TESTING:", url)
    r = requests.get(url, timeout=30)
    print("Status:", r.status_code)
    try:
        data = r.json()
        print(json.dumps(data, indent=2)[:3000])
    except Exception:
        print(r.text[:3000])