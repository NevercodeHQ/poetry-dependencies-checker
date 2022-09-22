#!/usr/bin/env python3

from __future__ import annotations

import importlib
import json
import urllib.request
import warnings
from typing import Dict
from typing import NamedTuple

import pytest
from packaging.specifiers import SpecifierSet
from packaging.version import Version

# tomllib is added in Python 3.11. In case this is not available,
# use either tomli (a backport of the same library) or toml package.
# Either one should be required by pytest.
for toml_package_name in ("tomllib", "tomli", "toml"):
    try:
        tomllib = importlib.import_module(toml_package_name)
    except ModuleNotFoundError:
        pass
    else:
        break
else:
    raise ImportError("Failed to import TOML parsing package")


@pytest.fixture()
def locked_versions() -> Dict[str, Version]:
    with open("poetry.lock") as f:
        lock_info = tomllib.loads(f.read())

    return {
        package["name"].lower(): Version(package["version"])
        for package in lock_info["package"]
    }


class Dependency(NamedTuple):
    name: str
    version_constraint: str

    def is_frozen(self) -> bool:
        # Check if fully qualified semver is specified as version constraint
        parts = self.version_constraint.split(".")
        return len(parts) == 3 and all(part.isdigit() for part in parts)

    @classmethod
    def load(cls):
        with open("pyproject.toml") as f:
            project_info = tomllib.loads(f.read())

        for name, version_info in project_info["tool"]["poetry"][
            "dependencies"
        ].items():
            if name.lower() == "python":
                continue
            if isinstance(version_info, str):
                version_constraint = version_info
            elif "version" in version_info:
                version_constraint = version_info["version"]
            else:
                warnings.warn(f"Failed to obtain version constraint for {name}")
                continue
            yield Dependency(name, version_constraint)

    def get_latest_version(self) -> Version:
        with urllib.request.urlopen(
            f"https://pypi.org/pypi/{self.name}/json"
        ) as response:
            payload = json.load(response)
        return Version(payload["info"]["version"])


@pytest.mark.parametrize(
    "dependency", (pytest.param(d, id=d.name) for d in Dependency.load())
)
def test_dependencies(dependency: Dependency, locked_versions: Dict[str, Version]):
    available_version = dependency.get_latest_version()
    locked_version = locked_versions[dependency.name.lower()]

    if dependency.is_frozen():
        skip_message = (
            f"{dependency.name} is frozen by constraint {dependency.version_constraint}. "
            f"Version {locked_version} is used, but {available_version} is available."
        )
        pytest.skip(skip_message)

    latest_version_specifier = SpecifierSet(
        f">={available_version.major}.{available_version.minor}"
    )
    if not latest_version_specifier.contains(locked_version):
        raise AssertionError(
            f"{dependency.name} is not up to date, {locked_version} < {available_version}"
        )

    if locked_version != available_version:
        warnings.warn(
            f"{dependency.name} - version {available_version} is available, but {locked_version} is used"
        )
    else:
        print(f"{dependency.name} is on latest version at {locked_version}")


if __name__ == "__main__":
    pytest.main([__file__, "--noconftest"])
