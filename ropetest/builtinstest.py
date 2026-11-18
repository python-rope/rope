import unittest
from textwrap import dedent

from rope.base import builtins, libutils, pyobjects
from rope.base.builtins import Dict
from ropetest import testutils


class BuiltinTypesTest(unittest.TestCase):
    def test_generic_alias_inequality_preserves_not_implemented(self):
        code = "Alias = list[str]\nSame = list[str]\n"
        namespace = {}
        exec(code, namespace)
        self.assertEqual(namespace['Alias'], namespace['Same'])
        self.assertNotEqual(namespace['Alias'], object())
        self.mod.write(code)
        module = self.project.get_pymodule(self.mod)
        alias = module['Alias'].get_object()
        same = module['Same'].get_object()
        self.assertIsInstance(alias, builtins.GenericAlias)
        self.assertEqual(alias, same)
        self.assertFalse(alias != same)
        self.assertIs(NotImplemented, alias.__ne__(pyobjects.get_unknown()))
        self.assertNotEqual(alias, pyobjects.get_unknown())

    def test_native_getattribute_preserves_callable_descriptor_binding(self):
        cases = [
            ("object.__getattribute__(Owner(), 'read')()", "Value"),
            ("type.__getattribute__(Owner, 'read')(Owner())", "Value"),
            ("object.__getattribute__(Owner(), 'static')()", "Value"),
            ("type.__getattribute__(Owner, 'static')()", "Value"),
            ("object.__getattribute__(Owner(), 'build')()", "Owner"),
            ("type.__getattribute__(Owner, 'build')()", "Owner"),
            ("getattr(Owner(), 'read')()", "Value"),
            ("getattr(Owner, 'read')(Owner())", "Value"),
            ("getattr(Owner(), 'static')()", "Value"),
            ("getattr(Owner, 'build')()", "Owner"),
        ]
        for expression, expected in cases:
            with self.subTest(expression=expression):
                code = (
                    "class Value:\n    pass\n\n"
                    "class Owner:\n    def read(self):\n        return Value()\n"
                    "    @staticmethod\n    def static():\n        return Value()\n"
                    "    @classmethod\n    def build(cls):\n        return cls()\n\n"
                    + "result = " + expression + "\n"
                )
                namespace = {}
                exec(code, namespace)
                self.assertIsInstance(namespace['result'], namespace[expected])
                self.mod.write(code)
                module = self.project.get_pymodule(self.mod)
                self.assertIs(module[expected].get_object(), module['result'].get_object().get_type())

    def test_native_getattribute_unknown_member_has_no_invented_result(self):
        code = "class Owner:\n    pass\n\nresult = object.__getattribute__(Owner(), 'missing')\n"
        with self.assertRaises(AttributeError):
            exec(code, {})
        self.mod.write(code)
        module = self.project.get_pymodule(self.mod)
        self.assertIs(pyobjects.get_unknown(), module['result'].get_object())

    def test_getattr_default_for_absent_member(self):
        cases = [
            ("getattr(Owner(), 'missing', Value())", "Value"),
            ("getattr(Owner, 'missing', Value())", "Value"),
            ("getattr(Owner(), 'read', Other())()", "Value"),
        ]
        for expression, expected in cases:
            with self.subTest(expression=expression):
                code = (
                    "class Value:\n    pass\n\nclass Other:\n    pass\n\n"
                    "class Owner:\n    def read(self):\n        return Value()\n\n"
                    + "result = " + expression + "\n"
                )
                namespace = {}
                exec(code, namespace)
                self.assertIsInstance(namespace['result'], namespace[expected])
                self.mod.write(code)
                module = self.project.get_pymodule(self.mod)
                self.assertIs(module[expected].get_object(), module['result'].get_object().get_type())

    def test_getattr_dynamic_hook_has_no_invented_callable_identity(self):
        code = (
            "class Owner:\n"
            "    def __getattribute__(self, name):\n        return lambda: 7\n"
            "result = getattr(Owner(), 'read')()\n"
        )
        namespace = {}
        exec(code, namespace)
        self.assertEqual(7, namespace['result'])
        self.mod.write(code)
        module = self.project.get_pymodule(self.mod)
        self.assertIs(pyobjects.get_unknown(), module['result'].get_object())

    def test_inspect_members_preserves_selected_callable_in_heterogeneous_namespace(self):
        for receiver, call in (("Owner()", "()"), ("Owner", "(Owner())")):
            with self.subTest(receiver=receiver):
                code = (
                    "import inspect\nclass Value:\n    pass\n\n"
                    "class Owner:\n    label = 'other member'\n"
                    "    def run(self):\n        return Value()\n\n"
                    + "result = dict(inspect.getmembers(" + receiver + "))['run']" + call + "\n"
                )
                namespace = {}
                exec(code, namespace)
                self.assertIsInstance(namespace['result'], namespace['Value'])
                self.mod.write(code)
                module = self.project.get_pymodule(self.mod)
                self.assertIs(module['Value'].get_object(), module['result'].get_object().get_type())

    def test_inspect_members_dynamic_hooks_remain_unresolved(self):
        code = (
            "import inspect\nclass Owner:\n"
            "    def __dir__(self):\n        return ['run']\n"
            "    def run(self):\n        return 7\n\n"
            "result = dict(inspect.getmembers(Owner()))['run']()\n"
        )
        namespace = {}
        exec(code, namespace)
        self.assertEqual(7, namespace['result'])
        self.mod.write(code)
        module = self.project.get_pymodule(self.mod)
        self.assertIs(pyobjects.get_unknown(), module['result'].get_object())

    def test_inspect_member_model_does_not_adopt_homonymous_source(self):
        code = (
            "class inspect:\n    @staticmethod\n    def getmembers(value):\n        return 'custom'\n\n"
            "result = inspect.getmembers(7)\n"
        )
        namespace = {}
        exec(code, namespace)
        self.assertEqual('custom', namespace['result'])
        self.mod.write(code)
        module = self.project.get_pymodule(self.mod)
        self.assertIsInstance(module['result'].get_object(), builtins.LiteralString)
        self.assertEqual('custom', module['result'].get_object().value)

    def test_map_next_preserves_callable_element_flow(self):
        code = (
            "class Value:\n    pass\n\n"
            "result = next(map(lambda value: value, [Value()]))\n"
        )
        namespace = {}
        exec(code, namespace)
        self.assertIsInstance(namespace['result'], namespace['Value'])
        self.mod.write(code)
        module = self.project.get_pymodule(self.mod)
        self.assertIs(module['Value'].get_object(), module['result'].get_object().get_type())

    def setUp(self):
        super().setUp()
        self.project = testutils.sample_project()
        self.pycore = self.project.pycore
        self.mod = testutils.create_module(self.project, "mod")

    def tearDown(self):
        testutils.remove_project(self.project)
        super().tearDown()

    def test_builtin_module_exposes_scope(self):
        module = builtins.BuiltinModule("builtins")
        scope = module.get_scope()
        self.assertEqual("Module", scope.get_kind())
        self.assertIn("len", scope.get_names())

    def test_simple_case(self):
        self.mod.write("l = []\n")
        pymod = self.project.get_pymodule(self.mod)
        self.assertTrue("append" in pymod["l"].get_object())

    def test_holding_type_information(self):
        self.mod.write(dedent("""\
            class C(object):
                pass
            l = [C()]
            a_var = l.pop()
        """))
        pymod = self.project.get_pymodule(self.mod)
        c_class = pymod["C"].get_object()
        a_var = pymod["a_var"].get_object()
        self.assertEqual(c_class, a_var.get_type())

    def test_get_items(self):
        self.mod.write(dedent("""\
            class C(object):
                def __getitem__(self, i):
                    return C()
            c = C()
            a_var = c[0]
        """))
        pymod = self.project.get_pymodule(self.mod)
        c_class = pymod["C"].get_object()
        a_var = pymod["a_var"].get_object()
        self.assertEqual(c_class, a_var.get_type())

    def test_get_items_for_lists(self):
        self.mod.write(dedent("""\
            class C(object):
                pass
            l = [C()]
            a_var = l[0]
        """))
        pymod = self.project.get_pymodule(self.mod)
        c_class = pymod["C"].get_object()
        a_var = pymod["a_var"].get_object()
        self.assertEqual(c_class, a_var.get_type())

    def test_get_items_passes_the_subscript_argument(self):
        code = dedent("""\
            class Value:
                pass
            class Container:
                def __getitem__(self, item):
                    return item
            value = Value()
            selected = Container()[value]
        """)
        namespace = {}
        exec(code, namespace)
        self.assertIs(namespace["value"], namespace["selected"])
        self.mod.write(code)
        pymod = self.project.get_pymodule(self.mod)
        self.assertIs(
            pymod["value"].get_object(), pymod["selected"].get_object()
        )

    def test_get_items_from_slices(self):
        self.mod.write(dedent("""\
            class C(object):
                pass
            l = [C()]
            a_var = l[:].pop()
        """))
        pymod = self.project.get_pymodule(self.mod)
        c_class = pymod["C"].get_object()
        a_var = pymod["a_var"].get_object()
        self.assertEqual(c_class, a_var.get_type())

    def test_simple_for_loops(self):
        self.mod.write(dedent("""\
            class C(object):
                pass
            l = [C()]
            for c in l:
                a_var = c
        """))
        pymod = self.project.get_pymodule(self.mod)
        c_class = pymod["C"].get_object()
        a_var = pymod["a_var"].get_object()
        self.assertEqual(c_class, a_var.get_type())

    def test_definition_location_for_loop_variables(self):
        self.mod.write(dedent("""\
            class C(object):
                pass
            l = [C()]
            for c in l:
                pass
        """))
        pymod = self.project.get_pymodule(self.mod)
        c_var = pymod["c"]
        self.assertEqual((pymod, 4), c_var.get_definition_location())

    def test_simple_case_for_dicts(self):
        self.mod.write("d = {}\n")
        pymod = self.project.get_pymodule(self.mod)
        self.assertTrue("get" in pymod["d"].get_object())

    def test_get_item_for_dicts(self):
        self.mod.write(dedent("""\
            class C(object):
                pass
            d = {1: C()}
            a_var = d[1]
        """))
        pymod = self.project.get_pymodule(self.mod)
        c_class = pymod["C"].get_object()
        a_var = pymod["a_var"].get_object()
        self.assertEqual(c_class, a_var.get_type())

    def test_dict_function_parent(self):
        self.mod.write(dedent("""\
            d = {1: 2}
            a_var = d.keys()
        """))
        pymod = self.project.get_pymodule(self.mod)
        a_var = pymod["d"].get_object()["keys"].get_object()
        self.assertEqual(type(a_var.parent), Dict)

    def test_popping_dicts(self):
        self.mod.write(dedent("""\
            class C(object):
                pass
            d = {1: C()}
            a_var = d.pop(1)
        """))
        pymod = self.project.get_pymodule(self.mod)
        c_class = pymod["C"].get_object()
        a_var = pymod["a_var"].get_object()
        self.assertEqual(c_class, a_var.get_type())

    def test_getting_keys_from_dicts(self):
        self.mod.write(dedent("""\
            class C1(object):
                pass
            class C2(object):
                pass
            d = {C1(): C2()}
            for c in d.keys():
                a_var = c
        """))
        pymod = self.project.get_pymodule(self.mod)
        c_class = pymod["C1"].get_object()
        a_var = pymod["a_var"].get_object()
        self.assertEqual(c_class, a_var.get_type())

    def test_getting_values_from_dicts(self):
        self.mod.write(dedent("""\
            class C1(object):
                pass
            class C2(object):
                pass
            d = {C1(): C2()}
            for c in d.values():
                a_var = c
        """))
        pymod = self.project.get_pymodule(self.mod)
        c_class = pymod["C2"].get_object()
        a_var = pymod["a_var"].get_object()
        self.assertEqual(c_class, a_var.get_type())

    def test_getting_iterkeys_from_dicts(self):
        self.mod.write(dedent("""\
            class C1(object):
                pass
            class C2(object):
                pass
            d = {C1(): C2()}
            for c in d.keys():
                a_var = c
        """))
        pymod = self.project.get_pymodule(self.mod)
        c_class = pymod["C1"].get_object()
        a_var = pymod["a_var"].get_object()
        self.assertEqual(c_class, a_var.get_type())

    def test_getting_itervalues_from_dicts(self):
        self.mod.write(dedent("""\
            class C1(object):
                pass
            class C2(object):
                pass
            d = {C1(): C2()}
            for c in d.values():
                a_var = c
        """))
        pymod = self.project.get_pymodule(self.mod)
        c_class = pymod["C2"].get_object()
        a_var = pymod["a_var"].get_object()
        self.assertEqual(c_class, a_var.get_type())

    def test_using_copy_for_dicts(self):
        self.mod.write(dedent("""\
            class C1(object):
                pass
            class C2(object):
                pass
            d = {C1(): C2()}
            for c in d.copy():
                a_var = c
        """))
        pymod = self.project.get_pymodule(self.mod)
        c_class = pymod["C1"].get_object()
        a_var = pymod["a_var"].get_object()
        self.assertEqual(c_class, a_var.get_type())

    def test_tuple_assignments_for_items(self):
        self.mod.write(dedent("""\
            class C1(object):
                pass
            class C2(object):
                pass
            d = {C1(): C2()}
            key, value = d.items()[0]
        """))
        pymod = self.project.get_pymodule(self.mod)
        c1_class = pymod["C1"].get_object()
        c2_class = pymod["C2"].get_object()
        key = pymod["key"].get_object()
        value = pymod["value"].get_object()
        self.assertEqual(c1_class, key.get_type())
        self.assertEqual(c2_class, value.get_type())

    def test_tuple_assignment_for_lists(self):
        self.mod.write(dedent("""\
            class C(object):
                pass
            l = [C(), C()]
            a, b = l
        """))
        pymod = self.project.get_pymodule(self.mod)
        c_class = pymod["C"].get_object()
        a_var = pymod["a"].get_object()
        b_var = pymod["b"].get_object()
        self.assertEqual(c_class, a_var.get_type())
        self.assertEqual(c_class, b_var.get_type())

    def test_tuple_assignments_for_iteritems_in_fors(self):
        self.mod.write(dedent("""\
            class C1(object):
                pass
            class C2(object):
                pass
            d = {C1(): C2()}
            for x, y in d.items():
                a = x;
                b = y
        """))
        pymod = self.project.get_pymodule(self.mod)
        c1_class = pymod["C1"].get_object()
        c2_class = pymod["C2"].get_object()
        a_var = pymod["a"].get_object()
        b_var = pymod["b"].get_object()
        self.assertEqual(c1_class, a_var.get_type())
        self.assertEqual(c2_class, b_var.get_type())

    def test_simple_tuple_assignments(self):
        self.mod.write(dedent("""\
            class C1(object):
                pass
            class C2(object):
                pass
            a, b = C1(), C2()
        """))
        pymod = self.project.get_pymodule(self.mod)
        c1_class = pymod["C1"].get_object()
        c2_class = pymod["C2"].get_object()
        a_var = pymod["a"].get_object()
        b_var = pymod["b"].get_object()
        self.assertEqual(c1_class, a_var.get_type())
        self.assertEqual(c2_class, b_var.get_type())

    def test_overriding_builtin_names(self):
        self.mod.write(dedent("""\
            class C(object):
                pass
            list = C
        """))
        pymod = self.project.get_pymodule(self.mod)
        c_class = pymod["C"].get_object()
        list_var = pymod["list"].get_object()
        self.assertEqual(c_class, list_var)

    def test_simple_builtin_scope_test(self):
        self.mod.write("l = list()\n")
        pymod = self.project.get_pymodule(self.mod)
        self.assertTrue("append" in pymod["l"].get_object())

    def test_simple_sets(self):
        self.mod.write("s = set()\n")
        pymod = self.project.get_pymodule(self.mod)
        self.assertTrue("add" in pymod["s"].get_object())

    def test_making_lists_using_the_passed_argument_to_init(self):
        self.mod.write(dedent("""\
            class C(object):
                pass
            l1 = [C()]
            l2 = list(l1)
            a_var = l2.pop()
        """))
        pymod = self.project.get_pymodule(self.mod)
        c_class = pymod["C"].get_object()
        a_var = pymod["a_var"].get_object()
        self.assertEqual(c_class, a_var.get_type())

    def test_making_tuples_using_the_passed_argument_to_init(self):
        self.mod.write(dedent("""\
            class C(object):
                pass
            l1 = [C()]
            l2 = tuple(l1)
            a_var = l2[0]
        """))
        pymod = self.project.get_pymodule(self.mod)
        c_class = pymod["C"].get_object()
        a_var = pymod["a_var"].get_object()
        self.assertEqual(c_class, a_var.get_type())

    def test_making_sets_using_the_passed_argument_to_init(self):
        self.mod.write(dedent("""\
            class C(object):
                pass
            l1 = [C()]
            l2 = set(l1)
            a_var = l2.pop()
        """))
        pymod = self.project.get_pymodule(self.mod)
        c_class = pymod["C"].get_object()
        a_var = pymod["a_var"].get_object()
        self.assertEqual(c_class, a_var.get_type())

    def test_making_dicts_using_the_passed_argument_to_init(self):
        self.mod.write(dedent("""\
            class C1(object):
                pass
            class C2(object):
                pass
            l1 = [(C1(), C2())]
            l2 = dict(l1)
            a, b = l2.items()[0]
        """))
        pymod = self.project.get_pymodule(self.mod)
        c1_class = pymod["C1"].get_object()
        c2_class = pymod["C2"].get_object()
        a_var = pymod["a"].get_object()
        b_var = pymod["b"].get_object()
        self.assertEqual(c1_class, a_var.get_type())
        self.assertEqual(c2_class, b_var.get_type())

    def test_range_builtin_function(self):
        self.mod.write("l = range(1)\n")
        pymod = self.project.get_pymodule(self.mod)
        l = pymod["l"].get_object()
        self.assertTrue("append" in l)

    def test_reversed_builtin_function(self):
        self.mod.write(dedent("""\
            class C(object):
                pass
            l = [C()]
            for x in reversed(l):
                a_var = x
        """))
        pymod = self.project.get_pymodule(self.mod)
        c_class = pymod["C"].get_object()
        a_var = pymod["a_var"].get_object()
        self.assertEqual(c_class, a_var.get_type())

    def test_sorted_builtin_function(self):
        self.mod.write(dedent("""\
            class C(object):
                pass
            l = [C()]
            a_var = sorted(l).pop()
        """))
        pymod = self.project.get_pymodule(self.mod)
        c_class = pymod["C"].get_object()
        a_var = pymod["a_var"].get_object()
        self.assertEqual(c_class, a_var.get_type())

    def test_super_builtin_function(self):
        self.mod.write(dedent("""\
            class C(object):
                pass
            class A(object):
                def a_f(self):
                    return C()
            class B(A):
                def b_f(self):
                    return super(B, self).a_f()
            a_var = B.b_f()
        """))
        pymod = self.project.get_pymodule(self.mod)
        c_class = pymod["C"].get_object()
        a_var = pymod["a_var"].get_object()
        self.assertEqual(c_class, a_var.get_type())

    def test_super_follows_the_method_resolution_order(self):
        self.mod.write(dedent("""\
            class C1(object):
                pass
            class C2(object):
                pass
            class Base(object):
                def a_f(self):
                    return C1()
            class Left(Base):
                pass
            class Right(Base):
                def a_f(self):
                    return C2()
            class Derived(Left, Right):
                def b_f(self):
                    return super(Derived, self).a_f()
            a_var = Derived().b_f()
        """))
        pymod = self.project.get_pymodule(self.mod)
        c2_class = pymod["C2"].get_object()
        a_var = pymod["a_var"].get_object()
        self.assertEqual(c2_class, a_var.get_type())

    def test_super_binds_the_receiver(self):
        self.mod.write(dedent("""\
            class Base(object):
                def get_self(self):
                    return self
            class Derived(Base):
                def get(self):
                    return super(Derived, self).get_self()
            a_var = Derived().get()
        """))
        pymod = self.project.get_pymodule(self.mod)
        derived = pymod["Derived"].get_object()
        a_var = pymod["a_var"].get_object()
        self.assertEqual(derived, a_var.get_type())

    def test_super_classmethod_binds_the_receiver_class(self):
        self.mod.write(dedent("""\
            class Base(object):
                @classmethod
                def make(cls):
                    return cls()
            class Derived(Base):
                @classmethod
                def build(cls):
                    return super(Derived, cls).make()
            a_var = Derived.build()
        """))
        pymod = self.project.get_pymodule(self.mod)
        derived = pymod["Derived"].get_object()
        a_var = pymod["a_var"].get_object()
        self.assertEqual(derived, a_var.get_type())

    def test_super_skips_the_class_itself(self):
        self.mod.write(dedent("""\
            class C1(object):
                pass
            class C2(object):
                pass
            class Base(object):
                def a_f(self):
                    return C1()
            class Derived(Base):
                def a_f(self):
                    return C2()
                def b_f(self):
                    return super(Derived, self).a_f()
            a_var = Derived().b_f()
        """))
        pymod = self.project.get_pymodule(self.mod)
        c1_class = pymod["C1"].get_object()
        a_var = pymod["a_var"].get_object()
        self.assertEqual(c1_class, a_var.get_type())

    def test_file_builtin_type(self):
        self.mod.write(dedent("""\
            for line in open("file.txt"):
                a_var = line
        """))
        pymod = self.project.get_pymodule(self.mod)
        a_var = pymod["a_var"].get_object()
        self.assertTrue(isinstance(a_var.get_type(), builtins.Str))

    def test_property_builtin_type(self):
        self.mod.write("p = property()\n")
        pymod = self.project.get_pymodule(self.mod)
        p_var = pymod["p"].get_object()
        self.assertTrue("fget" in p_var)

    def test_lambda_functions(self):
        self.mod.write("l = lambda: 1\n")
        pymod = self.project.get_pymodule(self.mod)
        l_var = pymod["l"].get_object()
        self.assertEqual(pyobjects.get_base_type("Function"), l_var.get_type())

    def test_lambda_function_definition(self):
        self.mod.write("l = lambda x, y = 2, *a, **b: x + y\n")
        pymod = self.project.get_pymodule(self.mod)
        l_var = pymod["l"].get_object()
        self.assertTrue(l_var.get_name() is not None)
        self.assertEqual(len(l_var.get_param_names()), 4)
        self.assertEqual((pymod, 1), pymod["l"].get_definition_location())

    def test_lambdas_that_return_unknown(self):
        self.mod.write("a_var = (lambda: None)()\n")
        pymod = self.project.get_pymodule(self.mod)
        a_var = pymod["a_var"].get_object()
        self.assertTrue(a_var is not None)

    def test_builtin_zip_function(self):
        self.mod.write(dedent("""\
            class C1(object):
                pass
            class C2(object):
                pass
            c1_list = [C1()]
            c2_list = [C2()]
            a, b = zip(c1_list, c2_list)[0]
        """))
        pymod = self.project.get_pymodule(self.mod)
        c1_class = pymod["C1"].get_object()
        c2_class = pymod["C2"].get_object()
        a_var = pymod["a"].get_object()
        b_var = pymod["b"].get_object()
        self.assertEqual(c1_class, a_var.get_type())
        self.assertEqual(c2_class, b_var.get_type())

    def test_builtin_zip_function_with_more_than_two_args(self):
        self.mod.write(dedent("""\
            class C1(object):
                pass
            class C2(object):
                pass
            c1_list = [C1()]
            c2_list = [C2()]
            a, b, c = zip(c1_list, c2_list, c1_list)[0]
        """))
        pymod = self.project.get_pymodule(self.mod)
        c1_class = pymod["C1"].get_object()
        c2_class = pymod["C2"].get_object()
        a_var = pymod["a"].get_object()
        b_var = pymod["b"].get_object()
        c_var = pymod["c"].get_object()
        self.assertEqual(c1_class, a_var.get_type())
        self.assertEqual(c2_class, b_var.get_type())
        self.assertEqual(c1_class, c_var.get_type())

    def test_wrong_arguments_to_zip_function(self):
        self.mod.write(dedent("""\
            class C1(object):
                pass
            c1_list = [C1()]
            a, b = zip(c1_list, 1)[0]
        """))
        pymod = self.project.get_pymodule(self.mod)
        c1_class = pymod["C1"].get_object()
        a_var = pymod["a"].get_object()
        b_var = pymod["b"].get_object()  # noqa
        self.assertEqual(c1_class, a_var.get_type())

    def test_enumerate_builtin_function(self):
        self.mod.write(dedent("""\
            class C(object):
                pass
            l = [C()]
            for i, x in enumerate(l):
                a_var = x
        """))
        pymod = self.project.get_pymodule(self.mod)
        c_class = pymod["C"].get_object()
        a_var = pymod["a_var"].get_object()
        self.assertEqual(c_class, a_var.get_type())

    def test_builtin_class_get_name(self):
        self.assertEqual("object", builtins.builtins["object"].get_object().get_name())
        self.assertEqual(
            "property", builtins.builtins["property"].get_object().get_name()
        )

    def test_star_args_and_double_star_args(self):
        self.mod.write(dedent("""\
            def func(p, *args, **kwds):
                pass
        """))
        pymod = self.project.get_pymodule(self.mod)
        func_scope = pymod["func"].get_object().get_scope()
        args = func_scope["args"].get_object()
        kwds = func_scope["kwds"].get_object()
        self.assertTrue(isinstance(args.get_type(), builtins.List))
        self.assertTrue(isinstance(kwds.get_type(), builtins.Dict))

    def test_simple_list_comprehension_test(self):
        self.mod.write("a_var = [i for i in range(10)]\n")
        pymod = self.project.get_pymodule(self.mod)
        a_var = pymod["a_var"].get_object()
        self.assertTrue(isinstance(a_var.get_type(), builtins.List))

    def test_simple_list_generator_expression(self):
        self.mod.write("a_var = (i for i in range(10))\n")
        pymod = self.project.get_pymodule(self.mod)
        a_var = pymod["a_var"].get_object()
        self.assertTrue(isinstance(a_var.get_type(), builtins.Iterator))

    def test_iter_builtin_function(self):
        self.mod.write(dedent("""\
            class C(object):
                pass
            l = [C()]
            for c in iter(l):
                a_var = c
        """))
        pymod = self.project.get_pymodule(self.mod)
        c_class = pymod["C"].get_object()
        a_var = pymod["a_var"].get_object()
        self.assertEqual(c_class, a_var.get_type())

    def test_simple_int_type(self):
        self.mod.write("l = 1\n")
        pymod = self.project.get_pymodule(self.mod)
        self.assertEqual(
            builtins.builtins["int"].get_object(), pymod["l"].get_object().get_type()
        )

    def test_simple_float_type(self):
        self.mod.write("l = 1.0\n")
        pymod = self.project.get_pymodule(self.mod)
        self.assertEqual(
            builtins.builtins["float"].get_object(), pymod["l"].get_object().get_type()
        )

    def test_simple_float_type2(self):
        self.mod.write("l = 1e1\n")
        pymod = self.project.get_pymodule(self.mod)
        self.assertEqual(
            builtins.builtins["float"].get_object(), pymod["l"].get_object().get_type()
        )

    def test_simple_complex_type(self):
        self.mod.write("l = 1.0j\n")
        pymod = self.project.get_pymodule(self.mod)
        self.assertEqual(
            builtins.builtins["complex"].get_object(),
            pymod["l"].get_object().get_type(),
        )

    def test_handling_unaryop_on_ints(self):
        self.mod.write("l = -(1)\n")
        pymod = self.project.get_pymodule(self.mod)
        self.assertEqual(
            builtins.builtins["int"].get_object(), pymod["l"].get_object().get_type()
        )

    def test_handling_binop_on_ints(self):
        self.mod.write("l = 1 + 1\n")
        pymod = self.project.get_pymodule(self.mod)
        self.assertEqual(
            builtins.builtins["int"].get_object(), pymod["l"].get_object().get_type()
        )

    def test_handling_compares(self):
        self.mod.write("l = 1 == 1\n")
        pymod = self.project.get_pymodule(self.mod)
        self.assertEqual(
            builtins.builtins["bool"].get_object(), pymod["l"].get_object().get_type()
        )

    def test_handling_boolops(self):
        self.mod.write("l = 1 and 2\n")
        pymod = self.project.get_pymodule(self.mod)
        self.assertEqual(
            builtins.builtins["int"].get_object(), pymod["l"].get_object().get_type()
        )

    def test_binary_or_left_value_unknown(self):
        code = "var = (asdsd or 3)\n"
        pymod = libutils.get_string_module(self.project, code)
        self.assertEqual(
            builtins.builtins["int"].get_object(), pymod["var"].get_object().get_type()
        )

    def test_unknown_return_object(self):
        src = dedent("""\
            import sys
            def foo():
              res = set(sys.builtin_module_names)
              if foo: res.add(bar)
        """)
        self.project.prefs["import_dynload_stdmods"] = True
        self.mod.write(src)
        self.project.pycore.analyze_module(self.mod)

    def test_abstractmethods_attribute(self):
        # see http://bugs.python.org/issue10006 for details
        src = "class SubType(type): pass\nsubtype = SubType()\n"
        self.mod.write(src)
        self.project.pycore.analyze_module(self.mod)


class BuiltinModulesTest(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.project = testutils.sample_project(
            extension_modules=["time", "invalid", "invalid.sub"]
        )
        self.mod = testutils.create_module(self.project, "mod")

    def tearDown(self):
        testutils.remove_project(self.project)
        super().tearDown()

    def test_simple_case(self):
        self.mod.write("import time")
        pymod = self.project.get_pymodule(self.mod)
        self.assertTrue("time" in pymod["time"].get_object())

    def test_ignored_extensions(self):
        self.mod.write("import os")
        pymod = self.project.get_pymodule(self.mod)
        self.assertTrue("rename" not in pymod["os"].get_object())

    def test_ignored_extensions_2(self):
        self.mod.write("import os")
        pymod = self.project.get_pymodule(self.mod)
        self.assertTrue("rename" not in pymod["os"].get_object())

    def test_nonexistent_modules(self):
        self.mod.write("import invalid")
        pymod = self.project.get_pymodule(self.mod)
        pymod["invalid"].get_object()

    def test_nonexistent_modules_2(self):
        self.mod.write(dedent("""\
            import invalid
            import invalid.sub
        """))
        pymod = self.project.get_pymodule(self.mod)
        invalid = pymod["invalid"].get_object()
        self.assertTrue("sub" in invalid)

    def test_time_in_std_mods(self):
        import rope.base.stdmods

        self.assertTrue("time" in rope.base.stdmods.standard_modules())

    def test_timemodule_normalizes_to_time(self):
        import rope.base.stdmods

        self.assertEqual(rope.base.stdmods.normalize_so_name("timemodule.so"), "time")
