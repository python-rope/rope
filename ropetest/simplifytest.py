import unittest

from rope.base import simplify


class SimplifyTest(unittest.TestCase):

    def setUp(self):
        super(SimplifyTest, self).setUp()

    def tearDown(self):
        super(SimplifyTest, self).tearDown()

    def test_trivial_case(self):
        self.assertEquals('', simplify.real_code(''))

    def test_empty_strs(self):
        code = 's = ""\n'
        self.assertEquals(code, simplify.real_code(code))

    def test_blanking_strs(self):
        code = 's = "..."\n'
        self.assertEquals('s = "   "\n', simplify.real_code(code))

    def test_changing_to_double_quotes(self):
        code = 's = \'\'\n'
        self.assertEquals('s = ""\n', simplify.real_code(code))

    def test_changing_to_double_quotes2(self):
        code = 's = """\n"""\n'
        self.assertEquals('s = "     "\n', simplify.real_code(code))

    def test_removing_comments(self):
        code = '# c\n'
        self.assertEquals('   \n', simplify.real_code(code))


if __name__ == '__main__':
    unittest.main()
