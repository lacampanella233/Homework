# AI-assisted offline tests for Python/Node process communication.
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from common import HomeworkError
from learn_bridge import read_node_homeworks


class NodeStartupTests(unittest.TestCase):
    def test_missing_node_is_an_error(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {"PATH": directory}):
                with self.assertRaisesRegex(HomeworkError, "Cannot start Node"):
                    read_node_homeworks("course_1", "unused.mjs")

    def test_timeout_is_an_error_without_exposing_output(self):
        error = subprocess.TimeoutExpired(
            "node", 30, output="private output", stderr="private diagnostic"
        )
        with patch("learn_bridge.subprocess.run", side_effect=error):
            with self.assertRaisesRegex(HomeworkError, "timed out") as caught:
                read_node_homeworks("course_1", "unused.mjs")
        self.assertNotIn("private", str(caught.exception))


@unittest.skipUnless(shutil.which("node"), "Node.js is required for process tests")
class NodeCommunicationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="作业 bridge ")
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.script = self.directory / "模拟 reader.mjs"

    def run_script(self, source):
        self.script.write_text(source, encoding="utf-8")
        return read_node_homeworks("course_1", self.script)

    def test_mock_reader_with_unicode_spaces_and_separate_stderr(self):
        fixture = Path(__file__).parent / "fixtures" / "mock_learn.mjs"
        shutil.copyfile(fixture, self.script)
        actual = read_node_homeworks("course_1", Path(os.path.relpath(self.script)))
        self.assertEqual(actual, [{
            "course_id": "course_1",
            "assignment_id": "homework_1",
            "title": "第一次作业：ε-δ",
            "due_at": "2026-11-30T23:59:00+08:00",
        }])

    def test_course_id_is_a_single_argument(self):
        self.script.write_text(
            "process.stdout.write(JSON.stringify([{baseId: process.argv[2], "
            "title: 'mock', deadline: ''}]));",
            encoding="utf-8",
        )
        course_id = "course 空格 ; $(mock)"
        actual = read_node_homeworks(course_id, self.script)
        self.assertEqual(actual[0]["assignment_id"], course_id)
        self.assertEqual(actual[0]["course_id"], course_id)

    def test_valid_empty_list(self):
        self.assertEqual(self.run_script("process.stdout.write('[]');"), [])

    def test_nonzero_exit_rejects_even_valid_json(self):
        with self.assertRaisesRegex(HomeworkError, "exit code 7") as caught:
            self.run_script(
                "process.stdout.write('[]'); "
                "console.error('private diagnostic'); process.exitCode = 7;"
            )
        self.assertNotIn("private diagnostic", str(caught.exception))

    def test_invalid_json_is_an_error(self):
        for output in ("", "not JSON", "log message\n[]"):
            with self.subTest(output=output):
                with self.assertRaisesRegex(HomeworkError, "valid JSON"):
                    self.run_script(f"process.stdout.write({json.dumps(output)});")

    def test_invalid_record_structure_is_an_error(self):
        valid = {"baseId": "hw_1", "title": "mock", "deadline": ""}
        cases = [({}, "JSON list"), ([None], "record 1 must be an object")]
        for field in valid:
            missing = dict(valid)
            del missing[field]
            cases.append(([missing], f"{field} must be a string"))
            cases.append(([dict(valid, **{field: 123})], f"{field} must be a string"))
        for data, message in cases:
            with self.subTest(data=data):
                with self.assertRaisesRegex(HomeworkError, message):
                    self.run_script(f"process.stdout.write(JSON.stringify({json.dumps(data)}));")

    def test_duplicate_identity_uses_existing_validation(self):
        record = {"baseId": "hw_1", "title": "mock", "deadline": ""}
        with self.assertRaisesRegex(ValueError, "hw_1"):
            self.run_script(
                f"process.stdout.write(JSON.stringify({json.dumps([record, record])}));"
            )

    def test_invalid_utf8_is_an_error(self):
        with self.assertRaisesRegex(HomeworkError, "UTF-8"):
            self.run_script("process.stdout.write(Buffer.from([0xff]));")
