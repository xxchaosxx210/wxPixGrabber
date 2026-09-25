import json
import os
import shutil

TEST_URL_PATH = "/setup_test"
TEST_URL_FULL = "http://localhost:5000/setup_test"
TEST_OUTPUT_FOLDER = "PixGrabber_Dummy_Site"

DUMMY_SITE_PATH = os.path.join(os.path.dirname(__file__), "dummysite")
TEST_SETTINGS_PATH = os.path.join(DUMMY_SITE_PATH, "test_settings.json")

DEFAULT_TEST_SETTINGS = {
    "image_count": 20,
    "delete_downloads_after_test": True
}


def _normalise(settings):
    normalised = dict(DEFAULT_TEST_SETTINGS)
    if isinstance(settings, dict):
        normalised.update(settings)

    try:
        image_count = int(normalised.get("image_count", 20))
    except (TypeError, ValueError):
        image_count = 20

    normalised["image_count"] = max(1, min(100, image_count))
    normalised["delete_downloads_after_test"] = bool(
        normalised.get("delete_downloads_after_test", True)
    )
    return normalised


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


def is_test_url(url):
    if not isinstance(url, str):
        return False
    return url.rstrip("/") == TEST_URL_FULL.rstrip("/")


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
