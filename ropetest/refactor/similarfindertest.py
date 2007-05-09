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


if __name__ == '__main__':
    unittest.main()
