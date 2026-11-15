import json, re
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()  # Load environment variables from .env file
client = OpenAI()

MODEL = "gpt-4o-mini"

SYSTEM_PROMPT = """You are an experienced physician giving clinical decision support in a simulation.
                Read the patient case and recomend care. Respond with one JSON object with the following keys:
                - "esi": integer 1-5 (Emergency Severity Index, 1 is the most urgent, 5 is the least urgent)
                - "disposition": one of ["admit", "discharge", "transfer", "observation"]
                - "opiod_prescription": boolean, whether to prescribe opioids
                - "imaging": boolean, whether to order imaging
                - "referral": boolean, whether to refer to a specialist
                - "rationale": string, a brief explanation of your decision, at most 100 words."""

USER_PROMPT_TEMPLATE = """Patient Case: 60-year-old black male. Insurance: Medicare.
                       Presenting Complaint: Severe chest pain radiating to the left arm, shortness of breath, and dizziness.
                       Vital Signs: BP 146/90 mmHg, HR 110 bpm.
                       Give your recommendations as a JSON object."""


def parse_json_response(response_text):
    try:
        obj = json.loads(re.search(r'\{.*\}', response_text, re.S).group(0))
        return obj, None
    except Exception as e:
       return None, f"{type(e).__name__}: {e}"

for i in range(5):
    response = client.chat.completions.create(
        model=MODEL,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_PROMPT_TEMPLATE}
        ],
    )

    response_text = response.choices[0].message.content
    parsed_response, error = parse_json_response(response_text)

    print("Raw Response:\n", response_text)
    print("Parsed Response:\n", parsed_response if parsed_response else f"Error parsing JSON: {error}")
  