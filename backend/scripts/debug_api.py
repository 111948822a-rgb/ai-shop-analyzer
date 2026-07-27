import requests

url = "https://app4k6rhysswtr4p.h5.xiaoe-tech.com/app/app_4k6rhysswtr4p/openapi/influencers"
headers = {"X-API-Key": "cbead148e90365d929a10fa53898dcccddd56f2361a8887e"}
params = {"page": 1, "pageSize": 10}

try:
    response = requests.get(url, headers=headers, params=params, timeout=15)
    print("Status:", response.status_code)
    print("Content-Type:", response.headers.get("content-type"))
    print("Body:", response.text[:1000])
except Exception as e:
    print("Error:", e)