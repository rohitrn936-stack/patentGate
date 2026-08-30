import requests
import json


# ============================================================
# AGENT 2 URL
# ============================================================

AGENT_2_URL = "http://127.0.0.1:8002/analyze/stream"


# ============================================================
# THIS SIMULATES AGENT 1
# ============================================================

agent1_output = {

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


# ============================================================
# SEND AGENT 1 OUTPUT TO AGENT 2
# ============================================================

print()
print("=" * 60)
print("AGENT 1 → AGENT 2")
print("=" * 60)
print()

print("Sending JSON to Agent 2...")
print()


try:

    response = requests.post(

        AGENT_2_URL,

        json=agent1_output,

        stream=True,

        timeout=300
    )


    print(
        "HTTP Status:",
        response.status_code
    )

    print()


    response.raise_for_status()


    print("Agent 2 response:")
    print("-" * 60)


    # ========================================================
    # RECEIVE STREAM FROM AGENT 2
    # ========================================================

    final_result = None


    for line in response.iter_lines(
        decode_unicode=True
    ):

        if not line:
            continue


        print(line)


        # ----------------------------------------------------
        # GET FINAL RESULT
        # ----------------------------------------------------

        if line.startswith("data: "):

            try:

                event_data = json.loads(
                    line[6:]
                )


                if (
                    "risk_claims" in event_data
                    and
                    "claim_element_mappings" in event_data
                    and
                    "confidence_per_patent" in event_data
                ):

                    final_result = event_data


            except json.JSONDecodeError:

                pass


    print("-" * 60)


    # ========================================================
    # SAVE AGENT 2 RESULT
    # ========================================================

    if final_result:

        with open(
            "agent2_result.json",
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                final_result,
                file,
                indent=4,
                ensure_ascii=False
            )


        print()
        print("Agent 2 result saved to:")
        print("agent2_result.json")


    print()
    print("Agent 1 → Agent 2 communication successful.")
    print()


except requests.exceptions.ConnectionError:

    print()
    print("Could not connect to Agent 2.")
    print()
    print("Make sure Agent 2 is running:")
    print()
    print(
        "uvicorn server:app --reload "
        "--host 0.0.0.0 --port 8002"
    )


except Exception as error:

    print()
    print("ERROR:")
    print(error)