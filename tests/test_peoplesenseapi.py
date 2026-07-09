import os
import json
import requests

from dotenv import load_dotenv

load_dotenv()

url = os.getenv("PEOPLESENSE_URL")
api_key = os.getenv("PEOPLESENSE_API_KEY")

headers = {
    "x-api-key": api_key
}

print("Calling PeopleSense API...")

response = requests.get(url, headers=headers)

print("Status Code:", response.status_code)

print()

print("Response:")

print(json.dumps(response.json(), indent=4))