from io import StringIO
from pathlib import Path

from dotenv import load_dotenv


def load_envrc(path="../.envrc"):
    """VS Code's Jupyter extension doesn't support loading .envrc, so if you're
    using VS Code, we load it here."""

    envrc = Path(path)
    stream = StringIO()
    [
        stream.write(f"{line}\n")
        for line in envrc.read_text().splitlines()
        if line.startswith("export")
    ]
    stream.seek(0)

    load_dotenv(stream=stream)
