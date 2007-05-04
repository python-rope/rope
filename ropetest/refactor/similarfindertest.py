import unittest

from rope.refactor import similarfinder


class SimilarFinderTest(unittest.TestCase):

    def setUp(self):
        super(SimilarFinderTest, self).setUp()

    def tearDown(self):
        super(SimilarFinderTest, self).tearDown()

    def test_trivial_case(self):
        finder = similarfinder.SimilarFinder('')
        self.assertEquals([], list(finder.find('10')))

    def test_constant_integer(self):
        source = 'a = 10\n'
        finder = similarfinder.SimilarFinder(source)
        result = [(source.index('10'), source.index('10') + 2)]
        self.assertEquals(result, list(finder.find('10')))


if __name__ == '__main__':
    unittest.main()
