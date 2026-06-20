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
                    str(REPO_ROOT / "scripts" / "install.sh"),
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
                [str(REPO_ROOT / "scripts" / "dev_ros_devkit.sh"), "doctor"],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )

            self.assertIn(f"Namespace root : {REPO_ROOT / 'skills' / '.curated' / 'ros2'}", completed.stdout)
            self.assertFalse((home / ".local" / "bin" / "ros-devkit").exists())

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
