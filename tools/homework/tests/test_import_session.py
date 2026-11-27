# AI-assisted tests; getpass is replaced with fake input and never reads a terminal.
import getpass
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import warnings

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from actions.import_session import read_session_input
from common import HomeworkError


class ReadSessionInputTests(unittest.TestCase):
    def test_return_fields_and_strip_surrounding_whitespace(self):
        for inputs in (
            ["JSESSIONID=fake-session", "fake-token"],
            [" \tJSESSIONID=fake-session \t", " \tfake-token \t"],
        ):
            with self.subTest(inputs=inputs):
                with patch("actions.import_session.getpass.getpass", side_effect=inputs):
                    actual = read_session_input()

                self.assertEqual(actual, {
                    "cookie_header": "JSESSIONID=fake-session",
                    "csrf_token": "fake-token",
                })

    def test_empty_cookie_is_rejected_without_exposing_token(self):
        token = "fake-private-csrf-token"
        for cookie in ("", " \t "):
            with self.subTest(cookie=cookie):
                with patch("actions.import_session.getpass.getpass", side_effect=[cookie, token]):
                    with self.assertRaises(ValueError) as caught:
                        read_session_input()

                self.assertNotIn(token, str(caught.exception))

    def test_empty_token_is_rejected_without_exposing_cookie(self):
        cookie = "JSESSIONID=fake-private-cookie"
        for token in ("", " \t "):
            with self.subTest(token=token):
                with patch("actions.import_session.getpass.getpass", side_effect=[cookie, token]):
                    with self.assertRaises(ValueError) as caught:
                        read_session_input()

                self.assertNotIn(cookie, str(caught.exception))

    def test_warning_stops_before_fallback_input(self):
        for failed_call in (1, 2):
            with self.subTest(failed_call=failed_call):
                calls = []

                def fake_getpass(prompt):
                    calls.append(prompt)
                    if len(calls) == failed_call:
                        warnings.warn("fake-private-warning", getpass.GetPassWarning)
                        self.fail("Input must stop before the echoed fallback")
                    return "JSESSIONID=fake-private-cookie"

                with patch("actions.import_session.getpass.getpass", side_effect=fake_getpass):
                    with self.assertRaises(HomeworkError) as caught:
                        read_session_input()

                self.assertEqual(len(calls), failed_call)
                self.assertIsInstance(caught.exception.__cause__, getpass.GetPassWarning)
                self.assertNotIn("fake-private", str(caught.exception))

    def test_eof_during_either_input_becomes_homework_error(self):
        for failed_call in (1, 2):
            with self.subTest(failed_call=failed_call):
                error = EOFError("fake-private-eof-details")
                inputs = ["JSESSIONID=fake-private-cookie"] * (failed_call - 1) + [error]
                with patch("actions.import_session.getpass.getpass", side_effect=inputs) as mocked:
                    with self.assertRaises(HomeworkError) as caught:
                        read_session_input()

                self.assertEqual(mocked.call_count, failed_call)
                self.assertIs(caught.exception.__cause__, error)
                self.assertNotIn("fake-private", str(caught.exception))

    def test_keyboard_interrupt_during_either_input_propagates(self):
        for failed_call in (1, 2):
            with self.subTest(failed_call=failed_call):
                error = KeyboardInterrupt()
                inputs = ["JSESSIONID=fake-cookie"] * (failed_call - 1) + [error]
                with patch("actions.import_session.getpass.getpass", side_effect=inputs) as mocked:
                    with self.assertRaises(KeyboardInterrupt) as caught:
                        read_session_input()

                self.assertIs(caught.exception, error)
                self.assertEqual(mocked.call_count, failed_call)

    def test_warning_filter_is_restored_after_each_exit(self):
        cases = [
            (["JSESSIONID=fake-cookie", "fake-token"], None),
            (["", "fake-token"], ValueError),
            ([getpass.GetPassWarning("fake warning")], HomeworkError),
            ([EOFError()], HomeworkError),
            ([KeyboardInterrupt()], KeyboardInterrupt),
        ]
        for inputs, expected_error in cases:
            with self.subTest(expected_error=expected_error):
                with warnings.catch_warnings(record=True) as recorded:
                    warnings.simplefilter("always", getpass.GetPassWarning)
                    with patch("actions.import_session.getpass.getpass", side_effect=inputs):
                        if expected_error is None:
                            read_session_input()
                        else:
                            with self.assertRaises(expected_error):
                                read_session_input()

                    # This must be recorded normally, rather than raised as an error.
                    warnings.warn("after session input", getpass.GetPassWarning)
                    self.assertEqual(len(recorded), 1)
