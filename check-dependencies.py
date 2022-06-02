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
    junit_xml: str
    no_junit_xml: bool
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
        description="Check if Poetry based Python project dependencies declared in pyproject.toml are up to date",
    )
    parser.add_argument(
        "--junit-xml",
        dest="junit_xml",
        default="poetry_dependencies_report.xml",
        help='generated JUnit XML test results path (default: "poetry_dependencies_report.xml")',
    )
    parser.add_argument(
        "--no-junit-xml",
        dest="no_junit_xml",
        action="store_true",
        help="skip saving test result to JUnit XML file",
    )
    parser.add_argument(
        "--no-pytest-install",
        dest="no_pytest_install",
        action="store_true",
        help="prohibit installing pytest if it is not present on the system",
    )
    parser.add_argument(
        "--pytest-executable",
        dest="pytest_executable",
        type=_custom_pytest_executable,
        help='specify custom pytest executable (default: "python -m pytest")',
    )
    parsed_args = parser.parse_args()
    return ProgramArguments(**vars(parsed_args))


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
def _test_script() -> pathlib.Path:
    tests_script_url = "https://raw.githubusercontent.com/NevercodeHQ/poetry-dependencies-checker/main/test-poetry-dependencies.py"
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
                junit_xml=(
                    None
                    if program_arguments.no_junit_xml
                    else program_arguments.junit_xml
                ),
            )
    except IOError as ioe:
        print(f"Error: {ioe}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
