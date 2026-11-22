from common import HomeworkError, Repository, preview
from assignment_storage import load_assignments, load_bindings, save_bindings, backup_bindings
from assignment_data import add_assignment_binding
from argparse import Namespace


def run(repo: Repository, args: Namespace) -> None:
    if not args.current:
        raise HomeworkError("BindAssignment requires --current")
    if not args.course_id:
        raise HomeworkError("BindAssignment requires --course-id")
    if not args.assignment_id:
        raise HomeworkError("BindAssignment requires --assignment-id")
    if not args.course:
        raise HomeworkError("BindAssignment requires --course")
    if not args.number:
        raise HomeworkError("BindAssignment requires --number")
    if not args.bindings:
        raise HomeworkError("BindAssignment requires --bindings")

    assignment_path = repo.assignment(course=args.course, number=args.number)[2]
    source_path = assignment_path / f"{args.number}.tex"
    if not source_path.is_file():
        raise HomeworkError(f"Assignment source file does not exist: {source_path}")
    assignments = load_assignments(args.current)
    bindings = load_bindings(args.bindings)
    selected_assignment = None
    for assignment in assignments:
        if assignment["course_id"] == args.course_id and assignment["assignment_id"] == args.assignment_id:
            selected_assignment = assignment
            break
    if selected_assignment == None:
        raise HomeworkError(f"Platform assignments {args.course_id} / {args.assignment_id} is not found.")
    new_bindings = add_assignment_binding(
        bindings, 
        {**selected_assignment, "local_course": args.course}, 
        args.number
    )

    print(
        f"Platform assignments: {selected_assignment['course_id']} / {selected_assignment['assignment_id']}\n",
        f"Title: {selected_assignment['title']}\n",
        f"Local assignment: {assignment_path}\n",
        f"Bindings file: {args.bindings}",
    )

    if new_bindings == bindings:
        print("Operation: none")
    else:
        print("Operation: add binding")
        print(f"Backup path: {args.bindings}.bak")

    if preview(args):
        return
    if new_bindings != bindings:
        backup_bindings(args.bindings)
        save_bindings(args.bindings, new_bindings)
        print("Backed up and saved bindings successfully. The previous backup was covered by the current one.")