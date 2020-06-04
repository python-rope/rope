try:
    import unittest2 as unittest
except ImportError:
    import unittest


from rope.contrib.codeassist import code_assist
from rope.base.oi.type_hinting import evaluate
from ropetest import testutils


class AbstractHintingTest(unittest.TestCase):

    def setUp(self):
        super(AbstractHintingTest, self).setUp()
        self.project = testutils.sample_project()

    def tearDown(self):
        testutils.remove_project(self.project)
        super(AbstractHintingTest, self).tearDown()

    def _assist(self, code, offset=None, resource=None, **kwds):
        if offset is None:
            offset = len(code)
        return code_assist(self.project, code, offset, resource, **kwds)

    def assert_completion_in_result(self, name, scope, result):
        for proposal in result:
            if proposal.name == name and proposal.scope == scope:
                return
        self.fail('completion <%s> in scope %r not proposed, available names: %r' % (
            name,
            scope,
            [(i.name, i.scope) for i in result]
        ))

    def assert_completion_not_in_result(self, name, scope, result):
        for proposal in result:
            if proposal.name == name and proposal.scope == scope:
                self.fail('completion <%s> was proposed' % name)

    def run(self, result=None):
        if self.__class__.__name__.startswith('Abstract'):
            return
        super(AbstractHintingTest, self).run(result)


class DocstringParamHintingTest(AbstractHintingTest):

    def test_hint_param(self):
        code = 'class Sample(object):\n' \
               '    def a_method(self, a_arg):\n' \
               '        """:type a_arg: threading.Thread"""\n' \
               '        a_arg.is_a'
        result = self._assist(code)
        self.assert_completion_in_result('is_alive', 'attribute', result)

    def test_hierarchical_hint_param(self):
        code = 'class ISample(object):\n' \
               '    def a_method(self, a_arg):\n' \
               '        """:type a_arg: threading.Thread"""\n' \
               '\n\n' \
               'class Sample(ISample):\n' \
               '    def a_method(self, a_arg):\n' \
               '        a_arg.is_a'
        result = self._assist(code)
        self.assert_completion_in_result('is_alive', 'attribute', result)


class DocstringReturnHintingTest(AbstractHintingTest):

    def test_hierarchical_hint_rtype(self):
        code = 'class ISample(object):\n' \
               '    def b_method(self):\n' \
               '        """:rtype: threading.Thread"""\n' \
               '\n\n' \
               'class Sample(ISample):\n' \
               '    def b_method(self):\n' \
               '        pass\n' \
               '    def a_method(self):\n' \
               '        self.b_method().is_a'
        result = self._assist(code)
        self.assert_completion_in_result('is_alive', 'attribute', result)


class AbstractAssignmentHintingTest(AbstractHintingTest):

    def _make_class_hint(self, type_str):
        raise NotImplementedError

    def _make_constructor_hint(self, type_str):
        raise NotImplementedError

    def test_hint_attr(self):
        code = 'class Sample(object):\n' \
               + self._make_class_hint('threading.Thread') + \
               '    def a_method(self):\n' \
               '        self.a_attr.is_a'
        result = self._assist(code)
        self.assert_completion_in_result('is_alive', 'attribute', result)

    def test_hierarchical_hint_attr(self):
        code = 'class ISample(object):\n' \
               + self._make_class_hint('threading.Thread') + \
               '\n\n' \
               'class Sample(ISample):\n' \
               '    a_attr = None\n'\
               '    def a_method(self):\n' \
               '        self.a_attr.is_a'
        result = self._assist(code)
        self.assert_completion_in_result('is_alive', 'attribute', result)

    def test_hint_defined_by_constructor(self):
        code = 'class Sample(object):\n' \
               '    def __init__(self, arg):\n' \
               + self._make_constructor_hint('threading.Thread') + \
               '    def a_method(self):\n' \
               '        self.a_attr.is_a'
        result = self._assist(code)
        self.assert_completion_in_result('is_alive', 'attribute', result)

    def test_hint_attr_redefined_by_constructor(self):
        code = 'class Sample(object):\n' \
               + self._make_class_hint('threading.Thread') + \
               '    def __init__(self):\n' \
               '        self.a_attr = None\n' \
               '    def a_method(self):\n' \
               '        self.a_attr.is_a'
        result = self._assist(code)
        self.assert_completion_in_result('is_alive', 'attribute', result)

    def test_hierarchical_hint_attr_redefined_by_constructor(self):
        code = 'class ISample(object):\n' \
               + self._make_class_hint('threading.Thread') + \
               '\n\n' \
               'class Sample(ISample):\n' \
               '    def __init__(self):\n' \
               '        self.a_attr = None\n' \
               '    def a_method(self):\n' \
               '        self.a_attr.is_a'
        result = self._assist(code)
        self.assert_completion_in_result('is_alive', 'attribute', result)

    def test_hint_attr_for_pre_defined_type(self):
        code = 'class Other(object):\n' \
               '    def is_alive(self):\n' \
               '        pass\n' \
               '\n\n' \
               'class Sample(object):\n' \
               + self._make_class_hint('Other') + \
               '    def a_method(self):\n' \
               '        self.a_attr.is_a'
        result = self._assist(code)
        self.assert_completion_in_result('is_alive', 'attribute', result)

    def test_hint_attr_for_post_defined_type(self):
        code = 'class Sample(object):\n' \
               + self._make_class_hint('Other') + \
               '    def a_method(self):\n' \
               '        self.a_attr.is_a'
        offset = len(code)
        code += '\n\n' \
                'class Other(object):\n' \
                '    def is_alive(self):\n' \
                '        pass\n'
        result = self._assist(code, offset)
        self.assert_completion_in_result('is_alive', 'attribute', result)

    def test_hint_parametrized_list(self):
        code = 'class Sample(object):\n' \
               + self._make_class_hint('list[threading.Thread]') + \
               '    def a_method(self):\n' \
               '        for i in self.a_attr:\n' \
               '            i.is_a'
        result = self._assist(code)
        self.assert_completion_in_result('is_alive', 'attribute', result)

    def test_hint_parametrized_tuple(self):
        code = 'class Sample(object):\n' \
               + self._make_class_hint('tuple[threading.Thread]') + \
               '    def a_method(self):\n' \
               '        for i in self.a_attr:\n' \
               '            i.is_a'
        result = self._assist(code)
        self.assert_completion_in_result('is_alive', 'attribute', result)

    def test_hint_parametrized_set(self):
        code = 'class Sample(object):\n' \
               + self._make_class_hint('set[threading.Thread]') + \
               '    def a_method(self):\n' \
               '        for i in self.a_attr:\n' \
               '            i.is_a'
        result = self._assist(code)
        self.assert_completion_in_result('is_alive', 'attribute', result)

    def test_hint_parametrized_iterable(self):
        code = 'class Sample(object):\n' \
               + self._make_class_hint('collections.Iterable[threading.Thread]') + \
               '    def a_method(self):\n' \
               '        for i in self.a_attr:\n' \
               '            i.is_a'
        result = self._assist(code)
        self.assert_completion_in_result('is_alive', 'attribute', result)

    def test_hint_parametrized_iterator(self):
        code = 'class Sample(object):\n' \
               + self._make_class_hint('collections.Iterator[threading.Thread]') + \
               '    def a_method(self):\n' \
               '        for i in self.a_attr:\n' \
               '            i.is_a'
        result = self._assist(code)
        self.assert_completion_in_result('is_alive', 'attribute', result)

    def test_hint_parametrized_dict_key(self):
        code = 'class Sample(object):\n' \
               + self._make_class_hint('dict[str, threading.Thread]') + \
               '    def a_method(self):\n' \
               '        for i in self.a_attr.keys():\n' \
               '            i.sta'
        result = self._assist(code)
        self.assert_completion_in_result('startswith', 'builtin', result)

    def test_hint_parametrized_dict_value(self):
        code = 'class Sample(object):\n' \
               + self._make_class_hint('dict[str, threading.Thread]') + \
               '    def a_method(self):\n' \
               '        for i in self.a_attr.values():\n' \
               '            i.is_a'
        result = self._assist(code)
        self.assert_completion_in_result('is_alive', 'attribute', result)

    def test_hint_parametrized_nested_tuple_list(self):
        code = 'class Sample(object):\n' \
               + self._make_class_hint('tuple[list[threading.Thread]]') + \
               '    def a_method(self):\n' \
               '        for j in self.a_attr:\n' \
               '            for i in j:\n' \
               '                i.is_a'
        result = self._assist(code)
        self.assert_completion_in_result('is_alive', 'attribute', result)

    def test_hint_or(self):
        code = 'class Sample(object):\n' \
               + self._make_class_hint('str | threading.Thread') + \
               '    def a_method(self):\n' \
               '        for i in self.a_attr.values():\n' \
               '            i.is_a'
        result = self._assist(code)
        # Be sure, there isn't errors currently
        # self.assert_completion_in_result('is_alive', 'attribute', result)

    def test_hint_nonexistent(self):
        code = 'class Sample(object):\n' \
               + self._make_class_hint('sdfdsf.asdfasdf.sdfasdf.Dffg') + \
               '    def a_method(self):\n' \
               '        for i in self.a_attr.values():\n' \
               '            i.is_a'
        self._assist(code)

    def test_hint_invalid_syntax(self):
        code = 'class Sample(object):\n' \
               + self._make_class_hint('sdf | & # &*') + \
               '    def a_method(self):\n' \
               '        for i in self.a_attr.values():\n' \
               '            i.is_a'
        self._assist(code)


class DocstringNoneAssignmentHintingTest(AbstractAssignmentHintingTest):

    def _make_class_hint(self, type_str):
        return '    """:type a_attr: ' + type_str + '"""\n' \
               '    a_attr = None\n'

    def _make_constructor_hint(self, type_str):
        return '        """:type arg: ' + type_str + '"""\n' \
               '        self.a_attr = arg\n'


class DocstringNotImplementedAssignmentHintingTest(AbstractAssignmentHintingTest):

    def _make_class_hint(self, type_str):
        return '    """:type a_attr: ' + type_str + '"""\n' \
               '    a_attr = NotImplemented\n'

    def _make_constructor_hint(self, type_str):
        return '        """:type arg: ' + type_str + '"""\n' \
               '        self.a_attr = arg\n'



class PEP0484CommentNoneAssignmentHintingTest(AbstractAssignmentHintingTest):

    def _make_class_hint(self, type_str):
        return '    a_attr = None  # type: ' + type_str + '\n'

    def _make_constructor_hint(self, type_str):
        return '        self.a_attr = None  # type: ' + type_str + '\n'


class PEP0484CommentNotImplementedAssignmentHintingTest(AbstractAssignmentHintingTest):

    def _make_class_hint(self, type_str):
        return '    a_attr = NotImplemented  # type: ' + type_str + '\n'

    def _make_constructor_hint(self, type_str):
        return '        self.a_attr = NotImplemented  # type: ' + type_str + '\n'


class EvaluateTest(unittest.TestCase):

    def test_parser(self):
        tests = [
            ("Foo",
             "(name Foo)"),
            ("mod1.Foo",
             "(name mod1.Foo)"),
            ("mod1.mod2.Foo",
             "(name mod1.mod2.Foo)"),
            ("Foo[Bar]",
             "('[' (name Foo) [(name Bar)])"),
            ("Foo[Bar1, Bar2, Bar3]",
             "('[' (name Foo) [(name Bar1), (name Bar2), (name Bar3)])"),
            ("Foo[Bar[Baz]]",
             "('[' (name Foo) [('[' (name Bar) [(name Baz)])])"),
            ("Foo[Bar1[Baz1], Bar2[Baz2]]",
             "('[' (name Foo) [('[' (name Bar1) [(name Baz1)]), ('[' (name Bar2) [(name Baz2)])])"),
            ("mod1.mod2.Foo[Bar]",
             "('[' (name mod1.mod2.Foo) [(name Bar)])"),
            ("mod1.mod2.Foo[mod1.mod2.Bar]",
             "('[' (name mod1.mod2.Foo) [(name mod1.mod2.Bar)])"),
            ("mod1.mod2.Foo[Bar1, Bar2, Bar3]",
             "('[' (name mod1.mod2.Foo) [(name Bar1), (name Bar2), (name Bar3)])"),
            ("mod1.mod2.Foo[mod1.mod2.Bar[mod1.mod2.Baz]]",
             "('[' (name mod1.mod2.Foo) [('[' (name mod1.mod2.Bar) [(name mod1.mod2.Baz)])])"),
            ("mod1.mod2.Foo[mod1.mod2.Bar1[mod1.mod2.Baz1], mod1.mod2.Bar2[mod1.mod2.Baz2]]",
             "('[' (name mod1.mod2.Foo) [('[' (name mod1.mod2.Bar1) [(name mod1.mod2.Baz1)]), ('[' (name mod1.mod2.Bar2) [(name mod1.mod2.Baz2)])])"),
            ("(Foo, Bar) -> Baz",
             "('(' [(name Foo), (name Bar)] (name Baz))"),
            (
            "(mod1.mod2.Foo[mod1.mod2.Bar1[mod1.mod2.Baz1], mod1.mod2.Bar2[mod1.mod2.Baz2]], mod1.mod2.Bar[mod1.mod2.Bar1[mod1.mod2.Baz1], mod1.mod2.Bar2[mod1.mod2.Baz2]]) -> mod1.mod2.Baz[mod1.mod2.Bar1[mod1.mod2.Baz1], mod1.mod2.Bar2[mod1.mod2.Baz2]]",
            "('(' [('[' (name mod1.mod2.Foo) [('[' (name mod1.mod2.Bar1) [(name mod1.mod2.Baz1)]), ('[' (name mod1.mod2.Bar2) [(name mod1.mod2.Baz2)])]), ('[' (name mod1.mod2.Bar) [('[' (name mod1.mod2.Bar1) [(name mod1.mod2.Baz1)]), ('[' (name mod1.mod2.Bar2) [(name mod1.mod2.Baz2)])])] ('[' (name mod1.mod2.Baz) [('[' (name mod1.mod2.Bar1) [(name mod1.mod2.Baz1)]), ('[' (name mod1.mod2.Bar2) [(name mod1.mod2.Baz2)])]))"),
            ("(Foo, Bar) -> Baz | Foo[Bar[Baz]]",
             "('|' ('(' [(name Foo), (name Bar)] (name Baz)) ('[' (name Foo) [('[' (name Bar) [(name Baz)])]))"),
            ("Foo[Bar[Baz | (Foo, Bar) -> Baz]]",
             "('[' (name Foo) [('[' (name Bar) [('|' (name Baz) ('(' [(name Foo), (name Bar)] (name Baz)))])])"),
        ]

        for t, expected in tests:
            result = repr(evaluate.compile(t))
            self.assertEqual(expected, result)


class RegressionHintingTest(AbstractHintingTest):

    def test_hierarchical_hint_for_mutable_attr_type(self):
        """Test for #157, AttributeError: 'PyObject' object has no attribute 'get_doc'"""
        code = 'class SuperClass(object):\n' \
               '    def __init__(self):\n' \
               '        self.foo = None\n' \
               '\n\n' \
               'class SubClass(SuperClass):\n' \
               '    def __init__(self):\n' \
               '        super(SubClass, self).__init__()\n' \
               '        self.bar = 3\n' \
               '\n\n' \
               '    def foo(self):\n' \
               '        return self.bar'
        result = self._assist(code)
        self.assert_completion_in_result('bar', 'attribute', result)


def suite():
    result = unittest.TestSuite()
    result.addTests(unittest.makeSuite(DocstringParamHintingTest))
    result.addTests(unittest.makeSuite(DocstringReturnHintingTest))
    result.addTests(unittest.makeSuite(DocstringNoneAssignmentHintingTest))
    result.addTests(unittest.makeSuite(DocstringNotImplementedAssignmentHintingTest))
    result.addTests(unittest.makeSuite(PEP0484CommentNoneAssignmentHintingTest))
    result.addTests(unittest.makeSuite(PEP0484CommentNotImplementedAssignmentHintingTest))
    result.addTests(unittest.makeSuite(EvaluateTest))
    result.addTests(unittest.makeSuite(RegressionHintingTest))
    return result


if __name__ == '__main__':
    unittest.main()
