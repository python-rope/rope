import unittest

from rope.refactor import similarfinder


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
        finder = similarfinder.SimilarFinder(source, start=2)
        result = list(finder.get_match_regions('1'))
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
        self.assertEquals('a', result[0].get_ast('a').name)

    def test_match_get_ast_for_statements(self):
        source = 'b = a\n'
        finder = similarfinder.SimilarFinder(source)
        result = list(finder.get_matches('b = ${a}'))
        self.assertEquals('a', result[0].get_ast('a').name)

    def test_matching_multiple_patterns(self):
        source = 'c = a + b\n'
        finder = similarfinder.SimilarFinder(source)
        result = list(finder.get_matches('${a} + ${b}'))
        self.assertEquals('a', result[0].get_ast('a').name)
        self.assertEquals('b', result[0].get_ast('b').name)

    def test_matching_any_patterns(self):
        source = 'b = a\n'
        finder = similarfinder.SimilarFinder(source)
        result = list(finder.get_matches('b = ${?x}'))
        self.assertEquals('a', result[0].get_ast('?x').name)

    def test_matching_any_patterns_repeating(self):
        source = 'b = 1 + 1\n'
        finder = similarfinder.SimilarFinder(source)
        result = list(finder.get_matches('b = ${?x} + ${?x}'))
        self.assertEquals(1, result[0].get_ast('?x').value)

    def test_matching_any_patterns_not_matching_different_nodes(self):
        source = 'b = 1 + 2\n'
        finder = similarfinder.SimilarFinder(source)
        result = list(finder.get_matches('b = ${?x} + ${?x}'))
        self.assertEquals(0, len(result))


class TemplateTest(unittest.TestCase):

    def test_simple_templates(self):
        template = similarfinder._Template('${a}\n')
        self.assertEquals(set(['a']), set(template.get_names()))

    def test_ignoring_matches_in_comments(self):
        template = similarfinder._Template('#${a}\n')
        self.assertEquals([], template.get_names())

    def test_ignoring_matches_in_strings(self):
        template = similarfinder._Template("'${a}'\n")
        self.assertEquals([], template.get_names())

    def test_simple_substitution(self):
        template = similarfinder._Template('${a}\n')
        self.assertEquals('b\n', template.substitute({'a': 'b'}))

    def test_substituting_multiple_names(self):
        template = similarfinder._Template('${a}, ${b}\n')
        self.assertEquals('1, 2\n', template.substitute({'a': '1', 'b': '2'}))


def suite():
    result = unittest.TestSuite()
    result.addTests(unittest.makeSuite(SimilarFinderTest))
    result.addTests(unittest.makeSuite(TemplateTest))
    return result

if __name__ == '__main__':
    unittest.main()
