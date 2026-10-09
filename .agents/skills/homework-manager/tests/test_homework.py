# AI-assisted behavioral tests; all Git mutations stay in disposable local repositories.
import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
from common import HomeworkError, Repository, open_target
ENTRY = SCRIPTS / 'homework.py'


def git(path, *args):
    result = subprocess.run(['git', '-c', 'core.quotepath=false', '-C', str(path), *args], capture_output=True, text=True)
    if result.returncode:
        raise AssertionError(result.stdout + result.stderr)
    return result.stdout.strip()


class HomeworkTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='homework-native-test-')
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.remote = self.base / 'remote.git'
        self.remote.mkdir()
        git(self.remote, 'init', '--bare', '-b', 'main')
        self.root = self.base / '中文 repository'
        self.root.mkdir()
        git(self.root, 'init', '-b', 'main')
        git(self.root, 'config', 'user.name', 'Homework Test')
        git(self.root, 'config', 'user.email', 'homework-test@example.invalid')
        git(self.root, 'config', 'core.autocrlf', 'false')
        self.course = '中文课程'
        for number in (1, 3):
            path = self.root / self.course / str(number)
            path.mkdir(parents=True)
            (path / f'{number}.tex').write_text(r'\documentclass{article}\usepackage[en]{homework}\config{Course Name}{2026 Fall}{3}\begin{document}test\end{document}', encoding='utf-8')
        (self.root / '.gitignore').write_text('*.log\n')
        (self.root / 'README.md').write_text('fixture\n')
        (self.root / 'homework.sty').write_text('% fixture\n')
        (self.root / 'homework.config.json').write_text(json.dumps({'semester': '2026 秋季', 'defaultLanguage': 'zh'}))
        git(self.root, 'add', '--', 'README.md', 'homework.sty', 'homework.config.json', '.gitignore', self.course)
        git(self.root, 'commit', '-m', 'Fixture')
        git(self.root, 'remote', 'add', 'origin', str(self.remote))
        git(self.root, 'push', '--set-upstream', 'origin', 'main')

    def cli(self, *args, env=None):
        return subprocess.run([sys.executable, str(ENTRY), *args, '--repo-path', str(self.root)], cwd=self.base, env=env, capture_output=True, text=True)

    def ok(self, *args):
        result = self.cli(*args)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def branch(self):
        git(self.root, 'switch', '-c', self.course + '-HW3')

    def test_status_reads_unicode_paths(self):
        result = self.ok('Status')
        self.assertIn('next: 4', result.stdout)
        self.assertEqual(git(self.root, 'status', '--porcelain'), '')

    def test_paths_reject_escape_and_symlink(self):
        repo = Repository(self.root)
        self.assertEqual(repo.child(self.course, '3'), self.root / self.course / '3')
        with self.assertRaises(HomeworkError):
            repo.child('..', 'outside')
        (self.root / 'link').symlink_to(self.base, target_is_directory=True)
        with self.assertRaises(HomeworkError):
            repo.child('link', 'outside')
        for name in ('../escape', 'bad\\name', 'CON', 'trailing.'):
            with self.assertRaises(HomeworkError):
                repo.course_path(name, must_exist=False)

    def test_new_homework_preview_has_no_side_effects(self):
        before = git(self.root, 'show-ref')
        result = self.ok('NewHomework', '--course', self.course)
        self.assertIn(self.course + '-HW4', result.stdout)
        self.assertIn('language=en', result.stdout)
        self.assertEqual(git(self.root, 'show-ref'), before)
        self.assertEqual(git(self.root, 'status', '--porcelain'), '')
        self.assertFalse((self.root / self.course / '4').exists())

    def test_other_previews_have_no_side_effects(self):
        self.ok('NewCourse', '--course', 'New Course')
        self.branch()
        self.ok('Switch', '--branch', 'main')
        self.ok('Sync')
        self.ok('Finish')
        self.assertEqual(git(self.root, 'branch', '--show-current'), self.course + '-HW3')
        self.assertEqual(git(self.root, 'status', '--porcelain'), '')
        self.assertFalse((self.root / 'New Course').exists())
        self.assertFalse(git(self.remote, 'branch', '--list', self.course + '-HW3'))

    def test_dirty_worktree_stops_mutations(self):
        (self.root / 'README.md').write_text('user change\n')
        self.branch()
        for args in [('NewCourse', '--course', 'New'), ('NewHomework', '--course', self.course), ('Switch', '--branch', 'main'), ('Finish',)]:
            result = self.cli(*args, '--apply')
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('README.md', result.stderr)
        self.assertEqual((self.root / 'README.md').read_text(), 'user change\n')

    def test_new_course_commits_only_keep(self):
        self.ok('NewCourse', '--course', 'New Course', '--apply')
        self.assertEqual(git(self.root, 'diff-tree', '--no-commit-id', '--name-only', '-r', 'HEAD'), 'New Course/.gitkeep')
        self.assertEqual(git(self.remote, 'rev-parse', 'main'), git(self.root, 'rev-parse', 'HEAD'))

    def test_new_homework_inherits_defaults_and_tracks_compiled_pdf(self):
        self.ok('NewHomework', '--course', self.course, '--apply')
        path = self.root / self.course / '4'
        content = (path / '4.tex').read_text()
        self.assertIn(r'\usepackage[en]{homework}', content)
        self.assertIn(r'\config{Course Name}{2026 秋季}{4}', content)
        self.assertEqual((path / 'homework.sty').read_bytes(), (self.root / 'homework.sty').read_bytes())
        output = path / '4.pdf'
        output.write_bytes(b'compiled PDF')
        self.ok('Sync', '--apply')
        self.assertEqual(git(self.root, 'ls-files', '--', self.course + '/4/4.pdf'), self.course + '/4/4.pdf')
        other = subprocess.run(['git', '-C', str(self.root), 'check-ignore', '--', self.course + '/4/2.pdf'], capture_output=True)
        self.assertEqual(other.returncode, 1)
        self.assertEqual(git(self.remote, 'show', self.course + '-HW4:' + self.course + '/4/4.pdf'), 'compiled PDF')
        self.assertEqual(git(self.root, 'status', '--porcelain'), '')
        self.assertEqual(git(self.remote, 'rev-parse', self.course + '-HW4'), git(self.root, 'rev-parse', 'HEAD'))

    def test_explicit_defaults_are_escaped(self):
        self.ok('NewHomework', '--course', self.course, '--number', '8', '--language', 'zh', '--display-course', 'A&B', '--semester', 'Fall_2026', '--apply')
        content = (self.root / self.course / '8/8.tex').read_text()
        self.assertIn(r'\config{A\&B}{Fall\_2026}{8}', content)
        self.assertIn(r'\usepackage[zh]{homework}', content)

    def test_sync_scopes_commit_and_skips_empty_commit(self):
        self.branch()
        (self.root / 'README.md').write_text('unrelated\n')
        source = self.root / self.course / '3/3.tex'
        source.write_text(source.read_text() + '\n% change\n')
        (source.parent / '3.pdf').write_bytes(b'generated')
        self.ok('Sync', '--apply')
        changed = git(self.root, 'diff-tree', '--no-commit-id', '--name-only', '-r', 'HEAD')
        self.assertEqual(set(changed.splitlines()), {self.course + '/3/3.tex', self.course + '/3/3.pdf'})
        self.assertEqual(git(self.remote, 'show', self.course + '-HW3:' + self.course + '/3/3.pdf'), 'generated')
        self.assertNotIn('README.md', changed)
        before = git(self.root, 'rev-parse', 'HEAD')
        self.ok('Sync', '--apply')
        self.assertEqual(git(self.root, 'rev-parse', 'HEAD'), before)
        self.assertIn('README.md', git(self.root, 'status', '--porcelain'))

    def test_sync_refuses_preexisting_staged_changes_and_main(self):
        self.assertNotEqual(self.cli('Sync', '--course', self.course, '--number', '3', '--apply').returncode, 0)
        self.branch()
        (self.root / 'README.md').write_text('staged user change\n')
        git(self.root, 'add', '--', 'README.md')
        result = self.cli('Sync', '--apply')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('already staged', result.stderr)
        self.assertEqual(git(self.root, 'diff', '--cached', '--name-only'), 'README.md')

    def test_finish_pushes_main_before_cleanup(self):
        self.branch()
        (self.root / self.course / '3/3.tex').write_text('updated\n')
        git(self.root, 'add', '--', self.course + '/3/3.tex')
        git(self.root, 'commit', '-m', 'Update')
        self.ok('Finish', '--apply')
        self.assertEqual(git(self.root, 'branch', '--show-current'), 'main')
        self.assertEqual(git(self.remote, 'rev-parse', 'main'), git(self.root, 'rev-parse', 'main'))
        self.assertEqual(git(self.root, 'branch', '--list', self.course + '-HW3'), '')
        self.assertEqual(git(self.remote, 'branch', '--list', self.course + '-HW3'), '')

    def test_failed_main_push_preserves_both_branches(self):
        self.branch()
        (self.root / self.course / '3/3.tex').write_text('changed on homework branch\n')
        git(self.root, 'add', '--', self.course + '/3/3.tex')
        git(self.root, 'commit', '-m', 'Branch update')
        hook = self.remote / 'hooks/pre-receive'
        hook.write_text('#!/bin/sh\nwhile read old new ref; do\n if [ "$ref" = refs/heads/main ]; then exit 1; fi\ndone\n')
        hook.chmod(0o755)
        result = self.cli('Finish', '--apply')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('No branch was deleted', result.stderr)
        self.assertTrue(git(self.root, 'branch', '--list', self.course + '-HW3'))
        self.assertTrue(git(self.remote, 'branch', '--list', self.course + '-HW3'))
        self.assertEqual(git(self.root, 'branch', '--show-current'), 'main')

    def test_cleanup_failure_is_warning_after_successful_merge(self):
        self.branch()
        hook = self.remote / 'hooks/pre-receive'
        hook.write_text('#!/bin/sh\nwhile read old new ref; do\n case "$new" in 0000000000000000000000000000000000000000) exit 1;; esac\ndone\n')
        hook.chmod(0o755)
        result = self.ok('Finish', '--apply')
        self.assertIn('WARNING:', result.stdout)
        self.assertTrue(git(self.remote, 'branch', '--list', self.course + '-HW3'))
        self.assertEqual(git(self.remote, 'rev-parse', 'main'), git(self.root, 'rev-parse', 'main'))

    def test_compile_unicode_cwd_and_exit_codes(self):
        self.branch()
        binary = self.base / 'bin'
        binary.mkdir()
        fake = binary / 'latexmk'
        fake.write_text('#!/bin/sh\nprintf "%s\\n" "$PWD" "$@" > "$HOMEWORK_TEST_MARKER"\nprintf "diagnostic\\n" > 3.log\nexit "$HOMEWORK_TEST_EXIT"\n')
        fake.chmod(0o755)
        marker = self.base / 'marker.txt'
        env = dict(os.environ, PATH=str(binary) + os.pathsep + os.environ['PATH'], HOMEWORK_TEST_MARKER=str(marker), HOMEWORK_TEST_EXIT='0')
        for code in (0, 7):
            env['HOMEWORK_TEST_EXIT'] = str(code)
            result = self.cli('Compile', env=env)
            self.assertEqual(result.returncode, code, result.stdout + result.stderr)
            self.assertTrue((self.root / self.course / '3/3.log').is_file())
        values = marker.read_text().splitlines()
        self.assertEqual(Path(values[0]), self.root / self.course / '3')
        self.assertIn('-xelatex', values)
        self.assertEqual(values[-1], '3.tex')
        self.assertEqual(self.cli('Compile', '--apply').returncode, 2)

    def test_native_open_preserves_space_and_unicode_arguments(self):
        repo = Repository(self.root)
        expected = {'finder': ['/usr/bin/open', self.root], 'explorer': ['/usr/bin/open', self.root], 'desktop': ['/usr/bin/open', '-a', 'GitHub Desktop', self.root]}
        with patch('common.sys.platform', 'darwin'), patch('common.command') as call, contextlib.redirect_stdout(io.StringIO()):
            for tool, args in expected.items():
                open_target(repo, repo.root, tool)
                call.assert_called_with(args)
            with patch('common.shutil.which', return_value=None):
                open_target(repo, repo.root, 'code')
                call.assert_called_with(['/usr/bin/open', '-a', 'Visual Studio Code', self.root])
        git(self.root, 'remote', 'set-url', 'origin', 'git@github.com:example/Homework.git')
        with patch('common.sys.platform', 'darwin'), patch('common.command') as call, patch.object(repo, 'git', return_value='git@github.com:example/Homework.git'), contextlib.redirect_stdout(io.StringIO()):
            open_target(repo, repo.root, 'web')
            call.assert_called_with(['/usr/bin/open', 'https://github.com/example/Homework'])


if __name__ == '__main__':
    unittest.main()
