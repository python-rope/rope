from textwrap import dedent

try:
    import unittest2 as unittest
except ImportError:
    import unittest

from rope.refactor import similarfinder
from ropetest import testutils


class SimilarFinderTest(unittest.TestCase):
    def setUp(self):
        super(SimilarFinderTest, self).setUp()
        self.project = testutils.sample_project()
        self.mod = testutils.create_module(self.project, "mod")

    def tearDown(self):
        testutils.remove_project(self.project)
        super(SimilarFinderTest, self).tearDown()

    def _create_finder(self, source, **kwds):
        self.mod.write(source)
        pymodule = self.project.get_pymodule(self.mod)
        return similarfinder.SimilarFinder(pymodule, **kwds)

    def test_trivial_case(self):
        finder = self._create_finder("")
        self.assertEqual([], list(finder.get_match_regions("10")))

    def test_constant_integer(self):
        source = "a = 10\n"
        finder = self._create_finder(source)
        result = [(source.index("10"), source.index("10") + 2)]
        self.assertEqual(result, list(finder.get_match_regions("10")))

    def test_bool_is_not_similar_to_integer(self):
        source = dedent("""\
            a = False
            b = 0""")
        finder = self._create_finder(source)
        result = [(source.index("False"), source.index("False") + len("False"))]
        self.assertEqual(result, list(finder.get_match_regions("False")))

    def test_simple_addition(self):
        source = "a = 1 + 2\n"
        finder = self._create_finder(source)
        result = [(source.index("1"), source.index("2") + 1)]
        self.assertEqual(result, list(finder.get_match_regions("1 + 2")))

    def test_simple_addition2(self):
        source = "a = 1 +2\n"
        finder = self._create_finder(source)
        result = [(source.index("1"), source.index("2") + 1)]
        self.assertEqual(result, list(finder.get_match_regions("1 + 2")))

    def test_simple_assign_statements(self):
        source = "a = 1 + 2\n"
        finder = self._create_finder(source)
        self.assertEqual(
            [(0, len(source) - 1)], list(finder.get_match_regions("a = 1 + 2"))
        )

    def test_simple_multiline_statements(self):
        source = dedent("""\
            a = 1
            b = 2
        """)
        finder = self._create_finder(source)
        self.assertEqual(
            [(0, len(source) - 1)], list(finder.get_match_regions("a = 1\nb = 2"))
        )

    def test_multiple_matches(self):
        source = "a = 1 + 1\n"
        finder = self._create_finder(source)
        result = list(finder.get_match_regions("1"))
        self.assertEqual(2, len(result))
        start1 = source.index("1")
        self.assertEqual((start1, start1 + 1), result[0])
        start2 = source.rindex("1")
        self.assertEqual((start2, start2 + 1), result[1])

    def test_multiple_matches2(self):
        source = dedent("""\
            a = 1
            b = 2

            a = 1
            b = 2
        """)
        finder = self._create_finder(source)
        self.assertEqual(2, len(list(finder.get_match_regions("a = 1\nb = 2"))))

    def test_restricting_the_region_to_search(self):
        source = "1\n\n1\n"
        finder = self._create_finder(source)
        result = list(finder.get_match_regions("1", start=2))
        start = source.rfind("1")
        self.assertEqual([(start, start + 1)], result)

    def test_matching_basic_patterns(self):
        source = "b = a\n"
        finder = self._create_finder(source)
        result = list(finder.get_match_regions("${a}", args={"a": "exact"}))
        start = source.rfind("a")
        self.assertEqual([(start, start + 1)], result)

    def test_match_get_ast(self):
        source = "b = a\n"
        finder = self._create_finder(source)
        result = list(finder.get_matches("${a}", args={"a": "exact"}))
        self.assertEqual("a", result[0].get_ast("a").id)

    def test_match_get_ast_for_statements(self):
        source = "b = a\n"
        finder = self._create_finder(source)
        result = list(finder.get_matches("b = ${a}"))
        self.assertEqual("a", result[0].get_ast("a").id)

    def test_matching_multiple_patterns(self):
        source = "c = a + b\n"
        finder = self._create_finder(source)
        result = list(finder.get_matches("${a} + ${b}"))
        self.assertEqual("a", result[0].get_ast("a").id)
        self.assertEqual("b", result[0].get_ast("b").id)

    def test_matching_any_patterns(self):
        source = "b = a\n"
        finder = self._create_finder(source)
        result = list(finder.get_matches("b = ${x}"))
        self.assertEqual("a", result[0].get_ast("x").id)

    def test_matching_any_patterns_repeating(self):
        source = "b = 1 + 1\n"
        finder = self._create_finder(source)
        result = list(finder.get_matches("b = ${x} + ${x}"))
        self.assertEqual(1, result[0].get_ast("x").n)

    def test_matching_any_patterns_not_matching_different_nodes(self):
        source = "b = 1 + 2\n"
        finder = self._create_finder(source)
        result = list(finder.get_matches("b = ${x} + ${x}"))
        self.assertEqual(0, len(result))

    def test_matching_normal_names_and_assname(self):
        source = "a = 1\n"
        finder = self._create_finder(source)
        result = list(finder.get_matches("${a} = 1"))
        self.assertEqual("a", result[0].get_ast("a").id)

    def test_matching_normal_names_and_assname2(self):
        source = "a = 1\n"
        finder = self._create_finder(source)
        result = list(finder.get_matches("${a}", args={"a": "exact"}))
        self.assertEqual(1, len(result))

    def test_matching_normal_names_and_attributes(self):
        source = "x.a = 1\n"
        finder = self._create_finder(source)
        result = list(finder.get_matches("${a} = 1", args={"a": "exact"}))
        self.assertEqual(0, len(result))

    def test_functions_not_matching_when_only_first_parameters(self):
        source = "f(1, 2)\n"
        finder = self._create_finder(source)
        self.assertEqual(0, len(list(finder.get_matches("f(1)"))))

    def test_matching_nested_try_finally(self):
        source = dedent("""\
            if 1:
                try:
                    pass
                except:
                    pass
        """)
        pattern = dedent("""\
            try:
                pass
            except:
                pass
        """)
        finder = self._create_finder(source)
        self.assertEqual(1, len(list(finder.get_matches(pattern))))

    def test_matching_dicts_inside_functions(self):
        source = dedent("""\
            def f(p):
                d = {1: p.x}
        """)
        pattern = "{1: ${a}.x}"
        finder = self._create_finder(source)
        self.assertEqual(1, len(list(finder.get_matches(pattern))))


class CheckingFinderTest(unittest.TestCase):
    def setUp(self):
        super(CheckingFinderTest, self).setUp()
        self.project = testutils.sample_project()
        self.mod1 = testutils.create_module(self.project, "mod1")

    def tearDown(self):
        testutils.remove_project(self.project)
        super(CheckingFinderTest, self).tearDown()

    def test_trivial_case(self):
        self.mod1.write("")
        pymodule = self.project.get_pymodule(self.mod1)
        finder = similarfinder.SimilarFinder(pymodule)
        self.assertEqual([], list(finder.get_matches("10", {})))

    def test_simple_finding(self):
        self.mod1.write(
            dedent("""\
                class A(object):
                    pass
                a = A()
            """)
        )
        pymodule = self.project.get_pymodule(self.mod1)
        finder = similarfinder.SimilarFinder(pymodule)
        result = list(finder.get_matches("${anything} = ${A}()", {}))
        self.assertEqual(1, len(result))

    def test_not_matching_when_the_name_does_not_match(self):
        self.mod1.write(
            dedent("""\
                class A(object):
                    pass
                a = list()
            """)
        )
        pymodule = self.project.get_pymodule(self.mod1)
        finder = similarfinder.SimilarFinder(pymodule)
        result = list(finder.get_matches("${anything} = ${C}()", {"C": "name=mod1.A"}))
        self.assertEqual(0, len(result))

    def test_not_matching_unknowns_finding(self):
        self.mod1.write(
            dedent("""\
                class A(object):
                    pass
                a = unknown()
            """)
        )
        pymodule = self.project.get_pymodule(self.mod1)
        finder = similarfinder.SimilarFinder(pymodule)
        result = list(finder.get_matches("${anything} = ${C}()", {"C": "name=mod1.A"}))
        self.assertEqual(0, len(result))

    def test_finding_and_matching_pyobjects(self):
        source = dedent("""\
            class A(object):
                pass
            NewA = A
            a = NewA()
        """)
        self.mod1.write(source)
        pymodule = self.project.get_pymodule(self.mod1)
        finder = similarfinder.SimilarFinder(pymodule)
        result = list(
            finder.get_matches("${anything} = ${A}()", {"A": "object=mod1.A"})
        )
        self.assertEqual(1, len(result))
        start = source.rindex("a =")
        self.assertEqual((start, len(source) - 1), result[0].get_region())

    def test_finding_and_matching_types(self):
        source = dedent("""\
            class A(object):
                def f(self):
                    pass
            a = A()
            b = a.f()
        """)
        self.mod1.write(source)
        pymodule = self.project.get_pymodule(self.mod1)
        finder = similarfinder.SimilarFinder(pymodule)
        result = list(
            finder.get_matches("${anything} = ${inst}.f()", {"inst": "type=mod1.A"})
        )
        self.assertEqual(1, len(result))
        start = source.rindex("b")
        self.assertEqual((start, len(source) - 1), result[0].get_region())

    def test_checking_the_type_of_an_ass_name_node(self):
        self.mod1.write(
            dedent("""\
                class A(object):
                    pass
                an_a = A()
            """)
        )
        pymodule = self.project.get_pymodule(self.mod1)
        finder = similarfinder.SimilarFinder(pymodule)
        result = list(finder.get_matches("${a} = ${assigned}", {"a": "type=mod1.A"}))
        self.assertEqual(1, len(result))

    def test_checking_instance_of_an_ass_name_node(self):
        self.mod1.write(
            dedent("""\
                class A(object):
                    pass
                class B(A):
                    pass
                b = B()
            """)
        )
        pymodule = self.project.get_pymodule(self.mod1)
        finder = similarfinder.SimilarFinder(pymodule)
        result = list(
            finder.get_matches("${a} = ${assigned}", {"a": "instance=mod1.A"})
        )
        self.assertEqual(1, len(result))

    def test_checking_equality_of_imported_pynames(self):
        mod2 = testutils.create_module(self.project, "mod2")
        mod2.write(
            dedent("""\
                class A(object):
                    pass
            """)
        )
        self.mod1.write(
            dedent("""\
                from mod2 import A
                an_a = A()
            """)
        )
        pymod1 = self.project.get_pymodule(self.mod1)
        finder = similarfinder.SimilarFinder(pymod1)
        result = list(finder.get_matches("${a_class}()", {"a_class": "name=mod2.A"}))
        self.assertEqual(1, len(result))


class TemplateTest(unittest.TestCase):
    def test_simple_templates(self):
        template = similarfinder.CodeTemplate("${a}\n")
        self.assertEqual(set(["a"]), set(template.get_names()))

    def test_ignoring_matches_in_comments(self):
        template = similarfinder.CodeTemplate("#${a}\n")
        self.assertEqual({}.keys(), template.get_names())

    def test_ignoring_matches_in_strings(self):
        template = similarfinder.CodeTemplate("'${a}'\n")
        self.assertEqual({}.keys(), template.get_names())

    def test_simple_substitution(self):
        template = similarfinder.CodeTemplate("${a}\n")
        self.assertEqual("b\n", template.substitute({"a": "b"}))

    def test_substituting_multiple_names(self):
        template = similarfinder.CodeTemplate("${a}, ${b}\n")
        self.assertEqual("1, 2\n", template.substitute({"a": "1", "b": "2"}))
