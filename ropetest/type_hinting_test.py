import unittest
from textwrap import dedent, indent

import pytest

from rope.base.oi.type_hinting import evaluate
from rope.contrib.codeassist import code_assist
from ropetest import testutils


class AbstractHintingTest(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.project = testutils.sample_project()

    def tearDown(self):
        testutils.remove_project(self.project)
        super().tearDown()

    def _assist(self, code, offset=None, resource=None, **kwds):
        if offset is None:
            offset = len(code)
        return code_assist(self.project, code, offset, resource, **kwds)

    def assert_completion_in_result(self, name, scope, result):
        for proposal in result:
            if proposal.name == name and proposal.scope == scope:
                return
        self.fail(
            "completion <%s> in scope %r not proposed, available names: %r"
            % (name, scope, [(i.name, i.scope) for i in result])
        )

    def assert_completion_not_in_result(self, name, scope, result):
        for proposal in result:
            if proposal.name == name and proposal.scope == scope:
                self.fail("completion <%s> was proposed" % name)

    def run(self, result=None):
        if self.__class__.__name__.startswith("Abstract"):
            return
        super().run(result)


class DocstringParamHintingTest(AbstractHintingTest):
    def test_hint_param(self):
        code = dedent('''\
            class Sample(object):
                def a_method(self, a_arg):
                    """:type a_arg: threading.Thread"""
                    a_arg.is_a''')
        result = self._assist(code)
        self.assert_completion_in_result("is_alive", "attribute", result)

    def test_hierarchical_hint_param(self):
        code = dedent('''\
            class ISample(object):
                def a_method(self, a_arg):
                    """:type a_arg: threading.Thread"""


            class Sample(ISample):
                def a_method(self, a_arg):
                    a_arg.is_a''')
        result = self._assist(code)
        self.assert_completion_in_result("is_alive", "attribute", result)


class DocstringReturnHintingTest(AbstractHintingTest):
    def test_hierarchical_hint_rtype(self):
        code = dedent('''\
            class ISample(object):
                def b_method(self):
                    """:rtype: threading.Thread"""


            class Sample(ISample):
                def b_method(self):
                    pass
                def a_method(self):
                    self.b_method().is_a''')
        result = self._assist(code)
        self.assert_completion_in_result("is_alive", "attribute", result)


def fix_indents(hint):
    return indent(hint, " " * 12).strip()


class AbstractAssignmentHintingTest(AbstractHintingTest):
    def _make_class_hint(self, type_str):
        raise NotImplementedError

    def _make_constructor_hint(self, type_str):
        raise NotImplementedError

    def test_hint_attr(self):
        code = dedent(f"""\
            class Sample(object):
                {fix_indents(self._make_class_hint("threading.Thread"))}
                def a_method(self):
                    self.a_attr.is_a""")
        result = self._assist(code)
        self.assert_completion_in_result("is_alive", "attribute", result)

    def test_hierarchical_hint_attr(self):
        code = dedent(f"""\
            class ISample(object):
                {fix_indents(self._make_class_hint("threading.Thread"))}


            class Sample(ISample):
                a_attr = None
                def a_method(self):
                    self.a_attr.is_a""")
        result = self._assist(code)
        self.assert_completion_in_result("is_alive", "attribute", result)

    def test_hint_defined_by_constructor(self):
        code = dedent(f"""\
            class Sample(object):
                def __init__(self, arg):
                    {fix_indents(self._make_constructor_hint("threading.Thread"))}
                def a_method(self):
                    self.a_attr.is_a""")
        result = self._assist(code)
        self.assert_completion_in_result("is_alive", "attribute", result)

    def test_hint_attr_redefined_by_constructor(self):
        code = dedent(f"""\
            class Sample(object):
                {fix_indents(self._make_class_hint("threading.Thread"))}
                def __init__(self):
                    self.a_attr = None
                def a_method(self):
                    self.a_attr.is_a""")
        result = self._assist(code)
        self.assert_completion_in_result("is_alive", "attribute", result)

    def test_hierarchical_hint_attr_redefined_by_constructor(self):
        code = dedent(f"""\
            class ISample(object):
                {fix_indents(self._make_class_hint("threading.Thread"))}


            class Sample(ISample):
                def __init__(self):
                    self.a_attr = None
                def a_method(self):
                    self.a_attr.is_a""")
        result = self._assist(code)
        self.assert_completion_in_result("is_alive", "attribute", result)

    def test_hint_attr_for_pre_defined_type(self):
        code = dedent(f"""\
            class Other(object):
                def is_alive(self):
                    pass


            class Sample(object):
                {fix_indents(self._make_class_hint("Other"))}
                def a_method(self):
                    self.a_attr.is_a""")
        result = self._assist(code)
        self.assert_completion_in_result("is_alive", "attribute", result)

    def test_hint_attr_for_post_defined_type(self):
        code = dedent(f"""\
            class Sample(object):
                {fix_indents(self._make_class_hint("Other"))}
                def a_method(self):
                    self.a_attr.is_a""")
        offset = len(code)
        # Note: the leading blank lines are required.
        code += dedent("""\


            class Other(object):
                def is_alive(self):
                    pass
        """)
        result = self._assist(code, offset)
        self.assert_completion_in_result("is_alive", "attribute", result)

    def test_hint_parametrized_list(self):
        code = dedent(f"""\
            class Sample(object):
                {fix_indents(self._make_class_hint("list[threading.Thread]"))}
                def a_method(self):
                    for i in self.a_attr:
                        i.is_a""")
        result = self._assist(code)
        self.assert_completion_in_result("is_alive", "attribute", result)

    def test_hint_parametrized_tuple(self):
        code = dedent(f"""\
            class Sample(object):
                {fix_indents(self._make_class_hint("tuple[threading.Thread]"))}
                def a_method(self):
                    for i in self.a_attr:
                        i.is_a""")
        result = self._assist(code)
        self.assert_completion_in_result("is_alive", "attribute", result)

    def test_hint_parametrized_set(self):
        code = dedent(f"""\
            class Sample(object):
                {fix_indents(self._make_class_hint("set[threading.Thread]"))}
                def a_method(self):
                    for i in self.a_attr:
                        i.is_a""")
        result = self._assist(code)
        self.assert_completion_in_result("is_alive", "attribute", result)

    def test_hint_parametrized_iterable(self):
        code = dedent(f"""\
            class Sample(object):
                {fix_indents(self._make_class_hint("collections.Iterable[threading.Thread]"))}
                def a_method(self):
                    for i in self.a_attr:
                        i.is_a""")
        result = self._assist(code)
        self.assert_completion_in_result("is_alive", "attribute", result)

    def test_hint_parametrized_iterator(self):
        code = dedent(f"""\
            class Sample(object):
                {fix_indents(self._make_class_hint("collections.Iterator[threading.Thread]"))}
                def a_method(self):
                    for i in self.a_attr:
                        i.is_a""")
        result = self._assist(code)
        self.assert_completion_in_result("is_alive", "attribute", result)

    def test_hint_parametrized_dict_key(self):
        code = dedent(f"""\
            class Sample(object):
                {fix_indents(self._make_class_hint("dict[str, threading.Thread]"))}
                def a_method(self):
                    for i in self.a_attr.keys():
                        i.sta""")
        result = self._assist(code)
        self.assert_completion_in_result("startswith", "builtin", result)

    def test_hint_parametrized_dict_value(self):
        code = dedent(f"""\
            class Sample(object):
                {fix_indents(self._make_class_hint("dict[str, threading.Thread]"))}
                def a_method(self):
                    for i in self.a_attr.values():
                        i.is_a""")
        result = self._assist(code)
        self.assert_completion_in_result("is_alive", "attribute", result)

    def test_hint_parametrized_nested_tuple_list(self):
        code = dedent(f"""\
            class Sample(object):
                {fix_indents(self._make_class_hint("tuple[list[threading.Thread]]"))}
                def a_method(self):
                    for j in self.a_attr:
                        for i in j:
                            i.is_a""")
        result = self._assist(code)
        self.assert_completion_in_result("is_alive", "attribute", result)

    def test_hint_or(self):
        code = dedent(f"""\
            class Sample(object):
                {fix_indents(self._make_class_hint("str | threading.Thread"))}
                def a_method(self):
                    for i in self.a_attr.values():
                        i.is_a""")
        result = self._assist(code)
        try:
            # Be sure, there isn't errors currently
            self.assert_completion_in_result('is_alive', 'attribute', result)
        except AssertionError as e:
            pytest.xfail("failing configuration (but should work)")

    def test_hint_nonexistent(self):
        code = dedent(f"""\
            class Sample(object):
                {fix_indents(self._make_class_hint("sdfdsf.asdfasdf.sdfasdf.Dffg"))}
                def a_method(self):
                    for i in self.a_attr.values():
                        i.is_a""")
        result = self._assist(code)
        self.assertEqual(result, [])

    def test_hint_invalid_syntax(self):
        code = dedent(f"""\
            class Sample(object):
                {fix_indents(self._make_class_hint("sdf | & # &*"))}
                def a_method(self):
                    for i in self.a_attr.values():
                        i.is_a""")
        result = self._assist(code)
        self.assertEqual(result, [])


class DocstringNoneAssignmentHintingTest(AbstractAssignmentHintingTest):
    def _make_class_hint(self, type_str):
        hint = dedent(f'''\
            """:type a_attr: {type_str}"""
            a_attr = None
        ''')
        return indent(hint, " " * 4)

    def _make_constructor_hint(self, type_str):
        hint = dedent(f'''\
            """:type arg: {type_str}"""
            self.a_attr = arg
        ''')
        return indent(hint, " " * 8)


class DocstringNotImplementedAssignmentHintingTest(AbstractAssignmentHintingTest):
    def _make_class_hint(self, type_str):
        hint = dedent(f'''\
            """:type a_attr: {type_str}"""
            a_attr = NotImplemented
        ''')
        return indent(hint, " " * 4)

    def _make_constructor_hint(self, type_str):
        hint = dedent(f'''\
            """:type arg: {type_str}"""
            self.a_attr = arg
        ''')
        return indent(hint, " " * 8)


class PEP0484CommentNoneAssignmentHintingTest(AbstractAssignmentHintingTest):
    def _make_class_hint(self, type_str):
        hint = dedent(f"""\
            a_attr = None  # type: {type_str}
        """)
        return indent(hint, " " * 4)

    def _make_constructor_hint(self, type_str):
        hint = dedent(f"""\
            self.a_attr = None  # type: {type_str}
        """)
        return indent(hint, " " * 8)


class PEP0484CommentNotImplementedAssignmentHintingTest(AbstractAssignmentHintingTest):
    def _make_class_hint(self, type_str):
        hint = dedent(f"""\
            a_attr = NotImplemented  # type: {type_str}
        """)
        return indent(hint, " " * 4)

    def _make_constructor_hint(self, type_str):
        hint = dedent(f"""\
            self.a_attr = NotImplemented  # type: {type_str}
        """)
        return indent(hint, " " * 8)


class EvaluateTest(unittest.TestCase):
    def test_parser(self):
        tests = [
            ("Foo", "(name Foo)"),
            ("mod1.Foo", "(name mod1.Foo)"),
            ("mod1.mod2.Foo", "(name mod1.mod2.Foo)"),
            ("Foo[Bar]", "('[' (name Foo) [(name Bar)])"),
            (
                "Foo[Bar1, Bar2, Bar3]",
                "('[' (name Foo) [(name Bar1), (name Bar2), (name Bar3)])",
            ),
            ("Foo[Bar[Baz]]", "('[' (name Foo) [('[' (name Bar) [(name Baz)])])"),
            (
                "Foo[Bar1[Baz1], Bar2[Baz2]]",
                "('[' (name Foo) [('[' (name Bar1) [(name Baz1)]), ('[' (name Bar2) [(name Baz2)])])",
            ),
            ("mod1.mod2.Foo[Bar]", "('[' (name mod1.mod2.Foo) [(name Bar)])"),
            (
                "mod1.mod2.Foo[mod1.mod2.Bar]",
                "('[' (name mod1.mod2.Foo) [(name mod1.mod2.Bar)])",
            ),
            (
                "mod1.mod2.Foo[Bar1, Bar2, Bar3]",
                "('[' (name mod1.mod2.Foo) [(name Bar1), (name Bar2), (name Bar3)])",
            ),
            (
                "mod1.mod2.Foo[mod1.mod2.Bar[mod1.mod2.Baz]]",
                "('[' (name mod1.mod2.Foo) [('[' (name mod1.mod2.Bar) [(name mod1.mod2.Baz)])])",
            ),
            (
                "mod1.mod2.Foo[mod1.mod2.Bar1[mod1.mod2.Baz1], mod1.mod2.Bar2[mod1.mod2.Baz2]]",
                "('[' (name mod1.mod2.Foo) [('[' (name mod1.mod2.Bar1) [(name mod1.mod2.Baz1)]), ('[' (name mod1.mod2.Bar2) [(name mod1.mod2.Baz2)])])",
            ),
            ("(Foo, Bar) -> Baz", "('(' [(name Foo), (name Bar)] (name Baz))"),
            (
                "(mod1.mod2.Foo[mod1.mod2.Bar1[mod1.mod2.Baz1], mod1.mod2.Bar2[mod1.mod2.Baz2]], mod1.mod2.Bar[mod1.mod2.Bar1[mod1.mod2.Baz1], mod1.mod2.Bar2[mod1.mod2.Baz2]]) -> mod1.mod2.Baz[mod1.mod2.Bar1[mod1.mod2.Baz1], mod1.mod2.Bar2[mod1.mod2.Baz2]]",
                "('(' [('[' (name mod1.mod2.Foo) [('[' (name mod1.mod2.Bar1) [(name mod1.mod2.Baz1)]), ('[' (name mod1.mod2.Bar2) [(name mod1.mod2.Baz2)])]), ('[' (name mod1.mod2.Bar) [('[' (name mod1.mod2.Bar1) [(name mod1.mod2.Baz1)]), ('[' (name mod1.mod2.Bar2) [(name mod1.mod2.Baz2)])])] ('[' (name mod1.mod2.Baz) [('[' (name mod1.mod2.Bar1) [(name mod1.mod2.Baz1)]), ('[' (name mod1.mod2.Bar2) [(name mod1.mod2.Baz2)])]))",
            ),
            (
                "(Foo, Bar) -> Baz | Foo[Bar[Baz]]",
                "('|' ('(' [(name Foo), (name Bar)] (name Baz)) ('[' (name Foo) [('[' (name Bar) [(name Baz)])]))",
            ),
            (
                "Foo[Bar[Baz | (Foo, Bar) -> Baz]]",
                "('[' (name Foo) [('[' (name Bar) [('|' (name Baz) ('(' [(name Foo), (name Bar)] (name Baz)))])])",
            ),
        ]

        for t, expected in tests:
            result = repr(evaluate.compile(t))
            self.assertEqual(expected, result)


class RegressionHintingTest(AbstractHintingTest):
    def test_hierarchical_hint_for_mutable_attr_type(self):
        """Test for #157, AttributeError: 'PyObject' object has no attribute 'get_doc'"""
        code = dedent("""\
            class SuperClass(object):
                def __init__(self):
                    self.foo = None


            class SubClass(SuperClass):
                def __init__(self):
                    super(SubClass, self).__init__()
                    self.bar = 3


                def foo(self):
                    return self.bar""")
        result = self._assist(code)
        self.assert_completion_in_result("bar", "attribute", result)
