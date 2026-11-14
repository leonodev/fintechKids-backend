"""Script para exportar el documento OpenAPI (Swagger) a un archivo JSON físico.

Uso:
    python3 scripts/export_openapi.py
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.main import app  # noqa: E402


def main() -> None:
    openapi_schema = app.openapi()
    output_path = ROOT_DIR / "openapi.json"
    output_path.write_text(
        json.dumps(openapi_schema, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Documento Swagger/OpenAPI exportado exitosamente en: {output_path}")


if __name__ == "__main__":
    main()
