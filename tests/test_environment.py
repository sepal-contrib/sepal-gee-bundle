"""Tests that sepal_environment.yml and the files consuming it still agree.

Nothing here builds an image. These are the drifts that stay invisible until
runtime: the container starts, the build succeeds, and the app is either absent
or missing a binary it only reaches for once a user asks for it.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
ENVIRONMENT_FILE = REPO_ROOT / "sepal_environment.yml"
DOCKERFILE = REPO_ROOT / "Dockerfile"
SUPERVISORD_CONF = REPO_ROOT / "supervisord.conf"
COMPOSE_FILE = REPO_ROOT / "docker-compose.yml"

CONTAINER_HOME = "/home/mambauser"
CREDENTIALS_PATH = f"{CONTAINER_HOME}/.config/earthengine/credentials"

MICROMAMBA_RUN = re.compile(r"micromamba run -n (\S+)")
MICROMAMBA_CREATE = re.compile(r"micromamba create[^\\\n]*")


@pytest.fixture(scope="module")
def environment():
    return yaml.safe_load(ENVIRONMENT_FILE.read_text())


@pytest.fixture(scope="module")
def conda_dependencies(environment):
    """The names conda resolves, dropping version pins and the pip section."""
    return {
        re.split(r"[=<>]", dependency)[0].strip()
        for dependency in environment["dependencies"]
        if not isinstance(dependency, dict)
    }


@pytest.fixture(scope="module")
def pip_dependencies(environment):
    for dependency in environment["dependencies"]:
        if isinstance(dependency, dict):
            return list(dependency["pip"])
    return []


class TestEnvironmentFile:
    def test_names_the_environment(self, environment):
        assert environment["name"] == "sepal-gee-bundle"

    def test_installs_this_project(self, pip_dependencies):
        """Without the pip section the image builds an env with no app in it."""
        assert "-e ." in pip_dependencies

    def test_resolves_from_conda_forge(self, environment):
        assert "conda-forge" in environment["channels"]

    def test_pins_the_python_version(self, conda_dependencies):
        """The Dockerfile stopped passing python=, so the file is the only pin."""
        assert "python" in conda_dependencies


class TestTheImageBuildsFromTheEnvironmentFile:
    def test_creates_the_environment_from_the_file(self):
        commands = MICROMAMBA_CREATE.findall(DOCKERFILE.read_text())

        assert len(commands) == 1
        assert "-f sepal_environment.yml" in commands[0]

    def test_pins_no_python_of_its_own(self):
        """A second source of truth is how the image drifts from local dev."""
        assert "python=" not in DOCKERFILE.read_text()


class TestTheEnvironmentNameIsConsistent:
    def test_supervisord_runs_the_environment_the_file_names(self, environment):
        """`micromamba run -n` against a missing env fails only at startup."""
        names = MICROMAMBA_RUN.findall(SUPERVISORD_CONF.read_text())

        assert names, "supervisord.conf no longer starts the app through micromamba"
        assert set(names) == {environment["name"]}


class TestBinaryDependencies:
    def test_tippecanoe_is_declared(self, conda_dependencies):
        """Vectortileserver shells out to tippecanoe, which pip cannot install.

        apps/basin_rivers/scripts/tiles.py imports vectortileserver to build the
        basin archives, so dropping this entry leaves the app importable and the
        basins unrenderable in the container.
        """
        assert "tippecanoe" in conda_dependencies


@pytest.fixture(scope="module")
def compose_service():
    compose = yaml.safe_load(COMPOSE_FILE.read_text())
    return compose["services"]["sepal-gee-bundle"]


class TestEarthEngineCredentials:
    """Graph building needs the global ee, and init_ee() skips it without these."""

    def test_compose_mounts_earth_engine_credentials(self, compose_service):
        volumes = compose_service.get("volumes", [])

        assert any("/.config/earthengine/credentials" in str(v) for v in volumes)

    def test_the_mount_lands_in_the_home_init_ee_reads(self, compose_service):
        volumes = compose_service.get("volumes", [])

        assert any(CREDENTIALS_PATH in str(v) for v in volumes)

    def test_the_container_still_runs_as_the_user_that_home_belongs_to(self):
        users = re.findall(r"^USER (\S+)", DOCKERFILE.read_text(), re.MULTILINE)

        assert users[-1] == "$MAMBA_USER"
