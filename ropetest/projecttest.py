import unittest
import os

from rope.project import Project, FileFinder, PythonFileRunner, RootFolder
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
    
    def test_getting_not_existing_project_file(self):
        try:
            projectFile = self.project.get_resource('DoesNotExistFile.txt')
            self.fail('Should have failed')
        except RopeException:
            pass

    def test_writing_in_project_files(self):
        projectFile = self.project.get_resource(self.projectMaker.get_sample_file_name())
        projectFile.write('another text\n')
        self.assertEquals('another text\n', projectFile.read())

    def test_creating_files(self):
        projectFile = 'newfile.txt'
        self.project.get_root_folder().create_file(projectFile)
        newFile = self.project.get_resource(projectFile)
        self.assertTrue(newFile is not None)

    def test_creating_files_that_already_exist(self):
        try:
            self.project.get_root_folder().create_file(self.projectMaker.get_sample_file_name())
            self.fail('Should have failed')
        except RopeException:
            pass

    def test_making_root_folder_if_it_does_not_exist(self):
        projectRoot = 'SampleProject2'
        try:
            project = Project(projectRoot)
            self.assertTrue(os.path.exists(projectRoot) and os.path.isdir(projectRoot))
        finally:
            testutils.remove_recursively(projectRoot)

    def test_failure_when_project_root_exists_and_is_a_file(self):
        projectRoot = 'SampleProject2'
        open(projectRoot, 'w').close()
        try:
            project = Project(projectRoot)
            self.fail('Should have failed')
        except RopeException:
            os.remove(projectRoot)

    def test_creating_folders(self):
        folderName = 'SampleFolder'
        self.project.get_root_folder().create_folder(folderName)
        folderPath = os.path.join(self.project.get_root_address(), folderName)
        self.assertTrue(os.path.exists(folderPath) and os.path.isdir(folderPath))

    def test_making_folder_that_already_exists(self):
        folderName = 'SampleFolder'
        self.project.get_root_folder().create_folder(folderName)
        try:
            self.project.get_root_folder().create_folder(folderName)
            self.fail('Should have failed')
        except RopeException:
            pass

    def test_failing_if_creating_folder_while_file_already_exists(self):
        folderName = 'SampleFolder'
        self.project.get_root_folder().create_file(folderName)
        try:
            self.project.get_root_folder().create_folder(folderName)
            self.fail('Should have failed')
        except RopeException:
            pass

    def test_creating_file_inside_folder(self):
        folder_name = 'sampleFolder'
        file_name = 'sample2.txt'
        file_path = folder_name + '/' + file_name
        parent_folder = self.project.get_root_folder().create_folder(folder_name)
        parent_folder.create_file(file_name)
        file = self.project.get_resource(file_path)
        file.write('sample notes')
        self.assertEquals(file_path, file.get_path())
        self.assertEquals('sample notes',
                          open(os.path.join(self.project.get_root_address(),
                                            file_path))
                          .read())

    def test_failing_when_creating_file_inside_non_existant_folder(self):
        try:
            self.project.get_root_folder().create_file('NonexistantFolder/SomeFile.txt')
            self.fail('Should have failed')
        except RopeException:
            pass

    def test_nested_directories(self):
        folder_name = 'SampleFolder'
        parent = self.project.get_root_folder().create_folder(folder_name)
        parent.create_folder(folder_name)
        folder_path = os.path.join(self.project.get_root_address(), folder_name, folder_name)
        self.assertTrue(os.path.exists(folder_path) and os.path.isdir(folder_path))

    def test_removing_riles(self):
        self.assertTrue(os.path.exists(os.path.join(self.project.get_root_address(),
                                                    self.projectMaker.get_sample_file_name())))
        self.project.get_resource(self.projectMaker.get_sample_file_name()).remove()
        self.assertFalse(os.path.exists(os.path.join(self.project.get_root_address(),
                                                     self.projectMaker.get_sample_file_name())))
                          
    def test_removing_directories(self):
        self.assertTrue(os.path.exists(os.path.join(self.project.get_root_address(),
                                                    self.projectMaker.get_sample_folder_name())))
        self.project.get_resource(self.projectMaker.get_sample_folder_name()).remove()
        self.assertFalse(os.path.exists(os.path.join(self.project.get_root_address(),
                                                     self.projectMaker.get_sample_folder_name())))

    def test_removing_non_existant_files(self):
        try:
            self.project.get_resource('NonExistantFile.txt').remove()
            self.fail('Should have failed')
        except RopeException:
            pass

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

    def test_getting_empty_source_folders(self):
        self.assertEquals([], self.project.get_source_folders())

    def test_root_source_folder(self):
        self.project.get_root_folder().create_file('sample.py')
        source_folders = self.project.get_source_folders()
        self.assertEquals(1, len(source_folders))
        self.assertTrue(self.project.get_root_folder() in source_folders)

    def test_src_source_folder(self):
        src = self.project.get_root_folder().create_folder('src')
        src.create_file('sample.py')
        source_folders = self.project.get_source_folders()
        self.assertEquals(1, len(source_folders))
        self.assertTrue(self.project.get_resource('src') in source_folders)

    def test_packages(self):
        src = self.project.get_root_folder().create_folder('src')
        pkg = src.create_folder('package')
        pkg.create_file('__init__.py')
        source_folders = self.project.get_source_folders()
        self.assertEquals(1, len(source_folders))
        self.assertTrue(src in source_folders)

    def test_multi_source_folders(self):
        src = self.project.get_root_folder().create_folder('src')
        package = src.create_folder('package')
        package.create_file('__init__.py')
        test = self.project.get_root_folder().create_folder('test')
        test.create_file('alltests.py')
        source_folders = self.project.get_source_folders()
        self.assertEquals(2, len(source_folders))
        self.assertTrue(src in source_folders)
        self.assertTrue(test in source_folders)

    def test_multi_source_folders2(self):
        mod1 = self.project.create_module(self.project.get_root_folder(), 'mod1')
        src = self.project.get_root_folder().create_folder('src')
        package = self.project.create_package(src, 'package')
        mod2 = self.project.create_module(package, 'mod2')
        source_folders = self.project.get_source_folders()
        self.assertEquals(2, len(source_folders))
        self.assertTrue(self.project.get_root_folder() in source_folders and \
                        src in source_folders)

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

    def test_module_creation(self):
        new_module = self.project.create_module(self.project.get_root_folder(), 'module')
        self.assertFalse(new_module.is_folder())
        self.assertEquals(self.project.get_resource('module.py'), new_module)

    def test_packaged_module_creation(self):
        package = self.project.get_root_folder().create_folder('package')
        new_module = self.project.create_module(self.project.get_root_folder(), 'package.module')
        self.assertEquals(self.project.get_resource('package/module.py'), new_module)

    def test_packaged_module_creation_with_nested_src(self):
        src = self.project.get_root_folder().create_folder('src')
        package = src.create_folder('pkg')
        new_module = self.project.create_module(src, 'pkg.mod')
        self.assertEquals(self.project.get_resource('src/pkg/mod.py'), new_module)

    def test_package_creation(self):
        new_package = self.project.create_package(self.project.get_root_folder(), 'pkg')
        self.assertTrue(new_package.is_folder())
        self.assertEquals(self.project.get_resource('pkg'), new_package)
        self.assertEquals(self.project.get_resource('pkg/__init__.py'), 
                          new_package.get_child('__init__.py'));

    def test_nested_package_creation(self):
        package = self.project.create_package(self.project.get_root_folder(), 'pkg1')
        nested_package = self.project.create_package(self.project.get_root_folder(), 'pkg1.pkg2')
        self.assertEquals(self.project.get_resource('pkg1/pkg2'), nested_package)

    def test_packaged_package_creation_with_nested_src(self):
        src = self.project.get_root_folder().create_folder('src')
        package = self.project.create_package(src, 'pkg1')
        nested_package = self.project.create_package(src, 'pkg1.pkg2')
        self.assertEquals(self.project.get_resource('src/pkg1/pkg2'), nested_package)

    def test_find_module(self):
        src = self.project.get_root_folder().create_folder('src')
        samplemod = self.project.create_module(src, 'samplemod')
        found_modules = self.project.find_module('samplemod')
        self.assertEquals(1, len(found_modules))
        self.assertEquals(samplemod, found_modules[0])

    def test_find_nested_module(self):
        src = self.project.get_root_folder().create_folder('src')
        samplepkg = self.project.create_package(src, 'samplepkg')
        samplemod = self.project.create_module(samplepkg, 'samplemod')
        found_modules = self.project.find_module('samplepkg.samplemod')
        self.assertEquals(1, len(found_modules))
        self.assertEquals(samplemod, found_modules[0])

    def test_find_multiple_module(self):
        src = self.project.get_root_folder().create_folder('src')
        samplemod1 = self.project.create_module(src, 'samplemod')
        samplemod2 = self.project.create_module(self.project.get_root_folder(), 'samplemod')
        test = self.project.get_root_folder().create_folder('test')
        samplemod3 = self.project.create_module(test, 'samplemod')
        found_modules = self.project.find_module('samplemod')
        self.assertEquals(3, len(found_modules))
        self.assertTrue(samplemod1 in found_modules and samplemod2 in found_modules and \
                        samplemod3 in found_modules)

    def test_find_module_packages(self):
        src = self.project.get_root_folder()
        samplepkg = self.project.create_package(src, 'samplepkg')
        found_modules = self.project.find_module('samplepkg')
        self.assertEquals(1, len(found_modules))
        self.assertEquals(samplepkg, found_modules[0])

    def test_find_module_when_module_and_package_with_the_same_name(self):
        src = self.project.get_root_folder()
        samplemod = self.project.create_module(src, 'sample')
        samplepkg = self.project.create_package(src, 'sample')
        found_modules = self.project.find_module('sample')
        self.assertEquals(1, len(found_modules))
        self.assertEquals(samplepkg, found_modules[0])

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


class SampleObserver(object):
    def __init__(self):
        self.change_count = 0
        self.last_changed = None

    def changed(self, resource):
        self.last_changed = resource
        self.change_count += 1


class FileFinderTest(unittest.TestCase):
    def setUp(self):
        unittest.TestCase.setUp(self)
        self.projectMaker = SampleProjectMaker()
        self.projectMaker.make_project()
        self.project = Project(self.projectMaker.get_root())
        self.finder = FileFinder(self.project)
        self.project.get_resource(self.projectMaker.get_sample_file_name()).remove()
        self.file1 = 'aa'
        self.file2 = 'abb'
        self.file3 = 'abc'
        self.file4 = 'b'
        self.parent = self.project.get_resource(self.projectMaker.get_sample_folder_name())
        self.parent.create_file(self.file1)
        self.parent.create_file(self.file2)
        self.parent.create_file(self.file3)
        self.parent.create_file(self.file4)
        
    def tearDown(self):
        self.projectMaker.remove_all()
        unittest.TestCase.tearDown(self)

    def testEmptyFinding(self):
        files = self.finder.find_files_starting_with('')
        self.assertEquals(4, len(files))

    def testFinding(self):
        self.assertEquals(3, len(self.finder.find_files_starting_with('a')))
        
    def testAbsoluteFinding(self):
        result = self.finder.find_files_starting_with('aa')
        self.assertEquals(1, len(result))
        self.assertEquals(self.file1, result[0].get_name())
        self.assertEquals(self.file2, self.finder.find_files_starting_with('abb')[0].get_name())

    def testSpecializedFinding(self):
        result = self.finder.find_files_starting_with('ab')
        self.assertEquals(2, len(result))

    def testEnsuringCorrectCaching(self):
        result0 = self.finder.find_files_starting_with('')
        self.assertEquals(4, len(result0))
        result1 = self.finder.find_files_starting_with('a')
        self.assertEquals(3, len(result1))
        result2 = self.finder.find_files_starting_with('ab')
        self.assertEquals(2, len(result2))
        result3 = self.finder.find_files_starting_with('aa')
        self.assertEquals(1, len(result3))
        result4 = self.finder.find_files_starting_with('a')
        self.assertEquals(3, len(result4))


class TestPythonFileRunner(unittest.TestCase):
    def setUp(self):
        unittest.TestCase.setUp(self)
        self.projectMaker = SampleProjectMaker()
        self.projectMaker.make_project()
        self.project = Project(self.projectMaker.get_root())

    def tearDown(self):
        self.projectMaker.remove_all()
        unittest.TestCase.tearDown(self)

    def make_sample_python_file(self, file_path, get_text_function_source=None):
        self.project.get_root_folder().create_file(file_path)
        file = self.project.get_resource(file_path)
        if not get_text_function_source:
            get_text_function_source = "def get_text():\n    return 'run'\n\n"
        file_content = get_text_function_source + \
                       "output = open('output.txt', 'w')\noutput.write(get_text())\noutput.close()\n"
        file.write(file_content)
        
    def get_output_file_content(self, file_path):
        try:
            output_path = ''
            last_slash = file_path.rfind('/')
            if last_slash != -1:
                output_path = file_path[0:last_slash + 1]
            file = self.project.get_resource(output_path + 'output.txt')
            return file.read()
        except RopeException:
            return ''

    def test_making_runner(self):
        file_path = 'sample.py'
        self.make_sample_python_file(file_path)
        file_resource = self.project.get_resource(file_path)
        runner = PythonFileRunner(file_resource)
        runner.wait_process()
        self.assertEquals('run', self.get_output_file_content(file_path))

    # FIXME: this does not work on windows
    def xxx_test_killing_runner(self):
        file_path = 'sample.py'
        self.make_sample_python_file(file_path,
                                     "def get_text():" +
                                     "\n    import time\n    time.sleep(1)\n    return 'run'\n")
        file_resource = self.project.get_resource(file_path)
        runner = PythonFileRunner(file_resource)
        runner.kill_process()
        self.assertEquals('', self.get_output_file_content(file_path))

    def test_running_nested_files(self):
        self.project.get_root_folder().create_folder('src')
        file_path = 'src/sample.py'
        self.make_sample_python_file(file_path)
        file_resource = self.project.get_resource(file_path)
        runner = PythonFileRunner(file_resource)
        runner.wait_process()
        self.assertEquals('run', self.get_output_file_content(file_path))

    def test_setting_process_input(self):
        file_path = 'sample.py'
        self.make_sample_python_file(file_path,
                                     "def get_text():" +
                                     "\n    import sys\n    return sys.stdin.readline()\n")
        temp_file_name = 'processtest.tmp'
        try:
            temp_file = open(temp_file_name, 'w')
            temp_file.write('input text\n')
            temp_file.close()
            file_resource = self.project.get_resource(file_path)
            stdin = open(temp_file_name)
            runner = PythonFileRunner(file_resource, stdin=stdin)
            runner.wait_process()
            stdin.close()
            self.assertEquals('input text\n', self.get_output_file_content(file_path))
        finally:
            os.remove(temp_file_name)
        
    def test_setting_process_output(self):
        file_path = 'sample.py'
        self.make_sample_python_file(file_path,
                                     "def get_text():" +
                                     "\n    print 'output text'\n    return 'run'\n")
        temp_file_name = 'processtest.tmp'
        try:
            file_resource = self.project.get_resource(file_path)
            stdout = open(temp_file_name, 'w')
            runner = PythonFileRunner(file_resource, stdout=stdout)
            runner.wait_process()
            stdout.close()
            temp_file = open(temp_file_name, 'r')
            self.assertEquals('output text\n', temp_file.read())
            temp_file.close()
        finally:
            os.remove(temp_file_name)

    def test_setting_pythonpath(self):
        src = self.project.get_root_folder().create_folder('src')
        src.create_file('sample.py')
        src.get_child('sample.py').write('def f():\n    pass\n')
        self.project.get_root_folder().create_folder('test')
        file_path = 'test/test.py'
        self.make_sample_python_file(file_path,
                                     "def get_text():" +
                                     "\n    import sample\n    sample.f()\n    return'run'\n")
        file_resource = self.project.get_resource(file_path)
        runner = PythonFileRunner(file_resource)
        runner.wait_process()
        self.assertEquals('run', self.get_output_file_content(file_path))


if __name__ == '__main__':
    unittest.main()
