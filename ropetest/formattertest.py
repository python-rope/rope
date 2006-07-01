import unittest

from rope.formatter import Formatter


class FormatterTest(unittest.TestCase):

    def setUp(self):
        super(FormatterTest, self).setUp()
        self.formatter = Formatter()

    def tearDown(self):
        super(FormatterTest, self).tearDown()

    def test_formatting_empty_string(self):
        formatted = self.formatter.format('')
        self.assertEquals('', formatted)

    def test_formatting_simple_equality(self):
        formatted = self.formatter.format('a_var       = 10\n')
        self.assertEquals('a_var = 10\n', formatted)


if __name__ == '__main__':
    unittest.main()

