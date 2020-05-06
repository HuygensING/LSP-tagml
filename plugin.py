# inspired by LSP-lemminx : https://github.com/sublimelsp/LSP-lemminx
import hashlib
import os
import shutil
import threading
import urllib.request

import sublime
from LSP.plugin.core.handlers import LanguageHandler
from LSP.plugin.core.settings import ClientConfig, read_client_config
from sublime_lib import ActivityIndicator

PACKAGE_NAME = 'LSP-tagml'
SETTINGS_FILENAME = 'LSP-tagml.sublime-settings'


def plugin_loaded() -> None:
    LspTAGMLServer.setup()


def plugin_unloaded() -> None:
    LspTAGMLServer.teardown()


def is_java_installed() -> bool:
    return shutil.which("java") is not None


def package_cache() -> str:
    cache_path = os.path.join(sublime.cache_path(), __package__)
    os.makedirs(cache_path, exist_ok=True)
    return cache_path


class LspTAGMLServer(object):
    binary = None
    checksum = None
    ready = False
    url = None
    version = None
    thread = None

    @classmethod
    def check_binary(cls) -> bool:
        """Check sha256 hash of downloaded binary.
        Make sure not to run malicious or corrupted code.
        """
        try:
            with open(cls.binary, "rb") as stream:
                checksum = hashlib.sha256(stream.read()).hexdigest()
                return cls.checksum == checksum
        except OSError:
            pass
        return False

    @classmethod
    def download(cls) -> None:
        with ActivityIndicator(
                target=sublime.active_window(),
                label="Downloading TAGML language server binary",
        ):
            urllib.request.urlretrieve(url=cls.url, filename=cls.binary)
            sublime.status_message("jar file downloaded")
            cls.ready = cls.check_binary()
            if not cls.ready:
                try:
                    os.remove(cls.binary)
                except OSError:
                    pass

        if not cls.ready:
            sublime.error_message("Error downloading TAGML server binary!")

        sublime.message_dialog(
            'The tagml-language-server has been installed, a restart of Sublime Text 3 is required to activate it.')
        cls.thread = None

    @classmethod
    def setup(cls) -> None:
        if cls.thread or cls.ready:
            return

        # read server source information
        filename = "Packages/{}/server.json".format(__package__)
        server_json = sublime.decode_value(sublime.load_resource(filename))

        cls.version = server_json["version"]
        cls.url = sublime.expand_variables(server_json["url"], {"version": cls.version})
        cls.checksum = server_json["sha256"].lower()

        # built local server binary path
        dest_path = package_cache()
        cls.binary = os.path.join(dest_path, os.path.basename(cls.url))
        # raise Exception(cls.version + ":" + cls.url + " -> " + cls.binary)

        # download server binary on demand
        cls.ready = cls.check_binary()
        if not cls.ready:
            cls.thread = threading.Thread(target=cls.download)
            cls.thread.start()

        # clear old server binaries
        for fn in os.listdir(dest_path):
            fp = os.path.join(dest_path, fn)
            if fn[-4:].lower() == ".jar" and not os.path.samefile(fp, cls.binary):
                try:
                    os.remove(fp)
                except OSError:
                    pass

    @classmethod
    def teardown(cls) -> None:
        cls.binary = None
        cls.checksum = None
        cls.ready = False
        cls.url = None
        cls.version = None


class LspTAGMLPlugin(LanguageHandler):
    @property
    def name(self) -> str:
        return __package__.lower()

    @property
    def config(self) -> ClientConfig:
        LspTAGMLServer.setup()

        default_configuration = {
            "enabled": True,
            "command": ["java", "-jar", LspTAGMLServer.binary],
        }

        loaded_settings = sublime.load_settings(SETTINGS_FILENAME)
        if loaded_settings:
            for key in ("env", "languages", "initializationOptions", "settings"):
                default_configuration[key] = loaded_settings.get(key)

        return read_client_config(self.name, default_configuration)

    def on_start(self, window) -> bool:
        if not is_java_installed():
            sublime.message_dialog(
                "Please install Java Runtime for the TAGML language server to work."
            )
            return False
        if not LspTAGMLServer.ready:
            sublime.status_message("Language server binary not yet downloaded.")
            return False
        return True
