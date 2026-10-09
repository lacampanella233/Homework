import re
from common import HomeworkError, preview


def run(repo, args):
    repo.clean('finish homework')
    branch = repo.branch()
    match = re.fullmatch(r'(.+)-HW([1-9][0-9]*)', branch)
    if not match:
        raise HomeworkError('Finish must run from a homework branch, not main or another branch.')
    repo.assignment(match.group(1), int(match.group(2)))
    repo.plan(f'finish and merge {branch}', [f'push origin/{branch}', 'switch to main and pull origin/main with --ff-only', f'merge {branch} into main with --no-ff and push main', f'after successful main push, delete origin/{branch} and local {branch}'])
    if preview(args):
        return
    repo.git('push', 'origin', branch)
    try:
        repo.git('switch', 'main')
        repo.git('pull', '--ff-only', 'origin', 'main')
    except HomeworkError:
        repo.git_result('switch', branch)
        raise
    try:
        repo.git('merge', '--no-ff', branch, '-m', f'Merge homework branch {branch} to main (via homework-manager skill)')
    except HomeworkError as error:
        abort = repo.git_result('merge', '--abort')
        back = repo.git_result('switch', branch)
        raise HomeworkError(f'Merge failed; homework branch was preserved. Abort exit: {abort.returncode}; return-to-branch exit: {back.returncode}.\n{error}')
    try:
        repo.git('push', 'origin', 'main')
    except HomeworkError as error:
        raise HomeworkError(f'The merge exists locally on main, but pushing main failed. No branch was deleted.\n{error}')
    print(f'Merged and pushed {branch} to main.')
    for arguments in [('push', 'origin', '--delete', branch), ('branch', '-d', branch)]:
        result = repo.git_result(*arguments)
        if result.returncode:
            print('WARNING: branch cleanup failed: ' + result.stdout.strip())
