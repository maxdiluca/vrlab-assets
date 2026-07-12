import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = Path(__file__).parents[1] / "scripts" / "assetbots_backup.py"
SPEC = importlib.util.spec_from_file_location("assetbots_backup", MODULE_PATH)
backup = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
sys.modules[SPEC.name] = backup
SPEC.loader.exec_module(backup)


class MinimisationTests(unittest.TestCase):
    def test_person_contains_only_name_and_email(self):
        value = backup.minimise_person(
            {
                "id": "pe_secret",
                "name": "A Person",
                "email": "person@example.test",
                "title": "Private title",
                "department": "Private department",
                "labels": ["Private label"],
            }
        )
        self.assertEqual(
            value, {"name": "A Person", "email": "person@example.test"}
        )

    def test_nested_person_reference_is_minimised(self):
        asset = {
            "id": "asset-1",
            "checkout": {
                "value": {
                    "person": {
                        "id": "pe_secret",
                        "type": "Person",
                        "value": {
                            "name": "A Person",
                            "email": "person@example.test",
                            "title": "Private title",
                        },
                    }
                }
            },
        }
        cleaned = backup.sanitise_person_references(asset)
        self.assertEqual(
            cleaned["checkout"]["value"]["person"],
            {"value": {"name": "A Person", "email": "person@example.test"}},
        )
        self.assertEqual(cleaned["id"], "asset-1")


class PaginationTests(unittest.TestCase):
    def test_fetch_collection_paginates(self):
        first = [{"id": str(index)} for index in range(backup.PAGE_SIZE)]
        second = [{"id": "last"}]
        calls = []

        def requester(path, api_key, *, params, base_url):
            calls.append(params["offset"])
            return {"data": first if params["offset"] == 0 else second}

        records = backup.fetch_collection("assets", "secret", requester=requester)
        self.assertEqual(len(records), backup.PAGE_SIZE + 1)
        self.assertEqual(calls, [0, backup.PAGE_SIZE])


class BackupTests(unittest.TestCase):
    def test_backup_is_atomic_and_validates(self):
        spec = backup.DatabaseSpec("test", "Test Database", "unused")

        def requester(path, api_key, *, params=None, base_url):
            if path == "databases":
                return {"data": [{"id": "db_test", "name": "Test Database"}]}
            if path == "assets":
                return {"data": [{"id": "asset-1"}]}
            if path == "people":
                return {
                    "data": [
                        {
                            "id": "private-id",
                            "name": "A Person",
                            "email": "person@example.test",
                            "department": "Private",
                        }
                    ]
                }
            if path == "locations":
                return {"data": [{"id": "location-1", "name": "Lab"}]}
            raise AssertionError(path)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(backup, "timestamp_utc", return_value="2026-07-12T070000Z"):
                created = backup.create_backup(
                    root,
                    specs=(spec,),
                    requester=requester,
                    key_loader=lambda _: "not-written",
                )
            self.assertEqual(created, root / "2026-07-12T070000Z")
            self.assertFalse(any(root.glob("*.partial-*")))
            people = json.loads(
                (created / "test" / "people-minimal.json").read_text()
            )
            self.assertEqual(
                people, [{"name": "A Person", "email": "person@example.test"}]
            )
            backup.validate_backup(created)

            (created / "test" / "assets.json").write_text("tampered")
            with self.assertRaises(backup.BackupError):
                backup.validate_backup(created)


if __name__ == "__main__":
    unittest.main()
