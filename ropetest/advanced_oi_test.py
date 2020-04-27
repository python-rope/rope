from rope.base.builtins import Str

try:
    import unittest2 as unittest
except ImportError:
    import unittest

import rope.base.libutils
import rope.base.oi
from rope.base.utils import pycompat
from ropetest import testutils


class DynamicOITest(unittest.TestCase):

    def setUp(self):
        super(DynamicOITest, self).setUp()
        self.project = testutils.sample_project(validate_objectdb=True)
        self.pycore = self.project.pycore

    def tearDown(self):
        testutils.remove_project(self.project)
        super(DynamicOITest, self).tearDown()

    def test_simple_dti(self):
        mod = testutils.create_module(self.project, 'mod')
        code = 'def a_func(arg):\n    return eval("arg")\n' \
               'a_var = a_func(a_func)\n'
        mod.write(code)
        self.pycore.run_module(mod).wait_process()
        pymod = self.project.get_pymodule(mod)
        self.assertEqual(pymod['a_func'].get_object(),
                          pymod['a_var'].get_object())

    def test_module_dti(self):
        mod1 = testutils.create_module(self.project, 'mod1')
        mod2 = testutils.create_module(self.project, 'mod2')
        code = 'import mod1\ndef a_func(arg):\n    return eval("arg")\n' \
               'a_var = a_func(mod1)\n'
        mod2.write(code)
        self.pycore.run_module(mod2).wait_process()
        pymod2 = self.project.get_pymodule(mod2)
        self.assertEqual(self.project.get_pymodule(mod1),
                          pymod2['a_var'].get_object())

    def test_class_from_another_module_dti(self):
        mod1 = testutils.create_module(self.project, 'mod1')
        mod2 = testutils.create_module(self.project, 'mod2')
        code1 = 'class AClass(object):\n    pass\n'
        code2 = 'from mod1 import AClass\n' \
            '\ndef a_func(arg):\n    return eval("arg")\n' \
            'a_var = a_func(AClass)\n'
        mod1.write(code1)
        mod2.write(code2)
        self.pycore.run_module(mod2).wait_process()
        #pymod1 = self.project.get_pymodule(mod1)
        pymod2 = self.project.get_pymodule(mod2)
        self.assertEqual(pymod2['AClass'].get_object(),
                          pymod2['a_var'].get_object())

    def test_class_dti(self):
        mod = testutils.create_module(self.project, 'mod')
        code = 'class AClass(object):\n    pass\n' \
               '\ndef a_func(arg):\n    return eval("arg")\n' \
               'a_var = a_func(AClass)\n'
        mod.write(code)
        self.pycore.run_module(mod).wait_process()
        pymod = self.project.get_pymodule(mod)
        self.assertEqual(pymod['AClass'].get_object(),
                          pymod['a_var'].get_object())

    def test_instance_dti(self):
        mod = testutils.create_module(self.project, 'mod')
        code = 'class AClass(object):\n    pass\n' \
               '\ndef a_func(arg):\n    return eval("arg()")\n' \
               'a_var = a_func(AClass)\n'
        mod.write(code)
        self.pycore.run_module(mod).wait_process()
        pymod = self.project.get_pymodule(mod)
        self.assertEqual(pymod['AClass'].get_object(),
                          pymod['a_var'].get_object().get_type())

    def test_method_dti(self):
        mod = testutils.create_module(self.project, 'mod')
        code = 'class AClass(object):\n    def a_method(self, arg):\n' \
               '        return eval("arg()")\n' \
               'an_instance = AClass()\n' \
               'a_var = an_instance.a_method(AClass)\n'
        mod.write(code)
        self.pycore.run_module(mod).wait_process()
        pymod = self.project.get_pymodule(mod)
        self.assertEqual(pymod['AClass'].get_object(),
                          pymod['a_var'].get_object().get_type())

    def test_function_argument_dti(self):
        mod = testutils.create_module(self.project, 'mod')
        code = 'def a_func(arg):\n    pass\n' \
               'a_func(a_func)\n'
        mod.write(code)
        self.pycore.run_module(mod).wait_process()
        pyscope = self.project.get_pymodule(mod).get_scope()
        self.assertEqual(pyscope['a_func'].get_object(),
                          pyscope.get_scopes()[0]['arg'].get_object())

    def test_classes_with_the_same_name(self):
        mod = testutils.create_module(self.project, 'mod')
        code = 'def a_func(arg):\n    class AClass(object):\n' \
               '        pass\n    return eval("arg")\n' \
               'class AClass(object):\n    pass\n' \
               'a_var = a_func(AClass)\n'
        mod.write(code)
        self.pycore.run_module(mod).wait_process()
        pymod = self.project.get_pymodule(mod)
        self.assertEqual(pymod['AClass'].get_object(),
                          pymod['a_var'].get_object())

    def test_nested_classes(self):
        mod = testutils.create_module(self.project, 'mod')
        code = 'def a_func():\n    class AClass(object):\n' \
               '        pass\n    return AClass\n' \
               'def another_func(arg):\n    return eval("arg")\n' \
               'a_var = another_func(a_func())\n'
        mod.write(code)
        self.pycore.run_module(mod).wait_process()
        pyscope = self.project.get_pymodule(mod).get_scope()
        self.assertEqual(pyscope.get_scopes()[0]['AClass'].get_object(),
                          pyscope['a_var'].get_object())

    def test_function_argument_dti2(self):
        mod = testutils.create_module(self.project, 'mod')
        code = 'def a_func(arg, a_builtin_type):\n    pass\n' \
               'a_func(a_func, [])\n'
        mod.write(code)
        self.pycore.run_module(mod).wait_process()
        pyscope = self.project.get_pymodule(mod).get_scope()
        self.assertEqual(pyscope['a_func'].get_object(),
                          pyscope.get_scopes()[0]['arg'].get_object())

    def test_dti_and_concluded_data_invalidation(self):
        mod = testutils.create_module(self.project, 'mod')
        code = 'def a_func(arg):\n    return eval("arg")\n' \
               'a_var = a_func(a_func)\n'
        mod.write(code)
        pymod = self.project.get_pymodule(mod)
        pymod['a_var'].get_object()
        self.pycore.run_module(mod).wait_process()
        self.assertEqual(pymod['a_func'].get_object(),
                          pymod['a_var'].get_object())

    def test_list_objects_and_dynamicoi(self):
        mod = testutils.create_module(self.project, 'mod')
        code = 'class C(object):\n    pass\n' \
               'def a_func(arg):\n    return eval("arg")\n' \
               'a_var = a_func([C()])[0]\n'
        mod.write(code)
        self.pycore.run_module(mod).wait_process()
        pymod = self.project.get_pymodule(mod)
        c_class = pymod['C'].get_object()
        a_var = pymod['a_var'].get_object()
        self.assertEqual(c_class, a_var.get_type())

    def test_for_loops_and_dynamicoi(self):
        mod = testutils.create_module(self.project, 'mod')
        code = 'class C(object):\n    pass\n' \
               'def a_func(arg):\n    return eval("arg")\n' \
               'for c in a_func([C()]):\n    a_var = c\n'
        mod.write(code)
        self.pycore.run_module(mod).wait_process()
        pymod = self.project.get_pymodule(mod)
        c_class = pymod['C'].get_object()
        a_var = pymod['a_var'].get_object()
        self.assertEqual(c_class, a_var.get_type())

    def test_dict_objects_and_dynamicoi(self):
        mod = testutils.create_module(self.project, 'mod')
        code = 'class C(object):\n    pass\n' \
               'def a_func(arg):\n    return eval("arg")\n' \
               'a_var = a_func({1: C()})[1]\n'
        mod.write(code)
        self.pycore.run_module(mod).wait_process()
        pymod = self.project.get_pymodule(mod)
        c_class = pymod['C'].get_object()
        a_var = pymod['a_var'].get_object()
        self.assertEqual(c_class, a_var.get_type())

    def test_dict_keys_and_dynamicoi(self):
        mod = testutils.create_module(self.project, 'mod')
        if pycompat.PY3:
            code = 'class C(object):\n    pass\n' \
                   'def a_func(arg):\n    return eval("arg")\n' \
                   'a_var = list(a_func({C(): 1}))[0]\n'
        else:
            code = 'class C(object):\n    pass\n' \
                   'def a_func(arg):\n    return eval("arg")\n' \
                   'a_var = a_func({C(): 1}).keys()[0]\n'
        mod.write(code)
        self.pycore.run_module(mod).wait_process()
        pymod = self.project.get_pymodule(mod)
        c_class = pymod['C'].get_object()
        a_var = pymod['a_var'].get_object()
        self.assertEqual(c_class, a_var.get_type())

    def test_dict_keys_and_dynamicoi2(self):
        mod = testutils.create_module(self.project, 'mod')
        code = 'class C1(object):\n    pass\nclass C2(object):\n    pass\n' \
               'def a_func(arg):\n    return eval("arg")\n' \
               'a, b = a_func((C1(), C2()))\n'
        mod.write(code)
        self.pycore.run_module(mod).wait_process()
        pymod = self.project.get_pymodule(mod)
        c1_class = pymod['C1'].get_object()
        c2_class = pymod['C2'].get_object()
        a_var = pymod['a'].get_object()
        b_var = pymod['b'].get_object()
        self.assertEqual(c1_class, a_var.get_type())
        self.assertEqual(c2_class, b_var.get_type())

    def test_strs_and_dynamicoi(self):
        mod = testutils.create_module(self.project, 'mod')
        code = 'def a_func(arg):\n    return eval("arg")\n' \
               'a_var = a_func("hey")\n'
        mod.write(code)
        self.pycore.run_module(mod).wait_process()
        pymod = self.project.get_pymodule(mod)
        a_var = pymod['a_var'].get_object()
        self.assertTrue(isinstance(a_var.get_type(), rope.base.builtins.Str))

    def test_textual_transformations(self):
        mod = testutils.create_module(self.project, 'mod')
        code = 'class C(object):\n    pass\ndef f():' \
               '\n    pass\na_var = C()\n' \
               'a_list = [C()]\na_str = "hey"\na_file = open("file.txt")\n'
        mod.write(code)
        to_pyobject = rope.base.oi.transform.TextualToPyObject(self.project)
        to_textual = rope.base.oi.transform.PyObjectToTextual(self.project)
        pymod = self.project.get_pymodule(mod)

        def complex_to_textual(pyobject):
            return to_textual.transform(
                to_pyobject.transform(to_textual.transform(pyobject)))

        test_variables = [
            ('C', ('defined', 'mod.py', 'C')),
            ('f', ('defined', 'mod.py', 'f')),
            ('a_var', ('instance', ('defined', 'mod.py', 'C'))),
            ('a_list',
             ('builtin', 'list', ('instance', ('defined', 'mod.py', 'C')))),
            ('a_str', ('builtin', 'str')),
            ('a_file', ('builtin', 'file')),
        ]
        test_cases = [(pymod[v].get_object(), r) for v, r in test_variables]
        test_cases += [
            (pymod, ('defined', 'mod.py')),
            (rope.base.builtins.builtins['enumerate'].get_object(),
             ('builtin', 'function', 'enumerate'))
        ]
        for var, result in test_cases:
            self.assertEqual(to_textual.transform(var), result)
            self.assertEqual(complex_to_textual(var), result)

    def test_arguments_with_keywords(self):
        mod = testutils.create_module(self.project, 'mod')
        code = 'class C1(object):\n    pass\nclass C2(object):\n    pass\n' \
               'def a_func(arg):\n    return eval("arg")\n' \
               'a = a_func(arg=C1())\nb = a_func(arg=C2())\n'
        mod.write(code)
        self.pycore.run_module(mod).wait_process()
        pymod = self.project.get_pymodule(mod)
        c1_class = pymod['C1'].get_object()
        c2_class = pymod['C2'].get_object()
        a_var = pymod['a'].get_object()
        b_var = pymod['b'].get_object()
        self.assertEqual(c1_class, a_var.get_type())
        self.assertEqual(c2_class, b_var.get_type())

    def test_a_function_with_different_returns(self):
        mod = testutils.create_module(self.project, 'mod')
        code = 'class C1(object):\n    pass\nclass C2(object):\n    pass\n' \
               'def a_func(arg):\n    return eval("arg")\n' \
               'a = a_func(C1())\nb = a_func(C2())\n'
        mod.write(code)
        self.pycore.run_module(mod).wait_process()
        pymod = self.project.get_pymodule(mod)
        c1_class = pymod['C1'].get_object()
        c2_class = pymod['C2'].get_object()
        a_var = pymod['a'].get_object()
        b_var = pymod['b'].get_object()
        self.assertEqual(c1_class, a_var.get_type())
        self.assertEqual(c2_class, b_var.get_type())

    def test_a_function_with_different_returns2(self):
        mod = testutils.create_module(self.project, 'mod')
        code = 'class C1(object):\n    pass\nclass C2(object):\n    pass\n' \
               'def a_func(p):\n    if p == C1:\n        return C1()\n' \
               '    else:\n        return C2()\n' \
               'a = a_func(C1)\nb = a_func(C2)\n'
        mod.write(code)
        self.pycore.run_module(mod).wait_process()
        pymod = self.project.get_pymodule(mod)
        c1_class = pymod['C1'].get_object()
        c2_class = pymod['C2'].get_object()
        a_var = pymod['a'].get_object()
        b_var = pymod['b'].get_object()
        self.assertEqual(c1_class, a_var.get_type())
        self.assertEqual(c2_class, b_var.get_type())

    def test_ignoring_star_args(self):
        mod = testutils.create_module(self.project, 'mod')
        code = 'class C1(object):\n    pass\nclass C2(object):\n    pass\n' \
               'def a_func(p, *args):' \
               '\n    if p == C1:\n        return C1()\n' \
               '    else:\n        return C2()\n' \
               'a = a_func(C1, 1)\nb = a_func(C2, 2)\n'
        mod.write(code)
        self.pycore.run_module(mod).wait_process()
        pymod = self.project.get_pymodule(mod)
        c1_class = pymod['C1'].get_object()
        c2_class = pymod['C2'].get_object()
        a_var = pymod['a'].get_object()
        b_var = pymod['b'].get_object()
        self.assertEqual(c1_class, a_var.get_type())
        self.assertEqual(c2_class, b_var.get_type())

    def test_ignoring_double_star_args(self):
        mod = testutils.create_module(self.project, 'mod')
        code = 'class C1(object):\n    pass\nclass C2(object):\n    pass\n' \
               'def a_func(p, *kwds, **args):\n    ' \
               'if p == C1:\n        return C1()\n' \
               '    else:\n        return C2()\n' \
               'a = a_func(C1, kwd=1)\nb = a_func(C2, kwd=2)\n'
        mod.write(code)
        self.pycore.run_module(mod).wait_process()
        pymod = self.project.get_pymodule(mod)
        c1_class = pymod['C1'].get_object()
        c2_class = pymod['C2'].get_object()
        a_var = pymod['a'].get_object()
        b_var = pymod['b'].get_object()
        self.assertEqual(c1_class, a_var.get_type())
        self.assertEqual(c2_class, b_var.get_type())

    def test_invalidating_data_after_changing(self):
        mod = testutils.create_module(self.project, 'mod')
        code = 'def a_func(arg):\n    return eval("arg")\n' \
               'a_var = a_func(a_func)\n'
        mod.write(code)
        self.pycore.run_module(mod).wait_process()
        mod.write(code.replace('a_func', 'newfunc'))
        mod.write(code)
        pymod = self.project.get_pymodule(mod)
        self.assertNotEqual(pymod['a_func'].get_object(),
                             pymod['a_var'].get_object())

    def test_invalidating_data_after_moving(self):
        mod2 = testutils.create_module(self.project, 'mod2')
        mod2.write('class C(object):\n    pass\n')
        mod = testutils.create_module(self.project, 'mod')
        code = 'import mod2\ndef a_func(arg):\n    return eval(arg)\n' \
               'a_var = a_func("mod2.C")\n'
        mod.write(code)
        self.pycore.run_module(mod).wait_process()
        mod.move('newmod.py')
        pymod = self.project.get_module('newmod')
        pymod2 = self.project.get_pymodule(mod2)
        self.assertEqual(pymod2['C'].get_object(),
                          pymod['a_var'].get_object())


class NewStaticOITest(unittest.TestCase):

    def setUp(self):
        super(NewStaticOITest, self).setUp()
        self.project = testutils.sample_project(validate_objectdb=True)
        self.pycore = self.project.pycore
        self.mod = testutils.create_module(self.project, 'mod')

    def tearDown(self):
        testutils.remove_project(self.project)
        super(NewStaticOITest, self).tearDown()

    def test_static_oi_for_simple_function_calls(self):
        code = 'class C(object):\n    pass\ndef f(p):\n    pass\nf(C())\n'
        self.mod.write(code)
        self.pycore.analyze_module(self.mod)
        pymod = self.project.get_pymodule(self.mod)
        c_class = pymod['C'].get_object()
        f_scope = pymod['f'].get_object().get_scope()
        p_type = f_scope['p'].get_object().get_type()
        self.assertEqual(c_class, p_type)

    def test_static_oi_not_failing_when_callin_callables(self):
        code = 'class C(object):\n    pass\nC()\n'
        self.mod.write(code)
        self.pycore.analyze_module(self.mod)

    def test_static_oi_for_nested_calls(self):
        code = 'class C(object):\n    pass\ndef f(p):\n    pass\n' \
               'def g(p):\n    return p\nf(g(C()))\n'
        self.mod.write(code)
        self.pycore.analyze_module(self.mod)
        pymod = self.project.get_pymodule(self.mod)
        c_class = pymod['C'].get_object()
        f_scope = pymod['f'].get_object().get_scope()
        p_type = f_scope['p'].get_object().get_type()
        self.assertEqual(c_class, p_type)

    def test_static_oi_class_methods(self):
        code = 'class C(object):\n    def f(self, p):\n        pass\n' \
               'C().f(C())'
        self.mod.write(code)
        self.pycore.analyze_module(self.mod)
        pymod = self.project.get_pymodule(self.mod)
        c_class = pymod['C'].get_object()
        f_scope = c_class['f'].get_object().get_scope()
        p_type = f_scope['p'].get_object().get_type()
        self.assertEqual(c_class, p_type)

    def test_static_oi_preventing_soi_maximum_recursion_exceptions(self):
        code = 'item = {}\nfor item in item.keys():\n    pass\n'
        self.mod.write(code)
        try:
            self.pycore.analyze_module(self.mod)
        except RuntimeError as e:
            self.fail(str(e))

    def test_static_oi_for_infer_return_typs_from_funcs_based_on_params(self):
        code = 'class C(object):\n    pass\ndef func(p):\n    return p\n' \
               'a_var = func(C())\n'
        self.mod.write(code)
        pymod = self.project.get_pymodule(self.mod)
        c_class = pymod['C'].get_object()
        a_var = pymod['a_var'].get_object()
        self.assertEqual(c_class, a_var.get_type())

    def test_a_function_with_different_returns(self):
        code = 'class C1(object):\n    pass\nclass C2(object):\n    pass\n' \
               'def a_func(arg):\n    return arg\n' \
               'a = a_func(C1())\nb = a_func(C2())\n'
        self.mod.write(code)
        pymod = self.project.get_pymodule(self.mod)
        c1_class = pymod['C1'].get_object()
        c2_class = pymod['C2'].get_object()
        a_var = pymod['a'].get_object()
        b_var = pymod['b'].get_object()
        self.assertEqual(c1_class, a_var.get_type())
        self.assertEqual(c2_class, b_var.get_type())

    def test_not_reporting_out_of_date_information(self):
        code = 'class C1(object):\n    pass\n' \
               'def f(arg):\n    return C1()\na_var = f('')\n'
        self.mod.write(code)
        pymod = self.project.get_pymodule(self.mod)
        c1_class = pymod['C1'].get_object()
        a_var = pymod['a_var'].get_object()
        self.assertEqual(c1_class, a_var.get_type())

        self.mod.write(code.replace('C1', 'C2'))
        pymod = self.project.get_pymodule(self.mod)
        c2_class = pymod['C2'].get_object()
        a_var = pymod['a_var'].get_object()
        self.assertEqual(c2_class, a_var.get_type())

    def test_invalidating_concluded_data_in_a_function(self):
        mod1 = testutils.create_module(self.project, 'mod1')
        mod2 = testutils.create_module(self.project, 'mod2')
        mod1.write('def func(arg):\n    temp = arg\n    return temp\n')
        mod2.write('import mod1\n'
                   'class C1(object):\n    pass\n'
                   'class C2(object):\n    pass\n'
                   'a_var = mod1.func(C1())\n')
        pymod2 = self.project.get_pymodule(mod2)
        c1_class = pymod2['C1'].get_object()
        a_var = pymod2['a_var'].get_object()
        self.assertEqual(c1_class, a_var.get_type())

        mod2.write(mod2.read()[:mod2.read().rfind('C1()')] + 'C2())\n')
        pymod2 = self.project.get_pymodule(mod2)
        c2_class = pymod2['C2'].get_object()
        a_var = pymod2['a_var'].get_object()
        self.assertEqual(c2_class, a_var.get_type())

    def test_handling_generator_functions_for_strs(self):
        self.mod.write('class C(object):\n    pass\ndef f(p):\n    yield p()\n'
                       'for c in f(C):\n    a_var = c\n')
        pymod = self.project.get_pymodule(self.mod)
        c_class = pymod['C'].get_object()
        a_var = pymod['a_var'].get_object()
        self.assertEqual(c_class, a_var.get_type())

    # TODO: Returning a generator for functions that yield unknowns
    @unittest.skip("Returning a generator that yields unknowns")
    def xxx_test_handl_generator_functions_when_unknown_type_is_yielded(self):
        self.mod.write('class C(object):\n    pass'
                       '\ndef f():\n    yield eval("C()")\n'
                       'a_var = f()\n')
        pymod = self.project.get_pymodule(self.mod)
        a_var = pymod['a_var'].get_object()
        self.assertTrue(isinstance(a_var.get_type(),
                                   rope.base.builtins.Generator))

    def test_static_oi_for_lists_depending_on_append_function(self):
        code = 'class C(object):\n    pass\nl = list()\n' \
               'l.append(C())\na_var = l.pop()\n'
        self.mod.write(code)
        self.pycore.analyze_module(self.mod)
        pymod = self.project.get_pymodule(self.mod)
        c_class = pymod['C'].get_object()
        a_var = pymod['a_var'].get_object()
        self.assertEqual(c_class, a_var.get_type())

    def test_static_oi_for_lists_per_object_for_get_item(self):
        code = 'class C(object):\n    pass\nl = list()\n' \
               'l.append(C())\na_var = l[0]\n'
        self.mod.write(code)
        self.pycore.analyze_module(self.mod)
        pymod = self.project.get_pymodule(self.mod)
        c_class = pymod['C'].get_object()
        a_var = pymod['a_var'].get_object()
        self.assertEqual(c_class, a_var.get_type())

    def test_static_oi_for_lists_per_object_for_fields(self):
        code = 'class C(object):\n    pass\n' \
               'class A(object):\n    ' \
               'def __init__(self):\n        self.l = []\n' \
               '    def set(self):\n        self.l.append(C())\n' \
               'a = A()\na.set()\na_var = a.l[0]\n'
        self.mod.write(code)
        self.pycore.analyze_module(self.mod)
        pymod = self.project.get_pymodule(self.mod)
        c_class = pymod['C'].get_object()
        a_var = pymod['a_var'].get_object()
        self.assertEqual(c_class, a_var.get_type())

    def test_static_oi_for_lists_per_object_for_set_item(self):
        code = 'class C(object):\n    pass\nl = [None]\n' \
               'l[0] = C()\na_var = l[0]\n'
        self.mod.write(code)
        self.pycore.analyze_module(self.mod)
        pymod = self.project.get_pymodule(self.mod)
        c_class = pymod['C'].get_object()
        a_var = pymod['a_var'].get_object()
        self.assertEqual(c_class, a_var.get_type())

    def test_static_oi_for_lists_per_object_for_extending_lists(self):
        code = 'class C(object):\n    pass\nl = []\n' \
               'l.append(C())\nl2 = []\nl2.extend(l)\na_var = l2[0]\n'
        self.mod.write(code)
        self.pycore.analyze_module(self.mod)
        pymod = self.project.get_pymodule(self.mod)
        c_class = pymod['C'].get_object()
        a_var = pymod['a_var'].get_object()
        self.assertEqual(c_class, a_var.get_type())

    def test_static_oi_for_lists_per_object_for_iters(self):
        code = 'class C(object):\n    pass\n' \
               'l = []\nl.append(C())\n' \
               'for c in l:\n    a_var = c\n'
        self.mod.write(code)
        self.pycore.analyze_module(self.mod)
        pymod = self.project.get_pymodule(self.mod)
        c_class = pymod['C'].get_object()
        a_var = pymod['a_var'].get_object()
        self.assertEqual(c_class, a_var.get_type())

    def test_static_oi_for_dicts_depending_on_append_function(self):
        code = 'class C1(object):\n    pass\nclass C2(object):\n    pass\n' \
               'd = {}\nd[C1()] = C2()\na, b = d.popitem()\n'
        self.mod.write(code)
        self.pycore.analyze_module(self.mod)
        pymod = self.project.get_pymodule(self.mod)
        c1_class = pymod['C1'].get_object()
        c2_class = pymod['C2'].get_object()
        a_var = pymod['a'].get_object()
        b_var = pymod['b'].get_object()
        self.assertEqual(c1_class, a_var.get_type())
        self.assertEqual(c2_class, b_var.get_type())

    def test_static_oi_for_dicts_depending_on_for_loops(self):
        code = 'class C1(object):\n    pass\nclass C2(object):\n    pass\n' \
            'd = {}\nd[C1()] = C2()\n' \
            'for k, v in d.items():\n    a = k\n    b = v\n'
        self.mod.write(code)
        self.pycore.analyze_module(self.mod)
        pymod = self.project.get_pymodule(self.mod)
        c1_class = pymod['C1'].get_object()
        c2_class = pymod['C2'].get_object()
        a_var = pymod['a'].get_object()
        b_var = pymod['b'].get_object()
        self.assertEqual(c1_class, a_var.get_type())
        self.assertEqual(c2_class, b_var.get_type())

    def test_static_oi_for_dicts_depending_on_update(self):
        code = 'class C1(object):\n    pass\nclass C2(object):\n    pass\n' \
            'd = {}\nd[C1()] = C2()\n' \
            'd2 = {}\nd2.update(d)\na, b = d2.popitem()\n'
        self.mod.write(code)
        self.pycore.analyze_module(self.mod)
        pymod = self.project.get_pymodule(self.mod)
        c1_class = pymod['C1'].get_object()
        c2_class = pymod['C2'].get_object()
        a_var = pymod['a'].get_object()
        b_var = pymod['b'].get_object()
        self.assertEqual(c1_class, a_var.get_type())
        self.assertEqual(c2_class, b_var.get_type())

    def test_static_oi_for_dicts_depending_on_update_on_seqs(self):
        code = 'class C1(object):\n    pass\nclass C2(object):\n    pass\n' \
               'd = {}\nd.update([(C1(), C2())])\na, b = d.popitem()\n'
        self.mod.write(code)
        self.pycore.analyze_module(self.mod)
        pymod = self.project.get_pymodule(self.mod)
        c1_class = pymod['C1'].get_object()
        c2_class = pymod['C2'].get_object()
        a_var = pymod['a'].get_object()
        b_var = pymod['b'].get_object()
        self.assertEqual(c1_class, a_var.get_type())
        self.assertEqual(c2_class, b_var.get_type())

    def test_static_oi_for_sets_per_object_for_set_item(self):
        code = 'class C(object):\n    pass\ns = set()\n' \
               's.add(C())\na_var = s.pop() \n'
        self.mod.write(code)
        self.pycore.analyze_module(self.mod)
        pymod = self.project.get_pymodule(self.mod)
        c_class = pymod['C'].get_object()
        a_var = pymod['a_var'].get_object()
        self.assertEqual(c_class, a_var.get_type())

    def test_properties_and_calling_get_property(self):
        code = 'class C1(object):\n    pass\n' \
               'class C2(object):\n    c1 = C1()\n' \
               '    def get_c1(self):\n        return self.c1\n' \
               '    p = property(get_c1)\nc2 = C2()\na_var = c2.p\n'
        self.mod.write(code)
        pymod = self.project.get_pymodule(self.mod)
        c1_class = pymod['C1'].get_object()
        a_var = pymod['a_var'].get_object()
        self.assertEqual(c1_class, a_var.get_type())

    def test_soi_on_constructors(self):
        code = 'class C1(object):\n    pass\n' \
               'class C2(object):\n' \
               '    def __init__(self, arg):\n        self.attr = arg\n' \
               'c2 = C2(C1())\na_var = c2.attr'
        self.mod.write(code)
        self.pycore.analyze_module(self.mod)
        pymod = self.project.get_pymodule(self.mod)
        c1_class = pymod['C1'].get_object()
        a_var = pymod['a_var'].get_object()
        self.assertEqual(c1_class, a_var.get_type())

    def test_soi_on_literal_assignment(self):
        code = 'a_var = ""'
        self.mod.write(code)
        self.pycore.analyze_module(self.mod)
        pymod = self.project.get_pymodule(self.mod)
        a_var = pymod['a_var'].get_object()
        self.assertEqual(Str, type(a_var.get_type()))

    @testutils.only_for_versions_higher('3.6')
    def test_soi_on_typed_assignment(self):
        code = 'a_var: str'
        self.mod.write(code)
        self.pycore.analyze_module(self.mod)
        pymod = self.project.get_pymodule(self.mod)
        a_var = pymod['a_var'].get_object()
        self.assertEqual(Str, type(a_var.get_type()))

    def test_not_saving_unknown_function_returns(self):
        mod2 = testutils.create_module(self.project, 'mod2')
        self.mod.write('class C(object):\n    pass\nl = []\nl.append(C())\n')
        mod2.write('import mod\ndef f():\n    '
                   'return mod.l.pop()\na_var = f()\n')
        pymod = self.project.get_pymodule(self.mod)
        pymod2 = self.project.get_pymodule(mod2)
        c_class = pymod['C'].get_object()
        a_var = pymod2['a_var']

        self.pycore.analyze_module(mod2)
        self.assertNotEqual(c_class, a_var.get_object().get_type())

        self.pycore.analyze_module(self.mod)
        self.assertEqual(c_class, a_var.get_object().get_type())

    def test_using_the_best_callinfo(self):
        code = 'class C1(object):\n    pass\n' \
               'def f(arg1, arg2, arg3):\n    pass\n' \
               'f("", None, C1())\nf("", C1(), None)\n'
        self.mod.write(code)
        self.pycore.analyze_module(self.mod)
        pymod = self.project.get_pymodule(self.mod)
        c1_class = pymod['C1'].get_object()
        f_scope = pymod['f'].get_object().get_scope()
        arg2 = f_scope['arg2'].get_object()
        self.assertEqual(c1_class, arg2.get_type())

    def test_call_function_and_parameters(self):
        code = 'class A(object):\n    def __call__(self, p):\n        pass\n' \
               'A()("")\n'
        self.mod.write(code)
        self.pycore.analyze_module(self.mod)
        scope = self.project.get_pymodule(self.mod).get_scope()
        p_object = scope.get_scopes()[0].get_scopes()[0]['p'].get_object()
        self.assertTrue(isinstance(p_object.get_type(),
                                   rope.base.builtins.Str))

    def test_report_change_in_libutils(self):
        self.project.prefs['automatic_soa'] = True
        code = 'class C(object):\n    pass\ndef f(p):\n    pass\nf(C())\n'
        with open(self.mod.real_path, 'w') as mod_file:
            mod_file.write(code)

        rope.base.libutils.report_change(self.project, self.mod.real_path, '')
        pymod = self.project.get_pymodule(self.mod)
        c_class = pymod['C'].get_object()
        f_scope = pymod['f'].get_object().get_scope()
        p_type = f_scope['p'].get_object().get_type()
        self.assertEqual(c_class, p_type)

    def test_report_libutils_and_analyze_all_modules(self):
        code = 'class C(object):\n    pass\ndef f(p):\n    pass\nf(C())\n'
        self.mod.write(code)
        rope.base.libutils.analyze_modules(self.project)
        pymod = self.project.get_pymodule(self.mod)
        c_class = pymod['C'].get_object()
        f_scope = pymod['f'].get_object().get_scope()
        p_type = f_scope['p'].get_object().get_type()
        self.assertEqual(c_class, p_type)

    def test_validation_problems_for_objectdb_retrievals(self):
        mod1 = testutils.create_module(self.project, 'mod1')
        mod2 = testutils.create_module(self.project, 'mod2')
        mod1.write('l = []\nvar = l.pop()\n')
        mod2.write('import mod1\n\nclass C(object):\n    pass\n'
                   'mod1.l.append(C())\n')
        self.pycore.analyze_module(mod2)

        pymod2 = self.project.get_pymodule(mod2)
        c_class = pymod2['C'].get_object()
        pymod1 = self.project.get_pymodule(mod1)
        var_pyname = pymod1['var']
        self.assertEqual(c_class, var_pyname.get_object().get_type())
        mod2.write('import mod1\n\nmod1.l.append("")\n')
        self.assertNotEqual(c_class, var_pyname.get_object().get_type(),
                             'Class `C` no more exists')

    def test_validation_problems_for_changing_builtin_types(self):
        mod1 = testutils.create_module(self.project, 'mod1')
        mod1.write('l = []\nl.append("")\n')
        self.pycore.analyze_module(mod1)

        mod1.write('l = {}\nv = l["key"]\n')
        pymod1 = self.project.get_pymodule(mod1)  # noqa
        var = pymod1['v'].get_object()  # noqa

    def test_always_returning_containing_class_for_selfs(self):
        code = 'class A(object):\n    def f(p):\n        return p\n' \
               'class B(object):\n    pass\nb = B()\nb.f()\n'
        self.mod.write(code)
        self.pycore.analyze_module(self.mod)
        pymod = self.project.get_pymodule(self.mod)
        a_class = pymod['A'].get_object()
        f_scope = a_class.get_scope().get_scopes()[0]
        p_type = f_scope['p'].get_object().get_type()
        self.assertEqual(a_class, p_type)

    def test_following_function_calls_when_asked_to(self):
        code = 'class A(object):\n    pass\n' \
               'class C(object):\n' \
               '    def __init__(self, arg):\n' \
               '        self.attr = arg\n' \
               'def f(p):\n    return C(p)\n' \
               'c = f(A())\nx = c.attr\n'
        self.mod.write(code)
        self.pycore.analyze_module(self.mod, followed_calls=1)
        pymod = self.project.get_pymodule(self.mod)
        a_class = pymod['A'].get_object()
        x_var = pymod['x'].get_object().get_type()
        self.assertEqual(a_class, x_var)


def suite():
    result = unittest.TestSuite()
    result.addTests(unittest.makeSuite(DynamicOITest))
    result.addTests(unittest.makeSuite(NewStaticOITest))
    return result


if __name__ == '__main__':
    unittest.main()
