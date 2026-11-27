import sys
import unittest
from pathlib import Path
import json
import tempfile
from shutil import copyfile
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from assignment_storage import (
    load_assignments,
    load_course_mapping,
    load_bindings,
    save_bindings,
    backup_bindings,
)
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


# AI-assisted tests for course mapping loading.
class LoadCourseMappingTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "课程 mapping.json"

    def test_load_valid_mapping_from_path_and_string(self):
        expected = {"course_1": "Algebra-1", "course_2": "物理课程"}
        self.path.write_text(
            json.dumps(expected, ensure_ascii=False), encoding="utf-8"
        )
        original_contents = self.path.read_bytes()

        for path in (self.path, str(self.path)):
            with self.subTest(path=path):
                self.assertEqual(load_course_mapping(path), expected)
        self.assertEqual(self.path.read_bytes(), original_contents)

    def test_load_empty_mapping(self):
        self.path.write_text("{}", encoding="utf-8")

        self.assertEqual(load_course_mapping(self.path), {})

    def test_missing_file(self):
        with self.assertRaises(FileNotFoundError):
            load_course_mapping(self.path)

    def test_invalid_json(self):
        self.path.write_text('{"course_1":', encoding="utf-8")

        with self.assertRaises(json.JSONDecodeError):
            load_course_mapping(self.path)

    def test_mapping_must_be_dictionary(self):
        for data in ([], None, True, 1, "Algebra-1"):
            with self.subTest(data=data):
                self.path.write_text(json.dumps(data), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "dictionary"):
                    load_course_mapping(self.path)

    def test_local_course_must_be_string(self):
        for value in (1, 1.5, True, None, [], {}):
            with self.subTest(value=value):
                data = {"valid_course": "Algebra-1", "invalid_course": value}
                self.path.write_text(json.dumps(data), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "invalid_course.*string"):
                    load_course_mapping(self.path)


class LoadBindingsTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "bindings.json"
        self.binding = {
            "course_id": "course_1",
            "assignment_id": "assignment_1",
            "local_course": "Analysis-1",
            "local_number": 7,
        }

    def write_bindings(self, data):
        self.path.write_text(json.dumps(data), encoding="utf-8")

    def test_load_valid_bindings_in_order(self):
        other = dict(self.binding, course_id="course_2", local_course="Algebra-1")
        expected = [other, self.binding]
        self.write_bindings(expected)

        self.assertEqual(load_bindings(self.path), expected)

    def test_load_empty_bindings(self):
        self.write_bindings([])

        self.assertEqual(load_bindings(self.path), [])

    def test_missing_file(self):
        with self.assertRaises(FileNotFoundError):
            load_bindings(self.path)

    def test_invalid_json(self):
        self.path.write_text("[{", encoding="utf-8")

        with self.assertRaises(json.JSONDecodeError):
            load_bindings(self.path)

    def test_invalid_structure(self):
        for data in ({}, [1]):
            with self.subTest(data=data):
                self.write_bindings(data)
                with self.assertRaises(ValueError):
                    load_bindings(self.path)

    def test_missing_required_field(self):
        for field in self.binding:
            with self.subTest(field=field):
                incomplete = self.binding.copy()
                del incomplete[field]
                self.write_bindings([incomplete])
                with self.assertRaisesRegex(ValueError, field):
                    load_bindings(self.path)

    def test_name_fields_must_be_strings(self):
        for field in ("course_id", "assignment_id", "local_course"):
            with self.subTest(field=field):
                self.write_bindings([dict(self.binding, **{field: 1})])
                with self.assertRaisesRegex(ValueError, field):
                    load_bindings(self.path)

    def test_local_number_must_be_positive_integer(self):
        for number in (0, -1, True, False, 1.0, "7"):
            with self.subTest(number=number):
                self.write_bindings([dict(self.binding, local_number=number)])
                with self.assertRaisesRegex(ValueError, "local_number.*positive integer"):
                    load_bindings(self.path)

    def test_repeated_platform_id_is_rejected(self):
        self.write_bindings([self.binding, self.binding.copy()])

        with self.assertRaisesRegex(ValueError, "course_1.*assignment_1"):
            load_bindings(self.path)

    def test_repeated_local_position_is_rejected(self):
        other = dict(self.binding, assignment_id="assignment_2")
        self.write_bindings([self.binding, other])

        with self.assertRaisesRegex(ValueError, "Analysis-1.*7"):
            load_bindings(self.path)


# AI-assisted tests for safe binding persistence.
class SaveBindingsTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "bindings.json"
        self.original_contents = b"[]\n"
        self.path.write_bytes(self.original_contents)
        self.binding = {
            "course_id": "course_1",
            "assignment_id": "assignment_1",
            "local_course": "分析课程",
            "local_number": 7,
        }

    def test_save_new_file_using_string_path(self):
        self.path.unlink()
        other = dict(self.binding, assignment_id="assignment_2", local_number=8)
        expected = [other, self.binding]

        save_bindings(str(self.path), expected)

        self.assertEqual(load_bindings(self.path), expected)
        self.assertIn("分析课程", self.path.read_text(encoding="utf-8"))
        self.assertEqual(set(self.path.parent.iterdir()), {self.path})

    def test_replace_existing_file(self):
        save_bindings(self.path, [self.binding])

        self.assertEqual(load_bindings(self.path), [self.binding])
        self.assertEqual(set(self.path.parent.iterdir()), {self.path})

    def test_save_empty_bindings(self):
        save_bindings(self.path, [])

        self.assertEqual(load_bindings(self.path), [])
        self.assertEqual(set(self.path.parent.iterdir()), {self.path})

    def test_invalid_bindings_preserve_existing_file(self):
        invalid_cases = [
            [dict(self.binding, local_number=0)],
            [dict(self.binding, local_number=True)],
            [self.binding, self.binding.copy()],
            [self.binding, dict(self.binding, assignment_id="assignment_2")],
        ]
        for bindings in invalid_cases:
            with self.subTest(bindings=bindings):
                with self.assertRaises(ValueError):
                    save_bindings(self.path, bindings)
                self.assertEqual(self.path.read_bytes(), self.original_contents)
                self.assertEqual(set(self.path.parent.iterdir()), {self.path})

    def test_partial_write_failure_preserves_file_and_cleans_temp(self):
        failure = OSError("Simulated write failure")

        def fail_write(bindings, file, **options):
            file.write("[")
            raise failure

        with patch("assignment_storage.json.dump", side_effect=fail_write):
            with self.assertRaises(OSError) as raised:
                save_bindings(self.path, [self.binding])

        self.assertIs(raised.exception, failure)
        self.assertEqual(self.path.read_bytes(), self.original_contents)
        self.assertEqual(set(self.path.parent.iterdir()), {self.path})

    def test_replace_failure_preserves_file_and_cleans_temp(self):
        failure = PermissionError("Simulated replace failure")
        with patch.object(Path, "replace", side_effect=failure):
            with self.assertRaises(PermissionError) as raised:
                save_bindings(self.path, [self.binding])

        self.assertIs(raised.exception, failure)
        self.assertEqual(self.path.read_bytes(), self.original_contents)
        self.assertEqual(set(self.path.parent.iterdir()), {self.path})

    def test_serialization_failure_preserves_file_and_cleans_temp(self):
        binding = dict(self.binding, metadata={"unsupported set"})

        with self.assertRaises(TypeError):
            save_bindings(self.path, [binding])

        self.assertEqual(self.path.read_bytes(), self.original_contents)
        self.assertEqual(set(self.path.parent.iterdir()), {self.path})

    def test_tempfile_creation_failure_preserves_file(self):
        failure = PermissionError("Simulated temporary-file creation failure")
        with patch("assignment_storage.NamedTemporaryFile", side_effect=failure):
            with self.assertRaises(PermissionError) as raised:
                save_bindings(self.path, [self.binding])

        self.assertIs(raised.exception, failure)
        self.assertEqual(self.path.read_bytes(), self.original_contents)
        self.assertEqual(set(self.path.parent.iterdir()), {self.path})


# AI-assisted tests for a single rolling binding backup.
class BackupBindingsTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "课程 bindings.json"
        self.backup_path = self.path.with_name(self.path.name + ".bak")

    def test_copy_exact_bytes_without_parsing_json(self):
        contents = b"not JSON\r\n\x00\xff"
        self.path.write_bytes(contents)

        for path in (self.path, str(self.path)):
            with self.subTest(path=path):
                self.assertEqual(backup_bindings(path), self.backup_path)
                self.assertEqual(self.backup_path.read_bytes(), contents)
                self.assertEqual(self.path.read_bytes(), contents)

    def test_repeated_backup_replaces_previous_version(self):
        self.path.write_bytes(b"first version")
        backup_bindings(self.path)
        self.path.write_bytes(b"second version")

        self.assertEqual(backup_bindings(self.path), self.backup_path)

        self.assertEqual(self.backup_path.read_bytes(), b"second version")
        self.assertEqual(self.path.read_bytes(), b"second version")
        self.assertEqual(set(self.path.parent.iterdir()), {self.path, self.backup_path})

    def test_missing_source_raises_without_creating_backup(self):
        with self.assertRaises(FileNotFoundError):
            backup_bindings(self.path)

        self.assertEqual(list(self.path.parent.iterdir()), [])

    def test_copy_failure_propagates_and_preserves_source(self):
        contents = b"[]\n"
        self.path.write_bytes(contents)
        self.backup_path.mkdir()

        with self.assertRaises(IsADirectoryError):
            backup_bindings(self.path)

        self.assertEqual(self.path.read_bytes(), contents)
        self.assertTrue(self.backup_path.is_dir())

    def test_restore_previous_bindings_from_backup(self):
        binding = {
            "course_id": "course_1",
            "assignment_id": "assignment_1",
            "local_course": "分析课程",
            "local_number": 7,
        }
        contents = (json.dumps([binding], ensure_ascii=False, indent=4) + "\n").encode("utf-8")
        self.path.write_bytes(contents)
        backup_path = backup_bindings(self.path)
        save_bindings(self.path, [])
        self.assertEqual(load_bindings(self.path), [])

        copyfile(backup_path, self.path)

        self.assertEqual(self.path.read_bytes(), contents)
        self.assertEqual(load_bindings(self.path), [binding])
