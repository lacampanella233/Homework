from common import HomeworkError, preview


def run(repo, args):
    course, number, path = repo.assignment(args.course, args.number)
    branch = repo.branch()
    if branch != f'{course}-HW{number}':
        raise HomeworkError('Sync must run on the matching homework branch.')
    relative = repo.git_path(path)
    repo.plan(f'sync {course} homework {number}', [f'stage only {relative}', 'commit if that directory has changes, then push the current branch'])
    print('Current status:\n' + repo.git('status', '--short', '--branch'))
    if preview(args):
        return
    staged = repo.git('diff', '--cached', '--name-only')
    if staged:
        raise HomeworkError('Refusing to mix with already staged changes:\n' + staged)
    repo.git('add', '--', relative)
    diff = repo.git_result('diff', '--cached', '--quiet', '--', relative)
    if diff.returncode == 1:
        repo.git('commit', '-m', args.message or f'Update homework branch {branch}')
    elif diff.returncode:
        raise HomeworkError(f'git diff --cached failed with exit code {diff.returncode}')
    repo.git('push', 'origin', branch)
    print(f'Synced {branch}; unrelated working-tree changes were not staged.')
