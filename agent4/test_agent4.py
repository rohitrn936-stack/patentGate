import json
import os
import sys

import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
URL = "http://127.0.0.1:8000/design"

OUTPUT_FILE = os.path.join(BASE_DIR, "output", "design_output.json")


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    product = load_json(os.path.join(BASE_DIR, "input", "product.json"))
    prosecutor = load_json(os.path.join(BASE_DIR, "input", "prosecutor.json"))
    defender = load_json(os.path.join(BASE_DIR, "input", "defender.json"))

    payload = {
        "product": product,
        "prosecutor": prosecutor,
        "defender": defender
    }

    print(f"POST {URL}")

    response = requests.post(URL, json=payload)

    print(f"Status code: {response.status_code}")
    print()

    try:
        body = response.json()
        print("Response JSON:")
        print(json.dumps(body, indent=2))
    except Exception as error:
        print(f"Could not parse response JSON: {error}")
        print(f"Raw response: {response.text}")
        sys.exit(1)

    if response.status_code != 200:
        print("Request failed.")
        sys.exit(1)

    if os.path.exists(OUTPUT_FILE):
        print()
        print(f"OK: {OUTPUT_FILE} was created.")
    else:
        print()
        print(f"WARN: {OUTPUT_FILE} was NOT created.")
        sys.exit(1)


if __name__ == "__main__":
    main()