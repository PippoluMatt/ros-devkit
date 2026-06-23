from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]


class InstallCommandTest(unittest.TestCase):
    def test_installer_warns_with_direct_command_when_bin_dir_is_not_on_path(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            remote = self._create_remote(root_path)
            home = root_path / "home"
            bin_dir = home / ".local" / "bin"

            env = os.environ.copy()
            env.update(
                {
                    "HOME": str(home),
                    "XDG_CONFIG_HOME": str(root_path / "config"),
                    "ROS_DEVKIT_INSTALL_HOME": str(root_path / "install-home"),
                    "ROS_DEVKIT_BIN_DIR": str(bin_dir),
                    "ROS_DEVKIT_REPO_URL": str(remote),
                    "PATH": "/usr/bin:/bin",
                }
            )

            completed = subprocess.run(
                [
                    "bash",
                    str(REPO_ROOT / "install" / "install.sh"),
                    "--agent",
                    "custom",
                    "--skill-root",
                    str(root_path / "skills"),
                ],
                cwd=root_path,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )

            self.assertIn(f"WARNING: {bin_dir} is not on PATH.", completed.stderr)
            self.assertIn(f"{bin_dir / 'ros-devkit'} doctor", completed.stderr)
            self.assertIsNone(shutil.which("ros-devkit", path=env["PATH"]))

            doctor = subprocess.run(
                [str(bin_dir / "ros-devkit"), "doctor"],
                cwd=root_path,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )
            self.assertIn("Namespace root", doctor.stdout)

    def test_dev_runner_uses_checkout_without_installing_global_command(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            home = root_path / "home"
            env = os.environ.copy()
            env.update(
                {
                    "HOME": str(home),
                    "XDG_CONFIG_HOME": str(root_path / "config"),
                    "PATH": "/usr/bin:/bin",
                }
            )

            completed = subprocess.run(
                [str(REPO_ROOT / "install" / "dev_ros_devkit.sh"), "doctor"],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )

            self.assertIn(f"Namespace root : {REPO_ROOT / 'skills' / '.curated' / 'ros2'}", completed.stdout)
            self.assertFalse((home / ".local" / "bin" / "ros-devkit").exists())

    def test_local_sandbox_installs_checkout_snapshot_in_isolated_paths(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            checkout = self._copy_checkout(root_path / "checkout")
            self._add_local_feature(checkout)
            sandbox = root_path / ".dev-install"
            env = self._sandbox_env(root_path)

            completed = subprocess.run(
                ["bash", str(checkout / "install" / "install.sh"), "--local-sandbox", ".dev-install"],
                cwd=root_path,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )

            command = sandbox / "bin" / "ros-devkit"
            config_file = sandbox / "config" / "ros-devkit" / "config.env"
            namespace_root = sandbox / "skills" / "ros2"
            source_snapshot = sandbox / "share" / "ros-devkit" / "source"

            self.assertIn(f"Sandbox root     : {sandbox}", completed.stdout)
            self.assertIn(f"Namespace root   : {namespace_root}", completed.stdout)
            self.assertIn(f"Config file      : {config_file}", completed.stdout)
            self.assertTrue((sandbox / ".ros-devkit-local-sandbox").is_file())
            self.assertTrue(command.exists())
            self.assertTrue(config_file.is_file())
            self.assertTrue(namespace_root.is_dir())
            self.assertFalse((source_snapshot / ".git").exists())
            self.assertFalse((root_path / "home" / ".local" / "bin" / "ros-devkit").exists())
            self.assertFalse((root_path / "user-config" / "ros-devkit" / "config.env").exists())

            feature = subprocess.run(
                [str(command), "local-feature"],
                cwd=root_path,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )
            self.assertIn("local feature from sandbox", feature.stdout)

            doctor = subprocess.run(
                [str(command), "doctor"],
                cwd=root_path,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )
            self.assertIn(f"Namespace root : {namespace_root}", doctor.stdout)
            self.assertIn(f"Config file    : {config_file}", doctor.stdout)

            update = subprocess.run(
                [str(command), "update"],
                cwd=root_path,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertNotEqual(0, update.returncode)
            self.assertIn("update is disabled for local sandbox installs", update.stderr)

    def test_local_sandbox_is_rerunnable_only_when_marked(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            checkout = self._copy_checkout(root_path / "checkout")
            env = self._sandbox_env(root_path)
            sandbox = root_path / ".dev-install"

            subprocess.run(
                ["bash", str(checkout / "install" / "install.sh"), "--local-sandbox", ".dev-install"],
                cwd=root_path,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )
            stale_file = sandbox / "stale.txt"
            stale_file.write_text("old sandbox content\n", encoding="utf-8")

            subprocess.run(
                ["bash", str(checkout / "install" / "install.sh"), "--local-sandbox", ".dev-install"],
                cwd=root_path,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )
            self.assertFalse(stale_file.exists())
            self.assertTrue((sandbox / ".ros-devkit-local-sandbox").is_file())

            unmarked = root_path / "unmarked"
            unmarked.mkdir()
            blocked = subprocess.run(
                ["bash", str(checkout / "install" / "install.sh"), "--local-sandbox", str(unmarked)],
                cwd=root_path,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertNotEqual(0, blocked.returncode)
            self.assertIn("without .ros-devkit-local-sandbox", blocked.stderr)
            self.assertTrue(unmarked.is_dir())

    def test_local_sandbox_rejects_normal_install_targeting_flags(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            checkout = self._copy_checkout(root_path / "checkout")
            env = self._sandbox_env(root_path)

            cases = [
                ["--agent", "custom"],
                ["--skill-root", str(root_path / "skills")],
                ["--ref", "main"],
            ]
            for index, extra_args in enumerate(cases):
                with self.subTest(extra_args=extra_args):
                    completed = subprocess.run(
                        [
                            "bash",
                            str(checkout / "install" / "install.sh"),
                            "--local-sandbox",
                            f".dev-install-{index}",
                            *extra_args,
                        ],
                        cwd=root_path,
                        env=env,
                        text=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        check=False,
                    )

                    self.assertNotEqual(0, completed.returncode)
                    self.assertIn(
                        "--local-sandbox cannot be combined with --agent, --skill-root, or --ref",
                        completed.stderr,
                    )

    def _sandbox_env(self, root_path: Path) -> dict[str, str]:
        env = os.environ.copy()
        env.update(
            {
                "HOME": str(root_path / "home"),
                "XDG_CONFIG_HOME": str(root_path / "user-config"),
                "PATH": "/usr/bin:/bin",
            }
        )
        return env

    def _copy_checkout(self, target: Path) -> Path:
        shutil.copytree(
            REPO_ROOT,
            target,
            ignore=shutil.ignore_patterns(
                ".git",
                ".pytest_cache",
                ".test-install",
                ".dev-install",
                "__pycache__",
                "*.pyc",
            ),
        )
        return target

    def _add_local_feature(self, checkout: Path) -> None:
        feature_script = (
            checkout
            / "skills"
            / ".curated"
            / "ros2"
            / "description-scaffold"
            / "scripts"
            / "local_feature.py"
        )
        feature_script.write_text('print("local feature from sandbox")\n', encoding="utf-8")

        registry_file = checkout / "src" / "ros_devkit" / "registry.py"
        registry_file.write_text(
            registry_file.read_text(encoding="utf-8").replace(
                "    ),\n}\n",
                '    ),\n    "local-feature": SkillCommand(\n'
                '        name="local-feature",\n'
                '        script_path="description-scaffold/scripts/local_feature.py",\n'
                "    ),\n}\n",
            ),
            encoding="utf-8",
        )

    def _create_remote(self, root: Path) -> Path:
        remote = root / "remote"
        shutil.copytree(
            REPO_ROOT,
            remote,
            ignore=shutil.ignore_patterns(".git", ".pytest_cache", ".test-install", "__pycache__", "*.pyc"),
        )
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=remote, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=remote, check=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=remote, check=True)
        subprocess.run(["git", "add", "."], cwd=remote, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "test remote"], cwd=remote, check=True)
        return remote


if __name__ == "__main__":
    unittest.main()
