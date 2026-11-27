import json
from pathlib import Path
import subprocess
from typing import Union

from assignment_data import Assignment
from common import HomeworkError
from learn_data import normalize_homeworks


def read_node_homeworks(
    course_id: str, script_path: Union[str, Path]
) -> list[Assignment]:
    """Run a Node script and convert its JSON homework list to assignments."""
    try:
        result = subprocess.run(
            ["node", str(Path(script_path).resolve()), course_id],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
        )
    except OSError as error:
        raise HomeworkError("Cannot start Node; check its installation and PATH.") from error
    except subprocess.TimeoutExpired as error:
        raise HomeworkError("Node homework reader timed out after 30 seconds.") from error
    except UnicodeError as error:
        raise HomeworkError("Node homework reader output must be UTF-8.") from error

    # Do not parse failed output or include potentially sensitive diagnostics.
    if result.returncode != 0:
        raise HomeworkError(
            f"Node homework reader failed with exit code {result.returncode}."
        )

    try:
        homeworks = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise HomeworkError("Node homework reader did not return valid JSON.") from error

    if not isinstance(homeworks, list):
        raise HomeworkError("Node homework reader must return a JSON list.")
    for index, homework in enumerate(homeworks, start=1):
        if not isinstance(homework, dict):
            raise HomeworkError(f"Node homework record {index} must be an object.")
        for field in ("baseId", "title", "deadline"):
            if not isinstance(homework.get(field), str):
                raise HomeworkError(
                    f"Node homework record {index}: {field} must be a string."
                )

    return normalize_homeworks(course_id, homeworks)
