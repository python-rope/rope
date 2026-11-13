import pytest

from rope.base.prefs import InvalidPreferenceKey


def test_get_pref(project):
    assert project.prefs["automatic_soa"] is False
    assert project.prefs.automatic_soa is False


def test_get_nonexistent_pref(project):
    assert project.prefs["nonexistent_pref"] is None
    sentinel = object()
    assert project.prefs.get("nonexistent_pref", sentinel) is sentinel
    assert not hasattr(project.prefs, "nonexistent_pref")


def test_set_pref_setitem(project):
    assert project.prefs["automatic_soa"] is False
    assert project.prefs.automatic_soa is False

    project.prefs["automatic_soa"] = True

    assert project.prefs["automatic_soa"] is True
    assert project.prefs.automatic_soa is True


def test_set_nonexistent_pref(project):
    assert project.prefs["nonexistent_pref"] is None

    with pytest.warns(
        RuntimeWarning,
        match="Invalid pref key <nonexistent_pref>",
    ):
        project.prefs["nonexistent_pref"] = True

    assert project.prefs["nonexistent_pref"] is True
    assert project.prefs.nonexistent_pref is True


def test_add_pref(project):
    assert project.prefs.python_files == ["*.py"]

    project.prefs.add("python_files", "*.xxx")

    assert project.prefs.python_files == ["*.py", "*.xxx"]


def test_add_nonexistent_pref(project):
    with pytest.raises(
        AttributeError,
        match="'Prefs' object has no attribute 'nonexistent_pref'",
    ):
        project.prefs.add("nonexistent_pref", "*.xxx")


def test_get_subpref(project):
    assert project.prefs["imports.preferred_import_style"] == "default"
    assert project.prefs.imports.preferred_import_style == "default"


def test_get_subpref_invalid_prefix(project):
    assert project.prefs["invalid_prefix.preferred_import_style"] is None
    sentinel = object()
    assert project.prefs.get("invalid_prefix.preferred_import_style", sentinel) is sentinel


def test_set_subpref(project):
    assert project.prefs["imports.preferred_import_style"] == "default"
    assert project.prefs.imports.preferred_import_style == "default"

    project.prefs["imports.preferred_import_style"] = "from-module"

    assert project.prefs["imports.preferred_import_style"] == "from-module"
    assert project.prefs.imports.preferred_import_style == "from-module"


def test_set_subpref_invalid_prefix(project):
    with pytest.warns(
        RuntimeWarning,
        match="Invalid pref key <invalid_prefix.nonexistent_pref>",
    ):
        project.prefs["invalid_prefix.nonexistent_pref"] = True

    assert not hasattr(project.prefs, 'invalid_prefix')
    assert not hasattr(project.prefs, 'nonexistent_pref')


def test_set_subpref_nonexistent_pref(project):
    assert project.prefs["autoimport.nonexistent_pref"] is None

    with pytest.warns(
        RuntimeWarning,
        match="Invalid pref key <autoimport.nonexistent_pref>",
    ):
        project.prefs["autoimport.nonexistent_pref"] = True

    assert not hasattr(project.prefs, 'nonexistent_pref')
    assert project.prefs["autoimport.nonexistent_pref"] is True


def test_add_subpref(project):
    test_data = ("test", "data")
    assert test_data not in project.prefs.autoimport.aliases

    project.prefs.add("autoimport.aliases", test_data)

    assert test_data in project.prefs.autoimport.aliases


def test_add_subpref_nonexistent_pref(project):
    test_data = ("test", "data")
    with pytest.raises(
        AttributeError,
        match="'AutoimportPrefs' object has no attribute 'nonexistent_pref'",
    ):
        project.prefs.add("autoimport.nonexistent_pref", test_data)


def test_add_subpref_invalid_prefix(project):
    test_data = ("test", "data")
    with pytest.warns(
        RuntimeWarning,
        match="Invalid pref key <invalid_prefix.nonexistent_pref>",
    ):
        with pytest.raises(InvalidPreferenceKey):
            project.prefs.add("invalid_prefix.nonexistent_pref", test_data)

    assert not hasattr(project.prefs, 'invalid_prefix')
    assert not hasattr(project.prefs, 'nonexistent_pref')


def test_add_subpref_optional_list(project):
    project.prefs["dependencies"] is None

    test_data = ("test", "data")
    project.prefs.add("dependencies", test_data)

    project.prefs["dependencies"] == [test_data]
