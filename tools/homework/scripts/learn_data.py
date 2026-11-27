from typing import TypedDict
from assignment_data import Assignment, validate_assignment_ids


class LearnHomework(TypedDict):
    baseId: str
    title: str
    deadline: str


def normalize_homeworks(
    course_id: str, homeworks: list[LearnHomework]
) -> list[Assignment]:
    """Normalize homeworks from thu-learn-lib, and check the assignments."""
    assignments = [{
        "course_id": course_id,
        "assignment_id": homework["baseId"],
        "title": homework["title"],
        "due_at": homework["deadline"],
    } for homework in homeworks]

    validate_assignment_ids(assignments)
    return assignments