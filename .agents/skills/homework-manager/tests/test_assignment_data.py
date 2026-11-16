import sys
import unittest
from copy import deepcopy
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from assignment_data import (
    add_assignment_binding,
    compare_assignments,
    map_assignment_courses,
)


class CompareAssignmentsTests(unittest.TestCase):
    def test_new_assignment(self):
        assignment = {
            "course_id": "course_1",
            "assignment_id": "assignment_1",
            "title": "第一次作业",
            "due_at": "2026-11-20 23:59",
        }

        new, updated = compare_assignments([], [assignment])

        self.assertEqual(new, [assignment])
        self.assertEqual(updated, [])

    def test_update_due(self):
        assignment_1 = {
            "course_id": "course_1",
            "assignment_id": "assignment_1",
            "title": "第一次作业",
            "due_at": "2026-11-20 23:59",
        }
        assignment_2 = {
            "course_id": "course_1",
            "assignment_id": "assignment_1",
            "title": "第一次作业",
            "due_at": "2026-11-21 23:59",
        }

        new, updated = compare_assignments([assignment_1], [assignment_2])

        self.assertEqual(new, [])
        self.assertEqual(updated, [assignment_2])

    def test_repeated_previous_id(self):
        assignment_1 = {
            "course_id": "course_1",
            "assignment_id": "assignment_1",
            "title": "第一次作业",
            "due_at": "2026-11-20 23:59",
        }
        assignment_2 = {
            "course_id": "course_1",
            "assignment_id": "assignment_1",
            "title": "第一次作业",
            "due_at": "2026-11-21 23:59",
        }

        with self.assertRaises(ValueError):
            compare_assignments([assignment_1, assignment_2], [])

    def test_repeated_current_id(self):
        assignment_1 = {
            "course_id": "course_1",
            "assignment_id": "assignment_1",
            "title": "第一次作业",
            "due_at": "2026-11-20 23:59",
        }
        assignment_2 = {
            "course_id": "course_1",
            "assignment_id": "assignment_1",
            "title": "第一次作业",
            "due_at": "2026-11-21 23:59",
        }

        with self.assertRaises(ValueError):
            compare_assignments([], [assignment_1, assignment_2])

class MapAssignmentCoursesTests(unittest.TestCase):
    def test_mapped_courses(self):
        assignment_to_map = {
            "course_id": "course_1",
            "assignment_id": "assignment_1",
            "title": "第一次作业",
            "due_at": "2026-11-20 23:59"
        }
        course_mapping = {"course_1": "Algebra-1"}
        assignment_mapped = assignment_to_map.copy()
        assignment_mapped["local_course"] = "Algebra-1"

        mapped, unmapped = map_assignment_courses([assignment_to_map], course_mapping)
        self.assertEqual(mapped, [assignment_mapped])
        self.assertEqual(unmapped, [])

    def test_unmapped_courses(self):
        assignment_not_to_map = {
            "course_id": "course_2",
            "assignment_id": "assignment_1",
            "title": "第一次作业",
            "due_at": "2026-11-21 23:59"
        }
        course_mapping = {"course_1": "Algebra-1"}

        mapped, unmapped = map_assignment_courses([assignment_not_to_map], course_mapping)
        self.assertEqual(mapped, [])
        self.assertEqual(unmapped, [assignment_not_to_map])

    def test_mixed_courses(self):
        assignment_to_map_1 = {
            "course_id": "course_1",
            "assignment_id": "assignment_1",
            "title": "第一次作业",
            "due_at": "2026-11-20 23:59"
        }
        assignment_to_map_2 = {
            "course_id": "course_1",
            "assignment_id": "assignment_2",
            "title": "第二次作业",
            "due_at": "2026-11-21 23:59"
        }
        assignment_not_to_map_1 = {
            "course_id": "course_2",
            "assignment_id": "assignment_1",
            "title": "第一次作业",
            "due_at": "2026-11-22 23:59"
        }
        assignment_not_to_map_2 = {
            "course_id": "course_2",
            "assignment_id": "assignment_2",
            "title": "第二次作业",
            "due_at": "2026-11-23 23:59"
        }
        course_mapping = {"course_1": "Algebra-1"}
        assignment_mapped_1 = assignment_to_map_1.copy()
        assignment_mapped_1["local_course"] = "Algebra-1"
        assignment_mapped_2 = assignment_to_map_2.copy()
        assignment_mapped_2["local_course"] = "Algebra-1"
        assignments = [assignment_to_map_1, assignment_not_to_map_1, assignment_to_map_2 ,assignment_not_to_map_2]

        mapped, unmapped = map_assignment_courses(assignments, course_mapping)
        self.assertEqual(mapped, [assignment_mapped_1, assignment_mapped_2])
        self.assertEqual(unmapped, [assignment_not_to_map_1, assignment_not_to_map_2])

    def test_keep_input_courses(self):
        assignment_to_map = {
            "course_id": "course_1",
            "assignment_id": "assignment_1",
            "title": "第一次作业",
            "due_at": "2026-11-20 23:59"
        }
        assignment_not_to_map = {
            "course_id": "course_2",
            "assignment_id": "assignment_1",
            "title": "第一次作业",
            "due_at": "2026-11-21 23:59"
        }
        course_mapping = {"course_1": "Algebra-1"}
        original_assignment_to_map = assignment_to_map.copy()
        original_assignment_not_to_map = assignment_not_to_map.copy()
        original_course_mapping = course_mapping.copy()

        map_assignment_courses([assignment_to_map, assignment_not_to_map], course_mapping)
        self.assertEqual(assignment_to_map, original_assignment_to_map)
        self.assertEqual(assignment_not_to_map, original_assignment_not_to_map)
        self.assertEqual(course_mapping, original_course_mapping)


# AI-assisted regression tests for assignment binding behavior.
class AddAssignmentBindingTests(unittest.TestCase):
    def setUp(self):
        self.assignment = {
            "course_id": "course_1",
            "assignment_id": "assignment_1",
            "title": "第一次作业",
            "due_at": "2026-11-20 23:59",
            "local_course": "Analysis-1",
        }
        self.binding = {
            "course_id": "course_1",
            "assignment_id": "assignment_1",
            "local_course": "Analysis-1",
            "local_number": 7,
        }

    def test_add_binding_preserves_existing_order(self):
        first_binding = {
            "course_id": "course_2",
            "assignment_id": "assignment_1",
            "local_course": "Physics-1",
            "local_number": 3,
        }
        second_binding = {
            "course_id": "course_1",
            "assignment_id": "assignment_2",
            "local_course": "Analysis-1",
            "local_number": 6,
        }
        bindings = [first_binding, second_binding]

        actual = add_assignment_binding(bindings, self.assignment, 7)

        self.assertEqual(actual, [first_binding, second_binding, self.binding])
        self.assertIsNot(actual, bindings)

    def test_repeated_binding_is_idempotent(self):
        bindings = [self.binding]
        first_result = add_assignment_binding(bindings, self.assignment, 7)
        changed_assignment = self.assignment.copy()
        changed_assignment["title"] = "更新后的作业标题"
        changed_assignment["due_at"] = "2026-11-22 23:59"

        second_result = add_assignment_binding(first_result, changed_assignment, 7)

        self.assertEqual(first_result, bindings)
        self.assertEqual(second_result, bindings)
        self.assertIsNot(first_result, bindings)
        self.assertIsNot(second_result, first_result)

    def test_platform_assignment_cannot_change_target(self):
        bindings = [self.binding]
        with self.assertRaises(ValueError):
            add_assignment_binding(bindings, self.assignment, 8)

        changed_assignment = self.assignment.copy()
        changed_assignment["local_course"] = "Algebra-1"
        with self.assertRaises(ValueError):
            add_assignment_binding(bindings, changed_assignment, 7)

    def test_local_target_cannot_be_used_by_another_assignment(self):
        bindings = [self.binding]
        other_assignment = self.assignment.copy()
        other_assignment["assignment_id"] = "assignment_2"

        with self.assertRaises(ValueError):
            add_assignment_binding(bindings, other_assignment, 7)

    def test_inputs_are_preserved(self):
        bindings = [self.binding]
        assignment = self.assignment.copy()
        assignment["assignment_id"] = "assignment_2"
        original_bindings = deepcopy(bindings)
        original_assignment = deepcopy(assignment)

        add_assignment_binding(bindings, assignment, 8)

        self.assertEqual(bindings, original_bindings)
        self.assertEqual(assignment, original_assignment)

    def test_binding_uses_only_required_fields(self):
        assignment = self.assignment.copy()
        assignment["description"] = "附加作业说明"
        assignment["attachments"] = [{"name": "题目.pdf"}]

        actual = add_assignment_binding([], assignment, 7)

        self.assertEqual(actual, [self.binding])
