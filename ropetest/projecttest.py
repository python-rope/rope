import unittest
import os

from rope.base.project import Project, NoProject, FilteredResourceObserver
from rope.base.exceptions import RopeError
from ropetest import testutils
from rope.base.fscommands import FileSystemCommands


class ProjectTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.project_root = 'sample_project'
        testutils.remove_recursively(self.project_root)
        self._make_sample_project()
        self.project = Project(self.project_root, ropefolder=None)
        self.no_project = NoProject()

    def _make_sample_project(self):
        self.sample_file = 'sample_file.txt'
        self.sample_path = os.path.join(self.project_root, 'sample_file.txt')
        os.mkdir(self.project_root)
        self.sample_folder = 'sample_folder'
        os.mkdir(os.path.join(self.project_root, self.sample_folder))
        sample = open(self.sample_path, 'w')
        sample.write('sample text\n')
        sample.close()

    def tearDown(self):
        testutils.remove_recursively(self.project_root)
        unittest.TestCase.tearDown(self)

    def test_project_creation(self):
        self.assertEquals(self.project_root, self.project.address)

    def test_getting_project_file(self):
        project_file = self.project.get_resource(self.sample_file)
        self.assertTrue(project_file is not None)

    def test_project_file_reading(self):
        projectFile = self.project.get_resource(self.sample_file)
        self.assertEquals('sample text\n', projectFile.read())

    @testutils.assert_raises(RopeError)
    def test_getting_not_existing_project_file(self):
        projectFile = self.project.get_resource('DoesNotExistFile.txt')
        self.fail('Should have failed')

    def test_writing_in_project_files(self):
        project_file = self.project.get_resource(self.sample_file)
        project_file.write('another text\n')
        self.assertEquals('another text\n', project_file.read())

    def test_creating_files(self):
        project_file = 'newfile.txt'
        self.project.root.create_file(project_file)
        newFile = self.project.get_resource(project_file)
        self.assertTrue(newFile is not None)

    @testutils.assert_raises(RopeError)
    def test_creating_files_that_already_exist(self):
        self.project.root.create_file(self.sample_file)
        self.fail('Should have failed')

    def test_making_root_folder_if_it_does_not_exist(self):
        projectRoot = 'SampleProject2'
        try:
            project = Project(projectRoot)
            self.assertTrue(os.path.exists(projectRoot) and os.path.isdir(projectRoot))
        finally:
            testutils.remove_recursively(projectRoot)

    @testutils.assert_raises(RopeError)
    def test_failure_when_project_root_exists_and_is_a_file(self):
        try:
            projectRoot = 'SampleProject2'
            open(projectRoot, 'w').close()
            project = Project(projectRoot)
        finally:
            os.remove(projectRoot)

    def test_creating_folders(self):
        folderName = 'SampleFolder'
        self.project.root.create_folder(folderName)
        folderPath = os.path.join(self.project.address, folderName)
        self.assertTrue(os.path.exists(folderPath) and os.path.isdir(folderPath))

    @testutils.assert_raises(RopeError)
    def test_making_folder_that_already_exists(self):
        folderName = 'SampleFolder'
        self.project.root.create_folder(folderName)
        self.project.root.create_folder(folderName)

    @testutils.assert_raises(RopeError)
    def test_failing_if_creating_folder_while_file_already_exists(self):
        folderName = 'SampleFolder'
        self.project.root.create_file(folderName)
        self.project.root.create_folder(folderName)

    def test_creating_file_inside_folder(self):
        folder_name = 'sampleFolder'
        file_name = 'sample2.txt'
        file_path = folder_name + '/' + file_name
        parent_folder = self.project.root.create_folder(folder_name)
        parent_folder.create_file(file_name)
        file = self.project.get_resource(file_path)
        file.write('sample notes')
        self.assertEquals(file_path, file.path)
        self.assertEquals('sample notes', open(os.path.join(self.project.address,
                                                            file_path)).read())

    @testutils.assert_raises(RopeError)
    def test_failing_when_creating_file_inside_non_existant_folder(self):
        self.project.root.create_file('NonexistantFolder/SomeFile.txt')

    def test_nested_directories(self):
        folder_name = 'SampleFolder'
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
        my_file = root_folder.create_file('my_file.txt')
        my_file.remove()
        self.assertFalse(root_folder.has_child('my_file.txt'))

    def test_removing_directories(self):
        self.assertTrue(os.path.exists(os.path.join(self.project.address,
                                                    self.sample_folder)))
        self.project.get_resource(self.sample_folder).remove()
        self.assertFalse(os.path.exists(os.path.join(self.project.address,
                                                     self.sample_folder)))

    @testutils.assert_raises(RopeError)
    def test_removing_non_existant_files(self):
        self.project.get_resource('NonExistantFile.txt').remove()

    def test_removing_nested_files(self):
        file_name = self.sample_folder + '/sample_file.txt'
        self.project.root.create_file(file_name)
        self.project.get_resource(file_name).remove()
        self.assertTrue(os.path.exists(os.path.join(self.project.address,
                                                    self.sample_folder)))
        self.assertTrue(not os.path.exists(os.path.join(self.project.address,
                                  file_name)))

    def test_file_get_name(self):
        file = self.project.get_resource(self.sample_file)
        self.assertEquals(self.sample_file, file.name)
        file_name = 'nestedFile.txt'
        parent = self.project.get_resource(self.sample_folder)
        filePath = self.sample_folder + '/' + file_name
        parent.create_file(file_name)
        nestedFile = self.project.get_resource(filePath)
        self.assertEquals(file_name, nestedFile.name)

    def test_folder_get_name(self):
        folder = self.project.get_resource(self.sample_folder)
        self.assertEquals(self.sample_folder, folder.name)

    def test_file_get_path(self):
        file = self.project.get_resource(self.sample_file)
        self.assertEquals(self.sample_file, file.path)
        fileName = 'nestedFile.txt'
        parent = self.project.get_resource(self.sample_folder)
        filePath = self.sample_folder + '/' + fileName
        parent.create_file(fileName)
        nestedFile = self.project.get_resource(filePath)
        self.assertEquals(filePath, nestedFile.path)

    def test_folder_get_path(self):
        folder = self.project.get_resource(self.sample_folder)
        self.assertEquals(self.sample_folder, folder.path)

    def test_is_folder(self):
        self.assertTrue(self.project.get_resource(self.sample_folder).is_folder())
        self.assertTrue(not self.project.get_resource(self.sample_file).is_folder())

    def testget_children(self):
        children = self.project.get_resource(self.sample_folder).get_children()
        self.assertEquals([], children)

    def test_nonempty_get_children(self):
        file_name = 'nestedfile.txt'
        filePath = self.sample_folder + '/' + file_name
        parent = self.project.get_resource(self.sample_folder)
        parent.create_file(file_name)
        children = parent.get_children()
        self.assertEquals(1, len(children))
        self.assertEquals(filePath, children[0].path)

    def test_nonempty_get_children2(self):
        file_name = 'nestedfile.txt'
        folder_name = 'nestedfolder.txt'
        filePath = self.sample_folder + '/' + file_name
        folderPath = self.sample_folder + '/' + folder_name
        parent = self.project.get_resource(self.sample_folder)
        parent.create_file(file_name)
        parent.create_folder(folder_name)
        children = parent.get_children()
        self.assertEquals(2, len(children))
        self.assertTrue(filePath == children[0].path or filePath == children[1].path)
        self.assertTrue(folderPath == children[0].path or folderPath == children[1].path)

    def test_getting_files(self):
        files = self.project.root.get_files()
        self.assertEquals(1, len(files))
        self.assertTrue(self.project.get_resource(self.sample_file) in files)

    def test_getting_folders(self):
        folders = self.project.root.get_folders()
        self.assertEquals(1, len(folders))
        self.assertTrue(self.project.get_resource(self.sample_folder) in folders)

    def test_nested_folder_get_files(self):
        parent = self.project.root.create_folder('top')
        parent.create_file('file1.txt')
        parent.create_file('file2.txt')
        files = parent.get_files()
        self.assertEquals(2, len(files))
        self.assertTrue(self.project.get_resource('top/file2.txt') in files)
        self.assertEquals(0, len(parent.get_folders()))

    def test_nested_folder_get_folders(self):
        parent = self.project.root.create_folder('top')
        parent.create_folder('dir1')
        parent.create_folder('dir2')
        folders = parent.get_folders()
        self.assertEquals(2, len(folders))
        self.assertTrue(self.project.get_resource('top/dir1') in folders)
        self.assertEquals(0, len(parent.get_files()))

    def test_root_folder(self):
        root_folder = self.project.root
        self.assertEquals(2, len(root_folder.get_children()))
        self.assertEquals('', root_folder.path)
        self.assertEquals('', root_folder.name)

    def test_get_all_files(self):
        files = self.project.get_files()
        self.assertEquals(1, len(files))
        self.assertEquals(self.sample_file, files[0].name)

    def test_multifile_get_all_files(self):
        fileName = 'nestedFile.txt'
        parent = self.project.get_resource(self.sample_folder)
        parent.create_file(fileName)
        files = self.project.get_files()
        self.assertEquals(2, len(files))
        self.assertTrue(fileName == files[0].name or fileName == files[1].name)

    def test_ignoring_dot_star_folders_in_get_files(self):
        root = self.project.address
        dot_test = os.path.join(root, '.test')
        os.mkdir(dot_test)
        test_py = os.path.join(dot_test, 'test.py')
        file(test_py, 'w').close()
        for x in self.project.get_files():
            self.assertNotEquals('.test/test.py', x.path)

    def test_ignoring_dot_pyc_files_in_get_files(self):
        root = self.project.address
        src_folder = os.path.join(root, 'src')
        os.mkdir(src_folder)
        test_pyc = os.path.join(src_folder, 'test.pyc')
        file(test_pyc, 'w').close()
        for x in self.project.get_files():
            self.assertNotEquals('src/test.pyc', x.path)

    def test_folder_creating_files(self):
        projectFile = 'NewFile.txt'
        self.project.root.create_file(projectFile)
        new_file = self.project.get_resource(projectFile)
        self.assertTrue(new_file is not None and not new_file.is_folder())

    def test_folder_creating_nested_files(self):
        project_file = 'NewFile.txt'
        parent_folder = self.project.get_resource(self.sample_folder)
        parent_folder.create_file(project_file)
        new_file = self.project.get_resource(self.sample_folder
                                            + '/' + project_file)
        self.assertTrue(new_file is not None and not new_file.is_folder())

    def test_folder_creating_files2(self):
        projectFile = 'newfolder'
        self.project.root.create_folder(projectFile)
        new_folder = self.project.get_resource(projectFile)
        self.assertTrue(new_folder is not None and new_folder.is_folder())

    def test_folder_creating_nested_files2(self):
        project_file = 'newfolder'
        parent_folder = self.project.get_resource(self.sample_folder)
        parent_folder.create_folder(project_file)
        new_folder = self.project.get_resource(self.sample_folder
                                               + '/' + project_file)
        self.assertTrue(new_folder is not None and new_folder.is_folder())

    def test_folder_get_child(self):
        folder = self.project.root
        folder.create_file('myfile.txt')
        folder.create_folder('myfolder')
        self.assertEquals(self.project.get_resource('myfile.txt'),
                          folder.get_child('myfile.txt'))
        self.assertEquals(self.project.get_resource('myfolder'),
                          folder.get_child('myfolder'))

    def test_folder_get_child_nested(self):
        root = self.project.root
        folder = root.create_folder('myfolder')
        folder.create_file('myfile.txt')
        folder.create_folder('myfolder')
        self.assertEquals(self.project.get_resource('myfolder/myfile.txt'),
                          folder.get_child('myfile.txt'))
        self.assertEquals(self.project.get_resource('myfolder/myfolder'),
                          folder.get_child('myfolder'))

    def test_project_root_is_root_folder(self):
        self.assertEquals('', self.project.root.path)

    def test_moving_files(self):
        root_folder = self.project.root
        my_file = root_folder.create_file('my_file.txt')
        my_file.move('my_other_file.txt')
        self.assertFalse(my_file.exists())
        root_folder.get_child('my_other_file.txt')

    def test_moving_folders(self):
        root_folder = self.project.root
        my_folder = root_folder.create_folder('my_folder')
        my_file = my_folder.create_file('my_file.txt')
        my_folder.move('new_folder')
        self.assertFalse(root_folder.has_child('my_folder'))
        self.assertFalse(my_file.exists())
        self.assertTrue(root_folder.get_child('new_folder') is not None)

    def test_moving_destination_folders(self):
        root_folder = self.project.root
        my_folder = root_folder.create_folder('my_folder')
        my_file = root_folder.create_file('my_file.txt')
        my_file.move('my_folder')
        self.assertFalse(root_folder.has_child('my_file.txt'))
        self.assertFalse(my_file.exists())
        my_folder.get_child('my_file.txt')

    def test_moving_files_and_resource_objects(self):
        root_folder = self.project.root
        my_file = root_folder.create_file('my_file.txt')
        old_hash = hash(my_file)
        my_file.move('my_other_file.txt')
        self.assertEquals(old_hash, hash(my_file))

    def test_file_encoding_reading(self):
        sample_file = self.project.root.create_file('my_file.txt')
        contents = u'# -*- coding: utf-8 -*-\n#\N{LATIN SMALL LETTER I WITH DIAERESIS}\n'
        file = open(sample_file.real_path, 'w')
        file.write(contents.encode('utf-8'))
        file.close()
        self.assertEquals(contents, sample_file.read())

    def test_file_encoding_writing(self):
        sample_file = self.project.root.create_file('my_file.txt')
        contents = u'# -*- coding: utf-8 -*-\n\N{LATIN SMALL LETTER I WITH DIAERESIS}\n'
        sample_file.write(contents)
        self.assertEquals(contents, sample_file.read())

    def test_using_utf8_when_writing_in_case_of_errors(self):
        sample_file = self.project.root.create_file('my_file.txt')
        contents = u'\n\N{LATIN SMALL LETTER I WITH DIAERESIS}\n'
        sample_file.write(contents)
        self.assertEquals(contents, sample_file.read())

    # XXX: supporting utf_8_sig
    def xxx_test_file_encoding_reading_for_notepad_styles(self):
        sample_file = self.project.root.create_file('my_file.txt')
        contents = u'#\N{LATIN SMALL LETTER I WITH DIAERESIS}\n'
        file = open(sample_file.real_path, 'w')
        # file.write('\xef\xbb\xbf')
        file.write(contents.encode('utf-8-sig'))
        file.close()
        self.assertEquals(contents, sample_file.read())

    def test_using_project_get_file(self):
        myfile = self.project.get_file(self.sample_file)
        self.assertTrue(myfile.exists())

    def test_using_file_create(self):
        myfile = self.project.get_file('myfile.txt')
        self.assertFalse(myfile.exists())
        myfile.create()
        self.assertTrue(myfile.exists())
        self.assertFalse(myfile.is_folder())

    def test_using_folder_create(self):
        myfolder = self.project.get_folder('myfolder')
        self.assertFalse(myfolder.exists())
        myfolder.create()
        self.assertTrue(myfolder.exists())
        self.assertTrue(myfolder.is_folder())

    @testutils.assert_raises(RopeError)
    def test_exception_when_creating_twice(self):
        myfile = self.project.get_file('myfile.txt')
        myfile.create()
        myfile.create()

    @testutils.assert_raises(RopeError)
    def test_exception_when_parent_does_not_exist(self):
        myfile = self.project.get_file('myfolder/myfile.txt')
        myfile.create()


class ResourceObserverTest(unittest.TestCase):

    def setUp(self):
        super(ResourceObserverTest, self).setUp()
        self.project_root = 'sample_project'
        testutils.remove_recursively(self.project_root)
        self.project = Project(self.project_root)

    def tearDown(self):
        testutils.remove_recursively(self.project_root)
        super(ResourceObserverTest, self).tearDown()

    def test_resource_change_observer(self):
        sample_file = self.project.root.create_file('my_file.txt')
        sample_file.write('a sample file version 1')
        sample_observer = _SampleObserver()
        self.project.add_observer(sample_observer)
        sample_file.write('a sample file version 2')
        self.assertEquals(1, sample_observer.change_count)
        self.assertEquals(sample_file, sample_observer.last_changed)

    def test_resource_change_observer_after_removal(self):
        sample_file = self.project.root.create_file('my_file.txt')
        sample_file.write('text')
        sample_observer = _SampleObserver()
        self.project.add_observer(FilteredResourceObserver(sample_observer,
                                                           [sample_file]))
        sample_file.remove()
        self.assertEquals(1, sample_observer.change_count)
        self.assertEquals((sample_file, None), sample_observer.last_moved)

    def test_resource_change_observer2(self):
        sample_file = self.project.root.create_file('my_file.txt')
        sample_observer = _SampleObserver()
        self.project.add_observer(sample_observer)
        self.project.remove_observer(sample_observer)
        sample_file.write('a sample file version 2')
        self.assertEquals(0, sample_observer.change_count)

    def test_resource_change_observer_for_folders(self):
        root_folder = self.project.root
        my_folder = root_folder.create_folder('my_folder')
        my_folder_observer = _SampleObserver()
        root_folder_observer = _SampleObserver()
        self.project.add_observer(FilteredResourceObserver(my_folder_observer,
                                                           [my_folder]))
        self.project.add_observer(FilteredResourceObserver(root_folder_observer,
                                                           [root_folder]))
        my_file = my_folder.create_file('my_file.txt')
        self.assertEquals(1, my_folder_observer.change_count)
        my_file.move('another_file.txt')
        self.assertEquals(2, my_folder_observer.change_count)
        self.assertEquals(1, root_folder_observer.change_count)
        self.project.get_resource('another_file.txt').remove()
        self.assertEquals(2, my_folder_observer.change_count)
        self.assertEquals(2, root_folder_observer.change_count)

    def test_resource_change_observer_after_moving(self):
        sample_file = self.project.root.create_file('my_file.txt')
        sample_observer = _SampleObserver()
        self.project.add_observer(sample_observer)
        sample_file.move('new_file.txt')
        self.assertEquals(1, sample_observer.change_count)
        self.assertEquals((sample_file, self.project.get_resource('new_file.txt')),
                           sample_observer.last_moved)

    def test_revalidating_files(self):
        root = self.project.root
        my_file = root.create_file('my_file.txt')
        sample_observer = _SampleObserver()
        self.project.add_observer(FilteredResourceObserver(sample_observer,
                                                           [my_file]))
        os.remove(my_file.real_path)
        self.project.validate(root)
        self.assertEquals((my_file, None), sample_observer.last_moved)
        self.assertEquals(1, sample_observer.change_count)

    def test_revalidating_files_and_no_changes2(self):
        root = self.project.root
        my_file = root.create_file('my_file.txt')
        sample_observer = _SampleObserver()
        self.project.add_observer(FilteredResourceObserver(sample_observer,
                                                           [my_file]))
        self.project.validate(root)
        self.assertEquals(None, sample_observer.last_moved)
        self.assertEquals(0, sample_observer.change_count)

    def test_revalidating_folders(self):
        root = self.project.root
        my_folder = root.create_folder('myfolder')
        my_file = my_folder.create_file('myfile.txt')
        sample_observer = _SampleObserver()
        self.project.add_observer(FilteredResourceObserver(sample_observer,
                                                           [my_folder]))
        testutils.remove_recursively(my_folder.real_path)
        self.project.validate(root)
        self.assertEquals((my_folder, None), sample_observer.last_moved)
        self.assertEquals(1, sample_observer.change_count)

    def test_removing_and_adding_resources_to_filtered_observer(self):
        my_file = self.project.root.create_file('my_file.txt')
        sample_observer = _SampleObserver()
        filtered_observer = FilteredResourceObserver(sample_observer)
        self.project.add_observer(filtered_observer)
        my_file.write('1')
        self.assertEquals(0, sample_observer.change_count)
        filtered_observer.add_resource(my_file)
        my_file.write('2')
        self.assertEquals(1, sample_observer.change_count)
        filtered_observer.remove_resource(my_file)
        my_file.write('3')
        self.assertEquals(1, sample_observer.change_count)

    def test_validation_and_changing_files(self):
        my_file = self.project.root.create_file('my_file.txt')
        sample_observer = _SampleObserver()
        timekeeper = _MockTimeKeepter()
        filtered_observer = FilteredResourceObserver(sample_observer, [my_file],
                                                     timekeeper=timekeeper)
        self.project.add_observer(filtered_observer)
        self._write_file(my_file.real_path)
        timekeeper.setmtime(my_file, 1)
        self.project.validate(self.project.root)
        self.assertEquals(1, sample_observer.change_count)

    def test_validation_and_changing_files2(self):
        my_file = self.project.root.create_file('my_file.txt')
        sample_observer = _SampleObserver()
        timekeeper = _MockTimeKeepter()
        self.project.add_observer(FilteredResourceObserver(
                                  sample_observer, [my_file],
                                  timekeeper=timekeeper))
        timekeeper.setmtime(my_file, 1)
        my_file.write('hey')
        self.assertEquals(1, sample_observer.change_count)
        self.project.validate(self.project.root)
        self.assertEquals(1, sample_observer.change_count)

    def test_not_reporting_multiple_changes_to_folders(self):
        root = self.project.root
        file1 = root.create_file('file1.txt')
        file2 = root.create_file('file2.txt')
        sample_observer = _SampleObserver()
        self.project.add_observer(FilteredResourceObserver(
                                  sample_observer, [root, file1, file2]))
        os.remove(file1.real_path)
        os.remove(file2.real_path)
        self.assertEquals(0, sample_observer.change_count)
        self.project.validate(self.project.root)
        self.assertEquals(3, sample_observer.change_count)

    def _write_file(self, path):
        my_file = open(path, 'w')
        my_file.write('\n')
        my_file.close()

    def test_moving_and_being_interested_about_a_folder_and_a_child(self):
        my_folder = self.project.root.create_folder('my_folder')
        my_file = my_folder.create_file('my_file.txt')
        sample_observer = _SampleObserver()
        filtered_observer = FilteredResourceObserver(
            sample_observer, [my_folder, my_file])
        self.project.add_observer(filtered_observer)
        my_folder.move('new_folder')
        self.assertEquals(2, sample_observer.change_count)

    def test_contains_for_folders(self):
        folder1 = self.project.root.create_folder('folder')
        folder2 = self.project.root.create_folder('folder2')
        self.assertFalse(folder1.contains(folder2))


class _MockTimeKeepter(object):

    def __init__(self):
        self.times = {}

    def setmtime(self, resource, time):
        self.times[resource] = time

    def getmtime(self, resource):
        return self.times.get(resource, 0)


class _SampleObserver(object):

    def __init__(self):
        self.change_count = 0
        self.last_changed = None
        self.last_moved = None

    def resource_changed(self, resource):
        self.last_changed = resource
        self.change_count += 1

    def resource_removed(self, resource, new_resource=None):
        self.last_moved = (resource, new_resource)
        self.change_count += 1


class OutOfProjectTest(unittest.TestCase):

    def setUp(self):
        super(OutOfProjectTest, self).setUp()
        self.project_root = 'sample_project'
        self.test_directory = 'temp_test_directory'
        testutils.remove_recursively(self.project_root)
        testutils.remove_recursively(self.test_directory)
        os.mkdir(self.test_directory)
        self.project = Project(self.project_root)
        self.no_project = NoProject()

    def tearDown(self):
        testutils.remove_recursively(self.project_root)
        testutils.remove_recursively(self.test_directory)
        super(OutOfProjectTest, self).tearDown()

    def test_simple_out_of_project_file(self):
        sample_file_path = os.path.join(self.test_directory, 'sample.txt')
        sample_file = file(sample_file_path, 'w')
        sample_file.write('sample content\n')
        sample_file.close()
        sample_resource = self.no_project.get_resource(sample_file_path)
        self.assertEquals('sample content\n', sample_resource.read())

    def test_simple_out_of_project_folder(self):
        sample_folder_path = os.path.join(self.test_directory, 'sample_folder')
        os.mkdir(sample_folder_path)
        sample_folder = self.no_project.get_resource(sample_folder_path)
        self.assertEquals([], sample_folder.get_children())

        sample_file_path = os.path.join(sample_folder_path, 'sample.txt')
        file(sample_file_path, 'w').close()
        sample_resource = self.no_project.get_resource(sample_file_path)
        self.assertEquals(sample_resource, sample_folder.get_children()[0])

    def test_using_absolute_path(self):
        sample_file_path = os.path.join(self.test_directory, 'sample.txt')
        file(sample_file_path, 'w').close()
        normal_sample_resource = self.no_project.get_resource(sample_file_path)
        absolute_sample_resource = \
            self.no_project.get_resource(os.path.abspath(sample_file_path))
        self.assertEquals(normal_sample_resource, absolute_sample_resource)

    def test_folder_get_child(self):
        sample_folder_path = os.path.join(self.test_directory, 'sample_folder')
        os.mkdir(sample_folder_path)
        sample_folder = self.no_project.get_resource(sample_folder_path)
        self.assertEquals([], sample_folder.get_children())

        sample_file_path = os.path.join(sample_folder_path, 'sample.txt')
        file(sample_file_path, 'w').close()
        sample_resource = self.no_project.get_resource(sample_file_path)
        self.assertTrue(sample_folder.has_child('sample.txt'))
        self.assertFalse(sample_folder.has_child('doesnothave.txt'))
        self.assertEquals(sample_resource, sample_folder.get_child('sample.txt'))


class _MockFSCommands(object):
    
    def __init__(self):
        self.log = ''
        self.fscommands = FileSystemCommands()

    def create_file(self, path):
        self.log += 'create_file '
        self.fscommands.create_file(path)

    def create_folder(self, path):
        self.log += 'create_folder '
        self.fscommands.create_folder(path)

    def move(self, path, new_location):
        self.log += 'move '
        self.fscommands.move(path, new_location)

    def remove(self, path):
        self.log += 'remove '
        self.fscommands.remove(path)


class RopeFolderTest(unittest.TestCase):

    def setUp(self):
        super(RopeFolderTest, self).setUp()
        self.project_root = 'sample_project'
        testutils.remove_recursively(self.project_root)

    def tearDown(self):
        testutils.remove_recursively(self.project_root)
        super(RopeFolderTest, self).tearDown()

    def test_none_project_rope_folder(self):
        project = Project(self.project_root, ropefolder=None)
        self.assertTrue(project.ropefolder is None)

    def test_getting_project_rope_folder(self):
        project = Project(self.project_root, ropefolder='.ropeproject')
        self.assertTrue(project.ropefolder.exists())
        self.assertTrue('.ropeproject', project.ropefolder.path)

    def test_setting_ignored_resources(self):
        project = Project(self.project_root)
        project.set_ignored_resources(['myfile.txt'])
        myfile = project.get_file('myfile.txt')
        file2 = project.get_file('file2.txt')
        self.assertTrue(project.is_ignored(myfile))
        self.assertFalse(project.is_ignored(file2))

    def test_ignored_folders(self):
        project = Project(self.project_root)
        project.set_ignored_resources(['myfolder'])
        myfolder = project.root.create_folder('myfolder')
        self.assertTrue(project.is_ignored(myfolder))
        myfile = myfolder.create_file('myfile.txt')
        self.assertTrue(project.is_ignored(myfile))

    def test_setting_ignored_resources_patterns(self):
        project = Project(self.project_root)
        project.set_ignored_resources(['m?file.*'])
        myfile = project.get_file('myfile.txt')
        file2 = project.get_file('file2.txt')
        self.assertTrue(project.is_ignored(myfile))
        self.assertFalse(project.is_ignored(file2))

    def test_normal_fscommands(self):
        fscommands = _MockFSCommands()
        project = Project(self.project_root, fscommands=fscommands)
        myfile = project.get_file('myfile.txt')
        myfile.create()
        self.assertTrue('create_file ', fscommands.log)

    def test_fscommands_and_ignored_resources(self):
        fscommands = _MockFSCommands()
        project = Project(self.project_root, fscommands=fscommands)
        project.set_ignored_resources(['myfile.txt'])
        myfile = project.get_file('myfile.txt')
        myfile.create()
        self.assertEquals('', fscommands.log)


def suite():
    result = unittest.TestSuite()
    result.addTests(unittest.makeSuite(ProjectTest))
    result.addTests(unittest.makeSuite(ResourceObserverTest))
    result.addTests(unittest.makeSuite(OutOfProjectTest))
    result.addTests(unittest.makeSuite(RopeFolderTest))
    return result

if __name__ == '__main__':
    unittest.main()
