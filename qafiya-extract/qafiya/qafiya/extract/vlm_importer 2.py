"""Scanned-PDF / image -> blocks via a document VLM. THIS is where the LLM is needed.

Loads a provider token from the environment or a .env file. CSV/TSV and Markdown/text
importers need NO token and no dependencies; this path does.
"""
import os


class MissingToken(Exception):
    pass


class NotWired(Exception):
    pass


def load_dotenv(path: str = ".env") -> dict:
    env = {}
    if os.path.exists(path):
        for line in read_lines(path):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def read_lines(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.readlines()


def resolve_token(explicit: str = None) -> str:
    tok = explicit or os.environ.get("TOGETHER_API_KEY") or load_dotenv().get("TOGETHER_API_KEY")
    if not tok:
        raise MissingToken(
            "Scanned/image extraction needs a document-VLM token.\n"
            "Add TOGETHER_API_KEY=<your key> to a .env file in the project root "
            "(see .env.example). CSV/TSV and Markdown/text work without it.")
    return tok


def import_scan(src_path: str, out_dir: str, token: str = None) -> dict:
    tok = resolve_token(token)          # raises MissingToken with guidance if absent
    raise NotWired(
        "TOGETHER_API_KEY detected — the VLM extraction call is the next build step "
        "(grounded spans + value-in-span check). Not implemented yet.")
