import unittest
import rope.codeanalyze
import rope.refactor.rename
import rope.exceptions
import rope.project
import ropetest


class ExtractMethodTest(unittest.TestCase):

    def setUp(self):
        super(ExtractMethodTest, self).setUp()
        self.project_root = 'sample_project'
        ropetest.testutils.remove_recursively(self.project_root)
        self.project = rope.project.Project(self.project_root)
        self.pycore = self.project.get_pycore()
        self.refactoring = self.project.get_pycore().get_refactoring()

    def tearDown(self):
        ropetest.testutils.remove_recursively(self.project_root)
        super(ExtractMethodTest, self).tearDown()
        
    def do_extract_method(self, source_code, start, end, extracted):
        testmod = self.pycore.create_module(self.project.get_root_folder(), 'testmod')
        testmod.write(source_code)
        self.refactoring.extract_method(testmod, start, end, extracted)
        return testmod.read()

    def _convert_line_range_to_offset(self, code, start, end):
        lines = rope.codeanalyze.SourceLinesAdapter(code)
        return lines.get_line_start(start), lines.get_line_end(end)
    
    def test_simple_extract_function(self):
        code = "def a_func():\n    print 'one'\n    print 'two'\n"
        start, end = self._convert_line_range_to_offset(code, 2, 2)
        refactored = self.do_extract_method(code, start, end, 'extracted')
        expected = "def a_func():\n    extracted()\n    print 'two'\n\n" \
                   "def extracted():\n    print 'one'\n"
        self.assertEquals(expected, refactored)

    def test_extract_function_after_scope(self):
        code = "def a_func():\n    print 'one'\n    print 'two'\n\nprint 'hey'\n"
        start, end = self._convert_line_range_to_offset(code, 2, 2)
        refactored = self.do_extract_method(code, start, end, 'extracted')
        expected = "def a_func():\n    extracted()\n    print 'two'\n\n" \
                   "def extracted():\n    print 'one'\n\nprint 'hey'\n"
        self.assertEquals(expected, refactored)

    def test_simple_extract_function_with_parameter(self):
        code = "def a_func():\n    a_var = 10\n    print a_var\n"
        start, end = self._convert_line_range_to_offset(code, 3, 3)
        refactored = self.do_extract_method(code, start, end, 'new_func')
        expected = "def a_func():\n    a_var = 10\n    new_func(a_var)\n\n" \
                   "def new_func(a_var):\n    print a_var\n"
        self.assertEquals(expected, refactored)

    def test_not_unread_variables_as_parameter(self):
        code = "def a_func():\n    a_var = 10\n    print 'hey'\n"
        start, end = self._convert_line_range_to_offset(code, 3, 3)
        refactored = self.do_extract_method(code, start, end, 'new_func')
        expected = "def a_func():\n    a_var = 10\n    new_func()\n\n" \
                   "def new_func():\n    print 'hey'\n"
        self.assertEquals(expected, refactored)

    def test_simple_extract_function_with_two_parameter(self):
        code = "def a_func():\n    a_var = 10\n    another_var = 20\n" \
               "    third_var = a_var + another_var\n"
        start, end = self._convert_line_range_to_offset(code, 4, 4)
        refactored = self.do_extract_method(code, start, end, 'new_func')
        expected = "def a_func():\n    a_var = 10\n    another_var = 20\n" \
                   "    new_func(a_var, another_var)\n\n" \
                   "def new_func(a_var, another_var):\n    third_var = a_var + another_var\n"
        self.assertEquals(expected, refactored)

    def test_simple_extract_function_with_return_value(self):
        code = "def a_func():\n    a_var = 10\n    print a_var\n"
        start, end = self._convert_line_range_to_offset(code, 2, 2)
        refactored = self.do_extract_method(code, start, end, 'new_func')
        expected = "def a_func():\n    a_var = new_func()\n    print a_var\n\n" \
                   "def new_func():\n    a_var = 10\n    return a_var\n"
        self.assertEquals(expected, refactored)

    def test_extract_function_with_multiple_return_values(self):
        code = "def a_func():\n    a_var = 10\n    another_var = 20\n" \
               "    third_var = a_var + another_var\n"
        start, end = self._convert_line_range_to_offset(code, 2, 3)
        refactored = self.do_extract_method(code, start, end, 'new_func')
        expected = "def a_func():\n    a_var, another_var = new_func()\n" \
                   "    third_var = a_var + another_var\n\n" \
                   "def new_func():\n    a_var = 10\n    another_var = 20\n" \
                   "    return a_var, another_var\n"
        self.assertEquals(expected, refactored)

    def test_simple_extract_method(self):
        code = "class AClass(object):\n\n" \
               "    def a_func(self):\n        print 'one'\n        print 'two'\n"
        start, end = self._convert_line_range_to_offset(code, 4, 4)
        refactored = self.do_extract_method(code, start, end, 'new_func')
        expected = "class AClass(object):\n\n" \
                   "    def a_func(self):\n        self.new_func()\n        print 'two'\n\n" \
                   "    def new_func(self):\n        print 'one'\n"
        self.assertEquals(expected, refactored)

    def test_extract_method_with_args_and_returns(self):
        code = "class AClass(object):\n" \
               "    def a_func(self):\n" \
               "        a_var = 10\n" \
               "        another_var = a_var * 3\n" \
               "        third_var = a_var + another_var\n"
        start, end = self._convert_line_range_to_offset(code, 4, 4)
        refactored = self.do_extract_method(code, start, end, 'new_func')
        expected = "class AClass(object):\n" \
                   "    def a_func(self):\n" \
                   "        a_var = 10\n" \
                   "        another_var = self.new_func(a_var)\n" \
                   "        third_var = a_var + another_var\n\n" \
                   "    def new_func(self, a_var):\n" \
                   "        another_var = a_var * 3\n" \
                   "        return another_var\n"
        self.assertEquals(expected, refactored)

    def test_extract_method_with_self_as_argument(self):
        code = "class AClass(object):\n" \
               "    def a_func(self):\n" \
               "        print self\n"
        start, end = self._convert_line_range_to_offset(code, 3, 3)
        refactored = self.do_extract_method(code, start, end, 'new_func')
        expected = "class AClass(object):\n" \
                   "    def a_func(self):\n" \
                   "        self.new_func()\n\n" \
                   "    def new_func(self):\n" \
                   "        print self\n"
        self.assertEquals(expected, refactored)

    def test_extract_method_with_multiple_methods(self):
        code = "class AClass(object):\n" \
               "    def a_func(self):\n" \
               "        print self\n\n" \
               "    def another_func(self):\n" \
               "        pass\n"
        start, end = self._convert_line_range_to_offset(code, 3, 3)
        refactored = self.do_extract_method(code, start, end, 'new_func')
        expected = "class AClass(object):\n" \
                   "    def a_func(self):\n" \
                   "        self.new_func()\n\n" \
                   "    def new_func(self):\n" \
                   "        print self\n\n" \
                   "    def another_func(self):\n" \
                   "        pass\n"
        self.assertEquals(expected, refactored)

    def test_extract_function_with_function_returns(self):
        code = "def a_func():\n    def inner_func():\n        pass\n    inner_func()\n"
        start, end = self._convert_line_range_to_offset(code, 2, 3)
        refactored = self.do_extract_method(code, start, end, 'new_func')
        expected = "def a_func():\n    inner_func = new_func()\n    inner_func()\n\n" \
                   "def new_func():\n    def inner_func():\n        pass\n    return inner_func\n"
        self.assertEquals(expected, refactored)

    def test_simple_extract_global_function(self):
        code = "print 'one'\nprint 'two'\nprint 'three'\n"
        start, end = self._convert_line_range_to_offset(code, 2, 2)
        refactored = self.do_extract_method(code, start, end, 'new_func')
        expected = "print 'one'\n\ndef new_func():\n    print 'two'\n\nnew_func()\nprint 'three'\n"
        self.assertEquals(expected, refactored)

    def test_extract_function_while_inner_function_reads(self):
        code = "def a_func():\n    a_var = 10\n    " \
               "def inner_func():\n        print a_var\n    return inner_func\n"
        start, end = self._convert_line_range_to_offset(code, 3, 4)
        refactored = self.do_extract_method(code, start, end, 'new_func')
        expected = "def a_func():\n    a_var = 10\n" \
                   "    inner_func = new_func(a_var)\n    return inner_func\n\n" \
                   "def new_func(a_var):\n    def inner_func():\n        print a_var\n" \
                   "    return inner_func\n"
        self.assertEquals(expected, refactored)

    @ropetest.testutils.assert_raises(rope.exceptions.RefactoringException)
    def test_extract_method_bad_range(self):
        code = "def a_func():\n    pass\na_var = 10\n"
        start, end = self._convert_line_range_to_offset(code, 2, 3)
        self.do_extract_method(code, start, end, 'new_func')

    @ropetest.testutils.assert_raises(rope.exceptions.RefactoringException)
    def test_extract_method_bad_range2(self):
        code = "class AClass(object):\n    pass\n"
        start, end = self._convert_line_range_to_offset(code, 1, 1)
        self.do_extract_method(code, start, end, 'new_func')

    @ropetest.testutils.assert_raises(rope.exceptions.RefactoringException)
    def test_extract_method_containing_return(self):
        code = "def a_func(arg):\n    return arg * 2\n"
        start, end = self._convert_line_range_to_offset(code, 2, 2)
        self.do_extract_method(code, start, end, 'new_func')

    @ropetest.testutils.assert_raises(rope.exceptions.RefactoringException)
    def test_extract_method_containing_yield(self):
        code = "def a_func(arg):\n    yield arg * 2\n"
        start, end = self._convert_line_range_to_offset(code, 2, 2)
        self.do_extract_method(code, start, end, 'new_func')

    def test_extract_function_and_argument_as_paramenter(self):
        code = "def a_func(arg):\n    print arg\n"
        start, end = self._convert_line_range_to_offset(code, 2, 2)
        refactored = self.do_extract_method(code, start, end, 'new_func')
        expected = "def a_func(arg):\n    new_func(arg)\n\n" \
                   "def new_func(arg):\n    print arg\n"
        self.assertEquals(expected, refactored)

    def test_extract_function_and_indented_blocks(self):
        code = "def a_func(arg):\n    if True:\n        if True:\n            print arg\n"
        start, end = self._convert_line_range_to_offset(code, 3, 4)
        refactored = self.do_extract_method(code, start, end, 'new_func')
        expected = "def a_func(arg):\n    if True:\n        new_func(arg)\n\n" \
                   "def new_func(arg):\n    if True:\n        print arg\n"
        self.assertEquals(expected, refactored)
    
    def test_extract_method_and_multi_line_headers(self):
        code = "def a_func(\n           arg):\n    print arg\n"
        start, end = self._convert_line_range_to_offset(code, 3, 3)
        refactored = self.do_extract_method(code, start, end, 'new_func')
        expected = "def a_func(\n           arg):\n    new_func(arg)\n\n" \
                   "def new_func(arg):\n    print arg\n"
        self.assertEquals(expected, refactored)
    
    def test_transform_module_to_package(self):
        mod1 = self.pycore.create_module(self.project.get_root_folder(), 'mod1')
        mod1.write('import mod2\nfrom mod2 import AClass\n')
        mod2 = self.pycore.create_module(self.project.get_root_folder(), 'mod2')
        mod2.write('class AClass(object):\n    pass\n')
        self.refactoring.transform_module_to_package(mod2)
        mod2 = self.project.get_resource('mod2')
        root_folder = self.project.get_root_folder()
        self.assertFalse(root_folder.has_child('mod2.py'))
        self.assertEquals('class AClass(object):\n    pass\n', root_folder.get_child('mod2').
                          get_child('__init__.py').read())

    def test_transform_module_to_package_undoing(self):
        pkg = self.pycore.create_package(self.project.get_root_folder(), 'pkg')
        mod = self.pycore.create_module(pkg, 'mod')
        self.refactoring.transform_module_to_package(mod)
        self.assertFalse(pkg.has_child('mod.py'))
        self.assertTrue(pkg.get_child('mod').has_child('__init__.py'))
        self.refactoring.undo()
        self.assertTrue(pkg.has_child('mod.py'))
        self.assertFalse(pkg.has_child('mod'))

    def test_transform_module_to_package_with_relative_imports(self):
        pkg = self.pycore.create_package(self.project.get_root_folder(), 'pkg')
        mod1 = self.pycore.create_module(pkg, 'mod1')
        mod1.write('import mod2\nfrom mod2 import AClass\n')
        mod2 = self.pycore.create_module(pkg, 'mod2')
        mod2.write('class AClass(object):\n    pass\n')
        self.refactoring.transform_module_to_package(mod1)
        new_init = self.project.get_resource('pkg/mod1/__init__.py')
        self.assertEquals('import pkg.mod2\nfrom pkg.mod2 import AClass\n',
                          new_init.read())
