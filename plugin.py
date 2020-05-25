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

SETTINGS_FILENAME = 'LSP-tagml.sublime-settings'


def plugin_loaded() -> None:
    LspTAGMLServer.setup()


def plugin_unloaded() -> None:
    LspTAGMLServer.teardown()


def is_java_installed() -> bool:
    return shutil.which("java") is not None


def is_tagml_installed() -> bool:
    cache_path = os.path.join(sublime.cache_path(), "TAGML")
    return os.path.isdir(cache_path)


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
    def setup(cls) -> None:
        if cls.thread or cls.ready:
            return

        # check TAGML is installed
        if not is_tagml_installed():
            msg = 'Install aborted:\nLSP-tagml depends on the TAGML Package to define the TAGML language for Sublime Text 3\nPlease install the TAGML Package first.'
            sublime.error_message(msg)
            LspTAGMLServer.teardown()
            raise Exception(msg)

        # read server source information
        filename = "Packages/{}/server.json".format(__package__)
        server_json = sublime.decode_value(sublime.load_resource(filename))

        cls.version = server_json["version"]
        cls.url = sublime.expand_variables(server_json["url"], {"version": cls.version})
        cls.checksum = server_json["sha256"].lower()

        # built local server binary path
        dest_path = package_cache()
        cls.binary = os.path.join(dest_path, os.path.basename(cls.url))

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
    def teardown(cls) -> None:
        try:
            os.remove(cls.binary)
        except OSError:
            pass
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
        missing_dependencies = []
        if not is_tagml_installed():
            missing_dependencies.append("Please install the TAGML Package.")
        if not is_java_installed():
            missing_dependencies.append("Please install Java Runtime for the TAGML language server to work.")
        if missing_dependencies:
            missing_dependencies.insert(0, "Some dependencies were missing:")
            sublime.message_dialog("\n  ".join(missing_dependencies))
            return False
        if not LspTAGMLServer.ready:
            sublime.status_message("Language server binary not yet downloaded.")
            return False
        return True
