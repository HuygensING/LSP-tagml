import os
import shutil

import sublime
from LSP.plugin.core.handlers import LanguageHandler
from LSP.plugin.core.settings import ClientConfig, read_client_config

PACKAGE_NAME = 'LSP-tagml'
SETTINGS_FILENAME = 'LSP-tagml.sublime-settings'
SERVER_DIRECTORY = 'vscode-css'
SERVER_BINARY_PATH = os.path.join(SERVER_DIRECTORY, 'out', 'tagml-language-server.jar')


def plugin_loaded():
    server.setup()


def plugin_unloaded():
    server.cleanup()


def is_java_installed() -> bool:
    return shutil.which("java") is not None


class LspTAGMLPlugin(LanguageHandler):
    @property
    def name(self) -> str:
        return PACKAGE_NAME.lower()

    @property
    def config(self) -> ClientConfig:
        # Calling setup() also here as this might run before `plugin_loaded`.
        # Will be a no-op if already ran.
        # See https://github.com/sublimelsp/LSP/issues/899
        server.setup()

        configuration = self.migrate_and_read_configuration()

        default_configuration = {
            'enabled': True,
            'command': ['java', '-jar', server.binary_path],
        }

        default_configuration.update(configuration)

        return read_client_config('lsp-tagml', default_configuration)

    def migrate_and_read_configuration(self) -> dict:
        settings = {}
        loaded_settings = sublime.load_settings(SETTINGS_FILENAME)

        if loaded_settings:
            if loaded_settings.has('client'):
                client = loaded_settings.get('client')
                loaded_settings.erase('client')
                # Migrate old keys
                for key in client:
                    loaded_settings.set(key, client[key])
                sublime.save_settings(SETTINGS_FILENAME)

            # Read configuration keys
            for key in ['languages', 'initializationOptions', 'settings']:
                settings[key] = loaded_settings.get(key)

        return settings

    def on_start(self, window) -> bool:
        if not is_java_installed():
            sublime.status_message('Please install the Java JRE (>=8) for the TAGML Language Server to work.')
            return False
        return server.ready

    def on_initialized(self, client) -> None:
        pass  # extra initialization here.
