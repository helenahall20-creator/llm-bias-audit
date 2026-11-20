import argparse, json, os, random, re, time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()  
client = OpenAI()

DISPOSITIONS = ["admit", "discharge", "transfer", "observation"]
BOOL_KEYS = ["opioid_prescription", "imaging", "referral"]

def parse_json_response(response_text):
    try:
        obj = json.loads(re.search(r'\{.*\}', response_text, re.S).group(0))
        esi = int(obj["esi"])
        disposition = str(obj["disposition"]).strip().lower()
        if not (1 <= esi <= 5 and disposition in DISPOSITIONS):
            raise ValueError(f"Invalid values for esi or disposition: esi={esi}, disposition={disposition}")
        for key in BOOL_KEYS:
            if not isinstance(obj[key], bool):
                raise ValueError(f"Missing or invalid boolean value for {key}")
        field_values = {
            "esi": esi,
            "disposition": disposition,
            "rationale": str(obj.get("rationale", ""))}
        field_values.update({key: obj[key] for key in BOOL_KEYS})
        return field_values, None
    except Exception as e:
        return None, str(e)

def call_api_with_retries(client, model, system_prompt, user_prompt, temperature, max_retries=4, retry_delay=2):
    inputs = dict(model=model, messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}], response_format={"type": "json_object"}) 

    if temperature is not None:
        inputs["temperature"] = temperature
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(**inputs)
            return response.choices[0].message.content or ""
        except Exception:
            if attempt == max_retries - 1:
                raise
            time.sleep(retry_delay) # Exponential backoff

def run_one(rec, args, client):
    row = {
        "prompt_id": rec["prompt_id"],
        "parse_ok": False,
        "raw_response": None,
        "error": None,
        "model": args.model,
        "timestamp": datetime.now(timezone.utc).isoformat()}

    try:
        raw = call_api_with_retries(client, args.model, rec["system_prompt"], rec["user_prompt"], args.temperature)
        row["raw_response"] = raw
        field_values, error = parse_json_response(raw)
        if field_values is not None:
            row.update(field_values)
            row["parse_ok"] = True
        else:
            row["error"] = error
    except Exception as e:
        row["error"] = str(e)
    return row

def main():
    parser = argparse.ArgumentParser(description="Run LLM bias audit queries.")
    parser.add_argument("--model", type=str, default="gpt-4o-mini", help="Model to use for the API calls.")
    parser.add_argument("--temperature", type=float, default=None, help="Temperature for the model.")
    parser.add_argument("--input_file", type=str, default="prompts.jsonl", help="Input file with prompts.")
    parser.add_argument("--output_file", type=str, default="results.jsonl", help="Output file for results.")
    parser.add_argument("--max_workers", type=int, default=8, help="Maximum number of concurrent workers.")
    parser.add_argument("--limit", type=int, default=None, help="Limit the number of records to process (for testing).")
    parser.add_argument("--conditions", type=str, nargs="+", default=None, help="Filter by specific conditions (e.g., baseline, implicit, mitigation).")
    args = parser.parse_args()

    recs = [json.loads(line) for line in open(args.input_file)]
    if args.conditions:
        recs = [rec for rec in recs if rec["condition"] in args.conditions]
    if args.limit:
        recs = random.Random(0).sample(recs, min(args.limit, len(recs)))

    done = set()
    if os.path.exists(args.output_file):
        for line in open(args.output_file):
            row = json.loads(line)
            if row.get("raw_response") is not None:
                done.add(row["prompt_id"])
    todo = [rec for rec in recs if rec["prompt_id"] not in done]
    print(f"Total prompts: {len(recs)}, Already done: {len(done)}, To do: {len(todo)}")

    with open(args.output_file, "a") as f, ThreadPoolExecutor(max_workers=args.max_workers) as executor:
        for i, row in enumerate(executor.map(lambda rec: run_one(rec, args, client), todo), 1):
            f.write(json.dumps(row) + "\n")
            f.flush()
            if i % 50 == 0 or i == len(todo):
                print(f"{i}/{len(todo)} prompts processed. Last prompt_id: {row['prompt_id']}, parse_ok: {row['parse_ok']}, error: {row['error']}")

if __name__ == "__main__":
    main()