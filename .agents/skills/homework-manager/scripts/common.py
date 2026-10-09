import json
from pathlib import Path
import re
import shutil
import subprocess
import sys


class HomeworkError(Exception):
    pass


def command(arguments, cwd=None, check=True):
    result = subprocess.run([str(arg) for arg in arguments], cwd=cwd,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, encoding='utf-8', errors='replace')
    if check and result.returncode:
        raise HomeworkError(f"{' '.join(map(str, arguments))} failed with exit code {result.returncode}\n{result.stdout.strip()}")
    return result


def one_line(value, label):
    if not isinstance(value, str) or not value or value != value.strip() or '\n' in value or '\r' in value or len(value) > 100:
        raise HomeworkError(f'{label} must be a trimmed, single-line string of 100 characters or fewer.')
    return value


def latex_text(value):
    replacements = {'\\': r'\textbackslash{}', '{': r'\{', '}': r'\}', '$': r'\$',
                    '&': r'\&', '#': r'\#', '%': r'\%', '_': r'\_',
                    '~': r'\textasciitilde{}', '^': r'\textasciicircum{}'}
    return ''.join(replacements.get(char, char) for char in value)


class Repository:
    def __init__(self, path):
        if not shutil.which('git'):
            raise HomeworkError('git is missing. Install the macOS Command Line Tools.')
        self.root = Path(command(['git', '-C', Path(path).expanduser().resolve(), 'rev-parse', '--show-toplevel']).stdout.strip()).resolve()
        if not self.ref_exists('refs/heads/main'):
            raise HomeworkError(f'Required local main branch is missing in {self.root}')

    def git_result(self, *arguments):
        return command(['git', '-c', 'core.quotepath=false', '-C', self.root, *arguments], check=False)

    def git(self, *arguments):
        result = self.git_result(*arguments)
        if result.returncode:
            raise HomeworkError(f"git {' '.join(arguments)} failed with exit code {result.returncode}\n{result.stdout.strip()}")
        return result.stdout.strip()

    def ref_exists(self, name):
        return self.git_result('show-ref', '--verify', '--quiet', name).returncode == 0

    def branch(self):
        name = self.git('branch', '--show-current')
        if not name:
            raise HomeworkError('Cannot continue from a detached HEAD.')
        return name

    def clean(self, operation):
        changes = self.git('status', '--porcelain', '--untracked-files=all')
        if changes:
            raise HomeworkError(f'Cannot {operation} because the worktree is not clean:\n{changes}')

    def child(self, *segments):
        target = self.root.joinpath(*segments).resolve()
        try:
            target.relative_to(self.root)
        except ValueError:
            raise HomeworkError(f'Path escapes the repository: {target}')
        return target

    def git_path(self, path):
        return Path(path).resolve().relative_to(self.root).as_posix()

    def course_path(self, name, must_exist=True):
        one_line(name, 'Course name')
        # Preserve portable names so the repository can still be checked out on Windows.
        if name in ('.', '..') or re.search(r'[<>:"/\\|?*\x00-\x1f]', name) or name.endswith('.') or re.match(r'^(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?$', name, re.I):
            raise HomeworkError(f"Course name '{name}' is reserved or unsafe.")
        path = self.child(name)
        if must_exist and not path.is_dir():
            raise HomeworkError(f"Course '{name}' does not exist.")
        return path

    def config(self):
        path = self.child('homework.config.json')
        try:
            data = json.loads(path.read_text(encoding='utf-8-sig'))
        except (OSError, ValueError) as error:
            raise HomeworkError(f'Cannot read repository configuration {path}: {error}')
        if not isinstance(data, dict):
            raise HomeworkError('homework.config.json must contain an object.')
        one_line(data.get('semester'), 'semester')
        if data.get('defaultLanguage') not in ('zh', 'en'):
            raise HomeworkError("defaultLanguage must be 'zh' or 'en'.")
        return data

    def next_number(self, course):
        return max((int(path.name) for path in course.iterdir() if path.is_dir() and re.fullmatch(r'[0-9]+', path.name)), default=0) + 1

    def new_assignment(self, args):
        course = self.course_path(args.course)
        number = args.number if args.number is not None else self.next_number(course)
        if number > 2147483647:
            raise HomeworkError('The next homework number exceeds the supported range.')
        path = self.child(args.course, str(number))
        branch = f'{args.course}-HW{number}'
        self.git('check-ref-format', '--branch', branch)
        if path.exists() or self.ref_exists('refs/heads/' + branch) or self.ref_exists('refs/remotes/origin/' + branch):
            raise HomeworkError(f'Assignment path or branch already exists: {path}; {branch}')
        style = self.child('homework.sty')
        if not style.is_file():
            raise HomeworkError(f'Root homework.sty is missing: {style}')
        config = self.config()
        semester = one_line(args.semester if args.semester is not None else config['semester'], 'semester')
        language = args.language if args.language != 'auto' else config['defaultLanguage']
        display = latex_text(args.display_course if args.display_course is not None else args.course)
        latest = sorted((p for p in course.iterdir() if p.is_dir() and re.fullmatch(r'[0-9]+', p.name)), key=lambda p: int(p.name), reverse=True)
        for directory in latest:
            source = directory / (directory.name + '.tex')
            if source.is_file():
                content = source.read_text(encoding='utf-8-sig')
                match = re.search(r'\\usepackage(?:\[(zh|en)\])?\{homework\}', content)
                if args.language == 'auto' and match:
                    language = match.group(1) or 'zh'
                match = re.search(r'\\config\{([^}]*)\}\{[^}]*\}\{[^}]*\}', content)
                if args.display_course is None and match:
                    display = match.group(1)
                break
        return path, branch, number, style, semester, language, display

    def assignment(self, course=None, number=None):
        branch = self.branch()
        match = re.fullmatch(r'(.+)-HW([1-9][0-9]*)', branch)
        if match:
            course = course or match.group(1)
            number = number if number is not None else int(match.group(2))
        if not course or number is None:
            raise HomeworkError('Cannot infer the assignment. Supply --course and --number.')
        self.course_path(course)
        path = self.child(course, str(number))
        if not path.is_dir():
            raise HomeworkError(f'Assignment directory does not exist: {path}')
        return course, number, path

    def plan(self, title, steps):
        print(f'PLAN: {title}\nRepository: {self.root}\nCurrent branch: {self.branch()}')
        for step in steps:
            print('  ' + step)


def preview(args):
    if not args.apply:
        print('Preview only; add --apply to execute.')
        return True
    return False


def open_target(repo, path, tool):
    if sys.platform != 'darwin':
        raise HomeworkError('Open requires macOS.')
    if tool == 'code':
        if shutil.which('code'):
            command(['code', path])
        else:
            command(['/usr/bin/open', '-a', 'Visual Studio Code', path])
    elif tool in ('finder', 'explorer'):
        command(['/usr/bin/open', path])
    elif tool == 'web':
        url = repo.git('remote', 'get-url', 'origin')
        match = re.fullmatch(r'git@github\.com:(.+)', url)
        if match:
            url = 'https://github.com/' + match.group(1)
        url = re.sub(r'\.git$', '', url)
        if not url.startswith('https://github.com/'):
            raise HomeworkError(f'Unsupported GitHub remote URL: {url}')
        command(['/usr/bin/open', url])
    elif tool == 'desktop':
        command(['/usr/bin/open', '-a', 'GitHub Desktop', repo.root])
    print(f'Opened {tool} for {path}')
