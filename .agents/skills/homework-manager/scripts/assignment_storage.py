"""Store assignment snapshots, course mappings, and bindings as UTF-8 JSON.

Loading checks required fields and types; binding loading and saving also
check identity and target uniqueness. Invalid records raise ValueError;
file I/O and JSON parsing errors propagate to the caller.
Saving validates first, writes a temporary file in the target directory,
then replaces the destination and cleans up the temporary file on failure.
"""

import json
from pathlib import Path
from shutil import copyfile
from assignment_data import build_binding_index, validate_assignment_ids
from tempfile import NamedTemporaryFile
from typing import Union


def load_assignments(path):
    "Load assignments json file from path."
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
    validate_assignment_ids(data)
    return data


def load_course_mapping(path: Union[str, Path]) -> dict[str, str]:
    """Load a course mapping from a UTF-8 JSON file."""
    text = Path(path).read_text(encoding = "utf-8")
    data = json.loads(text)

    if not isinstance(data, dict):
        raise ValueError("Course mapping must be a dictionary.")
    for course_id, local_course in data.items():
        if not isinstance(local_course, str):
            raise ValueError(f"Local course with course_id {course_id} must be a string.")
    return data


def _validate_binding_fields(bindings):
    """Validate binding structure and field values, raising ValueError for invalid data."""
    if not isinstance(bindings, list):
        raise ValueError("Assignment binding must be a list.")
    for index, binding in enumerate(bindings):
        if not isinstance(binding, dict):
            raise ValueError(f"Binding at index {index} must be a dictionary.")
        for field in ["course_id", "assignment_id", "local_course", "local_number"]:
            if field not in binding:
                raise ValueError(f"Binding at index {index} is missing required field '{field}'.")
            if field == "local_number":
                number = binding[field]
                if type(number) is not int or number <= 0:
                    raise ValueError(f"Binding at index {index} field 'local_number' must be a positive integer")
            elif not isinstance(binding[field], str):
                raise ValueError(f"Binding at index {index} field '{field}' must be a string.")


def load_bindings(path):
    text = Path(path).read_text(encoding="utf-8")
    data = json.loads(text)

    _validate_binding_fields(data)
    build_binding_index(data)
    return data


def save_bindings(path, bindings):
    """Save validated bindings via a temporary file and clean it up on failure."""
    path = Path(path)
    _validate_binding_fields(bindings)
    build_binding_index(bindings)
    temp_path = None
    try:
        with NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, delete=False
        ) as file:
            temp_path = Path(file.name)
            json.dump(bindings, file, ensure_ascii=False, indent=2)
        temp_path.replace(path)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


# AI-assisted implementation.
def backup_bindings(path: Union[str, Path]) -> Path:
    """Copy bindings to a fixed .bak file, overwriting the previous backup."""
    path = Path(path)
    backup_path = path.with_name(path.name + ".bak")
    copyfile(path, backup_path)
    return backup_path
