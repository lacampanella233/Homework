from common import HomeworkError, preview


def run(repo, args):
    repo.clean('switch branches')
    if not args.branch:
        raise HomeworkError('Switch requires --branch.')
    repo.git('check-ref-format', '--branch', args.branch)
    if not repo.ref_exists('refs/heads/' + args.branch):
        raise HomeworkError(f"Local branch '{args.branch}' does not exist.")
    repo.plan(f'switch from {repo.branch()} to {args.branch}', [f'switch to {args.branch} and pull origin/{args.branch} with --ff-only'])
    if preview(args):
        return
    repo.git('switch', args.branch)
    repo.git('pull', '--ff-only', 'origin', args.branch)
    print(f'Switched to and updated {args.branch}.')
