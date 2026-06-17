from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]


class UpdateCommandTest(unittest.TestCase):
    def test_clean_update_replaces_source_venv_wrapper_and_skills(self) -> None:
        with ManagedInstall() as install:
            install.run_update()

            self.assertEqual('9.9.9', install.installed_version())
            self.assertTrue((install.namespace_root / "description-scaffold" / "UPDATED.txt").is_file())

            wrapper = install.managed_bin_target.read_text(encoding="utf-8")
            self.assertIn(f"ROS_DEVKIT_SOURCE={install.source_dir}", wrapper)
            self.assertEqual(install.managed_bin_target, install.bin_path.resolve())

    def test_local_skill_edits_stop_update(self) -> None:
        with ManagedInstall() as install:
            skill_file = install.namespace_root / "description-scaffold" / "SKILL.md"
            original = skill_file.read_text(encoding="utf-8")
            skill_file.write_text(f"{original}\nlocal edit\n", encoding="utf-8")

            completed = install.run_update(check=False)

            self.assertNotEqual(0, completed.returncode)
            self.assertIn("Local changes detected", completed.stderr)
            self.assertEqual("0.1.0", install.installed_version())
            self.assertIn("local edit", skill_file.read_text(encoding="utf-8"))
            self.assertFalse((install.namespace_root / "description-scaffold" / "UPDATED.txt").exists())

    def test_force_replaces_locally_edited_skills(self) -> None:
        with ManagedInstall() as install:
            skill_file = install.namespace_root / "description-scaffold" / "SKILL.md"
            skill_file.write_text(
                f"{skill_file.read_text(encoding='utf-8')}\nlocal edit\n",
                encoding="utf-8",
            )

            completed = install.run_update("--force")

            self.assertEqual(0, completed.returncode)
            self.assertEqual("9.9.9", install.installed_version())
            self.assertNotIn("local edit", skill_file.read_text(encoding="utf-8"))
            self.assertTrue((install.namespace_root / "description-scaffold" / "UPDATED.txt").is_file())

    def test_dry_run_changes_nothing(self) -> None:
        with ManagedInstall() as install:
            wrapper_before = install.managed_bin_target.read_text(encoding="utf-8")

            completed = install.run_update("--dry-run")

            self.assertEqual(0, completed.returncode)
            self.assertIn("Dry run: no changes made.", completed.stdout)
            self.assertEqual("0.1.0", install.installed_version())
            self.assertEqual(wrapper_before, install.managed_bin_target.read_text(encoding="utf-8"))
            self.assertFalse((install.namespace_root / "description-scaffold" / "UPDATED.txt").exists())

    def test_unmanaged_command_path_fails(self) -> None:
        with ManagedInstall() as install:
            install.bin_path.unlink()
            unmanaged_target = install.root / "other-ros-devkit"
            unmanaged_target.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
            install.bin_path.symlink_to(unmanaged_target)

            completed = install.run_update(check=False)

            self.assertNotEqual(0, completed.returncode)
            self.assertIn("not managed by this installer", completed.stderr)
            self.assertEqual("0.1.0", install.installed_version())
            self.assertFalse((install.namespace_root / "description-scaffold" / "UPDATED.txt").exists())


class ManagedInstall:
    def __init__(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.install_home = self.root / "install-home"
        self.source_dir = self.install_home / "source"
        self.venv_dir = self.install_home / "venv"
        self.bin_dir = self.root / "bin"
        self.bin_path = self.bin_dir / "ros-devkit"
        self.managed_bin_target = self.venv_dir / "bin" / "ros-devkit"
        self.config_home = self.root / "config"
        self.agent_skill_root = self.root / "skills"
        self.namespace_root = self.agent_skill_root / "ros2"
        self.remote = self.root / "remote"

    def __enter__(self) -> "ManagedInstall":
        self._create_remote()
        self._create_managed_install()
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self._tmp.cleanup()

    def run_update(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env.update(
            {
                "HOME": str(self.root / "home"),
                "XDG_CONFIG_HOME": str(self.config_home),
                "ROS_DEVKIT_INSTALL_HOME": str(self.install_home),
                "ROS_DEVKIT_BIN_DIR": str(self.bin_dir),
                "ROS_DEVKIT_REPO_URL": str(self.remote),
                "ROS_DEVKIT_SOURCE": str(self.source_dir),
                "PYTHONPATH": str(self.source_dir / "src"),
            }
        )
        return subprocess.run(
            [sys.executable, "-m", "ros_devkit.cli", "update", *args],
            cwd=self.root,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=check,
        )

    def installed_version(self) -> str:
        namespace: dict[str, str] = {}
        exec((self.source_dir / "src" / "ros_devkit" / "__init__.py").read_text(encoding="utf-8"), namespace)
        return namespace["__version__"]

    def _create_remote(self) -> None:
        shutil.copytree(
            REPO_ROOT,
            self.remote,
            ignore=shutil.ignore_patterns(".git", ".pytest_cache", "__pycache__", "*.pyc"),
        )
        init_file = self.remote / "src" / "ros_devkit" / "__init__.py"
        init_file.write_text('__all__ = ["__version__"]\n\n__version__ = "9.9.9"\n', encoding="utf-8")
        updated_file = self.remote / "skills" / ".curated" / "ros2" / "description-scaffold" / "UPDATED.txt"
        updated_file.write_text("updated from main\n", encoding="utf-8")
        updated_script = (
            self.remote
            / "skills"
            / ".curated"
            / "ros2"
            / "description-scaffold"
            / "scripts"
            / "updated_check.py"
        )
        updated_script.write_text("raise SystemExit(0)\n", encoding="utf-8")
        registry_file = self.remote / "src" / "ros_devkit" / "registry.py"
        registry_file.write_text(
            registry_file.read_text(encoding="utf-8").replace(
                "    ),\n}\n",
                '    ),\n    "updated-check": SkillCommand(\n'
                '        name="updated-check",\n'
                '        script_path="description-scaffold/scripts/updated_check.py",\n'
                "    ),\n}\n",
            ),
            encoding="utf-8",
        )

        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=self.remote, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=self.remote, check=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=self.remote, check=True)
        subprocess.run(["git", "add", "."], cwd=self.remote, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "new main"], cwd=self.remote, check=True)

    def _create_managed_install(self) -> None:
        old_source = self.root / "old-source"
        shutil.copytree(
            REPO_ROOT,
            old_source,
            ignore=shutil.ignore_patterns(".git", ".pytest_cache", "__pycache__", "*.pyc"),
        )
        marker = old_source / ".ros-devkit-source"
        marker.write_text(f"repo={self.remote}\nref=main\n", encoding="utf-8")

        self.install_home.mkdir(parents=True)
        shutil.move(str(old_source), self.source_dir)

        shutil.copytree(self.source_dir / "skills" / ".curated" / "ros2", self.namespace_root)
        self._write_config()
        self._write_managed_wrapper()

    def _write_config(self) -> None:
        config_dir = self.config_home / "ros-devkit"
        config_dir.mkdir(parents=True)
        (config_dir / "config.env").write_text(
            textwrap.dedent(
                f"""\
                ROS_DEVKIT_AGENT=custom
                ROS_DEVKIT_SKILL_ROOT={self.namespace_root}
                """
            ),
            encoding="utf-8",
        )

    def _write_managed_wrapper(self) -> None:
        (self.venv_dir / "bin").mkdir(parents=True)
        self.managed_bin_target.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
        self.managed_bin_target.chmod(0o755)
        self.bin_dir.mkdir(parents=True)
        self.bin_path.symlink_to(self.managed_bin_target)


if __name__ == "__main__":
    unittest.main()
