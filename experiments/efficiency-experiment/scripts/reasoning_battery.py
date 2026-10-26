#!/usr/bin/env python3
"""Frozen reasoning-mode battery (evidence for the paper's operational claim).

Per model (Qwen3.5-9B, Qwen3.8-2.4T-A95B — both thinking-capable):
  - 2 calls with the LARGE tabular S2-raw prompt (all six raw datasets),
    reasoning ENABLED (provider default), max_tokens 8000
  - 1 short control prompt (same model, tiny input) for the contrast.
Every full response is frozen verbatim, including finish_reason and
reasoning_content. This is the artifact backing the claim; the claim is
scoped to exactly what these runs show.
"""
import json, sys, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "results" / "raw" / "reasoning_battery"
OUT.mkdir(parents=True, exist_ok=True)
ENV = Path("/Users/youssefhariri/Documents/ideas_2026 copy 2/DeewaanAI OS/05-model-router/.env")  # valid key lives here (rotated); never printed
MODELS = ["Qwen/Qwen3.5-9B", "Qwen/Qwen3.8-2.4T-A95B"]
API = "https://api.together.xyz/v1/chat/completions"


def key():
    for line in ENV.read_text().splitlines():
        if line.startswith("TOGETHER_AI_API_KEY="):
            return line.split("=", 1)[1].strip()
    sys.exit("key not found")


def big_prompt():
    raw_tpl = (ROOT / "prompts" / "deck_raw.txt").read_text()
    man = json.loads((ROOT / "corpus" / "manifest.json").read_text())
    docs = [(ROOT / "corpus" / d["file"]).read_text()
            for d in man["docs"] if d["stratum"] == "tabular"]
    return raw_tpl.replace("{DOCUMENT}", "\n\n".join(docs))


def call(k, model, prompt):
    body = json.dumps({"model": model, "temperature": 0, "max_tokens": 8000,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(API, data=body, headers={
        "Authorization": f"Bearer {k}", "Content-Type": "application/json",
        "User-Agent": "curl/8.0"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=280) as r:
        payload = json.loads(r.read())
    return payload, time.time() - t0


def main():
    k = key()
    big = big_prompt()
    small = "Summarize in one line: travel spend was 100 in Q2 and 88 in Q3."
    for model in MODELS:
        name = model.split("/")[-1]
        for i in range(2):
            f = OUT / f"{name}_big_{i}.json"
            if f.exists():
                print("cached", f.name); continue
            try:
                payload, secs = call(k, model, big)
                payload["_seconds"] = round(secs, 2)
                f.write_text(json.dumps(payload, ensure_ascii=False))
                m = payload["choices"][0]
                print(f"{name} big_{i}: finish={m.get('finish_reason')}, "
                      f"ct={payload['usage']['completion_tokens']}, "
                      f"content_len={len(m['message'].get('content') or '')}")
            except Exception as e:
                print(name, i, "ERROR", str(e)[:150])
        f = OUT / f"{name}_short_control.json"
        if not f.exists():
            payload, secs = call(k, model, small)
            payload["_seconds"] = round(secs, 2)
            f.write_text(json.dumps(payload, ensure_ascii=False))
            print(f"{name} short: ct={payload['usage']['completion_tokens']}, "
                  f"content_len={len(payload['choices'][0]['message'].get('content') or '')}")
    print("frozen ->", OUT)


if __name__ == "__main__":
    main()
