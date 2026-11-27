import getpass, warnings
from common import HomeworkError


def read_session_input() -> dict[str, str]:
    """Read Cookie and CSRF token inputs, rejecting empty values."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", getpass.GetPassWarning)
            cookie_header = getpass.getpass("Cookie header value: ").strip()
            csrf_token = getpass.getpass("CSRF token (_csrf): ").strip()
            if not cookie_header:
                raise ValueError("Cookie header value cannot be empty.")
            if not csrf_token:
                raise ValueError("CSRF token cannot be empty.")
            return {
                "cookie_header": cookie_header,
                "csrf_token": csrf_token,
            }
    except getpass.GetPassWarning as error:
        raise HomeworkError("Hidden input is unavailable.") from error
    except EOFError as error:
        raise HomeworkError("Session input ended before completion.") from error
