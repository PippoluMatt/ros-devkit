from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from ros_devkit.config import load_config


class ConfigTest(unittest.TestCase):
    def test_env_skill_root_can_supply_config_without_config_file(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root)
            skill_root = root_path / "checkout" / "skills" / ".curated" / "ros2"
            config_file = root_path / "missing" / "config.env"

            with mock.patch.dict(
                os.environ,
                {
                    "ROS_DEVKIT_SKILL_ROOT": str(skill_root),
                    "ROS_DEVKIT_AGENT": "custom",
                },
                clear=False,
            ):
                config = load_config(config_file=config_file)

            self.assertEqual("custom", config.agent)
            self.assertEqual(skill_root, config.skill_root)
            self.assertEqual(config_file, config.config_file)


if __name__ == "__main__":
    unittest.main()
