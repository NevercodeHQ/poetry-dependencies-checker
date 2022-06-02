# Ensure your Poetry dependencies are up to date

Check that the [Poetry]([https://github.com/python-poetry/poetry](https://python-poetry.org/)) based Python project dependencies declared in `pyproject.toml` are up to date by comparing the used versions from `poetry.lock` to latest available versions available in [PyPI](https://pypi.org/).

The checks are carried out using [pytest](https://docs.pytest.org/) testing framework to generate reports that are easily usabe in CI environments.

[![asciicast](https://asciinema.org/a/71YwN1YMD4smctaLYbxQdBPaq.svg)](https://asciinema.org/a/71YwN1YMD4smctaLYbxQdBPaq)

## Usage

MacOS / Linux / Bash on Windows

```bash
curl -sSL https://raw.githubusercontent.com/NevercodeHQ/poetry-dependencies-checker/main/check-dependencies.py | python -
```

Windows PowerShell

```bash
(Invoke-WebRequest -Uri https://raw.githubusercontent.com/NevercodeHQ/poetry-dependencies-checker/main/check-dependencies.py -UseBasicParsing).Content | python -
```
