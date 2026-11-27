"""Shared data contracts for offline assignment management.

Structures (str/int denote field types; ... denotes more items)::

    assignment = {
        "course_id": str,
        "assignment_id": str,
        "title": str,
        "due_at": str,
    }
    snapshot = [assignment, ...]  # previous or current

    course_mapping = {course_id: local_course, ...}  # str -> str
    mapped_assignment = {**assignment, "local_course": str}

    binding = {
        "course_id": str,
        "assignment_id": str,
        "local_course": str,
        "local_number": int,  # > 0; bool excluded
    }
    bindings = [binding, ...]
    binding_index = {
        (course_id, assignment_id): (local_course, local_number),
    }

Rules:
    - Shown record fields are required; extra fields and empty lists are allowed.
    - Snapshot key: (course_id, assignment_id), unique within each snapshot.
    - Course mappings suggest defaults; mapped records do not confirm bindings.
    - Bindings record confirmed targets, which take precedence over defaults.
    - Binding: platform key <-> (local_course, local_number), both unique.
    - Local directory: <local_course>/<local_number>/.
    - Inputs are preserved; field structure/types are checked in assignment_storage.
    - Read-only input interfaces use Sequence/Mapping; results use list/dict.

AUTOMATION_PLAN.md defines lookup and persistence policy; helpers do not
orchestrate that workflow.

Results:
    - compare_assignments -> (new, updated): complete current records, current order.
      Updates compare title/due_at as strings; previous-only records are omitted.
    - map_assignment_courses -> (mapped, unmapped): input order within each group;
      mapped records are copies with local_course added.
    - build_binding_index -> binding_index; duplicate keys/targets raise ValueError.
    - add_assignment_binding -> new bindings list; same binding adds nothing,
      conflicting bindings raise ValueError.

Documented with AI assistance.
"""


from collections.abc import Mapping, Sequence
from typing import TypedDict


# AI-assisted type annotations; records remain ordinary dictionaries.
class Assignment(TypedDict):
    course_id: str
    assignment_id: str
    title: str
    due_at: str


class MappedAssignment(Assignment):
    local_course: str


class AssignmentBinding(TypedDict):
    course_id: str
    assignment_id: str
    local_course: str
    local_number: int


def validate_assignment_ids(assignments: Sequence[Assignment]) -> None:
    """Check assignment identity uniqueness, raising ValueError on duplicates."""
    platform_ids = set()
    for platform_id in [(assignment["course_id"], assignment["assignment_id"]) for assignment in assignments]:
        if platform_id in platform_ids:
            raise ValueError(f"Repeated assignment identity: {platform_id}")
        else:
            platform_ids.add(platform_id)


def compare_assignments(
    previous: Sequence[Assignment], current: Sequence[Assignment]
) -> tuple[list[Assignment], list[Assignment]]:
    """Compare previous and current assignments, return new and updated assignments respectively."""
    pre_dict= {}
    new, updated= [], []
    validate_assignment_ids(previous)
    validate_assignment_ids(current)
    for pre_assignment in previous:
        pre_dict[(pre_assignment["course_id"], pre_assignment["assignment_id"])] = (pre_assignment["title"], pre_assignment["due_at"])
    for cur_assignment in current:
        if (cur_assignment["course_id"], cur_assignment["assignment_id"]) not in pre_dict.keys(): 
            new.append(cur_assignment)
        elif pre_dict[cur_assignment["course_id"], cur_assignment["assignment_id"]] != (cur_assignment["title"], cur_assignment["due_at"]):
            updated.append(cur_assignment)
    return new, updated


def map_assignment_courses(
    assignments: Sequence[Assignment], course_mapping: Mapping[str, str]
) -> tuple[list[MappedAssignment], list[Assignment]]:
    """Map course_id to local_course, return mapped and unmapped assignments respectively, add 'local_course' field for each mapped course."""
    mapped, unmapped = [], []
    for assignment in assignments:
        if assignment["course_id"] in course_mapping:
            mapped_assignment: MappedAssignment = {
                **assignment,
                "local_course": course_mapping[assignment["course_id"]],
            }
            mapped.append(mapped_assignment)
        else:
            unmapped.append(assignment)
    return mapped, unmapped


def build_binding_index(
    bindings: Sequence[AssignmentBinding],
) -> dict[tuple[str, str], tuple[str, int]]:
    """Build the binding dictionary from platform_id to local_id, check wheather platform_id or local_id is repeated."""
    binded_dict = {}
    for bind in bindings:
        platform_id = (bind["course_id"], bind["assignment_id"])
        local_id = (bind["local_course"], bind["local_number"])
        if platform_id in binded_dict:
            raise ValueError(f"Platform_id {platform_id} is repeated.")
        elif local_id in binded_dict.values():
            raise ValueError(f"Local_id {local_id} is repeated.")
        else:
            binded_dict[platform_id] = local_id
    return binded_dict


def add_assignment_binding(
    bindings: list[AssignmentBinding],
    assignment: MappedAssignment,
    local_number: int,
) -> list[AssignmentBinding]:
    """Return a new list with the assignment binding added if needed, raising ValueError on conflicts."""
    binded_dict = build_binding_index(bindings)
    new_bindings = bindings[:]
    assignment_platform_id = (assignment["course_id"], assignment["assignment_id"])
    assignment_local_id = (assignment["local_course"], local_number)
    if assignment_platform_id in binded_dict:
        if assignment_local_id != binded_dict[assignment_platform_id]:
            raise ValueError(f"Platform assignment '{assignment_platform_id}' has already binded to local assignment '{binded_dict[assignment_platform_id]}'.")
    else:
        if assignment_local_id in binded_dict.values():
            raise ValueError(f"Local assigment '{assignment_local_id}' has already been binded.")
        else:
            new_binding: AssignmentBinding = {
                "course_id": assignment["course_id"],
                "assignment_id": assignment["assignment_id"],
                "local_course": assignment["local_course"],
                "local_number": local_number
            }
            new_bindings.append(new_binding)
    return new_bindings
