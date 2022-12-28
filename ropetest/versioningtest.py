import secrets
from unittest.mock import patch

from rope.base import versioning


def test_calculate_version_hash(project):
    version_hash = versioning.calculate_version_hash(project)
    assert isinstance(version_hash, str)


def test_version_hash_is_constant(project):
    version_hash_1 = versioning.calculate_version_hash(project)
    version_hash_2 = versioning.calculate_version_hash(project)
    assert version_hash_1 == version_hash_2


def test_version_hash_varies_on_rope_version(project):
    actual_version_hash = versioning.calculate_version_hash(project)
    with patch("rope.VERSION", "1.0.0"):
        patched_version_hash = versioning.calculate_version_hash(project)
    assert actual_version_hash != patched_version_hash


def test_version_hash_varies_on_user_preferences(project):
    actual_version_hash = versioning.calculate_version_hash(project)
    assert project.prefs.get("automatic_soa") is False
    project.prefs.set("automatic_soa", True)
    patched_version_hash = versioning.calculate_version_hash(project)
    assert actual_version_hash != patched_version_hash


def test_version_hash_varies_on_get_file_content(project):
    actual_version_hash = versioning.calculate_version_hash(project)
    with patch("rope.base.versioning._get_file_content", return_value=secrets.token_hex()):
        patched_version_hash = versioning.calculate_version_hash(project)
    assert actual_version_hash != patched_version_hash
