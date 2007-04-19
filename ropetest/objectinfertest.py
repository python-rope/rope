import unittest

from rope.base import project, builtins
from rope.base.oi import memorydb, shelvedb
from ropetest import testutils


class ObjectInferTest(unittest.TestCase):

    def setUp(self):
        super(ObjectInferTest, self).setUp()
        self.project = testutils.sample_project()
        self.pycore = self.project.get_pycore()

    def tearDown(self):
        testutils.remove_project(self.project)
        super(ObjectInferTest, self).tearDown()

    def test_simple_type_inferencing(self):
        scope = self.pycore.get_string_scope(
            'class Sample(object):\n    pass\na_var = Sample()\n')
        sample_class = scope.get_name('Sample').get_object()
        a_var = scope.get_name('a_var').get_object()
        self.assertEquals(sample_class, a_var.get_type())

    def test_simple_type_inferencing_classes_defined_in_holding_scope(self):
        scope = self.pycore.get_string_scope('class Sample(object):\n    pass\n' +
                                             'def a_func():\n    a_var = Sample()\n')
        sample_class = scope.get_name('Sample').get_object()
        a_var = scope.get_name('a_func').get_object().\
                get_scope().get_name('a_var').get_object()
        self.assertEquals(sample_class, a_var.get_type())

    def test_simple_type_inferencing_classes_in_class_methods(self):
        code = 'class Sample(object):\n    pass\n' \
               'class Another(object):\n' \
               '    def a_method():\n        a_var = Sample()\n'
        scope = self.pycore.get_string_scope(code)
        sample_class = scope.get_name('Sample').get_object()
        another_class = scope.get_name('Another').get_object()
        a_var = another_class.get_attribute('a_method').\
                get_object().get_scope().get_name('a_var').get_object()
        self.assertEquals(sample_class, a_var.get_type())

    def test_simple_type_inferencing_class_attributes(self):
        code = 'class Sample(object):\n    pass\n' \
               'class Another(object):\n' \
               '    def __init__(self):\n        self.a_var = Sample()\n'
        scope = self.pycore.get_string_scope(code)
        sample_class = scope.get_name('Sample').get_object()
        another_class = scope.get_name('Another').get_object()
        a_var = another_class.get_attribute('a_var').get_object()
        self.assertEquals(sample_class, a_var.get_type())

    def test_simple_type_inferencing_for_in_class_assignments(self):
        scope = self.pycore.get_string_scope('class Sample(object):\n    pass\n' +
                                             'class Another(object):\n    an_attr = Sample()\n')
        sample_class = scope.get_name('Sample').get_object()
        another_class = scope.get_name('Another').get_object()
        an_attr = another_class.get_attribute('an_attr').get_object()
        self.assertEquals(sample_class, an_attr.get_type())

    def test_simple_type_inferencing_for_chained_assignments(self):
        mod = 'class Sample(object):\n    pass\n' \
              'copied_sample = Sample'
        mod_scope = self.project.get_pycore().get_string_scope(mod)
        sample_class = mod_scope.get_name('Sample')
        copied_sample = mod_scope.get_name('copied_sample')
        self.assertEquals(sample_class.get_object(),
                          copied_sample.get_object())

    def test_following_chained_assignments_avoiding_circles(self):
        mod = 'class Sample(object):\n    pass\n' \
              'sample_class = Sample\n' \
              'sample_class = sample_class\n'
        mod_scope = self.project.get_pycore().get_string_scope(mod)
        sample_class = mod_scope.get_name('Sample')
        sample_class_var = mod_scope.get_name('sample_class')
        self.assertEquals(sample_class.get_object(),
                          sample_class_var.get_object())

    def test_function_returned_object_static_type_inference1(self):
        src = 'class Sample(object):\n    pass\n' \
              'def a_func():\n    return Sample\n' \
              'a_var = a_func()\n'
        scope = self.project.get_pycore().get_string_scope(src)
        sample_class = scope.get_name('Sample')
        a_var = scope.get_name('a_var')
        self.assertEquals(sample_class.get_object(), a_var.get_object())

    def test_function_returned_object_static_type_inference2(self):
        src = 'class Sample(object):\n    pass\n' \
              'def a_func():\n    return Sample()\n' \
              'a_var = a_func()\n'
        scope = self.project.get_pycore().get_string_scope(src)
        sample_class = scope.get_name('Sample').get_object()
        a_var = scope.get_name('a_var').get_object()
        self.assertEquals(sample_class, a_var.get_type())

    def test_recursive_function_returned_object_static_type_inference(self):
        src = 'class Sample(object):\n    pass\n' \
              'def a_func():\n' \
              '    if True:\n        return Sample()\n' \
              '    else:\n        return a_func()\n' \
              'a_var = a_func()\n'
        scope = self.project.get_pycore().get_string_scope(src)
        sample_class = scope.get_name('Sample').get_object()
        a_var = scope.get_name('a_var').get_object()
        self.assertEquals(sample_class, a_var.get_type())

    def test_function_returned_object_using_call_special_function_static_type_inference(self):
        src = 'class Sample(object):\n' \
              '    def __call__(self):\n        return Sample\n' \
              'sample = Sample()\na_var = sample()'
        scope = self.project.get_pycore().get_string_scope(src)
        sample_class = scope.get_name('Sample')
        a_var = scope.get_name('a_var')
        self.assertEquals(sample_class.get_object(), a_var.get_object())

    def test_list_type_inferencing(self):
        src = 'class Sample(object):\n    pass\na_var = [Sample()]\n'
        scope = self.pycore.get_string_scope(src)
        sample_class = scope.get_name('Sample').get_object()
        a_var = scope.get_name('a_var').get_object()
        self.assertNotEquals(sample_class, a_var.get_type())

    def test_attributed_object_inference(self):
        src = 'class Sample(object):\n' \
              '    def __init__(self):\n        self.a_var = None\n' \
              '    def set(self):\n        self.a_var = Sample()\n'
        scope = self.pycore.get_string_scope(src)
        sample_class = scope.get_name('Sample').get_object()
        a_var = sample_class.get_attribute('a_var').get_object()
        self.assertEquals(sample_class, a_var.get_type())

    def test_getting_property_attributes(self):
        src = 'class A(object):\n    pass\n' \
              'def f(*args):\n    return A()\n' \
              'class B(object):\n    p = property(f)\n' \
              'a_var = B().p\n'
        pymod = self.pycore.get_string_module(src)
        a_class = pymod.get_attribute('A').get_object()
        a_var = pymod.get_attribute('a_var').get_object()
        self.assertEquals(a_class, a_var.get_type())

    def test_getting_property_attributes_with_method_getters(self):
        src = 'class A(object):\n    pass\n' \
              'class B(object):\n    def p_get(self):\n        return A()\n' \
              '    p = property(p_get)\n' \
              'a_var = B().p\n'
        pymod = self.pycore.get_string_module(src)
        a_class = pymod.get_attribute('A').get_object()
        a_var = pymod.get_attribute('a_var').get_object()
        self.assertEquals(a_class, a_var.get_type())

    def test_lambda_functions(self):
        mod = self.pycore.get_string_module(
            'class C(object):\n    pass\n'
            'l = lambda: C()\na_var = l()')
        c_class = mod.get_attribute('C').get_object()
        a_var = mod.get_attribute('a_var').get_object()
        self.assertEquals(c_class, a_var.get_type())

    def test_mixing_subscript_with_tuple_assigns(self):
        mod = self.pycore.get_string_module(
            'class C(object):\n    attr = 0\n'
            'd = {}\nd[0], b = (0, C())\n')
        c_class = mod.get_attribute('C').get_object()
        a_var = mod.get_attribute('b').get_object()
        self.assertEquals(c_class, a_var.get_type())

    def test_mixing_ass_attr_with_tuple_assignment(self):
        mod = self.pycore.get_string_module(
            'class C(object):\n    attr = 0\n'
            'c = C()\nc.attr, b = (0, C())\n')
        c_class = mod.get_attribute('C').get_object()
        a_var = mod.get_attribute('b').get_object()
        self.assertEquals(c_class, a_var.get_type())

    def test_mixing_slice_with_tuple_assigns(self):
        mod = self.pycore.get_string_module(
            'class C(object):\n    attr = 0\n'
            'd = [None] * 3\nd[0:2], b = ((0,), C())\n')
        c_class = mod.get_attribute('C').get_object()
        a_var = mod.get_attribute('b').get_object()
        self.assertEquals(c_class, a_var.get_type())

    def test_nested_tuple_assignments(self):
        mod = self.pycore.get_string_module(
            'class C1(object):\n    pass\nclass C2(object):\n    pass\n'
            'a, (b, c) = (C1(), (C2(), C1()))\n')
        c1_class = mod.get_attribute('C1').get_object()
        c2_class = mod.get_attribute('C2').get_object()
        a_var = mod.get_attribute('a').get_object()
        b_var = mod.get_attribute('b').get_object()
        c_var = mod.get_attribute('c').get_object()
        self.assertEquals(c1_class, a_var.get_type())
        self.assertEquals(c2_class, b_var.get_type())
        self.assertEquals(c1_class, c_var.get_type())

    def test_handling_generator_functions(self):
        mod = self.pycore.get_string_module(
            'class C(object):\n    pass\ndef f():\n    yield C()\n'
            'for c in f():\n    a_var = c\n')
        c_class = mod.get_attribute('C').get_object()
        a_var = mod.get_attribute('a_var').get_object()
        self.assertEquals(c_class, a_var.get_type())

    def test_handling_generator_functions_for_strs(self):
        mod = self.pycore.create_module(self.project.root, 'mod')
        mod.write('def f():\n    yield ""\n'
                  'for s in f():\n    a_var = s\n')
        pymod = self.pycore.resource_to_pyobject(mod)
        a_var = pymod.get_attribute('a_var').get_object()
        self.assertTrue(isinstance(a_var.get_type(), builtins.Str))

    def test_considering_nones_to_be_unknowns(self):
        mod = self.pycore.get_string_module(
            'class C(object):\n    pass\n'
            'a_var = None\na_var = C()\na_var = None\n')
        c_class = mod.get_attribute('C').get_object()
        a_var = mod.get_attribute('a_var').get_object()
        self.assertEquals(c_class, a_var.get_type())


def _do_for_all_dbs(function):
    def called(self):
        for db in self.dbs:
            function(self, db)
    return called


class _MockValidation(object):

    def is_value_valid(self, value):
        return value != -1

    def is_more_valid(self, new, old):
        return new != -1

    def is_file_valid(self, path):
        return path != 'invalid'

    def is_scope_valid(self, path, key):
        return path != 'invalid' and key != 'invalid'


class _MockFileListObserver(object):

    log = ''

    def added(self, path):
        self.log += 'added %s ' % path

    def removed(self, path):
        self.log += 'removed %s ' % path


class ObjectDBTest(unittest.TestCase):

    def setUp(self):
        super(ObjectDBTest, self).setUp()
        self.project = testutils.sample_project()
        validation = _MockValidation()
        self.dbs = [memorydb.MemoryObjectDB(validation),
                    shelvedb.ShelveObjectDB(self.project, validation)]

    def tearDown(self):
        for db in self.dbs:
            db.sync()
        testutils.remove_project(self.project)
        super(ObjectDBTest, self).tearDown()

    @_do_for_all_dbs
    def test_simple_per_name(self, db):
        db.add_pername('file', 'key', 'name', 1)
        self.assertEqual(1, db.get_pername('file', 'key', 'name'))

    @_do_for_all_dbs
    def test_simple_per_name_does_not_exist(self, db):
        self.assertEquals(None, db.get_pername('file', 'key', 'name'))

    @_do_for_all_dbs
    def test_simple_per_name_after_syncing(self, db):
        db.add_pername('file', 'key', 'name', 1)
        db.sync()

        self.assertEquals(1, db.get_pername('file', 'key', 'name'))

    @_do_for_all_dbs
    def test_getting_returned(self, db):
        db.add_callinfo('file', 'key', (1, 2), 3)
        self.assertEquals(3, db.get_returned('file', 'key', (1, 2)))

    @_do_for_all_dbs
    def test_getting_returned_when_does_not_match(self, db):
        db.add_callinfo('file', 'key', (1, 2), 3)
        self.assertEquals(None, db.get_returned('file', 'key', (1, 1)))

    @_do_for_all_dbs
    def test_getting_call_info(self, db):
        db.add_callinfo('file', 'key', (1, 2), 3)

        call_infos = list(db.get_callinfos('file', 'key'))
        self.assertEquals(1, len(call_infos))
        self.assertEquals((1, 2), call_infos[0].get_parameters())
        self.assertEquals(3, call_infos[0].get_returned())

    @_do_for_all_dbs
    def test_invalid_per_name(self, db):
        db.add_pername('file', 'key', 'name', -1)
        self.assertEquals(None, db.get_pername('file', 'key', 'name'))

    @_do_for_all_dbs
    def test_overwriting_per_name(self, db):
        db.add_pername('file', 'key', 'name', 1)
        db.add_pername('file', 'key', 'name', 2)
        self.assertEquals(2, db.get_pername('file', 'key', 'name'))

    @_do_for_all_dbs
    def test_not_overwriting_with_invalid_per_name(self, db):
        db.add_pername('file', 'key', 'name', 1)
        db.add_pername('file', 'key', 'name', -1)
        self.assertEquals(1, db.get_pername('file', 'key', 'name'))

    @_do_for_all_dbs
    def test_getting_invalid_returned(self, db):
        db.add_callinfo('file', 'key', (1, 2), -1)
        self.assertEquals(None, db.get_returned('file', 'key', (1, 2)))

    @_do_for_all_dbs
    def test_not_overwriting_with_invalid_returned(self, db):
        db.add_callinfo('file', 'key', (1, 2), 3)
        db.add_callinfo('file', 'key', (1, 2), -1)
        self.assertEquals(3, db.get_returned('file', 'key', (1, 2)))

    @_do_for_all_dbs
    def test_get_files(self, db):
        db.add_callinfo('file1', 'key', (1, 2), 3)
        db.add_callinfo('file2', 'key', (1, 2), 3)
        self.assertEquals(set(['file1', 'file2']), set(db.get_files()))

    @_do_for_all_dbs
    def test_validating_files(self, db):
        db.add_callinfo('invalid', 'key', (1, 2), 3)
        db.validate_files()
        self.assertEquals(0, len(db.get_files()))

    @_do_for_all_dbs
    def test_validating_file_for_scopes(self, db):
        db.add_callinfo('file', 'invalid', (1, 2), 3)
        db.validate_file('file')
        self.assertEquals(1, len(db.get_files()))
        self.assertEquals(0, len(list(db.get_callinfos('file', 'invalid'))))

    @_do_for_all_dbs
    def test_validating_file_moved(self, db):
        db.add_callinfo('file', 'key', (1, 2), 3)

        db.file_moved('file', 'newfile')
        self.assertEquals(1, len(db.get_files()))
        self.assertEquals(1, len(list(db.get_callinfos('newfile', 'key'))))

    @_do_for_all_dbs
    def test_using_file_list_observer(self, db):
        db.add_callinfo('invalid', 'key', (1, 2), 3)
        observer = _MockFileListObserver()
        db.add_file_list_observer(observer)
        db.validate_files()
        self.assertEquals('removed invalid ', observer.log)


def suite():
    result = unittest.TestSuite()
    result.addTests(unittest.makeSuite(ObjectInferTest))
    result.addTests(unittest.makeSuite(ObjectDBTest))
    return result


if __name__ == '__main__':
    unittest.main()
