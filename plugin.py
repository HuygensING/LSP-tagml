import hashlib
import os
import shutil
import threading
from urllib.request import urlretrieve

import sublime
from LSP.plugin import ClientConfig, LanguageHandler, read_client_config
from sublime_lib import ActivityIndicator

SERVER_URL = "http://cdn.huygens.knaw.nl/alexandria/tagml-language-server-0.1.jar"
SERVER_SHA256 = "4a11573c3c646cfa0a9d25c67ed428721282a912c0031d02e25f4417a9d14e72"


def is_java_installed() -> bool:
    return shutil.which("java") is not None


def is_tagml_installed() -> bool:
    cache_path = os.path.join(sublime.cache_path(), "TAGML")
    return os.path.isdir(cache_path)


def merge_configs(target: dict, source: dict):
    for key, value in target.items():
        new_value = source.get(key)
        if new_value is not None:
            if value:
                if isinstance(value, dict):
                    yield key, dict(merge_configs(value, new_value))
                    continue

                if isinstance(value, list):
                    if isinstance(value[0], dict):
                        # dicts are unhashable
                        yield key, new_value
                        continue
                    # always merge user values into defaults
                    yield key, list(set(value) + set(new_value))
                    continue

            yield key, new_value

        else:
            yield key, value

    return None


class LspTAGMLPlugin(LanguageHandler):
    binary = None
    ready = False
    thread = None

    def __init__(self):
        super().__init__()
        self.setup()

    @property
    def name(self) -> str:
        return __package__.lower()

    @property
    def config(self) -> ClientConfig:
        settings_file = "LSP-tagml.sublime-settings"

        client_config = {
            "enabled": True,
            "command": [
                "java",
                "-Xmx64M",
                "-XX:+UseG1GC",
                "-XX:+UseStringDeduplication",
                "-DwatchParentProcess=false",
                "-jar", self.binary
            ]
        }

        default_config = sublime.decode_value(
            sublime.load_resource("Packages/{}/{}".format(__package__, settings_file))
        )

        user_config = sublime.load_settings(settings_file)
        for key, value in merge_configs(default_config, user_config):
            client_config[key] = value

        # setup scheme cache directory
        client_config.setdefault("settings", {}).setdefault("xml", {}).setdefault(
            "server", {}
        )["workDir"] = os.path.dirname(self.binary)

        return read_client_config(self.name, client_config)

    def on_start(self, window) -> bool:
        if not is_java_installed():
            sublime.status_message(
                "Please install Java Runtime for the TAGML language server to work."
            )
            return False
        if not is_tagml_installed():
            sublime.status_message(
                "Please install the TAGML Package."
            )
            return False
        if not self.ready:
            sublime.status_message("Language server binary not yet downloaded.")
            return False
        return True

    @classmethod
    def setup(cls) -> None:
        if cls.thread or cls.ready:
            return

        # built local server binary path
        cls.binary = os.path.join(
            cls.storage_path(), __package__, os.path.basename(SERVER_URL)
        )

        # move from cache path to package storage
        try:
            old_server_dir = os.path.join(sublime.cache_path(), __package__)
            if os.path.isdir(old_server_dir):
                dest_path = os.path.dirname(cls.binary)
                os.makedirs(dest_path, exist_ok=True)
                shutil.move(old_server_dir, cls.storage_path())
        except OSError:
            shutil.rmtree(old_server_dir, ignore_errors=True)

        # download server binary on demand
        cls.ready = not cls._needs_update_or_installation()
        if not cls.ready:
            cls.thread = threading.Thread(target=cls._install_or_update)
            cls.thread.start()

    @classmethod
    def _needs_update_or_installation(cls) -> bool:
        """Check sha256 hash of downloaded binary.

        Make sure not to run malicious or corrupted code.
        """
        try:
            with open(cls.binary, "rb") as stream:
                checksum = hashlib.sha256(stream.read()).hexdigest()
                return checksum.lower() != SERVER_SHA256.lower()
        except OSError:
            pass
        return True

    @classmethod
    def _install_or_update(cls) -> None:
        try:
            with ActivityIndicator(
                    target=sublime.active_window(),
                    label="Downloading TAGML language server binary",
            ):
                dest_path = os.path.dirname(cls.binary)
                os.makedirs(dest_path, exist_ok=True)
                urlretrieve(url=SERVER_URL, filename=cls.binary)
                cls.ready = not cls._needs_update_or_installation()
                if not cls.ready:
                    try:
                        os.remove(cls.binary)
                    except FileNotFoundError:
                        pass
                    raise Exception("CRC error!")
                else:
                    # clear old server binaries
                    for file_name in os.listdir(dest_path):
                        if os.path.splitext(file_name)[1].lower() != ".jar":
                            continue

                        try:
                            file_path = os.path.join(dest_path, file_name)
                            if not os.path.samefile(file_path, cls.binary):
                                os.remove(file_path)
                        except FileNotFoundError:
                            pass

        except Exception as error:
            sublime.error_message(
                "Error downloading TAGML server binary!\n\n" + str(error)
            )

        cls.thread = None


def plugin_loaded() -> None:
    LspTAGMLPlugin.setup()
