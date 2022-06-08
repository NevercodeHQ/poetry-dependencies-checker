from __future__ import annotations

import argparse
import contextlib
import pathlib
import platform
import subprocess
import sys
import urllib.request
from tempfile import NamedTemporaryFile
from typing import NamedTuple
from typing import Optional


class ProgramArguments(NamedTuple):
    junit_xml: Optional[str]
    no_pytest_install: str
    pytest_executable: Optional[pathlib.Path]


def _custom_pytest_executable(custom_pytest_executable: str) -> pathlib.Path:
    pytest = pathlib.Path(custom_pytest_executable)
    if not pytest.exists():
        raise argparse.ArgumentTypeError(f"{pytest} does not exist")
    elif not pytest.is_file():
        raise argparse.ArgumentTypeError(f"{pytest} is not a file")
    elif not pytest.parent.exists():
        raise argparse.ArgumentTypeError(f"{pytest} parent directory does not exist")
    return pathlib.Path(pytest)


def _setup_arguments() -> ProgramArguments:
    parser = argparse.ArgumentParser(
        description=(
            "Check if Poetry based Python project dependencies "
            "declared in pyproject.toml are up to date"
        ),
    )
    parser.add_argument(
        "--junit-xml",
        dest="junit_xml",
        help="save check results as JUnit XML to specified path",
    )
    parser.add_argument(
        "--no-pytest-install",
        dest="no_pytest_install",
        action="store_true",
        help="prohibit installing pytest if it is not present on the system",
    )
    parser.add_argument(
        "--pytest",
        dest="pytest_executable",
        type=_custom_pytest_executable,
        help="specify custom pytest executable",
    )
    args = parser.parse_args()
    return ProgramArguments(
        junit_xml=args.junit_xml,
        no_pytest_install=args.no_pytest_install,
        pytest_executable=args.pytest_executable,
    )


def _check_python_version():
    if sys.version_info.major >= 3 and sys.version_info.minor >= 6:
        return
    raise IOError(
        f"Python 3.6+ is required, currently using {platform.python_version()}"
    )


def _ensure_pytest(
    custom_pytest_executable: Optional[pathlib.Path],
    allow_install: bool,
):
    if custom_pytest_executable:
        print(f"Using custom pytest executable at {custom_pytest_executable}")
        return

    python = pathlib.Path(sys.executable)
    try:
        subprocess.run(
            (python, "-m", "pytest", "--version"),
            capture_output=True,
            check=True,
        )
    except subprocess.CalledProcessError as cpe:
        if not allow_install:
            raise IOError(
                "pytest is not installed and installing it is prohibited"
            ) from cpe
    else:
        return

    print(f"> {python.name} -m pip install pytest")
    try:
        subprocess.run((python, "-m", "pip", "install", "pytest"), check=True)
    except subprocess.CalledProcessError as cpe:
        raise IOError("Failed to install pytest") from cpe


@contextlib.contextmanager
def _test_script(ref="main") -> pathlib.Path:
    repo_slug = "NevercodeHQ/poetry-dependencies-checker"
    tests_script_url = f"https://raw.githubusercontent.com/{repo_slug}/{ref}/test_poetry_dependencies.py"
    with urllib.request.urlopen(tests_script_url) as response:
        tests_script: bytes = response.read()

    with NamedTemporaryFile(
        prefix="test-poetry-dependencies-",
        suffix=".py",
        dir=pathlib.Path("."),
    ) as tf:
        tf.write(tests_script)
        tf.flush()
        yield pathlib.Path(tf.name)


def _run_tests(
    pytest_executable: Optional[pathlib.Path],
    test_file: pathlib.Path,
    junit_xml: Optional[pathlib.Path],
):
    if pytest_executable:
        test_command = [pytest_executable, test_file, "--noconftest"]
    else:
        test_command = [sys.executable, "-m", "pytest", test_file, "--noconftest"]

    if junit_xml:
        test_command.extend(["--junitxml", junit_xml])

    cp = subprocess.run(test_command)
    return cp.returncode


def main():
    try:
        _check_python_version()
        program_arguments = _setup_arguments()
        _ensure_pytest(
            program_arguments.pytest_executable,
            not program_arguments.no_pytest_install,
        )
        with _test_script() as tests_path:
            return _run_tests(
                program_arguments.pytest_executable,
                tests_path,
                junit_xml=program_arguments.junit_xml,
            )
    except IOError as ioe:
        print(f"Error: {ioe}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
