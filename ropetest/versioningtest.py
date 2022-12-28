from unittest.mock import patch

from rope.base import versioning


def test_calculate_version_hash():
    version_hash = versioning.calculate_version_hash()
    assert isinstance(version_hash, str)

def test_version_hash_is_constant():
    version_hash_1 = versioning.calculate_version_hash()
    version_hash_2 = versioning.calculate_version_hash()
    assert version_hash_1 == version_hash_2

def test_version_hash_varies_on_rope_version():
    actual_version_hash = versioning.calculate_version_hash()
    with patch("rope.VERSION", "1.0.0"):
        patched_version_hash = versioning.calculate_version_hash()
    assert actual_version_hash != patched_version_hash
