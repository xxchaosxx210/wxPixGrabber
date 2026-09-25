import json
import os
import shutil
from urllib.parse import urlparse

TEST_HOST = "localhost"
TEST_URL_PATH = "/setup_test"
TEST_OUTPUT_FOLDER = "PixGrabber_Dummy_Site"

DUMMY_SITE_PATH = os.path.join(os.path.dirname(__file__), "dummysite")
TEST_SETTINGS_PATH = os.path.join(DUMMY_SITE_PATH, "test_settings.json")

DEFAULT_TEST_SETTINGS = {
    "image_count": 20,
    "clean_downloads_before_test": True,
    "port": 5000
}


def _normalise(settings):
    source = settings if isinstance(settings, dict) else {}

    try:
        image_count = int(source.get("image_count", DEFAULT_TEST_SETTINGS["image_count"]))
    except (TypeError, ValueError):
        image_count = DEFAULT_TEST_SETTINGS["image_count"]

    try:
        port = int(source.get("port", DEFAULT_TEST_SETTINGS["port"]))
    except (TypeError, ValueError):
        port = DEFAULT_TEST_SETTINGS["port"]

    # Migrate the short-lived old cleanup option to the safer pre-test cleanup.
    clean_before = source.get("clean_downloads_before_test")
    if clean_before is None:
        clean_before = source.get("delete_downloads_after_test", True)

    return {
        "image_count": max(1, min(100, image_count)),
        "clean_downloads_before_test": bool(clean_before),
        "port": max(1, min(65535, port))
    }


def load_test_settings():
    settings = dict(DEFAULT_TEST_SETTINGS)
    try:
        if os.path.exists(TEST_SETTINGS_PATH):
            with open(TEST_SETTINGS_PATH, "r") as fp:
                settings = json.load(fp)
    except (OSError, ValueError, TypeError):
        settings = dict(DEFAULT_TEST_SETTINGS)

    settings = _normalise(settings)
    save_test_settings(settings)
    return settings


def save_test_settings(settings):
    settings = _normalise(settings)
    os.makedirs(DUMMY_SITE_PATH, exist_ok=True)
    with open(TEST_SETTINGS_PATH, "w") as fp:
        json.dump(settings, fp, indent=2)
    return settings


def get_test_url(settings=None):
    if settings is None:
        settings = load_test_settings()
    return f"http://{TEST_HOST}:{settings['port']}{TEST_URL_PATH}"


def is_test_url(url):
    if not isinstance(url, str):
        return False

    try:
        parsed = urlparse(url)
        port = parsed.port or 80
    except (TypeError, ValueError):
        return False

    settings = load_test_settings()
    return (
        parsed.hostname in ("localhost", "127.0.0.1")
        and port == settings["port"]
        and parsed.path.rstrip("/") == TEST_URL_PATH.rstrip("/")
    )


def get_test_output_path(save_path):
    return os.path.abspath(os.path.join(save_path, TEST_OUTPUT_FOLDER))


def cleanup_test_downloads(save_path):
    output_path = get_test_output_path(save_path)
    parent = os.path.abspath(save_path)

    # Safety guard: only ever remove the dedicated test folder directly
    # underneath the configured save path.
    if os.path.basename(output_path) != TEST_OUTPUT_FOLDER:
        return False
    if os.path.dirname(output_path) != parent:
        return False
    if not os.path.isdir(output_path):
        return False

    shutil.rmtree(output_path)
    return True
