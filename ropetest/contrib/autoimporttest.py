import pytest

from rope.contrib import autoimport
from ropetest import testutils


@pytest.fixture
def project():
    project = testutils.sample_project(extension_modules=["sys"])
    yield project
    testutils.remove_project(project)


@pytest.fixture
def project_name():
    return "sample_project"


@pytest.fixture
def importer(project):
    importer = autoimport.AutoImport(project, observe=False, memory=True)
    yield importer
    importer.close()


@pytest.fixture
def mod1(importer, project):
    mod1 = testutils.create_module(project, "mod1")
    yield mod1


@pytest.fixture
def pkg(importer, project):
    pkg = testutils.create_package(project, "pkg")
    yield pkg


@pytest.fixture
def importer_observing(project):
    project = testutils.sample_project()
    importer = autoimport.AutoImport(project, observe=True, memory=True)
    yield importer
    importer.close()


@pytest.fixture
def mod2(importer, project, pkg):
    mod2 = testutils.create_module(project, "mod2")
    yield mod2


class TestAutoImport:
    def test_simple_case(self, importer):
        assert [] == importer.import_assist("A")

    def test_update_resource(self, importer, mod1):
        mod1.write("myvar = None\n")
        importer.update_resource(mod1)
        assert [("myvar", "mod1")] == importer.import_assist("myva")

    def test_update_module(self, importer, mod1):
        mod1.write("myvar = None")
        importer.update_module("mod1")
        assert [("myvar", "mod1")] == importer.import_assist("myva")

    def test_update_non_existent_module(self, importer):
        importer.update_module("does_not_exists_this")
        assert [] == importer.import_assist("myva")

    def test_module_with_syntax_errors(self, importer, mod1):
        mod1.write("this is a syntax error\n")
        importer.update_resource(mod1)
        assert [] == importer.import_assist("myva")

    def test_excluding_imported_names(self, mod1, importer):
        mod1.write("import pkg\n")
        importer.update_resource(mod1)
        assert [] == importer.import_assist("pkg")

    def test_get_modules(self, mod1, importer, project_name):
        mod1.write("myvar = None\n")
        importer.update_resource(mod1)
        assert [f"{project_name}.mod1"] == importer.get_modules("myvar")

    def test_get_modules_inside_packages(self, mod1, mod2, importer, project_name):
        mod1.write("myvar = None\n")
        mod2.write("myvar = None\n")
        importer.update_resource(mod1)
        importer.update_resource(mod2)
        assert set([f"{project_name}.mod1", f"{project_name}.pkg.mod2"]) == set(
            importer.get_modules("myvar")
        )

    def test_trivial_insertion_line(self, importer):
        result = importer.find_insertion_line("")
        assert 1 == result

    def test_insertion_line(self, importer):
        result = importer.find_insertion_line("import mod\n")
        assert 2 == result

    def test_insertion_line_with_pydocs(self, importer):
        result = importer.find_insertion_line('"""docs\n\ndocs"""\nimport mod\n')
        assert 5 == result

    def test_insertion_line_with_multiple_imports(self, importer):
        result = importer.find_insertion_line("import mod1\n\nimport mod2\n")
        assert 4 == result

    def test_insertion_line_with_blank_lines(self, importer):
        result = importer.find_insertion_line("import mod1\n\n# comment\n")
        assert 2 == result

    def test_empty_cache(self, importer, mod1, project_name):
        mod1.write("myvar = None\n")
        importer.update_resource(mod1)
        assert [f"{project_name}.mod1"] == importer.get_modules("myvar")

        importer.clear_cache()
        assert [] == importer.get_modules("myvar")

    def test_not_caching_underlined_names(self, importer, mod1):
        mod1.write("_myvar = None\n")
        importer.update_resource(mod1, underlined=False)
        assert [] == importer.get_modules("_myvar")
        importer.update_resource(mod1, underlined=True)
        assert ["mod1"] == importer.get_modules("_myvar")

    def test_caching_underlined_names_passing_to_the_constructor(self, project, mod1):
        importer = autoimport.AutoImport(project, False, True)
        mod1.write("_myvar = None\n")
        importer.update_resource(mod1)
        assert ["mod1"] == importer.get_modules("_myvar")
        importer.close()

    def test_name_locations(self, importer, mod1):
        mod1.write("myvar = None\n")
        importer.update_resource(mod1)
        assert [(mod1, 1)] == importer.get_name_locations("myvar")

    def test_name_locations_with_multiple_occurrences(self, mod1, mod2, importer):
        mod1.write("myvar = None\n")
        mod2.write("\nmyvar = None\n")
        importer.update_resource(mod1)
        importer.update_resource(mod2)
        assert set([(mod1, 1), (mod2, 2)]) == set(importer.get_name_locations("myvar"))

    def test_handling_builtin_modules(self, importer):
        importer.update_module("sys")
        assert "sys" == importer.get_modules("exit")


class TestAutoImportObserving:
    def test_writing_files(self, importer_observing, mod1, project_name):
        mod1.write("myvar = None\n")
        assert [f"{project_name}.mod1"] == importer_observing.get_modules("myvar")

    def test_moving_files(self, importer_observing, mod1, project_name):
        mod1.write("myvar = None\n")
        mod1.move("mod3.py")
        assert [f"{project_name}.mod3"] == importer_observing.get_modules("myvar")

    def test_removing_files(self, importer_observing, mod1):
        mod1.write("myvar = None\n")
        mod1.remove()
        assert [] == importer_observing.get_modules("myvar")
