import unittest
import rope.base.project
import ropetest


class BuiltinTypesTest(unittest.TestCase):

    def setUp(self):
        super(BuiltinTypesTest, self).setUp()
        ropetest.testutils.remove_recursively(self.project_root)
        self.project = rope.base.project.Project(self.project_root)
        self.pycore = self.project.get_pycore()
        self.mod = self.pycore.create_module(self.project.get_root_folder(), 'mod')

    project_root = 'sample_project'

    def tearDown(self):
        ropetest.testutils.remove_recursively(self.project_root)
        super(BuiltinTypesTest, self).tearDown()

    def test_simple_case(self):
        self.mod.write('l = []\n')
        pymod = self.pycore.resource_to_pyobject(self.mod)
        self.assertTrue('append' in pymod.get_attribute('l').get_object().get_attributes())

    def test_holding_type_information(self):
        self.mod.write('class C(object):\n    pass\nl = [C()]\na_var = l.pop()\n')
        pymod = self.pycore.resource_to_pyobject(self.mod)
        c_class = pymod.get_attribute('C').get_object()
        a_var = pymod.get_attribute('a_var').get_object()
        self.assertEquals(c_class, a_var.get_type())

    def test_get_items(self):
        self.mod.write('class C(object):\n    def __getitem__(self, i):\n        return C()\n'
                       'c = C()\na_var = c[0]')
        pymod = self.pycore.resource_to_pyobject(self.mod)
        c_class = pymod.get_attribute('C').get_object()
        a_var = pymod.get_attribute('a_var').get_object()
        self.assertEquals(c_class, a_var.get_type())

    def test_get_items_for_lists(self):
        self.mod.write('class C(object):\n    pass\nl = [C()]\na_var = l[0]\n')
        pymod = self.pycore.resource_to_pyobject(self.mod)
        c_class = pymod.get_attribute('C').get_object()
        a_var = pymod.get_attribute('a_var').get_object()
        self.assertEquals(c_class, a_var.get_type())

    def test_get_items_from_slices(self):
        self.mod.write('class C(object):\n    pass\nl = [C()]\na_var = l[:].pop()\n')
        pymod = self.pycore.resource_to_pyobject(self.mod)
        c_class = pymod.get_attribute('C').get_object()
        a_var = pymod.get_attribute('a_var').get_object()
        self.assertEquals(c_class, a_var.get_type())

    def test_simple_for_loops(self):
        self.mod.write('class C(object):\n    pass\nl = [C()]\n'
                       'for c in l:\n    a_var = c\n')
        pymod = self.pycore.resource_to_pyobject(self.mod)
        c_class = pymod.get_attribute('C').get_object()
        a_var = pymod.get_attribute('a_var').get_object()
        self.assertEquals(c_class, a_var.get_type())

    def test_definition_location_for_loop_variables(self):
        self.mod.write('class C(object):\n    pass\nl = [C()]\n'
                       'for c in l:\n    pass\n')
        pymod = self.pycore.resource_to_pyobject(self.mod)
        c_var = pymod.get_attribute('c')
        self.assertEquals((pymod, 4), c_var.get_definition_location())

    def test_simple_case_for_dicts(self):
        self.mod.write('d = {}\n')
        pymod = self.pycore.resource_to_pyobject(self.mod)
        self.assertTrue('get' in pymod.get_attribute('d').get_object().get_attributes())

    def test_get_item_for_dicts(self):
        self.mod.write('class C(object):\n    pass\nd = {1: C()}\na_var = d[1]\n')
        pymod = self.pycore.resource_to_pyobject(self.mod)
        c_class = pymod.get_attribute('C').get_object()
        a_var = pymod.get_attribute('a_var').get_object()
        self.assertEquals(c_class, a_var.get_type())

    def test_popping_dicts(self):
        self.mod.write('class C(object):\n    pass\nd = {1: C()}\na_var = d.pop(1)\n')
        pymod = self.pycore.resource_to_pyobject(self.mod)
        c_class = pymod.get_attribute('C').get_object()
        a_var = pymod.get_attribute('a_var').get_object()
        self.assertEquals(c_class, a_var.get_type())

    def test_getting_keys_from_dicts(self):
        self.mod.write('class C1(object):\n    pass\nclass C2(object):\n    pass\n'
                       'd = {C1(): C2()}\nfor c in d.keys():\n    a_var = c\n')
        pymod = self.pycore.resource_to_pyobject(self.mod)
        c_class = pymod.get_attribute('C1').get_object()
        a_var = pymod.get_attribute('a_var').get_object()
        self.assertEquals(c_class, a_var.get_type())

    def test_getting_values_from_dicts(self):
        self.mod.write('class C1(object):\n    pass\nclass C2(object):\n    pass\n'
                       'd = {C1(): C2()}\nfor c in d.values():\n    a_var = c\n')
        pymod = self.pycore.resource_to_pyobject(self.mod)
        c_class = pymod.get_attribute('C2').get_object()
        a_var = pymod.get_attribute('a_var').get_object()
        self.assertEquals(c_class, a_var.get_type())

    def test_getting_iterkeys_from_dicts(self):
        self.mod.write('class C1(object):\n    pass\nclass C2(object):\n    pass\n'
                       'd = {C1(): C2()}\nfor c in d.iterkeys():\n    a_var = c\n')
        pymod = self.pycore.resource_to_pyobject(self.mod)
        c_class = pymod.get_attribute('C1').get_object()
        a_var = pymod.get_attribute('a_var').get_object()
        self.assertEquals(c_class, a_var.get_type())

    def test_getting_itervalues_from_dicts(self):
        self.mod.write('class C1(object):\n    pass\nclass C2(object):\n    pass\n'
                       'd = {C1(): C2()}\nfor c in d.itervalues():\n    a_var = c\n')
        pymod = self.pycore.resource_to_pyobject(self.mod)
        c_class = pymod.get_attribute('C2').get_object()
        a_var = pymod.get_attribute('a_var').get_object()
        self.assertEquals(c_class, a_var.get_type())

    def test_using_copy_for_dicts(self):
        self.mod.write('class C1(object):\n    pass\nclass C2(object):\n    pass\n'
                       'd = {C1(): C2()}\nfor c in d.copy():\n    a_var = c\n')
        pymod = self.pycore.resource_to_pyobject(self.mod)
        c_class = pymod.get_attribute('C1').get_object()
        a_var = pymod.get_attribute('a_var').get_object()
        self.assertEquals(c_class, a_var.get_type())

    def test_tuple_assignments_for_items(self):
        self.mod.write('class C1(object):\n    pass\nclass C2(object):\n    pass\n'
                       'd = {C1(): C2()}\nkey, value = d.items()[0]\n')
        pymod = self.pycore.resource_to_pyobject(self.mod)
        c1_class = pymod.get_attribute('C1').get_object()
        c2_class = pymod.get_attribute('C2').get_object()
        key = pymod.get_attribute('key').get_object()
        value = pymod.get_attribute('value').get_object()
        self.assertEquals(c1_class, key.get_type())
        self.assertEquals(c2_class, value.get_type())

    def test_tuple_assignment_for_lists(self):
        self.mod.write('class C(object):\n    pass\nl = [C(), C()]\na, b = l\n')
        pymod = self.pycore.resource_to_pyobject(self.mod)
        c_class = pymod.get_attribute('C').get_object()
        a_var = pymod.get_attribute('a').get_object()
        b_var = pymod.get_attribute('b').get_object()
        self.assertEquals(c_class, a_var.get_type())
        self.assertEquals(c_class, b_var.get_type())

    def test_tuple_assignments_for_iteritems_in_fors(self):
        self.mod.write('class C1(object):\n    pass\nclass C2(object):\n    pass\n'
                       'd = {C1(): C2()}\nfor x, y in d.iteritems():\n    a = x;\n    b = y\n')
        pymod = self.pycore.resource_to_pyobject(self.mod)
        c1_class = pymod.get_attribute('C1').get_object()
        c2_class = pymod.get_attribute('C2').get_object()
        a_var = pymod.get_attribute('a').get_object()
        b_var = pymod.get_attribute('b').get_object()
        self.assertEquals(c1_class, a_var.get_type())
        self.assertEquals(c2_class, b_var.get_type())

    def test_simple_tuple_assignments(self):
        self.mod.write('class C1(object):\n    pass\nclass C2(object):\n    pass\n'
                       'a, b = C1(), C2()\n')
        pymod = self.pycore.resource_to_pyobject(self.mod)
        c1_class = pymod.get_attribute('C1').get_object()
        c2_class = pymod.get_attribute('C2').get_object()
        a_var = pymod.get_attribute('a').get_object()
        b_var = pymod.get_attribute('b').get_object()
        self.assertEquals(c1_class, a_var.get_type())
        self.assertEquals(c2_class, b_var.get_type())

    def test_overriding_builtin_names(self):
        self.mod.write('class C(object):\n    pass\nlist = C\n')
        pymod = self.pycore.resource_to_pyobject(self.mod)
        c_class = pymod.get_attribute('C').get_object()
        list_var = pymod.get_attribute('list').get_object()
        self.assertEquals(c_class, list_var)

    def test_simple_builtin_scope_test(self):
        self.mod.write('l = list()\n')
        pymod = self.pycore.resource_to_pyobject(self.mod)
        self.assertTrue('append' in pymod.get_attribute('l').get_object().get_attributes())

    def test_simple_sets(self):
        self.mod.write('s = set()\n')
        pymod = self.pycore.resource_to_pyobject(self.mod)
        self.assertTrue('add' in pymod.get_attribute('s').get_object().get_attributes())

    def test_making_lists_using_the_passed_argument_to_init(self):
        self.mod.write('class C(object):\n    pass\nl1 = [C()]\n'
                       'l2 = list(l1)\na_var = l2.pop()')
        pymod = self.pycore.resource_to_pyobject(self.mod)
        c_class = pymod.get_attribute('C').get_object()
        a_var = pymod.get_attribute('a_var').get_object()
        self.assertEquals(c_class, a_var.get_type())

    def test_making_tuples_using_the_passed_argument_to_init(self):
        self.mod.write('class C(object):\n    pass\nl1 = [C()]\n'
                       'l2 = tuple(l1)\na_var = l2[0]')
        pymod = self.pycore.resource_to_pyobject(self.mod)
        c_class = pymod.get_attribute('C').get_object()
        a_var = pymod.get_attribute('a_var').get_object()
        self.assertEquals(c_class, a_var.get_type())

    def test_making_sets_using_the_passed_argument_to_init(self):
        self.mod.write('class C(object):\n    pass\nl1 = [C()]\n'
                       'l2 = set(l1)\na_var = l2.pop()')
        pymod = self.pycore.resource_to_pyobject(self.mod)
        c_class = pymod.get_attribute('C').get_object()
        a_var = pymod.get_attribute('a_var').get_object()
        self.assertEquals(c_class, a_var.get_type())

    def test_making_dicts_using_the_passed_argument_to_init(self):
        self.mod.write('class C1(object):\n    pass\nclass C2(object):\n    pass\n'
                       'l1 = [(C1(), C2())]\n'
                       'l2 = dict(l1)\na, b = l2.items()[0]')
        pymod = self.pycore.resource_to_pyobject(self.mod)
        c1_class = pymod.get_attribute('C1').get_object()
        c2_class = pymod.get_attribute('C2').get_object()
        a_var = pymod.get_attribute('a').get_object()
        b_var = pymod.get_attribute('b').get_object()
        self.assertEquals(c1_class, a_var.get_type())
        self.assertEquals(c2_class, b_var.get_type())


if __name__ == '__main__':
    unittest.main()
