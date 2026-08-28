"""
S1 - test isolato di correttezza del tool calling per il modello locale (LM Studio).
Gate: ogni prompt deve tornare un tool_calls valido, non testo che lo imita.
Uso: uv run --project tau2-bench python ../scripts/test_tool_calling_local.py
"""

import json

import litellm

MODEL = "openai/google/gemma-4-12b-qat"
API_BASE = "http://127.0.0.1:1234/v1"

FAKE_TOOL = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Restituisce il meteo attuale per una città.",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "Nome della città"},
                "unit": {
                    "type": "string",
                    "enum": ["celsius", "fahrenheit"],
                    "description": "Unità di misura della temperatura",
                },
            },
            "required": ["city"],
        },
    },
}

PROMPTS = [
    "Che tempo fa a Milano?",
    "Dimmi la temperatura di Tokyo in fahrenheit.",
    "Sto pensando di andare a Londra questo weekend, che tempo farà secondo te?",
    "Confrontami il meteo di Roma e Parigi.",
    "Usa il tool per controllare il meteo di Berlino, in gradi celsius.",
]


def run_prompt(prompt: str) -> dict:
    response = litellm.completion(
        model=MODEL,
        api_base=API_BASE,
        api_key="lm-studio",
        messages=[{"role": "user", "content": prompt}],
        tools=[FAKE_TOOL],
    )
    message = response.choices[0].message
    tool_calls = getattr(message, "tool_calls", None) or []
    valid = []
    invalid_reasons = []
    for call in tool_calls:
        try:
            args = json.loads(call.function.arguments)
        except (json.JSONDecodeError, TypeError) as exc:
            invalid_reasons.append(f"arguments non-JSON: {exc}")
            continue
        if call.function.name != "get_weather":
            invalid_reasons.append(f"tool inventato: {call.function.name}")
            continue
        if "city" not in args:
            invalid_reasons.append(f"manca 'city' negli argomenti: {args}")
            continue
        valid.append({"name": call.function.name, "arguments": args})

    return {
        "prompt": prompt,
        "n_tool_calls": len(tool_calls),
        "valid_calls": valid,
        "invalid_reasons": invalid_reasons,
        "content_fallback": message.content,
    }


def main():
    results = [run_prompt(p) for p in PROMPTS]

    print(f"Modello: {MODEL} @ {API_BASE}\n")
    n_pass = 0
    for i, r in enumerate(results, 1):
        ok = r["n_tool_calls"] > 0 and not r["invalid_reasons"]
        status = "PASS" if ok else "FAIL"
        n_pass += ok
        print(f"[{status}] {i}. {r['prompt']}")
        if r["valid_calls"]:
            print(f"        tool_calls validi: {r['valid_calls']}")
        if r["invalid_reasons"]:
            print(f"        problemi: {r['invalid_reasons']}")
        if r["n_tool_calls"] == 0:
            print(f"        NESSUN tool_call, ha risposto testo: {r['content_fallback']!r}")
        print()

    print(f"--- Esito: {n_pass}/{len(results)} prompt con tool_calls validi ---")
    print("Gate S1: serve 5/5 per considerare il modello affidabile sul tool calling isolato.")


if __name__ == "__main__":
    main()
