import unittest
import os

from rope.project import Project, RootFolder
from rope.exceptions import RopeException
from ropetest import testutils


class SampleProjectMaker(object):

    def __init__(self):
        self.projectRoot = 'SampleProject'
        self.sampleFile = 'sample.txt'
        self.sampleFolder = 'ASampleFolder'
        self.sample_content = 'sample text\n'
        
    def make_project(self):
        self.remove_all()
        self.sampleFilePath = os.path.join(self.projectRoot, self.sampleFile)
        os.mkdir(self.projectRoot)
        os.mkdir(os.path.join(self.projectRoot, self.sampleFolder))
        sample = open(self.sampleFilePath, 'w')
        sample.write(self.sample_content)
        sample.close()

    def get_root(self):
        return self.projectRoot

    def get_sample_file_name(self):
        return self.sampleFile

    def get_sample_folder_name(self):
        return self.sampleFolder

    def get_sample_file_contents(self):
        return 'sample text\n'

    def remove_all(self):
        testutils.remove_recursively(self.projectRoot)


class ProjectTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.projectMaker = SampleProjectMaker()
        self.projectMaker.make_project()
        self.project = Project(self.projectMaker.get_root())

    def tearDown(self):
        self.projectMaker.remove_all()
        unittest.TestCase.tearDown(self)

    def test_project_creation(self):
        self.assertEquals(self.projectMaker.get_root(), self.project.get_root_address())

    def test_getting_project_file(self):
        projectFile = self.project.get_resource(self.projectMaker.get_sample_file_name())
        self.assertTrue(projectFile is not None)

    def test_project_file_reading(self):
        projectFile = self.project.get_resource(self.projectMaker.get_sample_file_name())
        self.assertEquals(self.projectMaker.get_sample_file_contents(), projectFile.read())
    
    @testutils.assert_raises(RopeException)
    def test_getting_not_existing_project_file(self):
        projectFile = self.project.get_resource('DoesNotExistFile.txt')
        self.fail('Should have failed')

    def test_writing_in_project_files(self):
        projectFile = self.project.get_resource(self.projectMaker.get_sample_file_name())
        projectFile.write('another text\n')
        self.assertEquals('another text\n', projectFile.read())

    def test_creating_files(self):
        projectFile = 'newfile.txt'
        self.project.get_root_folder().create_file(projectFile)
        newFile = self.project.get_resource(projectFile)
        self.assertTrue(newFile is not None)

    @testutils.assert_raises(RopeException)
    def test_creating_files_that_already_exist(self):
        self.project.get_root_folder().create_file(self.projectMaker.get_sample_file_name())
        self.fail('Should have failed')

    def test_making_root_folder_if_it_does_not_exist(self):
        projectRoot = 'SampleProject2'
        try:
            project = Project(projectRoot)
            self.assertTrue(os.path.exists(projectRoot) and os.path.isdir(projectRoot))
        finally:
            testutils.remove_recursively(projectRoot)

    @testutils.assert_raises(RopeException)
    def test_failure_when_project_root_exists_and_is_a_file(self):
        try:
            projectRoot = 'SampleProject2'
            open(projectRoot, 'w').close()
            project = Project(projectRoot)
        finally:
            os.remove(projectRoot)

    def test_creating_folders(self):
        folderName = 'SampleFolder'
        self.project.get_root_folder().create_folder(folderName)
        folderPath = os.path.join(self.project.get_root_address(), folderName)
        self.assertTrue(os.path.exists(folderPath) and os.path.isdir(folderPath))

    @testutils.assert_raises(RopeException)
    def test_making_folder_that_already_exists(self):
        folderName = 'SampleFolder'
        self.project.get_root_folder().create_folder(folderName)
        self.project.get_root_folder().create_folder(folderName)

    @testutils.assert_raises(RopeException)
    def test_failing_if_creating_folder_while_file_already_exists(self):
        folderName = 'SampleFolder'
        self.project.get_root_folder().create_file(folderName)
        self.project.get_root_folder().create_folder(folderName)

    def test_creating_file_inside_folder(self):
        folder_name = 'sampleFolder'
        file_name = 'sample2.txt'
        file_path = folder_name + '/' + file_name
        parent_folder = self.project.get_root_folder().create_folder(folder_name)
        parent_folder.create_file(file_name)
        file = self.project.get_resource(file_path)
        file.write('sample notes')
        self.assertEquals(file_path, file.get_path())
        self.assertEquals('sample notes', open(os.path.join(self.project.get_root_address(),
                                                            file_path)).read())

    @testutils.assert_raises(RopeException)
    def test_failing_when_creating_file_inside_non_existant_folder(self):
        self.project.get_root_folder().create_file('NonexistantFolder/SomeFile.txt')

    def test_nested_directories(self):
        folder_name = 'SampleFolder'
        parent = self.project.get_root_folder().create_folder(folder_name)
        parent.create_folder(folder_name)
        folder_path = os.path.join(self.project.get_root_address(), folder_name, folder_name)
        self.assertTrue(os.path.exists(folder_path) and os.path.isdir(folder_path))

    def test_removing_files(self):
        self.assertTrue(os.path.exists(os.path.join(self.project.get_root_address(),
                                                    self.projectMaker.get_sample_file_name())))
        self.project.get_resource(self.projectMaker.get_sample_file_name()).remove()
        self.assertFalse(os.path.exists(os.path.join(self.project.get_root_address(),
                                                     self.projectMaker.get_sample_file_name())))
                          
    def test_removing_files_invalidating_in_project_resource_pool(self):
        root_folder = self.project.get_root_folder()
        my_file = root_folder.create_file('my_file.txt')
        my_file.remove()
        self.assertFalse(root_folder.has_child('my_file.txt'))
                          
    def test_removing_directories(self):
        self.assertTrue(os.path.exists(os.path.join(self.project.get_root_address(),
                                                    self.projectMaker.get_sample_folder_name())))
        self.project.get_resource(self.projectMaker.get_sample_folder_name()).remove()
        self.assertFalse(os.path.exists(os.path.join(self.project.get_root_address(),
                                                     self.projectMaker.get_sample_folder_name())))

    @testutils.assert_raises(RopeException)
    def test_removing_non_existant_files(self):
        self.project.get_resource('NonExistantFile.txt').remove()

    def test_removing_nested_files(self):
        fileName = self.projectMaker.get_sample_folder_name() + '/SampleFile.txt'
        self.project.get_root_folder().create_file(fileName)
        self.project.get_resource(fileName).remove()
        self.assertTrue(os.path.exists(os.path.join(self.project.get_root_address(),
                                                    self.projectMaker.get_sample_folder_name())))
        self.assertTrue(not os.path.exists(os.path.join(self.project.get_root_address(),
                                  fileName)))

    def test_file_get_name(self):
        file = self.project.get_resource(self.projectMaker.get_sample_file_name())
        self.assertEquals(self.projectMaker.get_sample_file_name(), file.get_name())
        file_name = 'nestedFile.txt'
        parent = self.project.get_resource(self.projectMaker.get_sample_folder_name())
        filePath = self.projectMaker.get_sample_folder_name() + '/' + file_name
        parent.create_file(file_name)
        nestedFile = self.project.get_resource(filePath)
        self.assertEquals(file_name, nestedFile.get_name())

    def test_folder_get_name(self):
        folder = self.project.get_resource(self.projectMaker.get_sample_folder_name())
        self.assertEquals(self.projectMaker.get_sample_folder_name(), folder.get_name())

    def test_file_get_path(self):
        file = self.project.get_resource(self.projectMaker.get_sample_file_name())
        self.assertEquals(self.projectMaker.get_sample_file_name(), file.get_path())
        fileName = 'nestedFile.txt'
        parent = self.project.get_resource(self.projectMaker.get_sample_folder_name())
        filePath = self.projectMaker.get_sample_folder_name() + '/' + fileName
        parent.create_file(fileName)
        nestedFile = self.project.get_resource(filePath)
        self.assertEquals(filePath, nestedFile.get_path())

    def test_folder_get_path(self):
        folder = self.project.get_resource(self.projectMaker.get_sample_folder_name())
        self.assertEquals(self.projectMaker.get_sample_folder_name(), folder.get_path())

    def test_is_folder(self):
        self.assertTrue(self.project.get_resource(self.projectMaker.get_sample_folder_name()).is_folder())
        self.assertTrue(not self.project.get_resource(self.projectMaker.get_sample_file_name()).is_folder())

    def testget_children(self):
        children = self.project.get_resource(self.projectMaker.get_sample_folder_name()).get_children()
        self.assertEquals([], children)
    
    def test_nonempty_get_children(self):
        file_name = 'nestedfile.txt'
        filePath = self.projectMaker.get_sample_folder_name() + '/' + file_name
        parent = self.project.get_resource(self.projectMaker.get_sample_folder_name())
        parent.create_file(file_name)
        children = parent.get_children()
        self.assertEquals(1, len(children))
        self.assertEquals(filePath, children[0].get_path())

    def test_nonempty_get_children2(self):
        file_name = 'nestedfile.txt'
        folder_name = 'nestedfolder.txt'
        filePath = self.projectMaker.get_sample_folder_name() + '/' + file_name
        folderPath = self.projectMaker.get_sample_folder_name() + '/' + folder_name
        parent = self.project.get_resource(self.projectMaker.get_sample_folder_name())
        parent.create_file(file_name)
        parent.create_folder(folder_name)
        children = parent.get_children()
        self.assertEquals(2, len(children))
        self.assertTrue(filePath == children[0].get_path() or filePath == children[1].get_path())
        self.assertTrue(folderPath == children[0].get_path() or folderPath == children[1].get_path())

    def test_getting_files(self):
        files = self.project.get_root_folder().get_files()
        self.assertEquals(1, len(files))
        self.assertTrue(self.project.get_resource(self.projectMaker.get_sample_file_name()) in files)
        
    def test_getting_folders(self):
        folders = self.project.get_root_folder().get_folders()
        self.assertEquals(1, len(folders))
        self.assertTrue(self.project.get_resource(self.projectMaker.get_sample_folder_name()) in folders)

    def test_nested_folder_get_files(self):
        parent = self.project.get_root_folder().create_folder('top')
        parent.create_file('file1.txt')
        parent.create_file('file2.txt')
        files = parent.get_files()
        self.assertEquals(2, len(files))
        self.assertTrue(self.project.get_resource('top/file2.txt') in files)
        self.assertEquals(0, len(parent.get_folders()))
        
    def test_nested_folder_get_folders(self):
        parent = self.project.get_root_folder().create_folder('top')
        parent.create_folder('dir1')
        parent.create_folder('dir2')
        folders = parent.get_folders()
        self.assertEquals(2, len(folders))
        self.assertTrue(self.project.get_resource('top/dir1') in folders)
        self.assertEquals(0, len(parent.get_files()))
        
    def testRootFolder(self):
        rootFolder = self.project.get_root_folder()
        self.assertEquals(2, len(rootFolder.get_children()))
        self.assertEquals('', rootFolder.get_path())
        self.assertEquals('', rootFolder.get_name())

    def testGetAllFiles(self):
        files = self.project.get_files()
        self.assertEquals(1, len(files))
        self.assertEquals(self.projectMaker.get_sample_file_name(), files[0].get_name())

    def testMultifileGetAllFiles(self):
        fileName = 'nestedFile.txt'
        parent = self.project.get_resource(self.projectMaker.get_sample_folder_name())
        parent.create_file(fileName)
        files = self.project.get_files()
        self.assertEquals(2, len(files))
        self.assertTrue(fileName == files[0].get_name() or fileName == files[1].get_name())

    def test_ignoring_dot_star_folders_in_get_files(self):
        root = self.project.get_root_address()
        dot_test = os.path.join(root, '.test')
        os.mkdir(dot_test)
        test_py = os.path.join(dot_test, 'test.py')
        file(test_py, 'w').close()
        for x in self.project.get_files():
            self.assertNotEquals('.test/test.py', x.get_path())

    def test_ignoring_dot_pyc_files_in_get_files(self):
        root = self.project.get_root_address()
        src_folder = os.path.join(root, 'src')
        os.mkdir(src_folder)
        test_pyc = os.path.join(src_folder, 'test.pyc')
        file(test_pyc, 'w').close()
        for x in self.project.get_files():
            self.assertNotEquals('src/test.pyc', x.get_path())

    def test_folder_creating_files(self):
        projectFile = 'NewFile.txt'
        self.project.get_root_folder().create_file(projectFile)
        new_file = self.project.get_resource(projectFile)
        self.assertTrue(new_file is not None and not new_file.is_folder())

    def test_folder_creating_nested_files(self):
        project_file = 'NewFile.txt'
        parent_folder = self.project.get_resource(self.projectMaker.get_sample_folder_name())
        parent_folder.create_file(project_file)
        newFile = self.project.get_resource(self.projectMaker.get_sample_folder_name()
                                            + '/' + project_file)
        self.assertTrue(new_file is not None and not new_file.is_folder())

    def test_folder_creating_files(self):
        projectFile = 'newfolder'
        self.project.get_root_folder().create_folder(projectFile)
        new_folder = self.project.get_resource(projectFile)
        self.assertTrue(new_folder is not None and new_folder.is_folder())

    def test_folder_creating_nested_files(self):
        project_file = 'newfolder'
        parent_folder = self.project.get_resource(self.projectMaker.get_sample_folder_name())
        parent_folder.create_folder(project_file)
        new_folder = self.project.get_resource(self.projectMaker.get_sample_folder_name()
                                               + '/' + project_file)
        self.assertTrue(new_folder is not None and new_folder.is_folder())

    def test_folder_get_child(self):
        folder = self.project.get_root_folder()
        folder.create_file('myfile.txt')
        folder.create_folder('myfolder')
        self.assertEquals(self.project.get_resource('myfile.txt'), 
                          folder.get_child('myfile.txt'))
        self.assertEquals(self.project.get_resource('myfolder'), 
                          folder.get_child('myfolder'))

    def test_folder_get_child_nested(self):
        root = self.project.get_root_folder()
        folder = root.create_folder('myfolder')
        folder.create_file('myfile.txt')
        folder.create_folder('myfolder')
        self.assertEquals(self.project.get_resource('myfolder/myfile.txt'),
                          folder.get_child('myfile.txt'))
        self.assertEquals(self.project.get_resource('myfolder/myfolder'),
                          folder.get_child('myfolder'))

    def test_project_root_is_root_folder(self):
        self.assertTrue(isinstance(self.project.get_root_folder(), RootFolder))

    def test_resource_change_observer(self):
        sample_file = self.project.get_root_folder().create_file('my_file.txt')
        sample_file.write('a sample file version 1')
        sample_observer = SampleObserver()
        sample_file.add_change_observer(sample_observer.changed)
        sample_file.write('a sample file version 2')
        self.assertEquals(1, sample_observer.change_count)
        self.assertEquals(sample_file, sample_observer.last_changed)

    def test_resource_change_observer_after_removal(self):
        sample_file = self.project.get_root_folder().create_file('my_file.txt')
        sample_file.write('a sample file version 1')
        sample_observer = SampleObserver()
        sample_file.add_change_observer(sample_observer.changed)
        sample_file.remove()
        self.assertEquals(1, sample_observer.change_count)
        self.assertEquals(sample_file, sample_observer.last_changed)

    def test_resource_change_observer(self):
        sample_file = self.project.get_root_folder().create_file('my_file.txt')
        sample_observer = SampleObserver()
        sample_file.add_change_observer(sample_observer.changed)
        sample_file.remove_change_observer(sample_observer.changed)
        sample_file.write('a sample file version 2')
        self.assertEquals(0, sample_observer.change_count)

    def test_resource_change_observer_for_folders(self):
        root_folder = self.project.get_root_folder()
        my_folder = root_folder.create_folder('my_folder')
        my_folder_observer = SampleObserver()
        root_folder_observer = SampleObserver()
        my_folder.add_change_observer(my_folder_observer.changed)
        root_folder.add_change_observer(root_folder_observer.changed)
        my_file = my_folder.create_file('my_file.txt')
        self.assertEquals(1, my_folder_observer.change_count)
        my_file.move('another_file.txt')
        self.assertEquals(2, my_folder_observer.change_count)
        self.assertEquals(1, root_folder_observer.change_count)
        my_file.remove()
        self.assertEquals(2, my_folder_observer.change_count)
        self.assertEquals(2, root_folder_observer.change_count)

    def test_moving_files(self):
        root_folder = self.project.get_root_folder()
        my_file = root_folder.create_file('my_file.txt')
        my_file.move('my_other_file.txt')
        self.assertFalse(root_folder.has_child('my_file.txt'))
        self.assertEquals(my_file, root_folder.get_child('my_other_file.txt'))
        self.assertEquals('my_other_file.txt', my_file.get_path())
                          
    def test_moving_folders(self):
        root_folder = self.project.get_root_folder()
        my_folder = root_folder.create_folder('my_folder')
        my_file = my_folder.create_file('my_file.txt')
        my_folder.move('new_folder')
        self.assertFalse(root_folder.has_child('my_folder'))
        self.assertEquals(my_folder, root_folder.get_child('new_folder'))
        self.assertEquals('new_folder/my_file.txt', my_file.get_path())
                          
    def test_moving_destination_folders(self):
        root_folder = self.project.get_root_folder()
        my_folder = root_folder.create_folder('my_folder')
        my_file = root_folder.create_file('my_file.txt')
        my_file.move('my_folder')
        self.assertFalse(root_folder.has_child('my_file.txt'))
        self.assertEquals(my_file, my_folder.get_child('my_file.txt'))
        self.assertEquals('my_folder/my_file.txt', my_file.get_path())
                          
    def test_moving_files_and_reference_objects(self):
        root_folder = self.project.get_root_folder()
        my_file = root_folder.create_file('my_file.txt')
        old_hash = hash(my_file)
        my_file.move('my_other_file.txt')
        self.assertEquals(old_hash, hash(my_file))
                          
    def test_resource_change_observer_after_moving(self):
        sample_file = self.project.get_root_folder().create_file('my_file.txt')
        sample_observer = SampleObserver()
        sample_file.add_change_observer(sample_observer.changed)
        sample_file.move('new_file.txt')
        self.assertEquals(1, sample_observer.change_count)
        self.assertEquals(sample_file, sample_observer.last_changed)


class SampleObserver(object):
    def __init__(self):
        self.change_count = 0
        self.last_changed = None

    def changed(self, resource):
        self.last_changed = resource
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

    def tearDown(self):
        testutils.remove_recursively(self.project_root)
        testutils.remove_recursively(self.test_directory)
        super(OutOfProjectTest, self).tearDown()

    def test_simple_out_of_project_file(self):
        sample_file_path = os.path.join(self.test_directory, 'sample.txt')
        sample_file = file(sample_file_path, 'w')
        sample_file.write('sample content\n')
        sample_file.close()
        sample_resource = self.project.get_out_of_project_resource(sample_file_path)
        self.assertEquals('sample content\n', sample_resource.read())

    def test_simple_out_of_project_folder(self):
        sample_folder_path = os.path.join(self.test_directory, 'sample_folder')
        os.mkdir(sample_folder_path)
        sample_folder = self.project.get_out_of_project_resource(sample_folder_path)
        self.assertEquals([], sample_folder.get_children())
        
        sample_file_path = os.path.join(sample_folder_path, 'sample.txt')
        file(sample_file_path, 'w').close()
        sample_resource = self.project.get_out_of_project_resource(sample_file_path)
        self.assertEquals(sample_resource, sample_folder.get_children()[0])

    def test_using_absolute_path(self):
        sample_file_path = os.path.join(self.test_directory, 'sample.txt')
        file(sample_file_path, 'w').close()
        normal_sample_resource = self.project.get_out_of_project_resource(sample_file_path)
        absolute_sample_resource = self.project.get_out_of_project_resource(os.path.abspath(sample_file_path))
        self.assertEquals(normal_sample_resource, absolute_sample_resource)

    def test_folder_get_child(self):
        sample_folder_path = os.path.join(self.test_directory, 'sample_folder')
        os.mkdir(sample_folder_path)
        sample_folder = self.project.get_out_of_project_resource(sample_folder_path)
        self.assertEquals([], sample_folder.get_children())
        
        sample_file_path = os.path.join(sample_folder_path, 'sample.txt')
        file(sample_file_path, 'w').close()
        sample_resource = self.project.get_out_of_project_resource(sample_file_path)
        self.assertTrue(sample_folder.has_child('sample.txt'))
        self.assertFalse(sample_folder.has_child('doesnothave.txt'))
        self.assertEquals(sample_resource, sample_folder.get_child('sample.txt'))


def suite():
    result = unittest.TestSuite()
    result.addTests(unittest.makeSuite(ProjectTest))
    result.addTests(unittest.makeSuite(OutOfProjectTest))
    return result

if __name__ == '__main__':
    unittest.main()

