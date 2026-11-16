def compare_assignments(previous, current):
    """Compare previous and current assignments, return new and updated assignments respectively."""
    pre_dict= {}
    new, updated= [], []
    pre_ids, cur_ids = set(), set()
    for pre_id in [(pre_assignment["course_id"], pre_assignment["assignment_id"]) for pre_assignment in previous]:
        if pre_id in pre_ids:
            raise ValueError(f"Repeated assigment id in previous: {pre_id}")
        else:
            pre_ids.add(pre_id)
    for cur_id in [(cur_assignment["course_id"], cur_assignment["assignment_id"]) for cur_assignment in current]:
        if cur_id in cur_ids:
            raise ValueError(f"Repeated assigment id in current: {cur_id}")
        else:
            cur_ids.add(cur_id)
    for pre_assignment in previous:
        pre_dict[(pre_assignment["course_id"], pre_assignment["assignment_id"])] = (pre_assignment["title"], pre_assignment["due_at"])
    for cur_assignment in current:
        if (cur_assignment["course_id"], cur_assignment["assignment_id"]) not in pre_dict.keys(): 
            new.append(cur_assignment)
        elif pre_dict[cur_assignment["course_id"], cur_assignment["assignment_id"]] != (cur_assignment["title"], cur_assignment["due_at"]):
            updated.append(cur_assignment)
    return new, updated


def map_assignment_courses(assignments, course_mapping):
    """Map course_id to local_course, return mapped and unmapped assignments respectively, add 'local_course' field for each mapped course."""
    mapped, unmapped = [], []
    for assignment in assignments:
        if assignment["course_id"] in course_mapping:
            mapped_assignment = assignment.copy()
            mapped_assignment["local_course"] = course_mapping[assignment["course_id"]]
            mapped.append(mapped_assignment)
        else:
            unmapped.append(assignment)
    return mapped, unmapped


def build_binding_index(bindings):
    """Build the binding dictionary from platform_id to local_id."""
    binded_dict = {}
    for bind in bindings:
        binded_dict[(bind["course_id"], bind["assignment_id"])] = (bind["local_course"], bind["local_number"])
    return binded_dict


def add_assignment_binding(bindings, assignment, local_number):
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
            new_binding = {
                "course_id": assignment["course_id"],
                "assignment_id": assignment["assignment_id"],
                "local_course": assignment["local_course"],
                "local_number": local_number
            }
            new_bindings.append(new_binding)
    return new_bindings