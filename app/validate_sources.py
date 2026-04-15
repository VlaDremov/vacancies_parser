from __future__ import annotations

import argparse
import sys

from app.parsers import PARSER_REGISTRY
from app.source_loader import iter_source_configs, validate_source_config


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate source config files")
    parser.add_argument("--source-dir", default=None, help="Optional override for source config dir")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source_dir = args.source_dir or "config/sources"

    try:
        sources = list(iter_source_configs(source_dir))
    except Exception as exc:
        print(f"Validation failed: {exc}")
        return 1

    errors: list[str] = []
    warnings: list[str] = []
    for source in sources:
        if source.parser_type not in PARSER_REGISTRY:
            errors.append(f"{source.id}: unknown parser type '{source.parser_type}'")
            continue

        source_errors, source_warnings = validate_source_config(source)
        errors.extend(f"{source.id}: {error}" for error in source_errors)
        warnings.extend(f"{source.id}: {warning}" for warning in source_warnings)

    for warning in warnings:
        print(f"WARNING: {warning}")

    if errors:
        for error in errors:
            print(error)
        return 1

    print(f"Validated {len(sources)} source configs successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
