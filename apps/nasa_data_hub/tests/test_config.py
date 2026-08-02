import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from nasa_data_hub.config import DEMO_KEY, Settings, load_dotenv


class ConfigTests(unittest.TestCase):
    def test_demo_key_is_default(self):
        settings = Settings.from_env(env_file=None, environ={})
        self.assertEqual(settings.api_key, DEMO_KEY)
        self.assertTrue(settings.using_demo_key)

    def test_personal_key_from_mapping(self):
        settings = Settings.from_env(env_file=None, environ={"NASA_API_KEY": "abc"})
        self.assertEqual(settings.api_key, "abc")
        self.assertEqual(settings.key_mode, "personal")

    def test_dotenv_loader_preserves_existing_values(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / ".env"
            path.write_text('NASA_API_KEY="from-file"\nNASA_HUB_PORT=9000\n', encoding="utf-8")
            with patch.dict(os.environ, {"NASA_API_KEY": "existing"}, clear=True):
                self.assertTrue(load_dotenv(path))
                self.assertEqual(os.environ["NASA_API_KEY"], "existing")
                self.assertEqual(os.environ["NASA_HUB_PORT"], "9000")

    def test_invalid_port_is_rejected(self):
        with self.assertRaises(ValueError):
            Settings.from_env(env_file=None, environ={"NASA_HUB_PORT": "99999"})


if __name__ == "__main__":
    unittest.main()
