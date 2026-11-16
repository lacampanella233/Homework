import json
from pathlib import Path


def load_assignments(path):
    text = Path(path).read_text(encoding = "utf-8")
    data = json.loads(text)

    if not isinstance(data, list):
        raise ValueError("Assignment snapshot must be a list.")
    for index, assignment in enumerate(data):
        if not isinstance(assignment, dict):
            raise ValueError(f"Assignment at index {index} must be a dictionary")
        for field in ["course_id", "assignment_id", "title", "due_at"]:
            if field not in assignment:
                raise ValueError(f"Assignment at index {index} is missing required field '{field}'.")
            elif not isinstance(assignment[field], str):
                raise ValueError(f"Assignment at index {index} field '{field}' must be a string.")
    return data