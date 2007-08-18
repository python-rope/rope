import unittest

from rope.refactor import similarfinder
from ropetest import testutils


class SimilarFinderTest(unittest.TestCase):

    def setUp(self):
        super(SimilarFinderTest, self).setUp()

    def tearDown(self):
        super(SimilarFinderTest, self).tearDown()

    def test_trivial_case(self):
        finder = similarfinder.SimilarFinder('')
        self.assertEquals([], list(finder.get_match_regions('10')))

    def test_constant_integer(self):
        source = 'a = 10\n'
        finder = similarfinder.SimilarFinder(source)
        result = [(source.index('10'), source.index('10') + 2)]
        self.assertEquals(result, list(finder.get_match_regions('10')))

    def test_simple_addition(self):
        source = 'a = 1 + 2\n'
        finder = similarfinder.SimilarFinder(source)
        result = [(source.index('1'), source.index('2') + 1)]
        self.assertEquals(result, list(finder.get_match_regions('1 + 2')))

    def test_simple_addition2(self):
        source = 'a = 1 +2\n'
        finder = similarfinder.SimilarFinder(source)
        result = [(source.index('1'), source.index('2') + 1)]
        self.assertEquals(result, list(finder.get_match_regions('1 + 2')))

    def test_simple_assign_statements(self):
        source = 'a = 1 + 2\n'
        finder = similarfinder.SimilarFinder(source)
        self.assertEquals([(0, len(source) - 1)],
                          list(finder.get_match_regions('a = 1 + 2')))

    def test_simple_multiline_statements(self):
        source = 'a = 1\nb = 2\n'
        finder = similarfinder.SimilarFinder(source)
        self.assertEquals([(0, len(source) - 1)],
                          list(finder.get_match_regions('a = 1\nb = 2')))

    def test_multiple_matches(self):
        source = 'a = 1 + 1\n'
        finder = similarfinder.SimilarFinder(source)
        result = list(finder.get_match_regions('1'))
        self.assertEquals(2, len(result))
        start1 = source.index('1')
        self.assertEquals((start1, start1 + 1) , result[0])
        start2 = source.rindex('1')
        self.assertEquals((start2, start2 + 1) , result[1])

    def test_multiple_matches2(self):
        source = 'a = 1\nb = 2\n\na = 1\nb = 2\n'
        finder = similarfinder.SimilarFinder(source)
        self.assertEquals(
            2, len(list(finder.get_match_regions('a = 1\nb = 2'))))

    def test_restricting_the_region_to_search(self):
        source = '1\n\n1\n'
        finder = similarfinder.SimilarFinder(source)
        result = list(finder.get_match_regions('1', start=2))
        start = source.rfind('1')
        self.assertEquals([(start, start + 1)], result)

    def test_matching_basic_patterns(self):
        source = 'b = a\n'
        finder = similarfinder.SimilarFinder(source)
        result = list(finder.get_match_regions('${a}'))
        start = source.rfind('a')
        self.assertEquals([(start, start + 1)], result)

    def test_match_get_ast(self):
        source = 'b = a\n'
        finder = similarfinder.SimilarFinder(source)
        result = list(finder.get_matches('${a}'))
        self.assertEquals('a', result[0].get_ast('a').id)

    def test_match_get_ast_for_statements(self):
        source = 'b = a\n'
        finder = similarfinder.SimilarFinder(source)
        result = list(finder.get_matches('b = ${a}'))
        self.assertEquals('a', result[0].get_ast('a').id)

    def test_matching_multiple_patterns(self):
        source = 'c = a + b\n'
        finder = similarfinder.SimilarFinder(source)
        result = list(finder.get_matches('${a} + ${b}'))
        self.assertEquals('a', result[0].get_ast('a').id)
        self.assertEquals('b', result[0].get_ast('b').id)

    def test_matching_any_patterns(self):
        source = 'b = a\n'
        finder = similarfinder.SimilarFinder(source)
        result = list(finder.get_matches('b = ${?x}'))
        self.assertEquals('a', result[0].get_ast('?x').id)

    def test_matching_any_patterns_repeating(self):
        source = 'b = 1 + 1\n'
        finder = similarfinder.SimilarFinder(source)
        result = list(finder.get_matches('b = ${?x} + ${?x}'))
        self.assertEquals(1, result[0].get_ast('?x').n)

    def test_matching_any_patterns_not_matching_different_nodes(self):
        source = 'b = 1 + 2\n'
        finder = similarfinder.SimilarFinder(source)
        result = list(finder.get_matches('b = ${?x} + ${?x}'))
        self.assertEquals(0, len(result))

    def test_matching_normal_names_and_assname(self):
        source = 'a = 1\n'
        finder = similarfinder.SimilarFinder(source)
        result = list(finder.get_matches('${a} = 1'))
        self.assertEquals('a', result[0].get_ast('a').id)

    def test_matching_normal_names_and_assname2(self):
        source = 'a = 1\n'
        finder = similarfinder.SimilarFinder(source)
        result = list(finder.get_matches('${a}'))
        self.assertEquals(1, len(result))

    def test_matching_normal_names_and_attributes(self):
        source = 'x.a = 1\n'
        finder = similarfinder.SimilarFinder(source)
        result = list(finder.get_matches('${a} = 1'))
        self.assertEquals(1, len(result))

    def test_functions_not_matching_when_only_first_parameters(self):
        source = 'f(1, 2)\n'
        finder = similarfinder.SimilarFinder(source)
        self.assertEquals(0, len(list(finder.get_matches('f(1)'))))


class CheckingFinderTest(unittest.TestCase):

    def setUp(self):
        super(CheckingFinderTest, self).setUp()
        self.project = testutils.sample_project()
        self.pycore = self.project.get_pycore()
        self.mod1 = self.pycore.create_module(self.project.root, 'mod1')

    def tearDown(self):
        testutils.remove_project(self.project)
        super(CheckingFinderTest, self).tearDown()

    def test_trivial_case(self):
        self.mod1.write('')
        pymodule = self.pycore.resource_to_pyobject(self.mod1)
        finder = similarfinder.CheckingFinder(pymodule, {})
        self.assertEquals([], list(finder.get_match_regions('10')))

    def test_simple_finding(self):
        self.mod1.write('class A(object):\n    pass\na = A()\n')
        pymodule = self.pycore.resource_to_pyobject(self.mod1)
        finder = similarfinder.CheckingFinder(pymodule, {})
        result = list(finder.get_matches('${?anything} = ${?A}()'))
        self.assertEquals(1, len(result))

    def test_finding2(self):
        self.mod1.write('class A(object):\n    pass\na = list()\n')
        pymodule = self.pycore.resource_to_pyobject(self.mod1)
        finder = similarfinder.CheckingFinder(
            pymodule, {'?A': pymodule.get_attribute('A')})
        result = list(finder.get_matches('${?anything} = ${?A}()'))
        self.assertEquals(0, len(result))

    def test_not_matching_unknowns_finding(self):
        self.mod1.write('class A(object):\n    pass\na = unknown()\n')
        pymodule = self.pycore.resource_to_pyobject(self.mod1)
        finder = similarfinder.CheckingFinder(
            pymodule, {'?A': pymodule.get_attribute('A')})
        result = list(finder.get_matches('${?anything} = ${?A}()'))
        self.assertEquals(0, len(result))

    def test_finding_and_matching_pyobjects(self):
        source = 'class A(object):\n    pass\nNewA = A\na = NewA()\n'
        self.mod1.write(source)
        pymodule = self.pycore.resource_to_pyobject(self.mod1)
        finder = similarfinder.CheckingFinder(
            pymodule, {'?A.object': pymodule.get_attribute('A').get_object()})
        result = list(finder.get_matches('${?anything} = ${?A}()'))
        self.assertEquals(1, len(result))
        start = source.rindex('a =')
        self.assertEquals((start, len(source) - 1), result[0].get_region())

    def test_finding_and_matching_types(self):
        source = 'class A(object):\n    def f(self):\n        pass\n' \
                 'a = A()\nb = a.f()\n'
        self.mod1.write(source)
        pymodule = self.pycore.resource_to_pyobject(self.mod1)
        finder = similarfinder.CheckingFinder(
            pymodule, {'?inst.type': pymodule.get_attribute('A').get_object()})
        result = list(finder.get_matches('${?anything} = ${?inst}.f()'))
        self.assertEquals(1, len(result))
        start = source.rindex('b')
        self.assertEquals((start, len(source) - 1), result[0].get_region())

    def test_checking_the_type_of_an_ass_name_node(self):
        self.mod1.write('class A(object):\n    pass\nan_a = A()\n')
        pymodule = self.pycore.resource_to_pyobject(self.mod1)
        finder = similarfinder.CheckingFinder(
            pymodule, {'?a.type':pymodule.get_attribute('A').get_object()})
        result = list(finder.get_matches('${?a} = ${?assigned}'))
        self.assertEquals(1, len(result))

    def test_checking_equality_of_imported_pynames(self):
        mod2 = self.pycore.create_module(self.project.root, 'mod2')
        mod2.write('class A(object):\n    pass\n')
        self.mod1.write('from mod2 import A\nan_a = A()\n')
        pymod2 = self.pycore.resource_to_pyobject(mod2)
        pymod1 = self.pycore.resource_to_pyobject(self.mod1)
        finder = similarfinder.CheckingFinder(
            pymod1, {'?a_class':pymod2.get_attribute('A')})
        result = list(finder.get_matches('${?a_class}()'))
        self.assertEquals(1, len(result))

    @testutils.assert_raises(similarfinder.BadNameInCheckError)
    def test_reporting_exception_when_bad_checks_are_given(self):
        self.mod1.write('1\n')
        pymodule = self.pycore.resource_to_pyobject(self.mod1)
        finder = similarfinder.CheckingFinder(
            pymodule, {'does_not_exist': pymodule})
        result = list(finder.get_matches('${?a}'))

class TemplateTest(unittest.TestCase):

    def test_simple_templates(self):
        template = similarfinder.CodeTemplate('${a}\n')
        self.assertEquals(set(['a']), set(template.get_names()))

    def test_ignoring_matches_in_comments(self):
        template = similarfinder.CodeTemplate('#${a}\n')
        self.assertEquals([], template.get_names())

    def test_ignoring_matches_in_strings(self):
        template = similarfinder.CodeTemplate("'${a}'\n")
        self.assertEquals([], template.get_names())

    def test_simple_substitution(self):
        template = similarfinder.CodeTemplate('${a}\n')
        self.assertEquals('b\n', template.substitute({'a': 'b'}))

    def test_substituting_multiple_names(self):
        template = similarfinder.CodeTemplate('${a}, ${b}\n')
        self.assertEquals('1, 2\n', template.substitute({'a': '1', 'b': '2'}))


def suite():
    result = unittest.TestSuite()
    result.addTests(unittest.makeSuite(SimilarFinderTest))
    result.addTests(unittest.makeSuite(CheckingFinderTest))
    result.addTests(unittest.makeSuite(TemplateTest))
    return result

if __name__ == '__main__':
    unittest.main()
