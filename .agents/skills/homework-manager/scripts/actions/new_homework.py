import shutil
from common import latex_text, open_target, preview


def run(repo, args):
    repo.clean('create homework')
    path, branch, number, style, semester, language, display = repo.new_assignment(args)
    repo.plan(f'create {args.course} homework {number}', ['switch to main and pull origin/main with --ff-only', f'create and switch to branch {branch}', f'create {args.course}/{number}/{number}.tex and copy root homework.sty', f'semester={semester}; language={language}; course label={display}', f'commit and push {branch} with upstream'] + (['open the assignment in VS Code after push'] if args.open else []))
    if preview(args):
        return
    repo.git('switch', 'main')
    repo.git('pull', '--ff-only', 'origin', 'main')
    repo.clean('create homework')
    path, branch, number, style, semester, language, display = repo.new_assignment(args)
    repo.git('switch', '-c', branch)
    path.mkdir()
    shutil.copyfile(style, path / 'homework.sty')
    source = '\\documentclass{article}\n' + f'\\usepackage[{language}]{{homework}}\n\n' + f'\\config{{{display}}}{{{latex_text(semester)}}}{{{number}}}\n\n' + '\\begin{document}\n\n\n\n\\end{document}\n'
    (path / f'{number}.tex').write_text(source, encoding='utf-8')
    repo.git('add', '--', repo.git_path(path))
    repo.git('commit', '-m', f'Initialize {branch}')
    repo.git('push', '--set-upstream', 'origin', branch)
    print(f'Created and pushed {branch}.')
    if args.open:
        open_target(repo, path, 'code')
