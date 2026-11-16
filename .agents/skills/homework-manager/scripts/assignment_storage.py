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


def load_bindings(path):
    text = Path(path).read_text(encoding="utf-8")
    data = json.loads(text)

    if not isinstance(data, list):
        raise ValueError("Assignment binding must be a list.")
    for index, binding in enumerate(data):
        if not isinstance(binding, dict):
            raise ValueError(f"Binding at index {index} must be a dictionary.")
        for field in ["course_id", "assignment_id", "local_course", "local_number"]:
            if field not in binding:
                raise ValueError(f"Binding at index {index} is missing required field '{field}'.")
            if field == "local_number" and not (isinstance(binding["local_number"], int) and binding["local_number"] > 0):
                raise ValueError(f"Binding at index {index} field 'local_number' must be a positive integer")
            elif not isinstance(binding[field], str):
                raise ValueError(f"Binding at index {index} field '{field}' must be a")
                