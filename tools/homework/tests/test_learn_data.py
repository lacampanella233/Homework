# AI-assisted tests for the platform-to-assignment data adapter.
import sys
import unittest
from copy import deepcopy
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from learn_data import normalize_homeworks


class NormalizeHomeworksTests(unittest.TestCase):
    def setUp(self):
        self.homework = {
            "id": "student_record_1",
            "baseId": "homework_1",
            "title": "第一次作业：ε-δ",
            "deadline": "2026-11-30T23:59:00+08:00",
            "submitted": False,
        }

    def test_convert_fields_using_base_id(self):
        actual = normalize_homeworks("course_1", [self.homework])

        self.assertEqual(actual, [{
            "course_id": "course_1",
            "assignment_id": "homework_1",
            "title": "第一次作业：ε-δ",
            "due_at": "2026-11-30T23:59:00+08:00",
        }])

    def test_empty_list(self):
        self.assertEqual(normalize_homeworks("course_1", []), [])

    def test_preserve_order_for_same_title_with_different_ids(self):
        other = dict(self.homework, id="student_record_2", baseId="homework_2")

        actual = normalize_homeworks("course_1", [other, self.homework])

        self.assertEqual([item["assignment_id"] for item in actual],
                         ["homework_2", "homework_1"])

    def test_preserve_input_and_create_independent_records(self):
        homeworks = [self.homework]
        original = deepcopy(homeworks)

        actual = normalize_homeworks("course_1", homeworks)

        self.assertEqual(homeworks, original)
        actual[0]["title"] = "只修改转换结果"
        self.assertEqual(homeworks, original)

    def test_repeated_base_id_is_rejected_without_changing_input(self):
        other = dict(self.homework, id="student_record_2", title="同一作业的新标题")
        homeworks = [self.homework, other]
        original = deepcopy(homeworks)

        with self.assertRaisesRegex(ValueError, "homework_1"):
            normalize_homeworks("course_1", homeworks)

        self.assertEqual(homeworks, original)
