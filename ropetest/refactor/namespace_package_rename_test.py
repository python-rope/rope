import subprocess
import sys
import unittest
from pathlib import Path
from textwrap import dedent

from rope.refactor.rename import Rename
from ropetest import testutils


class NamespacePackageRenameTest(unittest.TestCase):
    def setUp(self):
        self.project = testutils.sample_project()
        self.root = Path(self.project.address)
        self.project.root.create_file("sentinel.txt").write("untouched\n")

    def tearDown(self):
        testutils.remove_project(self.project)

    def _file(self, name, contents):
        folder = self.project.root
        parts = name.split("/")
        for part in parts[:-1]:
            if not folder.has_child(part):
                folder.create_folder(part)
            folder = folder.get_child(part)
        resource = folder.create_file(parts[-1])
        resource.write(contents)
        return resource

    def _run(self, module, expected):
        result = subprocess.run(
            [sys.executable, "-B", "-m", module],
            cwd=self.root,
            capture_output=True,
            text=True,
            timeout=15,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(expected, result.stdout)
        self.assertEqual("", result.stderr)

    def _rename(self, package, new_name, **options):
        before = {
            path.relative_to(self.root).as_posix(): path.read_bytes()
            for path in self.root.rglob("*")
            if path.is_file() and ".ropeproject" not in path.parts
        }
        changes = Rename(self.project, package).get_changes(new_name, **options)
        after = {
            path.relative_to(self.root).as_posix(): path.read_bytes()
            for path in self.root.rglob("*")
            if path.is_file() and ".ropeproject" not in path.parts
        }
        self.assertEqual(before, after)
        self.project.do(changes)
        self.assertEqual("untouched\n", (self.root / "sentinel.txt").read_text())

    def test_namespace_directory_rename_preserves_saved_module_value(self):
        foreign = dedent("""\
                      class Foreign:
                          field = 'FOREIGN'
                      old = Foreign()
                  """)
        subject = dedent("""\
            import valuespkg.foreign
            class Other:
                field = 'OTHER'
            class Owner:
                import valuespkg as slot
            saved = Owner.slot
            Owner.slot = Other()
            print(saved.foreign.old.field)
        """)
        self._file("valuespkg/foreign.py", foreign)
        self._file("subject.py", subject)
        self._run("subject", "FOREIGN\n")
        self._rename(self.project.root.get_child("valuespkg"), "renamed_pkg")
        self.assertFalse((self.root / "valuespkg").exists())
        self.assertFalse((self.root / "renamed_pkg/__init__.py").exists())
        self.assertEqual(foreign, (self.root / "renamed_pkg/foreign.py").read_text())
        self.assertEqual(
            subject.replace("import valuespkg", "import renamed_pkg"),
            (self.root / "subject.py").read_text(),
        )
        self._run("subject", "FOREIGN\n")

    def test_nested_namespace_directory_rename_preserves_relative_import(self):
        self._file("outer/inner/value.py", "value = 42\n")
        reader = dedent("""\
                     from .value import value
                     print(value)
                 """)
        self._file("outer/inner/reader.py", reader)
        self._file(
            "subject.py",
            dedent("""\
                                     from outer.inner.value import value
                                     print(value)
                                 """),
        )
        self._run("subject", "42\n")
        self._run("outer.inner.reader", "42\n")
        self._rename(self.project.root.get_child("outer/inner"), "renamed")
        self.assertFalse((self.root / "outer/inner").exists())
        self.assertFalse((self.root / "outer/renamed/__init__.py").exists())
        self.assertEqual(reader, (self.root / "outer/renamed/reader.py").read_text())
        self.assertEqual(
            dedent("""\
                from outer.renamed.value import value
                print(value)
            """),
            (self.root / "subject.py").read_text(),
        )
        self._run("subject", "42\n")
        self._run("outer.renamed.reader", "42\n")

    def test_namespace_directory_rename_preserves_import_alias(self):
        self._file("valuespkg/value.py", "value = 42\n")
        self._file(
            "subject.py",
            dedent("""\
                              from valuespkg import value as saved
                              print(saved.value)
                          """),
        )
        self._run("subject", "42\n")
        self._rename(self.project.root.get_child("valuespkg"), "renamed_pkg")
        self.assertEqual(
            dedent("""\
                from renamed_pkg import value as saved
                print(saved.value)
            """),
            (self.root / "subject.py").read_text(),
        )
        self.assertFalse((self.root / "valuespkg").exists())
        self._run("subject", "42\n")

    def test_empty_namespace_directory_rename_moves_directory(self):
        package = self.project.root.create_folder("valuespkg")
        self._file(
            "subject.py",
            dedent("""\
                              import valuespkg
                              print(hasattr(valuespkg, '__path__'))
                          """),
        )
        self._run("subject", "True\n")
        self._rename(package, "renamed_pkg")
        self.assertTrue((self.root / "renamed_pkg").is_dir())
        self.assertFalse((self.root / "valuespkg").exists())
        self.assertFalse((self.root / "renamed_pkg/__init__.py").exists())
        self._run("subject", "True\n")

    def test_namespace_directory_rename_with_only_importer_keeps_directory(self):
        value = self._file("valuespkg/value.py", "value = 42\n")
        subject = self._file("subject.py", "import valuespkg.value\n")
        self._rename(
            self.project.root.get_child("valuespkg"),
            "renamed_pkg",
            resources=[subject],
        )
        self.assertEqual("import renamed_pkg.value\n", subject.read())
        self.assertTrue((self.root / "valuespkg").is_dir())
        self.assertFalse((self.root / "renamed_pkg").exists())
        self.assertEqual("value = 42\n", value.read())

    def test_regular_package_directory_rename_preserves_initializer(self):
        initializer = "value = 42\n"
        self._file("valuespkg/__init__.py", initializer)
        self._file(
            "subject.py",
            dedent("""\
                                     import valuespkg
                                     print(valuespkg.value)
                                 """),
        )
        self._run("subject", "42\n")
        self._rename(self.project.root.get_child("valuespkg"), "renamed_pkg")
        self.assertFalse((self.root / "valuespkg").exists())
        self.assertEqual(
            initializer, (self.root / "renamed_pkg/__init__.py").read_text()
        )
        self._run("subject", "42\n")

    def test_namespace_directory_rename_with_all_package_files_moves_directory(self):
        value = self._file("valuespkg/value.py", "value = 42\n")
        other = self._file("valuespkg/other.py", "other = 7\n")
        subject = self._file(
            "subject.py",
            dedent("""\
                              from valuespkg.value import value
                              print(value)
                          """),
        )
        self._run("subject", "42\n")
        self._rename(
            self.project.root.get_child("valuespkg"),
            "renamed_pkg",
            resources=[value, other, subject],
        )
        self.assertFalse((self.root / "valuespkg").exists())
        self.assertEqual(
            "other = 7\n", (self.root / "renamed_pkg/other.py").read_text()
        )
        self._run("subject", "42\n")

    def test_namespace_directory_rename_with_partial_package_files_keeps_directory(
        self,
    ):
        value = self._file("valuespkg/value.py", "value = 42\n")
        other = self._file("valuespkg/other.py", "other = 7\n")
        subject = self._file("subject.py", "import valuespkg.value\n")
        self._rename(
            self.project.root.get_child("valuespkg"),
            "renamed_pkg",
            resources=[value, subject],
        )
        self.assertTrue((self.root / "valuespkg").is_dir())
        self.assertFalse((self.root / "renamed_pkg").exists())
        self.assertEqual("import renamed_pkg.value\n", subject.read())
        self.assertEqual("value = 42\n", value.read())
        self.assertEqual("other = 7\n", other.read())

    def test_empty_namespace_directory_with_explicit_resources_keeps_directory(self):
        package = self.project.root.create_folder("valuespkg")
        subject = self._file("subject.py", "import valuespkg\n")
        self._rename(package, "renamed_pkg", resources=[subject])
        self.assertTrue((self.root / "valuespkg").is_dir())
        self.assertFalse((self.root / "renamed_pkg").exists())
        self.assertEqual("import renamed_pkg\n", subject.read())

    def test_regular_package_with_only_importer_keeps_initializer_and_directory(self):
        initializer = self._file("valuespkg/__init__.py", "value = 42\n")
        subject = self._file("subject.py", "import valuespkg\n")
        self._rename(
            self.project.root.get_child("valuespkg"),
            "renamed_pkg",
            resources=[subject],
        )
        self.assertEqual("import renamed_pkg\n", subject.read())
        self.assertEqual("value = 42\n", initializer.read())
        self.assertTrue((self.root / "valuespkg").is_dir())
        self.assertFalse((self.root / "renamed_pkg").exists())
