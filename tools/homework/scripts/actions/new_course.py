from common import HomeworkError, preview


def run(repo, args):
    repo.clean('create a course')
    course = repo.course_path(args.course, must_exist=False)
    if course.exists():
        raise HomeworkError(f'Course already exists: {course}')
    repo.plan(f"create course '{args.course}'", ['switch to main and pull origin/main with --ff-only', f'create {args.course}/.gitkeep', 'commit and push main'])
    if preview(args):
        return
    repo.git('switch', 'main')
    repo.git('pull', '--ff-only', 'origin', 'main')
    repo.clean('create a course')
    if course.exists():
        raise HomeworkError(f'Course already exists after updating main: {course}')
    course.mkdir()
    keep = course / '.gitkeep'
    keep.touch()
    repo.git('add', '--', repo.git_path(keep))
    repo.git('commit', '-m', f'Add new course: {args.course}')
    repo.git('push', 'origin', 'main')
    print(f'Created and pushed course {args.course}.')
