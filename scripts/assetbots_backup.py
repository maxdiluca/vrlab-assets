#!/usr/bin/env python3
"""Create a minimized, checksummed Assetbots API snapshot.

Production API keys are read from macOS Keychain. They are never written to the
backup, command line, logs, or repository. Person data is limited to name and
email, including person references nested in asset checkout records.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import ssl
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


API_BASE = "https://api.assetbots.com/v1"
PAGE_SIZE = 1_000
USER_AGENT = "VRLab-Assetbots-Backup/1.0"


@dataclass(frozen=True)
class DatabaseSpec:
    slug: str
    expected_name: str
    keychain_service: str


DATABASES = (
    DatabaseSpec("it", "VR Lab IT", "uk.ac.bham.vrlab.assetbots.it"),
    DatabaseSpec("headsets", "VR lab headsets", "uk.ac.bham.vrlab.assetbots.headsets"),
    DatabaseSpec("misc", "VR Lab Misc", "uk.ac.bham.vrlab.assetbots.misc"),
    DatabaseSpec("storage", "VR Lab In storage", "uk.ac.bham.vrlab.assetbots.storage"),
    DatabaseSpec("visitor-cards", "Visitor cards", "uk.ac.bham.vrlab.assetbots.visitor-cards"),
)


class BackupError(RuntimeError):
    """A safe-to-display backup failure."""


def _normalise_scalar(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, dict):
        value = value.get("value")
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _casefold_get(record: dict[str, Any], key: str) -> Any:
    wanted = key.casefold()
    for candidate, value in record.items():
        if candidate.casefold() == wanted:
            return value
    return None


def minimise_person(record: dict[str, Any] | None) -> dict[str, str | None]:
    """Return exactly the two approved personal fields."""

    source = record if isinstance(record, dict) else {}
    return {
        "name": _normalise_scalar(_casefold_get(source, "name")),
        "email": _normalise_scalar(_casefold_get(source, "email")),
    }


def minimise_person_reference(value: Any) -> Any:
    """Minimize an Assetbots RelatedPerson wrapper without retaining its ID."""

    if not isinstance(value, dict):
        return value
    if isinstance(value.get("value"), dict):
        return {"value": minimise_person(value["value"])}
    return minimise_person(value)


def sanitise_person_references(value: Any) -> Any:
    """Recursively minimize values whose field name identifies a person."""

    if isinstance(value, list):
        return [sanitise_person_references(item) for item in value]
    if not isinstance(value, dict):
        return value

    cleaned: dict[str, Any] = {}
    for key, item in value.items():
        folded = key.casefold().replace("_", "").replace("-", "")
        if "person" in folded and isinstance(item, dict):
            cleaned[key] = minimise_person_reference(item)
        else:
            cleaned[key] = sanitise_person_references(item)
    return cleaned


def key_from_environment(spec: DatabaseSpec) -> str | None:
    name = "ASSETBOTS_API_KEY_" + spec.slug.upper().replace("-", "_")
    value = os.environ.get(name, "").strip()
    return value or None


def key_from_keychain(spec: DatabaseSpec) -> str:
    env_key = key_from_environment(spec)
    if env_key:
        return env_key

    command = [
        "/usr/bin/security",
        "find-generic-password",
        "-a",
        "api",
        "-s",
        spec.keychain_service,
        "-w",
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    value = result.stdout.strip()
    if result.returncode != 0 or not value:
        raise BackupError(
            f"Missing Keychain API key for {spec.slug} ({spec.keychain_service})."
        )
    return value


def request_document(
    path: str,
    api_key: str,
    *,
    params: dict[str, Any] | None = None,
    base_url: str = API_BASE,
    timeout: int = 30,
    attempts: int = 3,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    query = "?" + urlencode(params) if params else ""
    url = base_url.rstrip("/") + "/" + path.lstrip("/") + query
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
            "X-Api-Key": api_key,
        },
        method="GET",
    )

    for attempt in range(1, attempts + 1):
        try:
            with urlopen(request, timeout=timeout, context=ssl.create_default_context()) as response:
                payload = json.load(response)
            if not isinstance(payload, dict):
                raise BackupError(f"Unexpected API response for {path}.")
            return payload
        except HTTPError as error:
            retryable = error.code == 429 or 500 <= error.code < 600
            if retryable and attempt < attempts:
                retry_after = error.headers.get("Retry-After", "")
                delay = float(retry_after) if retry_after.isdigit() else 2 ** (attempt - 1)
                sleep(min(delay, 60))
                continue
            raise BackupError(f"Assetbots returned HTTP {error.code} for {path}.") from None
        except (URLError, TimeoutError, OSError) as error:
            if attempt < attempts:
                sleep(2 ** (attempt - 1))
                continue
            raise BackupError(f"Could not reach Assetbots for {path}: {error}") from None

    raise BackupError(f"Could not retrieve {path}.")


def fetch_collection(
    path: str,
    api_key: str,
    *,
    requester: Callable[..., dict[str, Any]] = request_document,
    base_url: str = API_BASE,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    offset = 0
    while True:
        document = requester(
            path,
            api_key,
            params={"limit": PAGE_SIZE, "offset": offset},
            base_url=base_url,
        )
        page = document.get("data")
        if not isinstance(page, list):
            raise BackupError(f"Assetbots returned no data collection for {path}.")
        if not all(isinstance(record, dict) for record in page):
            raise BackupError(f"Assetbots returned invalid records for {path}.")
        records.extend(page)
        if len(page) < PAGE_SIZE:
            return records
        offset += len(page)
        if offset > 10_000_000:
            raise BackupError(f"Pagination limit exceeded for {path}.")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    path.chmod(0o600)


def _database_record(document: dict[str, Any]) -> dict[str, Any]:
    data = document.get("data")
    if isinstance(data, list) and data and isinstance(data[0], dict):
        return data[0]
    if isinstance(data, dict):
        return data
    raise BackupError("Assetbots returned no database metadata.")


def backup_database(
    spec: DatabaseSpec,
    api_key: str,
    target: Path,
    *,
    requester: Callable[..., dict[str, Any]] = request_document,
    base_url: str = API_BASE,
) -> dict[str, Any]:
    database = _database_record(requester("databases", api_key, base_url=base_url))
    actual_name = str(database.get("name", "")).strip()
    if actual_name.casefold() != spec.expected_name.casefold():
        raise BackupError(
            f"The {spec.slug} API key belongs to {actual_name or 'an unnamed database'}, "
            f"not {spec.expected_name}."
        )

    assets = fetch_collection("assets", api_key, requester=requester, base_url=base_url)
    people = fetch_collection("people", api_key, requester=requester, base_url=base_url)
    locations = fetch_collection("locations", api_key, requester=requester, base_url=base_url)

    target.mkdir(mode=0o700, parents=True)
    files: dict[str, dict[str, Any]] = {}
    datasets = {
        "database.json": database,
        "assets.json": sanitise_person_references(assets),
        "people-minimal.json": [minimise_person(person) for person in people],
        "locations.json": sanitise_person_references(locations),
    }
    for filename, value in datasets.items():
        path = target / filename
        write_json(path, value)
        files[filename] = {"bytes": path.stat().st_size, "sha256": sha256_file(path)}

    manifest = {
        "database": {"slug": spec.slug, "name": actual_name},
        "counts": {
            "assets": len(assets),
            "people": len(people),
            "locations": len(locations),
        },
        "files": files,
        "personal_data": "Person values are limited to name and email.",
    }
    write_json(target / "manifest.json", manifest)
    return manifest


def timestamp_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")


def create_backup(
    output_root: Path,
    *,
    specs: Iterable[DatabaseSpec] = DATABASES,
    requester: Callable[..., dict[str, Any]] = request_document,
    key_loader: Callable[[DatabaseSpec], str] = key_from_keychain,
    base_url: str = API_BASE,
    dry_run: bool = False,
) -> Path | None:
    selected = tuple(specs)
    output_root.mkdir(mode=0o700, parents=True, exist_ok=True)
    output_root.chmod(0o700)
    stamp = timestamp_utc()
    partial = output_root / f".{stamp}.partial-{os.getpid()}"
    final = output_root / stamp
    if final.exists():
        raise BackupError(f"Backup destination already exists: {final}")

    keys = {spec.slug: key_loader(spec) for spec in selected}
    if dry_run:
        for spec in selected:
            database = _database_record(
                requester("databases", keys[spec.slug], base_url=base_url)
            )
            actual = str(database.get("name", ""))
            if actual.casefold() != spec.expected_name.casefold():
                raise BackupError(f"The {spec.slug} API key belongs to an unexpected database.")
            for resource in ("assets", "people", "locations"):
                fetch_collection(
                    resource,
                    keys[spec.slug],
                    requester=requester,
                    base_url=base_url,
                )
        return None

    partial.mkdir(mode=0o700)
    try:
        manifests = []
        for spec in selected:
            manifests.append(
                backup_database(
                    spec,
                    keys[spec.slug],
                    partial / spec.slug,
                    requester=requester,
                    base_url=base_url,
                )
            )
        write_json(
            partial / "manifest.json",
            {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "format_version": 1,
                "databases": manifests,
                "excluded": [
                    "API keys",
                    "person fields other than name and email",
                    "notes",
                    "attachments",
                    "complete checkout history",
                    "database configuration",
                ],
            },
        )
        partial.rename(final)
    except Exception:
        shutil.rmtree(partial, ignore_errors=True)
        raise
    return final


def validate_backup(path: Path) -> None:
    overall = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
    databases = overall.get("databases")
    if not isinstance(databases, list) or not databases:
        raise BackupError("The backup manifest has no databases.")
    for database in databases:
        slug = database.get("database", {}).get("slug")
        files = database.get("files")
        if not slug or not isinstance(files, dict):
            raise BackupError("The backup manifest is malformed.")
        for filename, metadata in files.items():
            target = path / slug / filename
            if not target.is_file() or sha256_file(target) != metadata.get("sha256"):
                raise BackupError(f"Checksum validation failed for {slug}/{filename}.")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, help="Directory for dated backups")
    parser.add_argument("--dry-run", action="store_true", help="Validate API keys only")
    parser.add_argument("--validate", type=Path, help="Validate an existing backup")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.validate:
            validate_backup(args.validate.expanduser().resolve())
            print("Backup checksums are valid.")
            return 0
        if not args.output_root:
            raise BackupError("--output-root is required.")
        destination = create_backup(
            args.output_root.expanduser().resolve(), dry_run=args.dry_run
        )
        if args.dry_run:
            print("All five API keys are present and assigned to the expected databases.")
        else:
            print(f"Backup completed: {destination}")
        return 0
    except BackupError as error:
        print(f"Backup failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
