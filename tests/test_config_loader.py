import json
import os
import asyncio
import tempfile
import urllib.request
import unittest
from pathlib import Path
from unittest.mock import patch

import main


class ConfigLoaderTests(unittest.TestCase):
    def test_resolve_bot_token_prefers_non_empty_environment_value(self):
        self.assertEqual(main.resolve_bot_token(' env-token ', 'config-token'), 'env-token')
        self.assertEqual(main.resolve_bot_token('   ', ' config-token '), 'config-token')
        self.assertEqual(main.resolve_bot_token('', ''), '')

    def test_health_server_serves_render_root_check(self):
        with patch.dict(os.environ, {'PORT': '0'}):
            server = main.start_health_server()

        try:
            self.assertIsNotNone(server)
            with urllib.request.urlopen(
                f'http://127.0.0.1:{server.server_address[1]}/'
            ) as response:
                self.assertEqual(response.status, 200)
                self.assertEqual(response.read(), b'OK')
        finally:
            server.shutdown()
            server.server_close()

    def test_setup_hook_loads_command_extensions(self):
        async def load_and_check():
            bot = main.bot
            try:
                await bot.setup_hook()
                for command_name in (
                    'warn', 'balance', 'profile', 'char_create',
                    'faction', 'help', 'about',
                ):
                    self.assertIn(command_name, bot.all_commands)
                help_cog = bot.get_cog('Помощь')
                listing = help_cog.command_listing()
                self.assertIn('!quest', listing)
                self.assertIn('!change_government', listing)
            finally:
                await bot.close()

        asyncio.run(load_and_check())

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
