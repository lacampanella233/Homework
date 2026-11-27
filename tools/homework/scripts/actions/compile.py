from pathlib import Path
import os
import shutil
import subprocess
import sys
from common import HomeworkError


def run(repo, args):
    course, number, directory = repo.assignment(args.course, args.number)
    source = directory / f'{number}.tex'
    if not source.is_file():
        raise HomeworkError(f'Assignment source is missing: {source}')
    compiler = shutil.which('latexmk')
    if not compiler and sys.platform == 'darwin':
        candidate = Path('/Library/TeX/texbin/latexmk')
        if candidate.is_file():
            compiler = str(candidate)
    if not compiler:
        raise HomeworkError('latexmk is missing. Install MacTeX and add /Library/TeX/texbin to PATH.')
    print(f'Compiling {course} homework {number}\nSource: {source}', flush=True)
    environment = os.environ.copy()
    if sys.platform == 'darwin' and Path('/Library/TeX/texbin').is_dir():
        environment['PATH'] = environment.get('PATH', '') + os.pathsep + '/Library/TeX/texbin'
    result = subprocess.run([compiler, '-xelatex', '-interaction=nonstopmode', '-halt-on-error', source.name], cwd=directory, env=environment)
    if result.returncode:
        print(f'latexmk failed with exit code {result.returncode}. Logs were preserved in {directory}.', file=sys.stderr)
    else:
        print(f'Compiled {source} successfully (exit code 0).')
    return result.returncode
