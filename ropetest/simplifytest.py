try:
    import unittest2 as unittest
except ImportError:
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

    def test_removing_comments_that_contain_strings(self):
        code = '# "c"\n'
        self.assertEquals('     \n', simplify.real_code(code))

    def test_removing_strings_containing_comments(self):
        code = '"#c"\n'
        self.assertEquals('"  "\n', simplify.real_code(code))

    def test_joining_implicit_continuations(self):
        code = '(\n)\n'
        self.assertEquals('( )\n', simplify.real_code(code))

    def test_joining_explicit_continuations(self):
        code = '1 + \\\n 2\n'
        self.assertEquals('1 +    2\n', simplify.real_code(code))

    def test_replacing_tabs(self):
        code = '1\t+\t2\n'
        self.assertEquals('1 + 2\n', simplify.real_code(code))

    def test_replacing_semicolons(self):
        code = 'a = 1;b = 2\n'
        self.assertEquals('a = 1\nb = 2\n', simplify.real_code(code))


def suite():
    result = unittest.TestSuite()
    result.addTests(unittest.makeSuite(SimplifyTest))
    return result

if __name__ == '__main__':
    unittest.main()
