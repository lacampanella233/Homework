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
from argparse import Namespace
from actions.bind_assignment import run as bind_assignment
from homework import main as homework_main
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
        (self.root / '.gitignore').write_text(f'*.log\n*.[pP][dD][fF]\n!/{self.course}/1/1.pdf\n!/{self.course}/3/3.pdf\n')
        (self.root / 'README.md').write_text('fixture\n')
        (self.root / 'homework.sty').write_text('% fixture\n')
        (self.root / 'homework.config.json').write_text(json.dumps({'courses': {self.course: {'semester': '2026 秋季', 'defaultLanguage': 'zh'}}}))
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

    def write_json(self, name, data):
        path = self.base / name
        path.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
        return path

    def branch(self):
        git(self.root, 'switch', '-c', self.course + '-HW3')

    def test_status_reads_unicode_paths(self):
        result = self.ok('Status')
        self.assertIn('next: 4', result.stdout)
        self.assertEqual(git(self.root, 'status', '--porcelain'), '')

    def test_default_repo_uses_program_location_outside_cwd(self):
        scripts = self.root / 'tools' / 'homework' / 'scripts'
        shutil.copytree(SCRIPTS, scripts)

        result = subprocess.run(
            [sys.executable, str(scripts / 'homework.py'), 'Status'],
            cwd=self.base, capture_output=True, text=True,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(f'Repository: {self.root}', result.stdout)
        self.assertIn('Current branch: main', result.stdout)
        self.assertIn('next: 4', result.stdout)

    def test_compare_assignments_reports_new_and_updated(self):
        old_assignment = {
            'course_id': 'course_1',
            'assignment_id': 'assignment_1',
            'title': '第一次作业',
            'due_at': '2026-11-20 23:59',
        }
        updated_assignment = dict(old_assignment, due_at='2026-11-21 23:59')
        new_assignment = {
            'course_id': 'course_1',
            'assignment_id': 'assignment_2',
            'title': '第二次作业',
            'due_at': '2026-11-22 23:59',
        }
        previous_path = self.base / 'previous.json'
        current_path = self.base / 'current.json'
        previous_path.write_text(
            json.dumps([old_assignment], ensure_ascii=False), encoding='utf-8'
        )
        current_path.write_text(
            json.dumps([updated_assignment, new_assignment], ensure_ascii=False),
            encoding='utf-8',
        )

        result = self.ok(
            'CompareAssignments',
            '--previous', str(previous_path),
            '--current', str(current_path),
        )

        expected_output = (
            'New assignments (1)\n'
            '  [course_1 / assignment_2] 第二次作业\n'
            '    Due: 2026-11-22 23:59\n'
            '\n'
            'Updated assignments (1)\n'
            '  [course_1 / assignment_1] 第一次作业\n'
            '    Due: 2026-11-21 23:59\n'
        )
        self.assertEqual(result.stdout, expected_output)
        self.assertEqual(result.stderr, '')

    def test_compare_assignments_requires_previous(self):
        current_path = self.base / 'current.json'
        current_path.write_text('[]', encoding='utf-8')

        result = self.cli('CompareAssignments', '--current', str(current_path))

        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, '')
        self.assertIn('CompareAssignments requires --previous.', result.stderr)

    def test_compare_assignments_requires_current(self):
        previous_path = self.base / 'previous.json'
        previous_path.write_text('[]', encoding='utf-8')

        result = self.cli('CompareAssignments', '--previous', str(previous_path))

        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, '')
        self.assertIn('CompareAssignments requires --current.', result.stderr)

    def test_compare_assignments_mapping_preserves_order_and_inputs(self):
        old_mapped = dict(course_id='course_1', assignment_id='old',
                          title='已映射作业', due_at='2026-11-20')
        old_unmapped = dict(old_mapped, course_id='course_2', title='未映射作业')
        updated_mapped = dict(old_mapped, due_at='2026-11-21')
        updated_unmapped = dict(old_unmapped, due_at='2026-11-21')
        new_mapped = dict(old_mapped, assignment_id='new', title='新增已映射')
        new_unmapped = dict(old_unmapped, assignment_id='new', title='新增未映射')
        previous_path = self.base / 'previous.json'
        current_path = self.base / 'current.json'
        mapping_path = self.base / '课程 mapping.json'
        inputs = (
            (previous_path, [old_mapped, old_unmapped]),
            (current_path, [new_unmapped, new_mapped, updated_unmapped, updated_mapped]),
            (mapping_path, {'course_1': '代数课程'}),
        )
        for path, data in inputs:
            path.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
        original_contents = {path: path.read_bytes() for path, _ in inputs}
        original_refs = git(self.root, 'show-ref')

        result = self.ok(
            'CompareAssignments', '--previous', str(previous_path),
            '--current', str(current_path),
            '--course-mapping', mapping_path.name,
        )

        expected_output = (
            'New assignments (2)\n'
            '  [course_2 / new] 新增未映射\n'
            '    Local course: (unmapped)\n'
            '    Due: 2026-11-20\n'
            '  [course_1 / new] 新增已映射\n'
            '    Local course: 代数课程\n'
            '    Due: 2026-11-20\n'
            '\n'
            'Updated assignments (2)\n'
            '  [course_2 / old] 未映射作业\n'
            '    Local course: (unmapped)\n'
            '    Due: 2026-11-21\n'
            '  [course_1 / old] 已映射作业\n'
            '    Local course: 代数课程\n'
            '    Due: 2026-11-21\n'
        )
        self.assertEqual(result.stdout, expected_output)
        self.assertEqual(result.stderr, '')
        for path, contents in original_contents.items():
            self.assertEqual(path.read_bytes(), contents)
        self.assertEqual(git(self.root, 'show-ref'), original_refs)
        self.assertEqual(git(self.root, 'status', '--porcelain'), '')

    def test_compare_assignments_empty_mapping_keeps_assignments(self):
        previous_path = self.base / 'previous.json'
        current_path = self.base / 'current.json'
        mapping_path = self.base / 'courses.json'
        assignment = dict(course_id='course_1', assignment_id='assignment_1',
                          title='作业', due_at='2026-11-20')
        previous_path.write_text('[]', encoding='utf-8')
        current_path.write_text(json.dumps([assignment]), encoding='utf-8')
        mapping_path.write_text('{}', encoding='utf-8')

        result = self.ok(
            'CompareAssignments', '--previous', str(previous_path),
            '--current', str(current_path), '--course-mapping', str(mapping_path),
        )

        self.assertIn('New assignments (1)', result.stdout)
        self.assertIn('[course_1 / assignment_1] 作业', result.stdout)
        self.assertIn('    Local course: (unmapped)\n', result.stdout)
        self.assertEqual(result.stderr, '')

    def test_compare_assignments_reports_mapping_file_errors(self):
        previous_path = self.base / 'previous.json'
        current_path = self.base / 'current.json'
        mapping_path = self.base / 'courses.json'
        previous_path.write_text('[]', encoding='utf-8')
        current_path.write_text('[]', encoding='utf-8')
        cases = (
            ('missing file', None, mapping_path.name),
            ('invalid JSON', '{', 'ERROR:'),
            ('wrong structure', '[]', 'dictionary'),
            ('wrong value type', '{"course_1": 1}', 'course_1'),
        )
        for name, contents, expected_error in cases:
            with self.subTest(case=name):
                if contents is None:
                    mapping_path.unlink(missing_ok=True)
                else:
                    mapping_path.write_text(contents, encoding='utf-8')
                result = self.cli(
                    'CompareAssignments', '--previous', str(previous_path),
                    '--current', str(current_path),
                    '--course-mapping', str(mapping_path),
                )
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, '')
                self.assertIn('ERROR:', result.stderr)
                self.assertIn(expected_error, result.stderr)
                self.assertNotIn('Traceback', result.stderr)

    def test_compare_assignments_bindings_preserve_order_and_inputs(self):
        old_bound = dict(course_id='course_1', assignment_id='old',
                         title='更新已绑定', due_at='2026-11-20')
        old_unbound = dict(old_bound, course_id='course_2', title='更新未绑定')
        new_bound = dict(old_bound, assignment_id='new', title='新增已绑定')
        new_unbound = dict(old_unbound, assignment_id='new', title='新增未绑定')
        previous = self.write_json('previous.json', [old_bound, old_unbound])
        current = self.write_json('current.json', [
            new_unbound, new_bound,
            dict(old_unbound, due_at='2026-11-21'),
            dict(old_bound, due_at='2026-11-21'),
        ])
        bindings = self.write_json('作业 bindings.json', [
            dict(course_id='course_1', assignment_id='new',
                 local_course='Algebra-1', local_number=7),
            dict(course_id='course_1', assignment_id='old',
                 local_course='Algebra-1', local_number=6),
        ])
        originals = {path: path.read_bytes() for path in (previous, current, bindings)}
        original_refs = git(self.root, 'show-ref')
        original_status = git(self.root, 'status', '--porcelain')

        result = self.ok(
            'CompareAssignments', '--previous', str(previous),
            '--current', str(current), '--bindings', bindings.name,
        )

        expected_output = (
            'New assignments (2)\n'
            '  [course_2 / new] 新增未绑定\n'
            '    Local assignment: (unbound)\n'
            '    Due: 2026-11-20\n'
            '  [course_1 / new] 新增已绑定\n'
            '    Local assignment: Algebra-1/7\n'
            '    Due: 2026-11-20\n'
            '\n'
            'Updated assignments (2)\n'
            '  [course_2 / old] 更新未绑定\n'
            '    Local assignment: (unbound)\n'
            '    Due: 2026-11-21\n'
            '  [course_1 / old] 更新已绑定\n'
            '    Local assignment: Algebra-1/6\n'
            '    Due: 2026-11-21\n'
        )
        self.assertEqual(result.stdout, expected_output)
        self.assertEqual(result.stderr, '')
        for path, contents in originals.items():
            self.assertEqual(path.read_bytes(), contents)
        self.assertEqual(git(self.root, 'show-ref'), original_refs)
        self.assertEqual(git(self.root, 'status', '--porcelain'), original_status)

    def test_compare_assignments_empty_bindings_keep_assignments(self):
        assignment = dict(course_id='course_1', assignment_id='hw_1',
                          title='作业', due_at='2026-11-20')
        previous = self.write_json('previous.json', [])
        current = self.write_json('current.json', [assignment])
        bindings = self.write_json('bindings.json', [])
        mapping = self.write_json('courses.json', {'course_1': 'Algebra-1'})

        result = self.ok(
            'CompareAssignments', '--previous', str(previous),
            '--current', str(current), '--bindings', str(bindings),
            '--course-mapping', str(mapping),
        )

        self.assertIn('New assignments (1)', result.stdout)
        self.assertIn('[course_1 / hw_1] 作业', result.stdout)
        self.assertIn('Local course: Algebra-1\n    Local assignment: (unbound)\n',
                      result.stdout)
        self.assertEqual(result.stderr, '')

    def test_compare_assignments_warns_without_changing_bindings(self):
        new = dict(course_id='course_1', assignment_id='new',
                   title='新增作业', due_at='2026-11-21')
        old = dict(new, course_id='course_2', assignment_id='old', title='更新作业')
        unchanged = dict(new, course_id='course_3', assignment_id='unchanged')
        previous = self.write_json('previous.json', [old, unchanged])
        current = self.write_json('current.json', [
            new, dict(old, due_at='2026-11-22'), unchanged,
        ])
        bindings = self.write_json('bindings.json', [
            dict(course_id='course_1', assignment_id='new',
                 local_course='Algebra-1', local_number=7),
            dict(course_id='course_2', assignment_id='old',
                 local_course='Physics-1', local_number=6),
            dict(course_id='course_3', assignment_id='unchanged',
                 local_course='Unchanged bound course', local_number=1),
        ])
        mapping = self.write_json('courses.json', {
            'course_1': 'Analysis-1', 'course_2': 'Analysis-0',
            'course_3': 'Unchanged default course',
        })
        originals = {p: p.read_bytes() for p in (previous, current, bindings, mapping)}

        result = self.ok(
            'CompareAssignments', '--previous', str(previous),
            '--current', str(current), '--bindings', str(bindings),
            '--course-mapping', str(mapping),
        )

        warnings = result.stderr.splitlines()
        self.assertEqual(len(warnings), 2)
        for line, identity, default, bound in (
            (warnings[0], '[course_1 / new]', 'Analysis-1', 'Algebra-1'),
            (warnings[1], '[course_2 / old]', 'Analysis-0', 'Physics-1'),
        ):
            self.assertTrue(line.startswith('WARNING:'))
            for field in (identity, default, bound):
                self.assertIn(field, line)
        self.assertIn('New assignments (1)', result.stdout)
        self.assertIn('Updated assignments (1)', result.stdout)
        self.assertIn('Local course: Analysis-1\n    Local assignment: Algebra-1/7\n',
                      result.stdout)
        self.assertIn('Local course: Analysis-0\n    Local assignment: Physics-1/6\n',
                      result.stdout)
        self.assertNotIn('WARNING:', result.stdout)
        for path, contents in originals.items():
            self.assertEqual(path.read_bytes(), contents)

    def test_compare_assignments_does_not_warn_without_relevant_difference(self):
        assignment = dict(course_id='course_1', assignment_id='hw_1',
                          title='作业', due_at='2026-11-20')
        binding = dict(course_id='course_1', assignment_id='hw_1',
                       local_course='Algebra-1', local_number=7)
        different_default = {'course_1': 'Analysis-1'}
        cases = (
            ('same course', [], [assignment], {'course_1': 'Algebra-1'}, [binding], True, True),
            ('missing default', [], [assignment], {}, [binding], True, True),
            ('unbound', [], [assignment], different_default, [], True, True),
            ('unchanged', [assignment], [assignment], different_default, [binding], True, True),
            ('absent from current', [assignment], [], different_default, [binding], True, True),
            ('only mapping', [], [assignment], different_default, [binding], True, False),
            ('only bindings', [], [assignment], different_default, [binding], False, True),
        )
        for name, old, new, defaults, records, use_mapping, use_bindings in cases:
            with self.subTest(case=name):
                previous = self.write_json('previous.json', old)
                current = self.write_json('current.json', new)
                mapping = self.write_json('courses.json', defaults)
                bindings = self.write_json('bindings.json', records)
                args = ['CompareAssignments', '--previous', str(previous),
                        '--current', str(current)]
                if use_mapping:
                    args += ['--course-mapping', str(mapping)]
                if use_bindings:
                    args += ['--bindings', str(bindings)]

                result = self.ok(*args)

                self.assertEqual(result.stderr, '')
                if not use_bindings:
                    self.assertNotIn('Local assignment:', result.stdout)
                if use_bindings and name in ('same course', 'missing default', 'only bindings'):
                    self.assertIn('Local assignment: Algebra-1/7', result.stdout)

    def test_compare_assignments_reports_binding_file_errors_before_output(self):
        assignment = dict(course_id='course_1', assignment_id='hw_1',
                          title='作业', due_at='2026-11-20')
        binding = dict(course_id='course_1', assignment_id='hw_1',
                       local_course='Algebra-1', local_number=7)
        previous = self.write_json('previous.json', [])
        bindings = self.base / 'bindings.json'
        cases = (
            ('missing file', None),
            ('invalid JSON', '['),
            ('wrong container', '{}'),
            ('wrong record', '[1]'),
            ('missing field', json.dumps([{'course_id': 'course_1'}])),
            ('invalid number', json.dumps([dict(binding, local_number=True)])),
            ('duplicate identity', json.dumps([binding, binding])),
            ('duplicate target', json.dumps([binding, dict(binding, assignment_id='hw_2')])),
        )
        for current_records in ([], [assignment]):
            current = self.write_json('current.json', current_records)
            for name, contents in cases:
                with self.subTest(case=name, has_results=bool(current_records)):
                    if contents is None:
                        bindings.unlink(missing_ok=True)
                    else:
                        bindings.write_text(contents, encoding='utf-8')
                    result = self.cli(
                        'CompareAssignments', '--previous', str(previous),
                        '--current', str(current), '--bindings', str(bindings),
                    )
                    self.assertEqual(result.returncode, 1)
                    self.assertEqual(result.stdout, '')
                    self.assertIn('ERROR:', result.stderr)
                    self.assertNotIn('Traceback', result.stderr)
                    if contents is None:
                        self.assertFalse(bindings.exists())
                    else:
                        self.assertEqual(bindings.read_text(encoding='utf-8'), contents)

    def test_compare_assignments_rejects_apply_with_bindings(self):
        result = self.cli(
            'CompareAssignments', '--previous', str(self.base / 'previous.json'),
            '--current', str(self.base / 'current.json'),
            '--bindings', str(self.base / 'bindings.json'), '--apply',
        )

        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, '')
        self.assertIn('does not accept --apply', result.stderr)

    def test_offline_assignment_workflow(self):
        """Verify comparison, confirmed binding, missing records, and repeat execution together."""
        assignment_a = dict(course_id='course_1', assignment_id='A',
                            title='作业 A', due_at='2026-11-24')
        updated_a = dict(assignment_a, due_at='2026-11-25')
        assignment_b = dict(assignment_a, assignment_id='B', title='作业 B')
        previous = self.write_json('previous.json', [assignment_a])
        current = self.write_json('current.json', [updated_a, assignment_b])
        latest = self.write_json('latest.json', [updated_a])
        mapping = self.write_json('course_mapping.json', {'course_1': self.course})
        binding_a = dict(course_id='course_1', assignment_id='A',
                         local_course=self.course, local_number=1)
        bindings = self.write_json('bindings.json', [binding_a])
        original_bindings = bindings.read_bytes()
        backup = Path(str(bindings) + '.bak')
        source_files = [self.root / self.course / f'{n}/{n}.tex' for n in (1, 3)]
        inputs = {p: p.read_bytes() for p in (previous, current, latest, mapping, *source_files)}
        refs = git(self.root, 'show-ref')
        status = git(self.root, 'status', '--porcelain')
        comparison = ('CompareAssignments', '--previous', str(previous),
                      '--current', str(current), '--course-mapping', str(mapping),
                      '--bindings', str(bindings))
        binding = ('BindAssignment', '--current', str(current),
                   '--course-id', 'course_1', '--assignment-id', 'B',
                   '--course', self.course, '--number', '3', '--bindings', str(bindings))

        # Discover B and the changed deadline for A, using the existing A binding.
        result = self.ok(*comparison)
        new_output, updated_output = result.stdout.split('\nUpdated assignments', 1)
        self.assertIn('New assignments (1)', new_output)
        self.assertIn('[course_1 / B]', new_output)
        self.assertIn(f'Local course: {self.course}', new_output)
        self.assertIn('Local assignment: (unbound)', new_output)
        self.assertIn('Updated assignments (1)', result.stdout)
        self.assertIn('[course_1 / A]', updated_output)
        self.assertIn(updated_a['due_at'], updated_output)
        self.assertIn(f'Local assignment: {self.course}/1', updated_output)
        self.assertEqual(result.stderr, '')

        # Preview leaves storage untouched; apply preserves A and backs up the old list.
        preview = self.ok(*binding)
        self.assertIn('Operation: add binding', preview.stdout)
        self.assertEqual(bindings.read_bytes(), original_bindings)
        self.assertFalse(backup.exists())
        self.ok(*binding, '--apply')
        binding_b = dict(course_id='course_1', assignment_id='B',
                         local_course=self.course, local_number=3)
        self.assertEqual(json.loads(bindings.read_text(encoding='utf-8')), [binding_a, binding_b])
        self.assertEqual(backup.read_bytes(), original_bindings)
        saved = bindings.read_bytes()

        # The same snapshot pair still reports B as new, now with its confirmed target.
        result = self.ok(*comparison)
        new_output = result.stdout.split('\nUpdated assignments', 1)[0]
        self.assertIn('New assignments (1)', new_output)
        self.assertIn('[course_1 / B]', new_output)
        self.assertIn(f'Local assignment: {self.course}/3', new_output)
        self.assertNotIn('(unbound)', new_output)

        # A later snapshot missing B must not remove its binding.
        result = self.ok('CompareAssignments', '--previous', str(current),
                         '--current', str(latest), '--course-mapping', str(mapping),
                         '--bindings', str(bindings))
        self.assertIn('New assignments (0)', result.stdout)
        self.assertIn('Updated assignments (0)', result.stdout)
        self.assertEqual(bindings.read_bytes(), saved)

        repeated = self.ok(*binding, '--apply')
        self.assertIn('Operation: none', repeated.stdout)
        self.assertEqual(bindings.read_bytes(), saved)
        self.assertEqual(backup.read_bytes(), original_bindings)
        for path, contents in inputs.items():
            self.assertEqual(path.read_bytes(), contents)
        self.assertEqual(git(self.root, 'show-ref'), refs)
        self.assertEqual(git(self.root, 'status', '--porcelain'), status)

    def test_bind_assignment_preview_preserves_files_and_refs(self):
        assignment = dict(course_id='course_1', assignment_id='hw_1',
                          title='待绑定作业', due_at='2026-11-20')
        binding = dict(course_id='course_1', assignment_id='hw_1',
                       local_course=self.course, local_number=3)
        snapshot = self.write_json('作业 snapshot.json', [assignment])
        source = self.root / self.course / '3/3.tex'
        refs = git(self.root, 'show-ref')
        status = git(self.root, 'status', '--porcelain')
        for records, operation in (([], 'add binding'), ([binding], 'none')):
            with self.subTest(operation=operation):
                bindings = self.write_json('bindings.json', records)
                originals = {p: p.read_bytes() for p in (snapshot, bindings, source)}
                contents = set(self.base.iterdir())

                result = self.ok(
                    'BindAssignment', '--current', str(snapshot),
                    '--course-id', 'course_1', '--assignment-id', 'hw_1',
                    '--course', self.course, '--number', '3',
                    '--bindings', str(bindings),
                )

                for field in ('course_1 / hw_1', assignment['title'],
                              str(source.parent), str(bindings), f'Operation: {operation}'):
                    self.assertIn(field, result.stdout)
                self.assertIn('Preview only', result.stdout)
                self.assertIn('add --apply', result.stdout)
                if operation == 'add binding':
                    self.assertIn(f'Backup path: {bindings}.bak', result.stdout)
                    self.assertIn('An existing backup will be overwritten.', result.stdout)
                else:
                    self.assertNotIn('Backup path:', result.stdout)
                self.assertEqual(result.stderr, '')
                for path, original in originals.items():
                    self.assertEqual(path.read_bytes(), original)
                self.assertEqual(set(self.base.iterdir()), contents)
                self.assertEqual(git(self.root, 'show-ref'), refs)
                self.assertEqual(git(self.root, 'status', '--porcelain'), status)

    def test_bind_assignment_requires_explicit_arguments(self):
        options = {
            '--current': str(self.base / 'snapshot.json'),
            '--course-id': 'course_1', '--assignment-id': 'hw_1',
            '--course': self.course, '--number': '3',
            '--bindings': str(self.base / 'bindings.json'),
        }
        for missing in options:
            with self.subTest(missing=missing):
                args = ['BindAssignment']
                for flag, value in options.items():
                    if flag != missing:
                        args += [flag, value]
                result = self.cli(*args)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, '')
                self.assertIn(f'requires {missing}', result.stderr)
                self.assertNotIn('Traceback', result.stderr)

    def test_bind_assignment_requires_existing_target_and_tex(self):
        snapshot = self.write_json('snapshot.json', [dict(
            course_id='course_1', assignment_id='hw_1', title='作业', due_at='',
        )])
        bindings = self.write_json('bindings.json', [])
        source = self.root / self.course / '3/3.tex'
        for case in ('missing course', 'missing directory', 'missing tex', 'tex is directory'):
            with self.subTest(case=case):
                course = 'Missing' if case == 'missing course' else self.course
                number = '99' if case == 'missing directory' else '3'
                if case == 'missing tex':
                    source.unlink()
                elif case == 'tex is directory':
                    source.mkdir()
                result = self.cli(
                    'BindAssignment', '--current', str(snapshot),
                    '--course-id', 'course_1', '--assignment-id', 'hw_1',
                    '--course', course, '--number', number, '--bindings', str(bindings),
                )
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, '')
                self.assertIn('ERROR:', result.stderr)
                self.assertNotIn('Traceback', result.stderr)
                if case in ('missing tex', 'tex is directory'):
                    self.assertIn(str(source), result.stderr)
                self.assertEqual(bindings.read_text(encoding='utf-8'), '[]')

    def test_bind_assignment_rejects_unusable_snapshots(self):
        assignment = dict(course_id='course_1', assignment_id='hw_1', title='作业', due_at='')
        other = dict(assignment, assignment_id='other')
        snapshot = self.base / 'snapshot.json'
        bindings = self.write_json('bindings.json', [])
        cases = (
            ('empty', '[]'),
            ('not found', json.dumps([other])),
            ('duplicate selected', json.dumps([assignment, assignment])),
            ('duplicate other', json.dumps([assignment, other, other])),
            ('invalid JSON', '{'),
            ('invalid root', 'null'),
            ('invalid record', '[1]'),
            ('missing ID', json.dumps([{'title': 'missing ID'}])),
            ('invalid ID type', json.dumps([dict(assignment, course_id=[])])),
        )
        for name, contents in cases:
            with self.subTest(case=name):
                snapshot.write_text(contents, encoding='utf-8')
                result = self.cli(
                    'BindAssignment', '--current', str(snapshot),
                    '--course-id', 'course_1', '--assignment-id', 'hw_1',
                    '--course', self.course, '--number', '3', '--bindings', str(bindings),
                )
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, '')
                self.assertIn('ERROR:', result.stderr)
                self.assertNotIn('Traceback', result.stderr)
                self.assertEqual(snapshot.read_text(encoding='utf-8'), contents)
                self.assertEqual(bindings.read_text(encoding='utf-8'), '[]')

    def test_bind_assignment_rejects_invalid_or_conflicting_bindings(self):
        assignment = dict(course_id='course_1', assignment_id='hw_1', title='作业', due_at='')
        snapshot = self.write_json('snapshot.json', [assignment])
        bindings = self.base / 'bindings.json'
        existing = dict(course_id='course_1', assignment_id='hw_1',
                        local_course=self.course, local_number=1)
        occupied = dict(existing, assignment_id='other', local_number=3)
        cases = (
            ('missing file', None),
            ('invalid JSON', '['),
            ('invalid structure', '{}'),
            ('duplicate identity', json.dumps([existing, existing])),
            ('duplicate target', json.dumps([existing, dict(existing, assignment_id='other')])),
            ('change existing target', json.dumps([existing])),
            ('occupied target', json.dumps([occupied])),
        )
        for name, contents in cases:
            with self.subTest(case=name):
                if contents is None:
                    bindings.unlink(missing_ok=True)
                else:
                    bindings.write_text(contents, encoding='utf-8')
                result = self.cli(
                    'BindAssignment', '--current', str(snapshot),
                    '--course-id', 'course_1', '--assignment-id', 'hw_1',
                    '--course', self.course, '--number', '3', '--bindings', str(bindings),
                )
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, '')
                self.assertIn('ERROR:', result.stderr)
                self.assertNotIn('Traceback', result.stderr)
                if contents is None:
                    self.assertFalse(bindings.exists())
                else:
                    self.assertEqual(bindings.read_text(encoding='utf-8'), contents)

    def test_bind_assignment_cli_apply_saves_and_repeat_preserves_backup(self):
        snapshot = self.write_json('snapshot.json', [dict(
            course_id='course_1', assignment_id='hw_1', title='作业', due_at='',
        )])
        bindings = self.write_json('bindings.json', [])
        source = self.root / self.course / '3/3.tex'
        originals = {p: p.read_bytes() for p in (snapshot, source)}
        original_bindings = bindings.read_bytes()
        backup = Path(str(bindings) + '.bak')
        backup.write_bytes(b'previous backup')
        refs = git(self.root, 'show-ref')
        status = git(self.root, 'status', '--porcelain')
        args = (
            'BindAssignment', '--current', snapshot.name,
            '--course-id', 'course_1', '--assignment-id', 'hw_1',
            '--course', self.course, '--number', '3', '--bindings', bindings.name, '--apply',
        )

        result = self.ok(*args)

        expected = [dict(course_id='course_1', assignment_id='hw_1',
                         local_course=self.course, local_number=3)]
        self.assertEqual(json.loads(bindings.read_text(encoding='utf-8')), expected)
        self.assertEqual(backup.read_bytes(), original_bindings)
        self.assertIn('saved bindings successfully', result.stdout)
        self.assertEqual(result.stderr, '')
        saved = bindings.read_bytes()
        repeated = self.ok(*args)
        self.assertIn('Operation: none', repeated.stdout)
        self.assertNotIn('saved bindings successfully', repeated.stdout)
        self.assertEqual(bindings.read_bytes(), saved)
        self.assertEqual(backup.read_bytes(), original_bindings)
        for path, original in originals.items():
            self.assertEqual(path.read_bytes(), original)
        self.assertEqual(git(self.root, 'show-ref'), refs)
        self.assertEqual(git(self.root, 'status', '--porcelain'), status)

    def test_bind_assignment_cli_apply_reads_latest_bindings(self):
        args = self._binding_action_args()
        flags = ('BindAssignment', '--current', str(args.current),
                 '--course-id', args.course_id, '--assignment-id', args.assignment_id,
                 '--course', args.course, '--number', str(args.number),
                 '--bindings', str(args.bindings))
        self.ok(*flags)
        backup = Path(str(args.bindings) + '.bak')
        self.assertFalse(backup.exists())
        other = dict(course_id='course_2', assignment_id='hw_2',
                     local_course=self.course, local_number=1)
        args.bindings.write_text(json.dumps([other]), encoding='utf-8')
        before_apply = args.bindings.read_bytes()

        self.ok(*flags, '--apply')

        records = json.loads(args.bindings.read_text(encoding='utf-8'))
        self.assertEqual(records, [other, dict(course_id='course_1', assignment_id='hw_1',
                                              local_course=self.course, local_number=3)])
        self.assertEqual(backup.read_bytes(), before_apply)

    def test_bind_assignment_cli_backup_failure_preserves_bindings(self):
        args = self._binding_action_args()
        original = args.bindings.read_bytes()
        Path(str(args.bindings) + '.bak').mkdir()

        result = self.cli(
            'BindAssignment', '--current', str(args.current),
            '--course-id', args.course_id, '--assignment-id', args.assignment_id,
            '--course', args.course, '--number', str(args.number),
            '--bindings', str(args.bindings), '--apply',
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn('ERROR:', result.stderr)
        self.assertNotIn('Traceback', result.stderr)
        self.assertNotIn('successfully', result.stdout)
        self.assertEqual(args.bindings.read_bytes(), original)

    def test_bind_assignment_cli_save_failure_returns_error_with_backup(self):
        args = self._binding_action_args()
        original = args.bindings.read_bytes()
        files = set(self.base.iterdir())
        argv = [str(ENTRY), 'BindAssignment', '--repo-path', str(self.root),
                '--current', str(args.current), '--course-id', args.course_id,
                '--assignment-id', args.assignment_id, '--course', args.course,
                '--number', str(args.number), '--bindings', str(args.bindings), '--apply']
        output, errors = io.StringIO(), io.StringIO()
        # Call the real dispatcher in-process to inject a filesystem failure.
        with patch.object(sys, 'argv', argv), patch.object(
            Path, 'replace', side_effect=PermissionError('Simulated replace failure')
        ), contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            result = homework_main()

        backup = Path(str(args.bindings) + '.bak')
        self.assertEqual(result, 1)
        self.assertIn('ERROR: Simulated replace failure', errors.getvalue())
        self.assertNotIn('successfully', output.getvalue())
        self.assertEqual(args.bindings.read_bytes(), original)
        self.assertEqual(backup.read_bytes(), original)
        self.assertEqual(set(self.base.iterdir()), files | {backup})

    def test_bind_assignment_cli_apply_rechecks_inputs_and_target(self):
        args = self._binding_action_args()
        flags = ('BindAssignment', '--current', str(args.current),
                 '--course-id', args.course_id, '--assignment-id', args.assignment_id,
                 '--course', args.course, '--number', str(args.number),
                 '--bindings', str(args.bindings))
        self.ok(*flags)
        snapshot = args.current.read_bytes()
        bindings = args.bindings.read_bytes()
        source = self.root / self.course / '3/3.tex'
        backup = Path(str(args.bindings) + '.bak')
        backup.write_bytes(b'previous backup')
        conflict = dict(course_id=args.course_id, assignment_id=args.assignment_id,
                        local_course=self.course, local_number=1)
        for case in ('invalid snapshot', 'binding conflict', 'missing target source'):
            with self.subTest(case=case):
                args.current.write_bytes(snapshot)
                args.bindings.write_bytes(bindings)
                if case == 'invalid snapshot':
                    args.current.write_text('null', encoding='utf-8')
                elif case == 'binding conflict':
                    args.bindings.write_text(json.dumps([conflict]), encoding='utf-8')
                else:
                    source.unlink()
                before = {p: p.read_bytes() for p in (args.current, args.bindings, backup)}

                result = self.cli(*flags, '--apply')

                self.assertEqual(result.returncode, 1)
                self.assertIn('ERROR:', result.stderr)
                self.assertNotIn('Traceback', result.stderr)
                self.assertNotIn('successfully', result.stdout)
                for path, contents in before.items():
                    self.assertEqual(path.read_bytes(), contents)

    # AI-assisted action tests complement the public CLI tests above.
    def _binding_action_args(self):
        snapshot = self.write_json('作业 snapshot.json', [dict(
            course_id='course_1', assignment_id='hw_1', title='待绑定作业', due_at='',
        )])
        bindings = self.write_json('bindings.json', [])
        return Namespace(current=snapshot, course_id='course_1', assignment_id='hw_1',
                         course=self.course, number=3, bindings=bindings, apply=True)

    def test_bind_assignment_action_saves_and_repeated_apply_is_noop(self):
        args = self._binding_action_args()
        original = args.bindings.read_bytes()
        backup = Path(str(args.bindings) + '.bak')
        backup.write_bytes(b'older backup')
        source = self.root / self.course / '3/3.tex'
        inputs = {path: path.read_bytes() for path in (args.current, source)}
        refs = git(self.root, 'show-ref')
        status = git(self.root, 'status', '--porcelain')
        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            bind_assignment(Repository(self.root), args)

        expected = [dict(course_id='course_1', assignment_id='hw_1',
                         local_course=self.course, local_number=3)]
        self.assertEqual(json.loads(args.bindings.read_text(encoding='utf-8')), expected)
        self.assertEqual(backup.read_bytes(), original)
        self.assertIn('saved bindings successfully', output.getvalue())
        saved = args.bindings.read_bytes()
        with contextlib.redirect_stdout(io.StringIO()):
            with patch('actions.bind_assignment.backup_bindings') as copy:
                with patch('actions.bind_assignment.save_bindings') as save:
                    bind_assignment(Repository(self.root), args)
                    copy.assert_not_called()
                    save.assert_not_called()
        self.assertEqual(args.bindings.read_bytes(), saved)
        self.assertEqual(backup.read_bytes(), original)
        for path, contents in inputs.items():
            self.assertEqual(path.read_bytes(), contents)
        self.assertEqual(git(self.root, 'show-ref'), refs)
        self.assertEqual(git(self.root, 'status', '--porcelain'), status)

    def test_bind_assignment_action_backup_failure_stops_save(self):
        args = self._binding_action_args()
        original = args.bindings.read_bytes()
        Path(str(args.bindings) + '.bak').mkdir()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            with patch('actions.bind_assignment.save_bindings') as save:
                with self.assertRaises(IsADirectoryError):
                    bind_assignment(Repository(self.root), args)
                save.assert_not_called()

        self.assertEqual(args.bindings.read_bytes(), original)
        self.assertNotIn('successfully', output.getvalue())

    def test_bind_assignment_action_save_failure_keeps_backup(self):
        args = self._binding_action_args()
        original = args.bindings.read_bytes()
        failure = OSError('Simulated save failure')
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            with patch('actions.bind_assignment.save_bindings', side_effect=failure):
                with self.assertRaises(OSError) as raised:
                    bind_assignment(Repository(self.root), args)

        self.assertIs(raised.exception, failure)
        self.assertEqual(args.bindings.read_bytes(), original)
        self.assertEqual(Path(str(args.bindings) + '.bak').read_bytes(), original)
        self.assertNotIn('successfully', output.getvalue())

    def test_bind_assignment_action_rereads_bindings_after_preview(self):
        args = self._binding_action_args()
        repo = Repository(self.root)
        args.apply = False
        with contextlib.redirect_stdout(io.StringIO()):
            bind_assignment(repo, args)
        backup = Path(str(args.bindings) + '.bak')
        self.assertFalse(backup.exists())
        other = dict(course_id='course_2', assignment_id='hw_2',
                     local_course=self.course, local_number=1)
        args.bindings.write_text(json.dumps([other]), encoding='utf-8')
        original = args.bindings.read_bytes()
        args.apply = True

        with contextlib.redirect_stdout(io.StringIO()):
            bind_assignment(repo, args)

        records = json.loads(args.bindings.read_text(encoding='utf-8'))
        self.assertEqual(records, [other, dict(course_id='course_1', assignment_id='hw_1',
                                              local_course=self.course, local_number=3)])
        self.assertEqual(backup.read_bytes(), original)

    def test_course_defaults_and_explicit_overrides(self):
        config = {'courses': {
            self.course: {'semester': '2026 秋季', 'defaultLanguage': 'zh'},
            'Physics-1': {'semester': '2026 Fall', 'defaultLanguage': 'en'},
        }}
        (self.root / 'homework.config.json').write_text(json.dumps(config))
        (self.root / 'Physics-1').mkdir()
        git(self.root, 'add', '--', 'homework.config.json')
        git(self.root, 'commit', '-m', 'Configure course defaults')
        # A course without previous assignments uses its own configured language.
        result = self.ok('NewHomework', '--course', 'Physics-1')
        self.assertIn('semester=2026 Fall; language=en', result.stdout)
        result = self.ok('NewHomework', '--course', 'Physics-1', '--semester', '2027 Spring', '--language', 'zh')
        self.assertIn('semester=2027 Spring; language=zh', result.stdout)
        # Existing assignments still supply language and display-name inheritance.
        result = self.ok('NewHomework', '--course', self.course)
        self.assertIn('semester=2026 秋季; language=en; course label=Course Name', result.stdout)
        status = self.ok('Status').stdout
        self.assertIn('Physics-1 (next: 1; semester=2026 Fall; language=en)', status)
        self.assertIn(f'{self.course} (next: 4; semester=2026 秋季; language=zh)', status)

    def test_unconfigured_course_requires_missing_defaults(self):
        (self.root / 'New').mkdir()
        result = self.cli('NewHomework', '--course', 'New')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('--semester', result.stderr)
        result = self.cli('NewHomework', '--course', 'New', '--semester', '2027 Spring')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('--language', result.stderr)
        self.ok('NewHomework', '--course', 'New', '--semester', '2027 Spring', '--language', 'en')
        result = self.ok('Status')
        self.assertIn('New (next: 1; defaults not configured)', result.stdout)

    def test_invalid_course_config_is_rejected(self):
        for config in ({}, {'courses': []}, {'courses': {'New': []}},
                       {'courses': {'New': {'semester': '', 'defaultLanguage': 'en'}}},
                       {'courses': {'New': {'semester': '2026 Fall', 'defaultLanguage': 'fr'}}}):
            with self.subTest(config=config):
                (self.root / 'homework.config.json').write_text(json.dumps(config))
                result = self.cli('Status')
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('ERROR:', result.stderr)

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
        self.assertEqual(git(self.root, 'ls-files', '--', self.course + '/4/.gitignore'), self.course + '/4/.gitignore')
        for name in ('4-figure.pdf', 'HW 4.pdf', 'SOURCE.PDF', 'source.pdf'):
            (path / name).write_bytes(b'local source/figure PDF')
        output = path / '4.pdf'
        output.write_bytes(b'compiled PDF')
        self.ok('Sync', '--apply')
        self.assertEqual(git(self.root, 'ls-files', '--', self.course + '/4/4.pdf'), self.course + '/4/4.pdf')
        other = subprocess.run(['git', '-C', str(self.root), 'check-ignore', '--', self.course + '/4/2.pdf'], capture_output=True)
        self.assertEqual(other.returncode, 0)
        self.assertEqual(git(self.remote, 'show', self.course + '-HW4:' + self.course + '/4/4.pdf'), 'compiled PDF')
        for name in ('4-figure.pdf', 'HW 4.pdf', 'SOURCE.PDF', 'source.pdf'):
            self.assertEqual(git(self.root, 'ls-files', '--', self.course + '/4/' + name), '')
            self.assertTrue((path / name).is_file())
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
        (source.parent / 'HW 3.pdf').write_bytes(b'problem source')
        (source.parent / '3-figure.pdf').write_bytes(b'figure source')
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
