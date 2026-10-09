from common import HomeworkError, open_target


def run(repo, args):
    path = repo.root
    if args.course:
        path = repo.course_path(args.course)
    if args.number is not None:
        _, _, path = repo.assignment(args.course, args.number)
    open_target(repo, path, args.tool)
