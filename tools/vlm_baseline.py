"""Optional VLM baseline: send each oracle crop to Claude or Gemini and save the raw output."""
import argparse
import base64
import json
import os
import sys
import time
import unicodedata as ud
import urllib.request
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from khojki import log_experiment  # noqa: E402

PROMPT = ("Transcribe this line of Khojki script. Output only Unicode Khojki characters "
          "(U+11200–U+1124F), U+1123A between words, Gujarati digits for numbers. No other text.")
GT_DIR = Path("data/gt_lines")
OUT_DIR = Path("results/vlm_raw")


def _post(url: str, body: dict, headers: dict) -> dict:
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={"content-type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def ask_claude(png: bytes, model: str, key: str) -> tuple[str, int, int]:
    """Return (text, input tokens, output tokens) from the Anthropic Messages API."""
    body = {"model": model, "max_tokens": 512, "messages": [{"role": "user", "content": [
        {"type": "image", "source": {"type": "base64", "media_type": "image/png",
                                     "data": base64.b64encode(png).decode()}},
        {"type": "text", "text": PROMPT}]}]}
    r = _post("https://api.anthropic.com/v1/messages", body,
              {"x-api-key": key, "anthropic-version": "2023-06-01"})
    text = "".join(b.get("text", "") for b in r["content"])
    return text, r["usage"]["input_tokens"], r["usage"]["output_tokens"]


def ask_gemini(png: bytes, model: str, key: str) -> tuple[str, int, int]:
    """Return (text, input tokens, output tokens) from the Gemini generateContent API."""
    body = {"contents": [{"parts": [
        {"inline_data": {"mime_type": "image/png", "data": base64.b64encode(png).decode()}},
        {"text": PROMPT}]}]}
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    r = _post(url, body, {"x-goog-api-key": key})
    text = "".join(p.get("text", "") for p in r["candidates"][0]["content"]["parts"])
    usage = r.get("usageMetadata", {})
    return text, usage.get("promptTokenCount", 0), usage.get("candidatesTokenCount", 0)


def script_of(ch: str) -> str:
    """Rough script label from the Unicode character name."""
    if ch.isspace():
        return "SPACE"
    name = ud.name(ch, "UNKNOWN")
    return name.split()[0]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--provider", choices=["auto", "anthropic", "gemini"], default="auto")
    ap.add_argument("--model", help="model id (defaults per provider)")
    ap.add_argument("--usd-per-mtok-in", type=float, help="input price, USD per million tokens")
    ap.add_argument("--usd-per-mtok-out", type=float, help="output price, USD per million tokens")
    a = ap.parse_args()

    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    keys = {"anthropic": os.getenv("ANTHROPIC_API_KEY"), "gemini": os.getenv("GEMINI_API_KEY")}
    provider = a.provider
    if provider == "auto":
        provider = next((p for p in ("gemini", "anthropic") if keys[p]), None)
    if not provider or not keys.get(provider):
        print("no ANTHROPIC_API_KEY or GEMINI_API_KEY in .env: VLM baseline skipped")
        log_experiment("vlm_baseline", "no API key", "status", "skipped", 0)
        return

    model = a.model or {"anthropic": "claude-opus-5-5", "gemini": "gemini-2.5-pro"}[provider]
    ask = ask_claude if provider == "anthropic" else ask_gemini
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    start = time.time()
    rows, scripts = [], Counter()
    for crop in sorted(GT_DIR.glob("p18_l0?.png")):
        line_id = crop.stem
        text, tin, tout = ask(crop.read_bytes(), model, keys[provider])
        (OUT_DIR / f"{line_id}.txt").write_text(text, encoding="utf-8")
        chars = [c for c in text if not c.isspace()]
        outside = [c for c in chars if not 0x11200 <= ord(c) <= 0x1124F]
        scripts.update(script_of(c) for c in chars)
        cost = None
        if a.usd_per_mtok_in is not None and a.usd_per_mtok_out is not None:
            cost = (tin * a.usd_per_mtok_in + tout * a.usd_per_mtok_out) / 1e6
        rows.append({"id": line_id, "chars": len(chars), "outside_khojki": len(outside),
                     "input_tokens": tin, "output_tokens": tout, "usd": cost})
        print(f"{line_id}: {len(chars)} chars, {len(outside)} outside Khojki, {tin}+{tout} tokens")
    total = sum(r["chars"] for r in rows)
    summary = {
        "provider": provider, "model": model, "prompt": PROMPT, "lines": rows,
        "outside_khojki_share": round(sum(r["outside_khojki"] for r in rows) / total, 4) if total else None,
        "scripts": dict(scripts),
        "usd_per_line": (sum(r["usd"] for r in rows) / len(rows)) if rows and rows[0]["usd"] is not None else None,
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False), encoding="utf-8")
    log_experiment("vlm_baseline", f"{provider}:{model}", "outside_khojki_share",
                   summary["outside_khojki_share"], (time.time() - start) / 60)


if __name__ == "__main__":
    main()
