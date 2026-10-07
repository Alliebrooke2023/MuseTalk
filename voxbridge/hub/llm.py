# voxbridge/hub/llm.py
"""Read a text file, ask Claude for a spoken-style reply, write it to a file."""
import argparse
from pathlib import Path

SYSTEM = ("You are a voice assistant. Reply in plain spoken sentences, "
          "no markdown, no lists, under 80 words.")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default="claude-opus-5-5")
    a = ap.parse_args(argv)

    import anthropic
    client = anthropic.Anthropic()
    resp = client.beta.messages.create(
        model=a.model,
        max_tokens=16000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        output_config={"effort": "low"},
        system=SYSTEM,
        messages=[{"role": "user", "content": Path(a.src).read_text(encoding="utf-8")}],
    )
    if resp.stop_reason == "refusal":
        raise SystemExit("model declined the request")
    text = "".join(b.text for b in resp.content if b.type == "text").strip()
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
