import json
import os
import tempfile
import unittest
from pathlib import Path

import main


class ConfigLoaderTests(unittest.TestCase):
    def test_resolve_bot_token_prefers_non_empty_environment_value(self):
        self.assertEqual(main.resolve_bot_token(' env-token ', 'config-token'), 'env-token')
        self.assertEqual(main.resolve_bot_token('   ', ' config-token '), 'config-token')

    def test_load_config_merges_defaults(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / 'config.json'
            config_path.write_text(json.dumps({'default_prefix': '?'}), encoding='utf-8')

            config = main.load_config(str(config_path))

            self.assertEqual(config['default_prefix'], '?')
            self.assertIn('government_structure', config)
            self.assertEqual(config['advertising_enabled'], False)

    def test_load_config_creates_default_file_for_invalid_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / 'config.json'
            config_path.write_text('{broken json', encoding='utf-8')

            config = main.load_config(str(config_path))

            self.assertTrue(config_path.exists())
            self.assertIn('default_prefix', config)
            self.assertEqual(config['default_prefix'], '!')

    def test_load_config_creates_default_file_for_missing_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / 'missing.json'

            config = main.load_config(str(config_path))

            self.assertTrue(config_path.exists())
            self.assertIn('government_structure', config)


if __name__ == '__main__':
    unittest.main()
