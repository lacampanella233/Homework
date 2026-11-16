import sys
import unittest
from pathlib import Path
import json
import tempfile

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from assignment_storage import load_assignments
from assignment_data import compare_assignments

class LoadAssignmentsTests(unittest.TestCase):
    def test_load_valid_snapshot(self):
        expected = [
            {
                "course_id": "course_1",
                "assignment_id": "assignment_1",
                "title": "第一次作业",
                "due_at": "2026-11-20 23:59",
            }
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "snapshot.json"
            path.write_text(
                json.dumps(expected, ensure_ascii=False),
                encoding="utf-8",
            )
            actual = load_assignments(path)
            self.assertEqual(actual, expected)

    def test_missing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing.json"
            with self.assertRaises(FileNotFoundError):
                load_assignments(path)

    def test_invalid_json(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.json"
            path.write_text('{"course_id":', encoding="utf-8")
            with self.assertRaises(json.JSONDecodeError):
                load_assignments(path)

    def test_snapshot_must_be_list(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "snapshot_not_list.json"
            path.write_text("{}", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_assignments(path)

    def test_assignment_must_be_dictionary(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "assignment_not_dictionary.json"
            path.write_text('[1]', encoding="utf-8")
            with self.assertRaises(ValueError):
                load_assignments(path)

    def test_missing_required_field(self):
        fake_assignment = {
            "course_id": "course_1",
            "assignment_id": "assignment_1",
            "title": "第一次作业",
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "assignment_missing_field.json"
            path.write_text(
                json.dumps([fake_assignment], ensure_ascii=False),
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                load_assignments(path)

    def test_field_must_be_string(self):
        fake_assignment = {
            "course_id": "course_1",
            "assignment_id": "assignment_1",
            "title": "第一次作业",
            "due_at": 1
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "assignment_field_not_string.json"
            path.write_text(
                json.dumps([fake_assignment], ensure_ascii=False),
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                load_assignments(path)

    def test_load_and_compare_snapshots(self):
        old_assignment = {
            "course_id": "course_1",
            "assignment_id": "assignment_1",
            "title": "第一次作业",
            "due_at": "2026-11-20 23:59"
        }
        changed_assignment = {
            "course_id": "course_1",
            "assignment_id": "assignment_1",
            "title": "第一次作业",
            "due_at": "2026-11-21 23:59"
        }
        added_assignment = {
            "course_id": "course_1",
            "assignment_id": "assignment_2",
            "title": "第二次作业",
            "due_at": "2026-11-22 23:59"
        }
        with tempfile.TemporaryDirectory() as directory:
            previous_path = Path(directory) / "previous.json"
            current_path = Path(directory) / "current.json"
            previous_path.write_text(
                json.dumps([old_assignment], ensure_ascii=False),
                encoding="utf-8",
            )
            current_path.write_text(
                json.dumps([changed_assignment, added_assignment], ensure_ascii=False),
                encoding="utf-8",
            )
            previous = load_assignments(previous_path)
            current = load_assignments(current_path)
            new, updated = compare_assignments(previous, current)
            self.assertEqual(new, [added_assignment])
            self.assertEqual(updated, [changed_assignment])