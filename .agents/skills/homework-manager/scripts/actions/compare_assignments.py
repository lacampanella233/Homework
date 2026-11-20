"""Present new and updated assignments from args.previous and args.current.

Shared record formats and comparison rules are documented in assignment_data;
UTF-8 JSON loading and validation are handled by assignment_storage.
"""

from argparse import Namespace

from common import HomeworkError, Repository
from assignment_data import compare_assignments, map_assignment_courses
from assignment_storage import load_assignments, load_course_mapping


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
        print(f"    Due: {updated_assignment['due_at']}")
