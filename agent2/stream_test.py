import requests
import json


URL = "http://127.0.0.1:8002/analyze/stream"

# ------------------------------------------------------------
# TEST INPUT
# ------------------------------------------------------------

data = {

    "product": {

        "name": "SmartPay Fraud Detection",

        "description":
        "A system that analyzes financial transactions "
        "to identify potentially fraudulent activity.",

        "features": [
            "Detects suspicious financial transactions",
            "Analyzes user transaction behavior",
            "Uses historical transaction data",
            "Generates a fraud risk score"
        ]
    },

    "patents": [

        {
            "id": "US123456",

            "summary":
            "A system for detecting fraudulent financial "
            "transactions using behavioral analysis.",

            "claims":
            "Claim 1: A computer-implemented method comprising "
            "analyzing transaction behavior of a user and "
            "determining whether the transaction is "
            "potentially fraudulent."
        },

        {
            "id": "US234567",

            "summary":
            "A system for encrypting financial transaction "
            "data before transmission.",

            "claims":
            "Claim 1: A method comprising encrypting "
            "transaction data before transmitting the "
            "transaction data to a remote server."
        },

        {
            "id": "US345678",

            "summary":
            "A system for generating financial risk scores "
            "based on historical transaction information.",

            "claims":
            "Claim 1: A computer-implemented method comprising "
            "receiving historical transaction information "
            "and calculating a risk score based on the "
            "historical information."
        },

        {
            "id": "US456789",

            "summary":
            "A system for authenticating users using "
            "biometric information.",

            "claims":
            "Claim 1: A method comprising receiving biometric "
            "information from a user and authenticating "
            "the user based on the biometric information."
        },

        {
            "id": "US567890",

            "summary":
            "A financial monitoring system that identifies "
            "unusual transaction patterns.",

            "claims":
            "Claim 1: A method comprising monitoring "
            "transaction activity and identifying unusual "
            "transaction patterns."
        }
    ]
}


# ------------------------------------------------------------
# START
# ------------------------------------------------------------

print()
print("=" * 60)
print("PATENTGATE - PROSECUTOR AGENT")
print("=" * 60)
print()

print("Connecting to Agent 2...")
print()


try:

    response = requests.post(
        URL,
        json=data,
        stream=True,
        timeout=300
    )

    print(
        "HTTP Status:",
        response.status_code
    )

    print()


    # --------------------------------------------------------
    # CHECK SERVER RESPONSE
    # --------------------------------------------------------

    if response.status_code != 200:

        print("Server returned an error:")
        print(response.text)

        exit()


    print("STREAM:")
    print("-" * 60)


    # This will store the final structured JSON
    final_result = None


    # --------------------------------------------------------
    # READ STREAM
    # --------------------------------------------------------

    for line in response.iter_lines(
        decode_unicode=True
    ):

        if not line:
            continue


        print(line)


        # ----------------------------------------------------
        # LOOK FOR RESULT EVENT
        # ----------------------------------------------------

        if line.startswith("data: "):

            json_text = line[6:]


            try:

                event_data = json.loads(
                    json_text
                )


                # --------------------------------------------
                # FINAL RESULT
                # --------------------------------------------

                if (
                    "risk_claims" in event_data
                    and
                    "claim_element_mappings" in event_data
                    and
                    "confidence_per_patent" in event_data
                ):

                    final_result = event_data


            except json.JSONDecodeError:

                # This is normal for token events.
                pass


    print("-" * 60)
    print()


    # --------------------------------------------------------
    # SAVE FINAL JSON
    # --------------------------------------------------------

    if final_result is not None:

        with open(
            "result.json",
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                final_result,
                file,
                indent=4,
                ensure_ascii=False
            )


        print("SUCCESS!")
        print()
        print("Final JSON saved to:")

        print(
            "result.json"
        )

        print()


    else:

        print(
            "WARNING: No final structured result was found."
        )

        print(
            "Check the server output."
        )


    print("Streaming finished.")
    print()


# ------------------------------------------------------------
# ERRORS
# ------------------------------------------------------------

except requests.exceptions.ConnectionError:

    print()
    print("ERROR: Could not connect to Agent 2.")
    print()
    print(
        "Make sure the FastAPI server is running:"
    )
    print()
    print(
        "uvicorn server:app --reload --host 0.0.0.0 --port 8002"
    )


except requests.exceptions.Timeout:

    print()
    print("ERROR: Request timed out.")


except Exception as error:

    print()
    print("ERROR:")
    print(error)