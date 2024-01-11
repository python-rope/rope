import os.path
import pathlib
import tempfile
import unittest
from textwrap import dedent

from rope.base.exceptions import ResourceNotFoundError, RopeError
from rope.base.fscommands import FileSystemCommands
from rope.base.libutils import path_to_resource
from rope.base.project import NoProject, Project, _realpath
from rope.base.resourceobserver import FilteredResourceObserver
from rope.base.resources import File, Folder
from ropetest import testutils


class ProjectTest(unittest.TestCase):
    def setUp(self):
        unittest.TestCase.setUp(self)
        self.project = testutils.sample_project(
            foldername="sampleproject", ropefolder=None
        )
        self.project_root = self.project.address
        self._make_sample_project()
        self.no_project = NoProject()

    def _make_sample_project(self):
        self.sample_file = "sample_file.txt"
        self.sample_path = os.path.join(self.project_root, "sample_file.txt")
        if not os.path.exists(self.project_root):
            os.mkdir(self.project_root)
        self.sample_folder = "sample_folder"
        os.mkdir(os.path.join(self.project_root, self.sample_folder))
        sample = open(self.sample_path, "w")
        sample.write("sample text\n")
        sample.close()

    def tearDown(self):
        testutils.remove_project(self.project)
        unittest.TestCase.tearDown(self)

    def test_project_creation(self):
        self.assertEqual(_realpath(self.project_root), self.project.address)

    def test_getting_project_file(self):
        project_file = self.project.get_resource(self.sample_file)
        self.assertTrue(project_file is not None)

    def test_project_file_reading(self):
        projectFile = self.project.get_resource(self.sample_file)
        self.assertEqual("sample text\n", projectFile.read())

    def test_getting_not_existing_project_file(self):
        with self.assertRaises(ResourceNotFoundError):
            self.project.get_resource("DoesNotExistFile.txt")

    def test_writing_in_project_files(self):
        project_file = self.project.get_resource(self.sample_file)
        project_file.write("another text\n")
        self.assertEqual("another text\n", project_file.read())

    def test_creating_files(self):
        project_file = "newfile.txt"
        self.project.root.create_file(project_file)
        newFile = self.project.get_resource(project_file)
        self.assertTrue(newFile is not None)

    def test_creating_files_that_already_exist(self):
        with self.assertRaises(RopeError):
            self.project.root.create_file(self.sample_file)

    def test_making_root_folder_if_it_does_not_exist(self):
        with tempfile.TemporaryDirectory(dir=testutils.RUN_TMP_DIR) as tmpdir:
            project_root = pathlib.Path(tmpdir) / "sampleproject2"
            assert not project_root.exists()

            project = Project(project_root)

            assert project_root.exists()
            assert project_root.is_dir()

    def test_failure_when_project_root_exists_and_is_a_file(self):
        with tempfile.TemporaryDirectory(dir=testutils.RUN_TMP_DIR) as tmpdir:
            project_root = pathlib.Path(tmpdir) / "sampleproject2"
            project_root.touch()
            assert project_root.exists() and project_root.is_file()

            with self.assertRaises(RopeError):
                Project(project_root)

    def test_creating_folders(self):
        folderName = "SampleFolder"
        self.project.root.create_folder(folderName)
        folderPath = os.path.join(self.project.address, folderName)
        self.assertTrue(os.path.exists(folderPath) and os.path.isdir(folderPath))

    def test_making_folder_that_already_exists(self):
        folderName = "SampleFolder"
        with self.assertRaises(RopeError):
            self.project.root.create_folder(folderName)
            self.project.root.create_folder(folderName)

    def test_failing_if_creating_folder_while_file_already_exists(self):
        folderName = "SampleFolder"
        with self.assertRaises(RopeError):
            self.project.root.create_file(folderName)
            self.project.root.create_folder(folderName)

    def test_creating_file_inside_folder(self):
        folder_name = "sampleFolder"
        file_name = "sample2.txt"
        file_path = folder_name + "/" + file_name
        parent_folder = self.project.root.create_folder(folder_name)
        parent_folder.create_file(file_name)
        file = self.project.get_resource(file_path)
        file.write("sample notes")
        self.assertEqual(file_path, file.path)
        self.assertEqual(
            "sample notes", open(os.path.join(self.project.address, file_path)).read()
        )

    def test_failing_when_creating_file_inside_non_existent_folder(self):
        with self.assertRaises(ResourceNotFoundError):
            self.project.root.create_file("NonexistentFolder/SomeFile.txt")

    def test_nested_directories(self):
        folder_name = "SampleFolder"
        parent = self.project.root.create_folder(folder_name)
        parent.create_folder(folder_name)
        folder_path = os.path.join(self.project.address, folder_name, folder_name)
        self.assertTrue(os.path.exists(folder_path) and os.path.isdir(folder_path))

    def test_removing_files(self):
        self.assertTrue(os.path.exists(self.sample_path))
        self.project.get_resource(self.sample_file).remove()
        self.assertFalse(os.path.exists(self.sample_path))

    def test_removing_files_invalidating_in_project_resource_pool(self):
        root_folder = self.project.root
        my_file = root_folder.create_file("my_file.txt")
        my_file.remove()
        self.assertFalse(root_folder.has_child("my_file.txt"))

    def test_removing_directories(self):
        self.assertTrue(
            os.path.exists(os.path.join(self.project.address, self.sample_folder))
        )
        self.project.get_resource(self.sample_folder).remove()
        self.assertFalse(
            os.path.exists(os.path.join(self.project.address, self.sample_folder))
        )

    def test_removing_non_existent_files(self):
        with self.assertRaises(ResourceNotFoundError):
            self.project.get_resource("NonExistentFile.txt").remove()

    def test_removing_nested_files(self):
        file_name = self.sample_folder + "/sample_file.txt"
        self.project.root.create_file(file_name)
        self.project.get_resource(file_name).remove()
        self.assertTrue(
            os.path.exists(os.path.join(self.project.address, self.sample_folder))
        )
        self.assertTrue(
            not os.path.exists(os.path.join(self.project.address, file_name))
        )

    def test_file_get_name(self):
        file = self.project.get_resource(self.sample_file)
        self.assertEqual(self.sample_file, file.name)
        file_name = "nestedFile.txt"
        parent = self.project.get_resource(self.sample_folder)
        filePath = self.sample_folder + "/" + file_name
        parent.create_file(file_name)
        nestedFile = self.project.get_resource(filePath)
        self.assertEqual(file_name, nestedFile.name)

    def test_folder_get_name(self):
        folder = self.project.get_resource(self.sample_folder)
        self.assertEqual(self.sample_folder, folder.name)

    def test_file_get_path(self):
        file = self.project.get_resource(self.sample_file)
        self.assertEqual(self.sample_file, file.path)
        fileName = "nestedFile.txt"
        parent = self.project.get_resource(self.sample_folder)
        filePath = self.sample_folder + "/" + fileName
        parent.create_file(fileName)
        nestedFile = self.project.get_resource(filePath)
        self.assertEqual(filePath, nestedFile.path)

    def test_folder_get_path(self):
        folder = self.project.get_resource(self.sample_folder)
        self.assertEqual(self.sample_folder, folder.path)

    def test_is_folder(self):
        self.assertTrue(self.project.get_resource(self.sample_folder).is_folder())
        self.assertTrue(not self.project.get_resource(self.sample_file).is_folder())

    def testget_children(self):
        children = self.project.get_resource(self.sample_folder).get_children()
        self.assertEqual([], children)

    def test_nonempty_get_children(self):
        file_name = "nestedfile.txt"
        filePath = self.sample_folder + "/" + file_name
        parent = self.project.get_resource(self.sample_folder)
        parent.create_file(file_name)
        children = parent.get_children()
        self.assertEqual(1, len(children))
        self.assertEqual(filePath, children[0].path)

    def test_nonempty_get_children2(self):
        file_name = "nestedfile.txt"
        folder_name = "nestedfolder.txt"
        filePath = self.sample_folder + "/" + file_name
        folderPath = self.sample_folder + "/" + folder_name
        parent = self.project.get_resource(self.sample_folder)
        parent.create_file(file_name)
        parent.create_folder(folder_name)
        children = parent.get_children()
        self.assertEqual(2, len(children))
        self.assertTrue(filePath == children[0].path or filePath == children[1].path)
        self.assertTrue(
            folderPath == children[0].path or folderPath == children[1].path
        )

    def test_does_not_fail_for_permission_denied(self):
        with tempfile.TemporaryDirectory(suffix="bad_dir") as bad_dir:
            os.chmod(bad_dir, 0o000)
            try:
                parent = self.project.get_resource(self.sample_folder)

                parent.get_children()

            finally:
                os.chmod(bad_dir, 0o755)

    def test_getting_files(self):
        files = self.project.root.get_files()
        self.assertEqual(1, len(files))
        self.assertTrue(self.project.get_resource(self.sample_file) in files)

    def test_getting_folders(self):
        folders = self.project.root.get_folders()
        self.assertEqual(1, len(folders))
        self.assertTrue(self.project.get_resource(self.sample_folder) in folders)

    def test_nested_folder_get_files(self):
        parent = self.project.root.create_folder("top")
        parent.create_file("file1.txt")
        parent.create_file("file2.txt")
        files = parent.get_files()
        self.assertEqual(2, len(files))
        self.assertTrue(self.project.get_resource("top/file2.txt") in files)
        self.assertEqual(0, len(parent.get_folders()))

    def test_nested_folder_get_folders(self):
        parent = self.project.root.create_folder("top")
        parent.create_folder("dir1")
        parent.create_folder("dir2")
        folders = parent.get_folders()
        self.assertEqual(2, len(folders))
        self.assertTrue(self.project.get_resource("top/dir1") in folders)
        self.assertEqual(0, len(parent.get_files()))

    def test_root_folder(self):
        root_folder = self.project.root
        self.assertEqual(2, len(root_folder.get_children()))
        self.assertEqual("", root_folder.path)
        self.assertEqual("", root_folder.name)

    def test_get_all_files(self):
        files = tuple(self.project.get_files())
        self.assertEqual(1, len(files))
        self.assertEqual(self.sample_file, files[0].name)

    def test_get_all_files_after_changing(self):
        self.assertEqual(1, len(self.project.get_files()))
        myfile = self.project.root.create_file("myfile.txt")
        self.assertEqual(2, len(self.project.get_files()))
        myfile.move("newfile.txt")
        self.assertEqual(2, len(self.project.get_files()))
        self.project.get_file("newfile.txt").remove()
        self.assertEqual(1, len(self.project.get_files()))

    def test_multifile_get_all_files(self):
        fileName = "nestedFile.txt"
        parent = self.project.get_resource(self.sample_folder)
        parent.create_file(fileName)
        files = list(self.project.get_files())
        self.assertEqual(2, len(files))
        self.assertTrue(fileName == files[0].name or fileName == files[1].name)

    def test_ignoring_dot_pyc_files_in_get_files(self):
        root = self.project.address
        src_folder = os.path.join(root, "src")
        os.mkdir(src_folder)
        test_pyc = os.path.join(src_folder, "test.pyc")
        open(test_pyc, "w").close()
        for x in self.project.get_files():
            self.assertNotEqual("src/test.pyc", x.path)

    def test_folder_creating_files(self):
        projectFile = "NewFile.txt"
        self.project.root.create_file(projectFile)
        new_file = self.project.get_resource(projectFile)
        self.assertTrue(new_file is not None and not new_file.is_folder())

    def test_folder_creating_nested_files(self):
        project_file = "NewFile.txt"
        parent_folder = self.project.get_resource(self.sample_folder)
        parent_folder.create_file(project_file)
        new_file = self.project.get_resource(self.sample_folder + "/" + project_file)
        self.assertTrue(new_file is not None and not new_file.is_folder())

    def test_folder_creating_files2(self):
        projectFile = "newfolder"
        self.project.root.create_folder(projectFile)
        new_folder = self.project.get_resource(projectFile)
        self.assertTrue(new_folder is not None and new_folder.is_folder())

    def test_folder_creating_nested_files2(self):
        project_file = "newfolder"
        parent_folder = self.project.get_resource(self.sample_folder)
        parent_folder.create_folder(project_file)
        new_folder = self.project.get_resource(self.sample_folder + "/" + project_file)
        self.assertTrue(new_folder is not None and new_folder.is_folder())

    def test_folder_get_child(self):
        folder = self.project.root
        folder.create_file("myfile.txt")
        folder.create_folder("myfolder")
        self.assertEqual(
            self.project.get_resource("myfile.txt"), folder.get_child("myfile.txt")
        )
        self.assertEqual(
            self.project.get_resource("myfolder"), folder.get_child("myfolder")
        )

    def test_folder_get_child_nested(self):
        root = self.project.root
        folder = root.create_folder("myfolder")
        folder.create_file("myfile.txt")
        folder.create_folder("myfolder")
        self.assertEqual(
            self.project.get_resource("myfolder/myfile.txt"),
            folder.get_child("myfile.txt"),
        )
        self.assertEqual(
            self.project.get_resource("myfolder/myfolder"), folder.get_child("myfolder")
        )

    def test_project_root_is_root_folder(self):
        self.assertEqual("", self.project.root.path)

    def test_moving_files(self):
        root_folder = self.project.root
        my_file = root_folder.create_file("my_file.txt")
        my_file.move("my_other_file.txt")
        self.assertFalse(my_file.exists())
        root_folder.get_child("my_other_file.txt")

    def test_moving_folders(self):
        root_folder = self.project.root
        my_folder = root_folder.create_folder("my_folder")
        my_file = my_folder.create_file("my_file.txt")
        my_folder.move("new_folder")
        self.assertFalse(root_folder.has_child("my_folder"))
        self.assertFalse(my_file.exists())
        self.assertTrue(root_folder.get_child("new_folder") is not None)

    def test_moving_destination_folders(self):
        root_folder = self.project.root
        my_folder = root_folder.create_folder("my_folder")
        my_file = root_folder.create_file("my_file.txt")
        my_file.move("my_folder")
        self.assertFalse(root_folder.has_child("my_file.txt"))
        self.assertFalse(my_file.exists())
        my_folder.get_child("my_file.txt")

    def test_moving_files_and_resource_objects(self):
        root_folder = self.project.root
        my_file = root_folder.create_file("my_file.txt")
        old_hash = hash(my_file)
        my_file.move("my_other_file.txt")
        self.assertEqual(old_hash, hash(my_file))

    def test_file_encoding_reading(self):
        sample_file = self.project.root.create_file("my_file.txt")
        contents = (
            b"# -*- coding: utf-8 -*-\n"
            + br"#\N{LATIN SMALL LETTER I WITH DIAERESIS}\n"
        ).decode("utf8")
        file = open(sample_file.real_path, "wb")
        file.write(contents.encode("utf-8"))
        file.close()
        self.assertEqual(contents, sample_file.read())

    def test_file_encoding_writing(self):
        sample_file = self.project.root.create_file("my_file.txt")
        contents = (
            b"# -*- coding: utf-8 -*-\n" + br"\N{LATIN SMALL LETTER I WITH DIAERESIS}\n"
        ).decode("utf8")
        sample_file.write(contents)
        self.assertEqual(contents, sample_file.read())

    def test_using_utf8_when_writing_in_case_of_errors(self):
        sample_file = self.project.root.create_file("my_file.txt")
        contents = br"\n\N{LATIN SMALL LETTER I WITH DIAERESIS}\n".decode("utf8")
        sample_file.write(contents)
        self.assertEqual(contents, sample_file.read())

    def test_encoding_declaration_in_the_second_line(self):
        sample_file = self.project.root.create_file("my_file.txt")
        contents = b"\n# -*- coding: latin-1 -*-\n\xa9\n"
        file = open(sample_file.real_path, "wb")
        file.write(contents)
        file.close()
        self.assertEqual(contents, sample_file.read().encode("latin-1"))

    def test_not_an_encoding_declaration(self):
        sample_file = self.project.root.create_file("my_file.txt")
        contents = b"def my_method(self, encoding='latin-1'):\n    var = {}\n\xc2\xa9\n"
        file = open(sample_file.real_path, "wb")
        file.write(contents)
        file.close()
        self.assertEqual(contents, sample_file.read().encode("utf-8"))
        self.assertNotEqual(contents, sample_file.read().encode("latin-1"))

    def test_read_bytes(self):
        sample_file = self.project.root.create_file("my_file.txt")
        contents = b"\n# -*- coding: latin-1 -*-\n\xa9\n"
        file = open(sample_file.real_path, "wb")
        file.write(contents)
        file.close()
        self.assertEqual(contents, sample_file.read_bytes())

    def test_file_with_unix_line_ending(self):
        sample_file = self.project.root.create_file("my_file.txt")
        contents = b"1\n"
        file = open(sample_file.real_path, "wb")
        file.write(contents)
        file.close()
        self.assertIsNone(sample_file.newlines)
        self.assertEqual("1\n", sample_file.read())
        self.assertEqual("\n", sample_file.newlines)

        sample_file.write("1\n")
        self.assertEqual(b"1\n", sample_file.read_bytes())

    def test_file_with_dos_line_ending(self):
        sample_file = self.project.root.create_file("my_file.txt")
        contents = b"1\r\n"
        file = open(sample_file.real_path, "wb")
        file.write(contents)
        file.close()
        self.assertIsNone(sample_file.newlines)
        self.assertEqual("1\n", sample_file.read())
        self.assertEqual("\r\n", sample_file.newlines)

        sample_file.write("1\n")
        self.assertEqual(b"1\r\n", sample_file.read_bytes())

    def test_file_with_mac_line_ending(self):
        sample_file = self.project.root.create_file("my_file.txt")
        contents = b"1\r"
        file = open(sample_file.real_path, "wb")
        file.write(contents)
        file.close()
        self.assertIsNone(sample_file.newlines)
        self.assertEqual("1\n", sample_file.read())
        self.assertEqual("\r", sample_file.newlines)

        sample_file.write("1\n")
        self.assertEqual(b"1\r", sample_file.read_bytes())

    def test_file_binary(self):
        sample_file = self.project.root.create_file("my_file.txt")
        contents = b"1\r\n"
        file = open(sample_file.real_path, "wb")
        file.write(contents)
        file.close()
        self.assertIsNone(sample_file.newlines)
        self.assertEqual(b"1\r\n", sample_file.read_bytes())
        self.assertIsNone(sample_file.newlines)

        sample_file.write(b"1\nx\r")
        self.assertEqual((b"1\nx\r"), sample_file.read_bytes())

    # TODO: Detecting utf-16 encoding
    def xxx_test_using_utf16(self):
        sample_file = self.project.root.create_file("my_file.txt")
        contents = b"# -*- coding: utf-16 -*-\n# This is a sample file ...\n"
        file = open(sample_file.real_path, "w")
        file.write(contents.encode("utf-16"))
        file.close()
        sample_file.write(contents)
        self.assertEqual(contents, sample_file.read())

    # XXX: supporting utf_8_sig
    def xxx_test_file_encoding_reading_for_notepad_styles(self):
        sample_file = self.project.root.create_file("my_file.txt")
        contents = "#\N{LATIN SMALL LETTER I WITH DIAERESIS}\n"
        file = open(sample_file.real_path, "w")
        # file.write('\xef\xbb\xbf')
        file.write(contents.encode("utf-8-sig"))
        file.close()
        self.assertEqual(contents, sample_file.read())

    def test_using_project_get_file(self):
        myfile = self.project.get_file(self.sample_file)
        self.assertTrue(myfile.exists())

    def test_using_file_create(self):
        myfile = self.project.get_file("myfile.txt")
        self.assertFalse(myfile.exists())
        myfile.create()
        self.assertTrue(myfile.exists())
        self.assertFalse(myfile.is_folder())

    def test_using_folder_create(self):
        myfolder = self.project.get_folder("myfolder")
        self.assertFalse(myfolder.exists())
        myfolder.create()
        self.assertTrue(myfolder.exists())
        self.assertTrue(myfolder.is_folder())

    def test_exception_when_creating_twice(self):
        with self.assertRaises(RopeError):
            myfile = self.project.get_file("myfile.txt")
            myfile.create()
            myfile.create()

    def test_exception_when_parent_does_not_exist(self):
        with self.assertRaises(ResourceNotFoundError):
            myfile = self.project.get_file("myfolder/myfile.txt")
            myfile.create()

    def test_simple_path_to_resource(self):
        myfile = self.project.root.create_file("myfile.txt")
        self.assertEqual(myfile, path_to_resource(self.project, myfile.real_path))
        self.assertEqual(
            myfile, path_to_resource(self.project, myfile.real_path, type="file")
        )
        myfolder = self.project.root.create_folder("myfolder")
        self.assertEqual(myfolder, path_to_resource(self.project, myfolder.real_path))
        self.assertEqual(
            myfolder, path_to_resource(self.project, myfolder.real_path, type="folder")
        )

    @testutils.skipNotPOSIX()
    def test_ignoring_symlinks_inside_project(self):
        project2 = testutils.sample_project(folder_name="sampleproject2")
        mod = project2.root.create_file("mod.py")
        try:
            path = os.path.join(self.project.address, "linkedfile.txt")
            os.symlink(mod.real_path, path)
            files = self.project.root.get_files()
            self.assertEqual(1, len(files))
        finally:
            testutils.remove_project(project2)

    def test_getting_empty_source_folders(self):
        self.assertEqual([], self.project.get_source_folders())

    def test_root_source_folder(self):
        self.project.root.create_file("sample.py")
        source_folders = self.project.get_source_folders()
        self.assertEqual(1, len(source_folders))
        self.assertTrue(self.project.root in source_folders)

    def test_root_source_folder2(self):
        self.project.root.create_file("mod1.py")
        self.project.root.create_file("mod2.py")
        source_folders = self.project.get_source_folders()
        self.assertEqual(1, len(source_folders))
        self.assertTrue(self.project.root in source_folders)

    def test_src_source_folder(self):
        src = self.project.root.create_folder("src")
        src.create_file("sample.py")
        source_folders = self.project.get_source_folders()
        self.assertEqual(1, len(source_folders))
        self.assertTrue(self.project.get_resource("src") in source_folders)

    def test_packages(self):
        src = self.project.root.create_folder("src")
        pkg = src.create_folder("package")
        pkg.create_file("__init__.py")
        source_folders = self.project.get_source_folders()
        self.assertEqual(1, len(source_folders))
        self.assertTrue(src in source_folders)

    def test_multi_source_folders(self):
        src = self.project.root.create_folder("src")
        package = src.create_folder("package")
        package.create_file("__init__.py")
        test = self.project.root.create_folder("test")
        test.create_file("alltests.py")
        source_folders = self.project.get_source_folders()
        self.assertEqual(2, len(source_folders))
        self.assertTrue(src in source_folders)
        self.assertTrue(test in source_folders)

    def test_multi_source_folders2(self):
        testutils.create_module(self.project, "mod1")
        src = self.project.root.create_folder("src")
        package = testutils.create_package(self.project, "package", src)
        testutils.create_module(self.project, "mod2", package)
        source_folders = self.project.get_source_folders()
        self.assertEqual(2, len(source_folders))
        self.assertTrue(self.project.root in source_folders and src in source_folders)

    def test_folder_is_pathlike(self):
        resource = self.project.root.create_folder("src")
        self.assertIsInstance(resource, Folder)

        self.assertIsInstance(os.fspath(resource), str)

    def test_file_is_pathlike(self):
        resource = self.project.root.create_file("mod.py")
        self.assertIsInstance(resource, File)

        self.assertIsInstance(os.fspath(resource), str)


class ResourceObserverTest(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.project = testutils.sample_project()

    def tearDown(self):
        testutils.remove_project(self.project)
        super().tearDown()

    def test_resource_change_observer(self):
        sample_file = self.project.root.create_file("my_file.txt")
        sample_file.write("a sample file version 1")
        sample_observer = _SampleObserver()
        self.project.add_observer(sample_observer)
        sample_file.write("a sample file version 2")
        self.assertEqual(1, sample_observer.change_count)
        self.assertEqual(sample_file, sample_observer.last_changed)

    def test_resource_change_observer_after_removal(self):
        sample_file = self.project.root.create_file("my_file.txt")
        sample_file.write("text")
        sample_observer = _SampleObserver()
        self.project.add_observer(
            FilteredResourceObserver(sample_observer, [sample_file])
        )
        sample_file.remove()
        self.assertEqual(1, sample_observer.change_count)
        self.assertEqual(sample_file, sample_observer.last_removed)

    def test_resource_change_observer2(self):
        sample_file = self.project.root.create_file("my_file.txt")
        sample_observer = _SampleObserver()
        self.project.add_observer(sample_observer)
        self.project.remove_observer(sample_observer)
        sample_file.write("a sample file version 2")
        self.assertEqual(0, sample_observer.change_count)

    def test_resource_change_observer_for_folders(self):
        root_folder = self.project.root
        my_folder = root_folder.create_folder("my_folder")
        my_folder_observer = _SampleObserver()
        root_folder_observer = _SampleObserver()
        self.project.add_observer(
            FilteredResourceObserver(my_folder_observer, [my_folder])
        )
        self.project.add_observer(
            FilteredResourceObserver(root_folder_observer, [root_folder])
        )
        my_file = my_folder.create_file("my_file.txt")
        self.assertEqual(1, my_folder_observer.change_count)
        my_file.move("another_file.txt")
        self.assertEqual(2, my_folder_observer.change_count)
        self.assertEqual(1, root_folder_observer.change_count)
        self.project.get_resource("another_file.txt").remove()
        self.assertEqual(2, my_folder_observer.change_count)
        self.assertEqual(2, root_folder_observer.change_count)

    def test_resource_change_observer_after_moving(self):
        sample_file = self.project.root.create_file("my_file.txt")
        sample_observer = _SampleObserver()
        self.project.add_observer(sample_observer)
        sample_file.move("new_file.txt")
        self.assertEqual(1, sample_observer.change_count)
        self.assertEqual(
            (sample_file, self.project.get_resource("new_file.txt")),
            sample_observer.last_moved,
        )

    def test_revalidating_files(self):
        root = self.project.root
        my_file = root.create_file("my_file.txt")
        sample_observer = _SampleObserver()
        self.project.add_observer(FilteredResourceObserver(sample_observer, [my_file]))
        os.remove(my_file.real_path)
        self.project.validate(root)
        self.assertEqual(my_file, sample_observer.last_removed)
        self.assertEqual(1, sample_observer.change_count)

    def test_revalidating_files_and_no_changes2(self):
        root = self.project.root
        my_file = root.create_file("my_file.txt")
        sample_observer = _SampleObserver()
        self.project.add_observer(FilteredResourceObserver(sample_observer, [my_file]))
        self.project.validate(root)
        self.assertEqual(None, sample_observer.last_moved)
        self.assertEqual(0, sample_observer.change_count)

    def test_revalidating_folders(self):
        root = self.project.root
        my_folder = root.create_folder("myfolder")
        my_file = my_folder.create_file("myfile.txt")  # noqa
        sample_observer = _SampleObserver()
        self.project.add_observer(
            FilteredResourceObserver(sample_observer, [my_folder])
        )
        testutils.remove_recursively(my_folder.real_path)
        self.project.validate(root)
        self.assertEqual(my_folder, sample_observer.last_removed)
        self.assertEqual(1, sample_observer.change_count)

    def test_removing_and_adding_resources_to_filtered_observer(self):
        my_file = self.project.root.create_file("my_file.txt")
        sample_observer = _SampleObserver()
        filtered_observer = FilteredResourceObserver(sample_observer)
        self.project.add_observer(filtered_observer)
        my_file.write("1")
        self.assertEqual(0, sample_observer.change_count)
        filtered_observer.add_resource(my_file)
        my_file.write("2")
        self.assertEqual(1, sample_observer.change_count)
        filtered_observer.remove_resource(my_file)
        my_file.write("3")
        self.assertEqual(1, sample_observer.change_count)

    def test_validation_and_changing_files(self):
        my_file = self.project.root.create_file("my_file.txt")
        sample_observer = _SampleObserver()
        timekeeper = _MockChangeIndicator()
        filtered_observer = FilteredResourceObserver(
            sample_observer, [my_file], timekeeper=timekeeper
        )
        self.project.add_observer(filtered_observer)
        self._write_file(my_file.real_path)
        timekeeper.set_indicator(my_file, 1)
        self.project.validate(self.project.root)
        self.assertEqual(1, sample_observer.change_count)

    def test_validation_and_changing_files2(self):
        my_file = self.project.root.create_file("my_file.txt")
        sample_observer = _SampleObserver()
        timekeeper = _MockChangeIndicator()
        self.project.add_observer(
            FilteredResourceObserver(sample_observer, [my_file], timekeeper=timekeeper)
        )
        timekeeper.set_indicator(my_file, 1)
        my_file.write("hey")
        self.assertEqual(1, sample_observer.change_count)
        self.project.validate(self.project.root)
        self.assertEqual(1, sample_observer.change_count)

    def test_not_reporting_multiple_changes_to_folders(self):
        root = self.project.root
        file1 = root.create_file("file1.txt")
        file2 = root.create_file("file2.txt")
        sample_observer = _SampleObserver()
        self.project.add_observer(
            FilteredResourceObserver(sample_observer, [root, file1, file2])
        )
        os.remove(file1.real_path)
        os.remove(file2.real_path)
        self.assertEqual(0, sample_observer.change_count)
        self.project.validate(self.project.root)
        self.assertEqual(3, sample_observer.change_count)

    def _write_file(self, path):
        my_file = open(path, "w")
        my_file.write("\n")
        my_file.close()

    def test_moving_and_being_interested_about_a_folder_and_a_child(self):
        my_folder = self.project.root.create_folder("my_folder")
        my_file = my_folder.create_file("my_file.txt")
        sample_observer = _SampleObserver()
        filtered_observer = FilteredResourceObserver(
            sample_observer, [my_folder, my_file]
        )
        self.project.add_observer(filtered_observer)
        my_folder.move("new_folder")
        self.assertEqual(2, sample_observer.change_count)

    def test_contains_for_folders(self):
        folder1 = self.project.root.create_folder("folder")
        folder2 = self.project.root.create_folder("folder2")
        self.assertFalse(folder1.contains(folder2))

    def test_validating_when_created(self):
        root = self.project.root
        my_file = self.project.get_file("my_file.txt")
        sample_observer = _SampleObserver()
        self.project.add_observer(FilteredResourceObserver(sample_observer, [my_file]))
        open(my_file.real_path, "w").close()
        self.project.validate(root)
        self.assertEqual(my_file, sample_observer.last_created)
        self.assertEqual(1, sample_observer.change_count)

    def test_validating_twice_when_created(self):
        root = self.project.root
        my_file = self.project.get_file("my_file.txt")
        sample_observer = _SampleObserver()
        self.project.add_observer(FilteredResourceObserver(sample_observer, [my_file]))
        open(my_file.real_path, "w").close()
        self.project.validate(root)
        self.project.validate(root)
        self.assertEqual(my_file, sample_observer.last_created)
        self.assertEqual(1, sample_observer.change_count)

    def test_changes_and_adding_resources(self):
        root = self.project.root  # noqa
        file1 = self.project.get_file("file1.txt")
        file2 = self.project.get_file("file2.txt")
        file1.create()
        sample_observer = _SampleObserver()
        self.project.add_observer(
            FilteredResourceObserver(sample_observer, [file1, file2])
        )
        file1.move(file2.path)
        self.assertEqual(2, sample_observer.change_count)
        self.assertEqual(file2, sample_observer.last_created)
        self.assertEqual((file1, file2), sample_observer.last_moved)

    def test_validating_get_files_list(self):
        root = self.project.root  # noqa
        self.assertEqual(0, len(self.project.get_files()))
        file = open(os.path.join(self.project.address, "myfile.txt"), "w")
        file.close()
        self.project.validate()
        self.assertEqual(1, len(self.project.get_files()))

    def test_clear_observed_resources_for_filtered_observers(self):
        sample_file = self.project.root.create_file("myfile.txt")
        sample_observer = _SampleObserver()
        filtered = FilteredResourceObserver(sample_observer)
        self.project.add_observer(filtered)
        filtered.add_resource(sample_file)
        filtered.clear_resources()
        sample_file.write("1")
        self.assertEqual(0, sample_observer.change_count)


class _MockChangeIndicator:
    def __init__(self):
        self.times = {}

    def set_indicator(self, resource, time):
        self.times[resource] = time

    def get_indicator(self, resource):
        return self.times.get(resource, 0)


class _SampleObserver:
    def __init__(self):
        self.change_count = 0
        self.last_changed = None
        self.last_moved = None
        self.last_created = None
        self.last_removed = None

    def resource_changed(self, resource):
        self.last_changed = resource
        self.change_count += 1

    def resource_moved(self, resource, new_resource):
        self.last_moved = (resource, new_resource)
        self.change_count += 1

    def resource_created(self, resource):
        self.last_created = resource
        self.change_count += 1

    def resource_removed(self, resource):
        self.last_removed = resource
        self.change_count += 1


class OutOfProjectTest(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.test_directory = "temp_test_directory"
        testutils.remove_recursively(self.test_directory)
        os.mkdir(self.test_directory)
        self.project = testutils.sample_project()
        self.no_project = NoProject()

    def tearDown(self):
        testutils.remove_project(self.project)
        testutils.remove_recursively(self.test_directory)
        super().tearDown()

    def test_simple_out_of_project_file(self):
        sample_file_path = os.path.join(self.test_directory, "sample.txt")
        sample_file = open(sample_file_path, "w")
        sample_file.write("sample content\n")
        sample_file.close()
        sample_resource = self.no_project.get_resource(sample_file_path)
        self.assertEqual("sample content\n", sample_resource.read())

    def test_simple_out_of_project_folder(self):
        sample_folder_path = os.path.join(self.test_directory, "sample_folder")
        os.mkdir(sample_folder_path)
        sample_folder = self.no_project.get_resource(sample_folder_path)
        self.assertEqual([], sample_folder.get_children())

        sample_file_path = os.path.join(sample_folder_path, "sample.txt")
        open(sample_file_path, "w").close()
        sample_resource = self.no_project.get_resource(sample_file_path)
        self.assertEqual(sample_resource, sample_folder.get_children()[0])

    def test_using_absolute_path(self):
        sample_file_path = os.path.join(self.test_directory, "sample.txt")
        open(sample_file_path, "w").close()
        normal_sample_resource = self.no_project.get_resource(sample_file_path)
        absolute_sample_resource = self.no_project.get_resource(
            os.path.abspath(sample_file_path)
        )
        self.assertEqual(normal_sample_resource, absolute_sample_resource)

    def test_folder_get_child(self):
        sample_folder_path = os.path.join(self.test_directory, "sample_folder")
        os.mkdir(sample_folder_path)
        sample_folder = self.no_project.get_resource(sample_folder_path)
        self.assertEqual([], sample_folder.get_children())

        sample_file_path = os.path.join(sample_folder_path, "sample.txt")
        open(sample_file_path, "w").close()
        sample_resource = self.no_project.get_resource(sample_file_path)
        self.assertTrue(sample_folder.has_child("sample.txt"))
        self.assertFalse(sample_folder.has_child("doesnothave.txt"))
        self.assertEqual(sample_resource, sample_folder.get_child("sample.txt"))

    def test_out_of_project_files_and_path_to_resource(self):
        sample_file_path = os.path.join(self.test_directory, "sample.txt")
        sample_file = open(sample_file_path, "w")
        sample_file.write("sample content\n")
        sample_file.close()
        sample_resource = self.no_project.get_resource(sample_file_path)
        self.assertEqual(
            sample_resource, path_to_resource(self.project, sample_file_path)
        )


class _MockFSCommands:
    def __init__(self):
        self.log = ""
        self.fscommands = FileSystemCommands()

    def create_file(self, path):
        self.log += "create_file "
        self.fscommands.create_file(path)

    def create_folder(self, path):
        self.log += "create_folder "
        self.fscommands.create_folder(path)

    def move(self, path, new_location):
        self.log += "move "
        self.fscommands.move(path, new_location)

    def remove(self, path):
        self.log += "remove "
        self.fscommands.remove(path)

    def read(self, path):
        self.log += "read "
        return self.fscommands.read(path)


class _DeprecatedFSCommands:
    def __init__(self):
        self.log = ""
        self.fscommands = FileSystemCommands()

    def create_file(self, path):
        self.log += "create_file "
        self.fscommands.create_file(path)

    def create_folder(self, path):
        self.log += "create_folder "
        self.fscommands.create_folder(path)

    def move(self, path, new_location):
        self.log += "move "
        self.fscommands.move(path, new_location)

    def remove(self, path):
        self.log += "remove "
        self.fscommands.remove(path)


class RopeFolderTest(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.project = None

    def tearDown(self):
        if self.project:
            testutils.remove_project(self.project)
        super().tearDown()

    def test_none_project_rope_folder(self):
        self.project = testutils.sample_project(ropefolder=None)
        self.assertTrue(self.project.ropefolder is None)

    def test_getting_project_rope_folder(self):
        self.project = testutils.sample_project()
        self.assertTrue(self.project.ropefolder.exists())
        self.assertEqual(".ropeproject", self.project.ropefolder.path)

    def test_setting_ignored_resources(self):
        self.project = testutils.sample_project(ignored_resources=["myfile.txt"])
        myfile = self.project.get_file("myfile.txt")
        file2 = self.project.get_file("file2.txt")
        self.assertTrue(self.project.is_ignored(myfile))
        self.assertFalse(self.project.is_ignored(file2))

    def test_ignored_folders(self):
        self.project = testutils.sample_project(ignored_resources=["myfolder"])
        myfolder = self.project.root.create_folder("myfolder")
        self.assertTrue(self.project.is_ignored(myfolder))
        myfile = myfolder.create_file("myfile.txt")
        self.assertTrue(self.project.is_ignored(myfile))

    def test_ignored_resources_and_get_files(self):
        self.project = testutils.sample_project(
            ignored_resources=["myfile.txt"], ropefolder=None
        )
        myfile = self.project.get_file("myfile.txt")
        self.assertEqual(0, len(self.project.get_files()))
        myfile.create()
        self.assertEqual(0, len(self.project.get_files()))

    def test_ignored_resources_and_get_files2(self):
        self.project = testutils.sample_project(
            ignored_resources=["myfile.txt"], ropefolder=None
        )
        myfile = self.project.root.create_file("myfile.txt")  # noqa
        self.assertEqual(0, len(self.project.get_files()))

    def test_setting_ignored_resources_patterns(self):
        self.project = testutils.sample_project(ignored_resources=["m?file.*"])
        myfile = self.project.get_file("myfile.txt")
        file2 = self.project.get_file("file2.txt")
        self.assertTrue(self.project.is_ignored(myfile))
        self.assertFalse(self.project.is_ignored(file2))

    def test_star_should_not_include_slashes(self):
        self.project = testutils.sample_project(ignored_resources=["f*.txt"])
        folder = self.project.root.create_folder("folder")
        file1 = folder.create_file("myfile.txt")
        file2 = folder.create_file("file2.txt")
        self.assertFalse(self.project.is_ignored(file1))
        self.assertTrue(self.project.is_ignored(file2))

    def test_normal_fscommands(self):
        fscommands = _MockFSCommands()
        self.project = testutils.sample_project(fscommands=fscommands)
        myfile = self.project.get_file("myfile.txt")
        myfile.create()
        self.assertEqual("create_file ", fscommands.log)

    def test_fscommands_and_ignored_resources(self):
        fscommands = _MockFSCommands()
        self.project = testutils.sample_project(
            fscommands=fscommands, ignored_resources=["myfile.txt"], ropefolder=None
        )
        myfile = self.project.get_file("myfile.txt")
        myfile.create()
        self.assertEqual("", fscommands.log)

    def test_deprecated_fscommands(self):
        fscommands = _DeprecatedFSCommands()
        self.project = testutils.sample_project(fscommands=fscommands)
        myfile = self.project.get_file("myfile.txt")
        myfile.create()
        self.assertEqual("create_file ", fscommands.log)

    def test_ignored_resources_and_prefixes(self):
        self.project = testutils.sample_project(ignored_resources=[".hg"])
        myfile = self.project.root.create_file(".hgignore")
        self.assertFalse(self.project.is_ignored(myfile))

    def test_loading_config_dot_py(self):
        self.project = testutils.sample_project()
        config = self.project.get_file(".ropeproject/config.py")
        if not config.exists():
            config.create()
        config.write(dedent("""\
            def set_prefs(prefs):
                prefs["ignored_resources"] = ["myfile.txt"]
            def project_opened(project):
                project.root.create_file("loaded")
        """))
        self.project.close()
        self.project = Project(self.project.address)
        self.assertTrue(self.project.get_file("loaded").exists())
        myfile = self.project.get_file("myfile.txt")
        self.assertTrue(self.project.is_ignored(myfile))

    def test_loading_pyproject(self):
        self.project = testutils.sample_project()
        config = self.project.get_file("pyproject.toml")
        if not config.exists():
            config.create()
        config.write(dedent("""\
            [tool.rope]
            ignored_resources=["pyproject.py"]
        """))
        self.project.close()
        self.project = Project(self.project.address)
        myfile = self.project.get_file("pyproject.py")
        self.assertTrue(self.project.is_ignored(myfile))

    def test_loading_pyproject_empty_file(self):
        self.project = testutils.sample_project()
        config = self.project.get_file("pyproject.toml")
        if not config.exists():
            config.create()
        config.write("")
        self.project.close()
        self.project = Project(self.project.address)
        myfile = self.project.get_file("pyproject.py")
        self.assertFalse(self.project.is_ignored(myfile))

    def test_loading_pyproject_no_tool_section(self):
        self.project = testutils.sample_project()
        config = self.project.get_file("pyproject.toml")
        if not config.exists():
            config.create()
        config.write(dedent("""\
            [project]
            name = 'testproject'
        """))
        self.project.close()
        self.project = Project(self.project.address)
        myfile = self.project.get_file("pyproject.py")
        self.assertFalse(self.project.is_ignored(myfile))

    def test_loading_pyproject_no_tool_rope_section(self):
        self.project = testutils.sample_project()
        config = self.project.get_file("pyproject.toml")
        if not config.exists():
            config.create()
        config.write(dedent("""\
            [tool.anothertool]
            name = 'testproject'
        """))
        self.project.close()
        self.project = Project(self.project.address)
        myfile = self.project.get_file("pyproject.py")
        self.assertFalse(self.project.is_ignored(myfile))

    def test_ignoring_syntax_errors(self):
        self.project = testutils.sample_project(
            ropefolder=None, ignore_syntax_errors=True
        )
        mod = testutils.create_module(self.project, "mod")
        mod.write("xyz print")
        pymod = self.project.get_pymodule(mod)  # noqa

    def test_compressed_history(self):
        self.project = testutils.sample_project(compress_history=True)
        mod = testutils.create_module(self.project, "mod")
        mod.write("")

    def test_compressed_objectdb(self):
        self.project = testutils.sample_project(compress_objectdb=True)
        mod = testutils.create_module(self.project, "mod")
        self.project.pycore.analyze_module(mod)

    def test_nested_dot_ropeproject_folder(self):
        self.project = testutils.sample_project(ropefolder=".f1/f2")
        ropefolder = self.project.ropefolder
        self.assertEqual(".f1/f2", ropefolder.path)
        self.assertTrue(ropefolder.exists())
