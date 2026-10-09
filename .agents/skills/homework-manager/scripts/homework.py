#!/usr/bin/env python3
# AI-assisted migration of the homework manager to Python's standard library.
import argparse
import importlib
from pathlib import Path
import sys

sys.dont_write_bytecode = True
from common import HomeworkError, Repository

ACTIONS = {
    'Status': 'status', 'NewCourse': 'new_course', 'NewHomework': 'new_homework',
    'Compile': 'compile', 'Sync': 'sync', 'Switch': 'switch',
    'Finish': 'finish', 'Open': 'open',
}


def positive_number(value):
    number = int(value)
    if not 1 <= number <= 2147483647:
        raise argparse.ArgumentTypeError('number must be between 1 and 2147483647')
    return number


def main():
    parser = argparse.ArgumentParser(description='Manage Git and LaTeX homework on macOS.')
    parser.add_argument('action', choices=ACTIONS)
    parser.add_argument('--course')
    parser.add_argument('--number', type=positive_number)
    parser.add_argument('--semester')
    parser.add_argument('--language', choices=('auto', 'zh', 'en'), default='auto')
    parser.add_argument('--display-course')
    parser.add_argument('--branch')
    parser.add_argument('--message')
    parser.add_argument('--tool', choices=('code', 'finder', 'explorer', 'web', 'desktop'), default='code')
    parser.add_argument('--repo-path', type=Path, default=Path(__file__).resolve().parents[4])
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--open', action='store_true')
    args = parser.parse_args()
    if args.action in ('Compile', 'Open', 'Status') and args.apply:
        parser.error(f'{args.action} does not accept --apply')
    try:
        repo = Repository(args.repo_path)
        action = importlib.import_module('actions.' + ACTIONS[args.action])
        return action.run(repo, args) or 0
    except (HomeworkError, OSError, ValueError) as error:
        print(f'ERROR: {error}', file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print('Interrupted; source files and compiler logs were preserved.', file=sys.stderr)
        return 130


if __name__ == '__main__':
    sys.exit(main())
