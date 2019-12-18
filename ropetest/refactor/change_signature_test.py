try:
    import unittest2 as unittest
except ImportError:
    import unittest

import rope.base.exceptions
from rope.refactor import change_signature
from ropetest import testutils


class ChangeSignatureTest(unittest.TestCase):

    def setUp(self):
        super(ChangeSignatureTest, self).setUp()
        self.project = testutils.sample_project()
        self.pycore = self.project.pycore
        self.mod = testutils.create_module(self.project, 'mod')

    def tearDown(self):
        testutils.remove_project(self.project)
        super(ChangeSignatureTest, self).tearDown()

    def test_normalizing_parameters_for_trivial_case(self):
        code = 'def a_func():\n    pass\na_func()'
        self.mod.write(code)
        signature = change_signature.ChangeSignature(
            self.project, self.mod, self.mod.read().index('a_func') + 1)
        self.project.do(signature.get_changes(
            [change_signature.ArgumentNormalizer()]))
        self.assertEqual(code, self.mod.read())

    def test_normalizing_parameters_for_trivial_case2(self):
        code = 'def a_func(param):\n    pass\na_func(2)'
        self.mod.write(code)
        signature = change_signature.ChangeSignature(
            self.project, self.mod, self.mod.read().index('a_func') + 1)
        self.project.do(signature.get_changes(
            [change_signature.ArgumentNormalizer()]))
        self.assertEqual(code, self.mod.read())

    def test_normalizing_parameters_for_unneeded_keyword(self):
        self.mod.write('def a_func(param):\n    pass\na_func(param=1)')
        signature = change_signature.ChangeSignature(
            self.project, self.mod, self.mod.read().index('a_func') + 1)
        self.project.do(signature.get_changes(
            [change_signature.ArgumentNormalizer()]))
        self.assertEqual('def a_func(param):\n    pass\na_func(1)',
                          self.mod.read())

    def test_normalizing_parameters_for_unneeded_keyword_for_methods(self):
        code = 'class A(object):\n' \
               '    def a_func(self, param):\n' \
               '        pass\n' \
               'a_var = A()\n' \
               'a_var.a_func(param=1)\n'
        self.mod.write(code)
        signature = change_signature.ChangeSignature(
            self.project, self.mod, self.mod.read().index('a_func') + 1)
        self.project.do(signature.get_changes(
            [change_signature.ArgumentNormalizer()]))
        expected = 'class A(object):\n' \
                   '    def a_func(self, param):\n' \
                   '        pass\n' \
                   'a_var = A()\n' \
                   'a_var.a_func(1)\n'
        self.assertEqual(expected, self.mod.read())

    def test_normalizing_parameters_for_unsorted_keyword(self):
        self.mod.write('def a_func(p1, p2):\n    pass\na_func(p2=2, p1=1)')
        signature = change_signature.ChangeSignature(
            self.project, self.mod, self.mod.read().index('a_func') + 1)
        self.project.do(signature.get_changes(
            [change_signature.ArgumentNormalizer()]))
        self.assertEqual('def a_func(p1, p2):\n    pass\na_func(1, 2)',
                          self.mod.read())

    def test_raising_exceptions_for_non_functions(self):
        self.mod.write('a_var = 10')
        with self.assertRaises(rope.base.exceptions.RefactoringError):
            change_signature.ChangeSignature(
                self.project, self.mod, self.mod.read().index('a_var') + 1)

    def test_normalizing_parameters_for_args_parameter(self):
        self.mod.write('def a_func(*arg):\n    pass\na_func(1, 2)\n')
        signature = change_signature.ChangeSignature(
            self.project, self.mod, self.mod.read().index('a_func') + 1)
        self.project.do(signature.get_changes(
            [change_signature.ArgumentNormalizer()]))
        self.assertEqual('def a_func(*arg):\n    pass\na_func(1, 2)\n',
                          self.mod.read())

    def test_normalizing_parameters_for_args_parameter_and_keywords(self):
        self.mod.write(
            'def a_func(param, *args):\n    pass\na_func(*[1, 2, 3])\n')
        signature = change_signature.ChangeSignature(
            self.project, self.mod, self.mod.read().index('a_func') + 1)
        self.project.do(signature.get_changes(
            [change_signature.ArgumentNormalizer()]))
        self.assertEqual('def a_func(param, *args):\n    pass\n'
                          'a_func(*[1, 2, 3])\n', self.mod.read())

    def test_normalizing_functions_from_other_modules(self):
        mod1 = testutils.create_module(self.project, 'mod1')
        mod1.write('def a_func(param):\n    pass\n')
        self.mod.write('import mod1\nmod1.a_func(param=1)\n')
        signature = change_signature.ChangeSignature(
            self.project, mod1, mod1.read().index('a_func') + 1)
        self.project.do(signature.get_changes(
            [change_signature.ArgumentNormalizer()]))
        self.assertEqual('import mod1\nmod1.a_func(1)\n', self.mod.read())

    def test_normalizing_parameters_for_keyword_parameters(self):
        self.mod.write('def a_func(p1, **kwds):\n    pass\n'
                       'a_func(p2=2, p1=1)\n')
        signature = change_signature.ChangeSignature(
            self.project, self.mod, self.mod.read().index('a_func') + 1)
        self.project.do(signature.get_changes(
            [change_signature.ArgumentNormalizer()]))
        self.assertEqual('def a_func(p1, **kwds):\n    pass\n'
                          'a_func(1, p2=2)\n', self.mod.read())

    def test_removing_arguments(self):
        self.mod.write('def a_func(p1):\n    pass\na_func(1)\n')
        signature = change_signature.ChangeSignature(
            self.project, self.mod, self.mod.read().index('a_func') + 1)
        self.project.do(signature.get_changes(
            [change_signature.ArgumentRemover(0)]))
        self.assertEqual('def a_func():\n    pass\na_func()\n',
                          self.mod.read())

    def test_removing_arguments_with_multiple_args(self):
        self.mod.write('def a_func(p1, p2):\n    pass\na_func(1, 2)\n')
        signature = change_signature.ChangeSignature(
            self.project, self.mod, self.mod.read().index('a_func') + 1)
        self.project.do(signature.get_changes(
            [change_signature.ArgumentRemover(0)]))
        self.assertEqual('def a_func(p2):\n    pass\na_func(2)\n',
                          self.mod.read())

    def test_removing_arguments_passed_as_keywords(self):
        self.mod.write('def a_func(p1):\n    pass\na_func(p1=1)\n')
        signature = change_signature.ChangeSignature(
            self.project, self.mod, self.mod.read().index('a_func') + 1)
        self.project.do(signature.get_changes(
            [change_signature.ArgumentRemover(0)]))
        self.assertEqual('def a_func():\n    pass\na_func()\n',
                          self.mod.read())

    def test_removing_arguments_with_defaults(self):
        self.mod.write('def a_func(p1=1):\n    pass\na_func(1)\n')
        signature = change_signature.ChangeSignature(
            self.project, self.mod, self.mod.read().index('a_func') + 1)
        self.project.do(signature.get_changes(
            [change_signature.ArgumentRemover(0)]))
        self.assertEqual('def a_func():\n    pass\na_func()\n',
                          self.mod.read())

    def test_removing_arguments_star_args(self):
        self.mod.write('def a_func(p1, *args):\n    pass\na_func(1)\n')
        signature = change_signature.ChangeSignature(
            self.project, self.mod, self.mod.read().index('a_func') + 1)
        self.project.do(signature.get_changes(
            [change_signature.ArgumentRemover(1)]))
        self.assertEqual('def a_func(p1):\n    pass\na_func(1)\n',
                          self.mod.read())

    def test_removing_keyword_arg(self):
        self.mod.write('def a_func(p1, **kwds):\n    pass\na_func(1)\n')
        signature = change_signature.ChangeSignature(
            self.project, self.mod, self.mod.read().index('a_func') + 1)
        self.project.do(signature.get_changes(
            [change_signature.ArgumentRemover(1)]))
        self.assertEqual('def a_func(p1):\n    pass\na_func(1)\n',
                          self.mod.read())

    def test_removing_keyword_arg2(self):
        self.mod.write('def a_func(p1, *args, **kwds):\n    pass\na_func(1)\n')
        signature = change_signature.ChangeSignature(
            self.project, self.mod, self.mod.read().index('a_func') + 1)
        self.project.do(signature.get_changes(
            [change_signature.ArgumentRemover(2)]))
        self.assertEqual('def a_func(p1, *args):\n    pass\na_func(1)\n',
                          self.mod.read())

    # XXX: What to do here for star args?
    @unittest.skip("How to deal with start args?")
    def xxx_test_removing_arguments_star_args2(self):
        self.mod.write('def a_func(p1, *args):\n    pass\n'
                       'a_func(2, 3, p1=1)\n')
        signature = change_signature.ChangeSignature(
            self.project, self.mod, self.mod.read().index('a_func') + 1)
        self.project.do(signature.get_changes(
            [change_signature.ArgumentRemover(1)]))
        self.assertEqual('def a_func(p1):\n    pass\na_func(p1=1)\n',
                          self.mod.read())

    # XXX: What to do here for star args?
    def xxx_test_removing_arguments_star_args3(self):
        self.mod.write('def a_func(p1, *args):\n    pass\n'
                       'a_func(*[1, 2, 3])\n')
        signature = change_signature.ChangeSignature(
            self.project, self.mod, self.mod.read().index('a_func') + 1)
        self.project.do(signature.get_changes(
            [change_signature.ArgumentRemover(1)]))
        self.assertEqual('def a_func(p1):\n    pass\na_func(*[1, 2, 3])\n',
                          self.mod.read())

    def test_adding_arguments_for_normal_args_changing_definition(self):
        self.mod.write('def a_func():\n    pass\n')
        signature = change_signature.ChangeSignature(
            self.project, self.mod, self.mod.read().index('a_func') + 1)
        self.project.do(signature.get_changes(
            [change_signature.ArgumentAdder(0, 'p1')]))
        self.assertEqual('def a_func(p1):\n    pass\n', self.mod.read())

    def test_adding_arguments_for_normal_args_with_defaults(self):
        self.mod.write('def a_func():\n    pass\na_func()\n')
        signature = change_signature.ChangeSignature(
            self.project, self.mod, self.mod.read().index('a_func') + 1)
        adder = change_signature.ArgumentAdder(0, 'p1', 'None')
        self.project.do(signature.get_changes([adder]))
        self.assertEqual('def a_func(p1=None):\n    pass\na_func()\n',
                          self.mod.read())

    def test_adding_arguments_for_normal_args_changing_calls(self):
        self.mod.write('def a_func():\n    pass\na_func()\n')
        signature = change_signature.ChangeSignature(
            self.project, self.mod, self.mod.read().index('a_func') + 1)
        adder = change_signature.ArgumentAdder(0, 'p1', 'None', '1')
        self.project.do(signature.get_changes([adder]))
        self.assertEqual('def a_func(p1=None):\n    pass\na_func(1)\n',
                          self.mod.read())

    def test_adding_arguments_for_norm_args_chang_calls_with_kwords(self):
        self.mod.write('def a_func(p1=0):\n    pass\na_func()\n')
        signature = change_signature.ChangeSignature(
            self.project, self.mod, self.mod.read().index('a_func') + 1)
        adder = change_signature.ArgumentAdder(1, 'p2', '0', '1')
        self.project.do(signature.get_changes([adder]))
        self.assertEqual('def a_func(p1=0, p2=0):\n    pass\na_func(p2=1)\n',
                          self.mod.read())

    def test_adding_arguments_for_norm_args_chang_calls_with_no_value(self):
        self.mod.write('def a_func(p2=0):\n    pass\na_func(1)\n')
        signature = change_signature.ChangeSignature(
            self.project, self.mod, self.mod.read().index('a_func') + 1)
        adder = change_signature.ArgumentAdder(0, 'p1', '0', None)
        self.project.do(signature.get_changes([adder]))
        self.assertEqual('def a_func(p1=0, p2=0):\n    pass\na_func(p2=1)\n',
                          self.mod.read())

    def test_adding_duplicate_parameter_and_raising_exceptions(self):
        self.mod.write('def a_func(p1):\n    pass\n')
        with self.assertRaises(rope.base.exceptions.RefactoringError):
            signature = change_signature.ChangeSignature(
                self.project, self.mod, self.mod.read().index('a_func') + 1)
            self.project.do(signature.get_changes(
                [change_signature.ArgumentAdder(1, 'p1')]))

    def test_inlining_default_arguments(self):
        self.mod.write('def a_func(p1=0):\n    pass\na_func()\n')
        signature = change_signature.ChangeSignature(
            self.project, self.mod, self.mod.read().index('a_func') + 1)
        self.project.do(signature.get_changes(
            [change_signature.ArgumentDefaultInliner(0)]))
        self.assertEqual('def a_func(p1=0):\n    pass\n'
                          'a_func(0)\n', self.mod.read())

    def test_inlining_default_arguments2(self):
        self.mod.write('def a_func(p1=0):\n    pass\na_func(1)\n')
        signature = change_signature.ChangeSignature(
            self.project, self.mod, self.mod.read().index('a_func') + 1)
        self.project.do(signature.get_changes(
            [change_signature.ArgumentDefaultInliner(0)]))
        self.assertEqual('def a_func(p1=0):\n    pass\n'
                          'a_func(1)\n', self.mod.read())

    def test_preserving_args_and_keywords_order(self):
        self.mod.write('def a_func(*args, **kwds):\n    pass\n'
                       'a_func(3, 1, 2, a=1, c=3, b=2)\n')
        signature = change_signature.ChangeSignature(
            self.project, self.mod, self.mod.read().index('a_func') + 1)
        self.project.do(signature.get_changes(
            [change_signature.ArgumentNormalizer()]))
        self.assertEqual('def a_func(*args, **kwds):\n    pass\n'
                          'a_func(3, 1, 2, a=1, c=3, b=2)\n', self.mod.read())

    def test_change_order_for_only_one_parameter(self):
        self.mod.write('def a_func(p1):\n    pass\na_func(1)\n')
        signature = change_signature.ChangeSignature(
            self.project, self.mod, self.mod.read().index('a_func') + 1)
        self.project.do(signature.get_changes(
            [change_signature.ArgumentReorderer([0])]))
        self.assertEqual('def a_func(p1):\n    pass\na_func(1)\n',
                          self.mod.read())

    def test_change_order_for_two_parameter(self):
        self.mod.write('def a_func(p1, p2):\n    pass\na_func(1, 2)\n')
        signature = change_signature.ChangeSignature(
            self.project, self.mod, self.mod.read().index('a_func') + 1)
        self.project.do(signature.get_changes(
            [change_signature.ArgumentReorderer([1, 0])]))
        self.assertEqual('def a_func(p2, p1):\n    pass\na_func(2, 1)\n',
                          self.mod.read())

    def test_reordering_multi_line_function_headers(self):
        self.mod.write('def a_func(p1,\n p2):\n    pass\na_func(1, 2)\n')
        signature = change_signature.ChangeSignature(
            self.project, self.mod, self.mod.read().index('a_func') + 1)
        self.project.do(signature.get_changes(
            [change_signature.ArgumentReorderer([1, 0])]))
        self.assertEqual('def a_func(p2, p1):\n    pass\na_func(2, 1)\n',
                          self.mod.read())

    def test_changing_order_with_static_params(self):
        self.mod.write('def a_func(p1, p2=0, p3=0):\n    pass\na_func(1, 2)\n')
        signature = change_signature.ChangeSignature(
            self.project, self.mod, self.mod.read().index('a_func') + 1)
        self.project.do(signature.get_changes(
            [change_signature.ArgumentReorderer([0, 2, 1])]))
        self.assertEqual('def a_func(p1, p3=0, p2=0):\n    pass\n'
                          'a_func(1, p2=2)\n', self.mod.read())

    def test_doing_multiple_changes(self):
        changers = []
        self.mod.write('def a_func(p1):\n    pass\na_func(1)\n')
        changers.append(change_signature.ArgumentRemover(0))
        changers.append(change_signature.ArgumentAdder(0, 'p2', None, None))
        signature = change_signature.ChangeSignature(
            self.project, self.mod, self.mod.read().index('a_func') + 1)
        signature.get_changes(changers).do()
        self.assertEqual('def a_func(p2):\n    pass\na_func()\n',
                          self.mod.read())

    def test_doing_multiple_changes2(self):
        changers = []
        self.mod.write('def a_func(p1, p2):\n    pass\na_func(p2=2)\n')
        changers.append(change_signature.ArgumentAdder(2, 'p3', None, '3'))
        changers.append(change_signature.ArgumentReorderer([1, 0, 2]))
        changers.append(change_signature.ArgumentRemover(1))
        signature = change_signature.ChangeSignature(
            self.project, self.mod, self.mod.read().index('a_func') + 1)
        signature.get_changes(changers).do()
        self.assertEqual('def a_func(p2, p3):\n    pass\na_func(2, 3)\n',
                          self.mod.read())

    def test_changing_signature_in_subclasses(self):
        self.mod.write(
            'class A(object):\n    def a_method(self):\n        pass\n'
            'class B(A):\n    def a_method(self):\n        pass\n')
        signature = change_signature.ChangeSignature(
            self.project, self.mod, self.mod.read().index('a_method') + 1)
        signature.get_changes([change_signature.ArgumentAdder(1, 'p1')],
                              in_hierarchy=True).do()
        self.assertEqual(
            'class A(object):\n    def a_method(self, p1):\n        pass\n'
            'class B(A):\n    def a_method(self, p1):\n        pass\n',
            self.mod.read())

    def test_differentiating_class_accesses_from_instance_accesses(self):
        self.mod.write(
            'class A(object):\n    def a_func(self, param):\n        pass\n'
            'a_var = A()\nA.a_func(a_var, param=1)')
        signature = change_signature.ChangeSignature(
            self.project, self.mod, self.mod.read().index('a_func') + 1)
        self.project.do(signature.get_changes(
            [change_signature.ArgumentRemover(1)]))
        self.assertEqual(
            'class A(object):\n    def a_func(self):\n        pass\n'
            'a_var = A()\nA.a_func(a_var)', self.mod.read())

    def test_changing_signature_for_constructors(self):
        self.mod.write(
            'class C(object):\n    def __init__(self, p):\n        pass\n'
            'c = C(1)\n')
        signature = change_signature.ChangeSignature(
            self.project, self.mod, self.mod.read().index('C') + 1)
        signature.get_changes([change_signature.ArgumentRemover(1)]).do()
        self.assertEqual(
            'class C(object):\n    def __init__(self):\n        pass\n'
            'c = C()\n',
            self.mod.read())

    def test_changing_signature_for_constructors2(self):
        self.mod.write(
            'class C(object):\n    def __init__(self, p):\n        pass\n'
            'c = C(1)\n')
        signature = change_signature.ChangeSignature(
            self.project, self.mod, self.mod.read().index('__init__') + 1)
        signature.get_changes([change_signature.ArgumentRemover(1)]).do()
        self.assertEqual(
            'class C(object):\n    def __init__(self):\n        pass\n'
            'c = C()\n',
            self.mod.read())

    def test_changing_signature_for_constructors_when_using_super(self):
        self.mod.write(
            'class A(object):\n    def __init__(self, p):\n        pass\n'
            'class B(A):\n    '
            'def __init__(self, p):\n        super(B, self).__init__(p)\n')
        signature = change_signature.ChangeSignature(
            self.project, self.mod, self.mod.read().index('__init__') + 1)
        signature.get_changes([change_signature.ArgumentRemover(1)]).do()
        self.assertEqual(
            'class A(object):\n    def __init__(self):\n        pass\n'
            'class B(A):\n    '
            'def __init__(self, p):\n        super(B, self).__init__()\n',
            self.mod.read())

    def test_redordering_arguments_reported_by_mft(self):
        self.mod.write('def f(a, b, c):\n    pass\nf(1, 2, 3)\n')
        signature = change_signature.ChangeSignature(
            self.project, self.mod, self.mod.read().rindex('f'))
        signature.get_changes(
            [change_signature.ArgumentReorderer([1, 2, 0])]).do()
        self.assertEqual('def f(b, c, a):\n    pass\nf(2, 3, 1)\n',
                          self.mod.read())

    def test_resources_parameter(self):
        mod1 = testutils.create_module(self.project, 'mod1')
        mod1.write('def a_func(param):\n    pass\n')
        self.mod.write('import mod1\nmod1.a_func(1)\n')
        signature = change_signature.ChangeSignature(
            self.project, mod1, mod1.read().index('a_func') + 1)
        signature.get_changes([change_signature.ArgumentRemover(0)],
                              resources=[mod1]).do()
        self.assertEqual('import mod1\nmod1.a_func(1)\n', self.mod.read())
        self.assertEqual('def a_func():\n    pass\n', mod1.read())

    def test_reordering_and_automatic_defaults(self):
        code = 'def f(p1, p2=2):\n' \
               '    pass\n' \
               'f(1, 2)\n'
        self.mod.write(code)
        signature = change_signature.ChangeSignature(
            self.project, self.mod, code.index('f('))
        reorder = change_signature.ArgumentReorderer([1, 0], autodef='1')
        signature.get_changes([reorder]).do()
        expected = 'def f(p2=2, p1=1):\n' \
                   '    pass\n' \
                   'f(2, 1)\n'
        self.assertEqual(expected, self.mod.read())


if __name__ == '__main__':
    unittest.main()
