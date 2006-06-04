import unittest

from ropetest import testutils
from rope.pycore import PyCore, PyType
from rope.project import Project

class PyElementHierarchyTest(unittest.TestCase):

    def setUp(self):
        super(PyElementHierarchyTest, self).setUp()
        self.project_root = 'sample_project'
        testutils.remove_recursively(self.project_root)
        self.project = Project(self.project_root)
        self.pycore = PyCore(self.project)

    def tearDown(self):
        testutils.remove_recursively(self.project_root)
        super(PyElementHierarchyTest, self).tearDown()

    def test_simple_module(self):
        self.project.create_module(self.project.get_root_folder(), 'mod')
        result = self.pycore.get_module('mod')
        self.assertEquals(PyType.get_type('Module'), result.type)
        self.assertEquals(0, len(result.attributes))
    
    def test_package(self):
        pkg = self.project.create_package(self.project.get_root_folder(), 'pkg')
        mod = self.project.create_module(pkg, 'mod')
        result = self.pycore.get_module('pkg')
        self.assertEquals(PyType.get_type('Module'), result.type)
        
    def test_simple_class(self):
        mod = self.project.create_module(self.project.get_root_folder(), 'mod')
        mod.write('class SampleClass(object):\n    pass\n')
        mod_element = self.pycore.get_module('mod')
        result = mod_element.attributes['SampleClass']
        self.assertEquals(PyType.get_type('Type'), result.type)

    def test_simple_function(self):
        mod = self.project.create_module(self.project.get_root_folder(), 'mod')
        mod.write('def sample_function():\n    pass\n')
        mod_element = self.pycore.get_module('mod')
        result = mod_element.attributes['sample_function']
        self.assertEquals(PyType.get_type('Function'), result.type)

    def test_class_methods(self):
        mod = self.project.create_module(self.project.get_root_folder(), 'mod')
        mod.write('class SampleClass(object):\n    def sample_method(self):\n        pass\n')
        mod_element = self.pycore.get_module('mod')
        sample_class = mod_element.attributes['SampleClass']
        self.assertEquals(1, len(sample_class.attributes))
        method = sample_class.attributes['sample_method']
                
    def test_global_variables(self):
        mod = self.project.create_module(self.project.get_root_folder(), 'mod')
        mod.write('var = 10')
        mod_element = self.pycore.get_module('mod')
        result = mod_element.attributes['var']
        
    def test_class_variables(self):
        mod = self.project.create_module(self.project.get_root_folder(), 'mod')
        mod.write('class SampleClass(object):\n    var = 10\n')
        mod_element = self.pycore.get_module('mod')
        sample_class = mod_element.attributes['SampleClass']
        var = sample_class.attributes['var']
        
    def test_class_attributes_set_in_init(self):
        mod = self.project.create_module(self.project.get_root_folder(), 'mod')
        mod.write('class SampleClass(object):\n    def __init__(self):\n        self.var = 20\n')
        mod_element = self.pycore.get_module('mod')
        sample_class = mod_element.attributes['SampleClass']
        var = sample_class.attributes['var']
        
    def test_classes_inside_other_classes_set_in_init(self):
        mod = self.project.create_module(self.project.get_root_folder(), 'mod')
        mod.write('class SampleClass(object):\n    class InnerClass(object):\n        pass\n\n')
        mod_element = self.pycore.get_module('mod')
        sample_class = mod_element.attributes['SampleClass']
        var = sample_class.attributes['InnerClass']
        self.assertEquals(PyType.get_type('Type'), var.type)


if __name__ == '__main__':
    unittest.main()
