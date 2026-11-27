"""Present new and updated assignments from args.previous and args.current.

Shared record formats and comparison rules are documented in assignment_data;
UTF-8 JSON loading and validation are handled by assignment_storage.
"""

from argparse import Namespace
import sys
from common import HomeworkError, Repository
from assignment_data import compare_assignments, map_assignment_courses, build_binding_index
from assignment_storage import load_assignments, load_course_mapping, load_bindings


def run(repo: Repository, args: Namespace) -> None:
    if not args.previous:
        raise HomeworkError("CompareAssignments requires --previous.")
    if not args.current:
        raise HomeworkError("CompareAssignments requires --current.")
    pre_assignments = load_assignments(args.previous)
    cur_assignments = load_assignments(args.current)
    new_assignments, updated_assignments = compare_assignments(pre_assignments, cur_assignments)
    if args.course_mapping:
        course_mapping = load_course_mapping(args.course_mapping)
        mapped_new_assignments, unmapped_new_assignments = map_assignment_courses(new_assignments, course_mapping)
        mapped_updated_assignments, unmapped_updated_assignments = map_assignment_courses(updated_assignments, course_mapping)
    if args.bindings:
        bindings = build_binding_index(load_bindings(args.bindings))

    if args.course_mapping and args.bindings:
        for assignment in new_assignments + updated_assignments:
            platform_id = (assignment["course_id"], assignment["assignment_id"])
            if (platform_id in bindings) and (assignment["course_id"] in course_mapping) and (bindings[platform_id][0] != course_mapping[assignment["course_id"]]):
                print(f"WARNING: [{assignment['course_id']} / {assignment['assignment_id']}] Default course {course_mapping[assignment['course_id']]} differs from bound course {bindings[platform_id][0]}", file=sys.stderr)

    print(f"New assignments ({len(new_assignments)})")
    for new_assignment in new_assignments:
        print(
            (f"  [{new_assignment['course_id']} / {new_assignment['assignment_id']}] "
             f"{new_assignment['title']}")
        )
        if args.course_mapping:
            if new_assignment in unmapped_new_assignments:
                print("    Local course: (unmapped)")
            else:
                print(f"    Local course: {course_mapping[new_assignment['course_id']]}")
        if args.bindings:
            platform_id = (new_assignment["course_id"], new_assignment["assignment_id"])
            if platform_id in bindings:
                print(f"    Local assignment: {bindings[platform_id][0]}/{bindings[platform_id][1]}")
            else:
                print("    Local assignment: (unbound)")
        print(f"    Due: {new_assignment['due_at']}")

    print(f"\nUpdated assignments ({len(updated_assignments)})")
    for updated_assignment in updated_assignments:
        print(
            (f"  [{updated_assignment['course_id']} / {updated_assignment['assignment_id']}] "
             f"{updated_assignment['title']}")
        )
        if args.course_mapping:
            if updated_assignment in unmapped_updated_assignments:
                print("    Local course: (unmapped)")
            else:
                print(f"    Local course: {course_mapping[updated_assignment['course_id']]}")
        if args.bindings:
            platform_id = (updated_assignment["course_id"], updated_assignment["assignment_id"])
            if platform_id in bindings:
                print(f"    Local assignment: {bindings[platform_id][0]}/{bindings[platform_id][1]}")
            else:
                print("    Local assignment: (unbound)")
        print(f"    Due: {updated_assignment['due_at']}")
