import unittest

from ropeide.formatter import Formatter


class FormatterTest(unittest.TestCase):

    def setUp(self):
        super(FormatterTest, self).setUp()
        self.formatter = Formatter()

    def tearDown(self):
        super(FormatterTest, self).tearDown()

    def test_removing_extra_spaces(self):
        formatted = self.formatter.format('  \n')
        self.assertEquals('\n', formatted)

    def test_removing_extra_spaces2(self):
        formatted = self.formatter.format('def a_func():  \n    print(1)  \n  ')
        self.assertEquals('def a_func():\n    print(1)\n', formatted)

    def test_removing_extra_blank_lines2(self):
        formatted = self.formatter.format('a = 1\n\n\n\nb = 2\nc=3\n\nd=4\n')
        self.assertEquals('a = 1\n\n\nb = 2\nc=3\n\nd=4\n', formatted)

    def test_removing_extra_blank_lines3(self):
        formatted = self.formatter.format('\n\n\n\na = 1\n')
        self.assertEquals('\n\na = 1\n', formatted)

    def test_removing_extra_blank_lines_at_the_end_of_file(self):
        formatted = self.formatter.format('\n\n\n')
        self.assertEquals('\n', formatted)

    def test_removing_extra_blank_lines_at_the_end_of_file2(self):
        formatted = self.formatter.format('a = 1\n\n')
        self.assertEquals('a = 1\n', formatted)

    def test_inserting_new_line_at_the_end_of_file(self):
        formatted = self.formatter.format('a = 1')
        self.assertEquals('a = 1\n', formatted)

    def xxx_test_formatting_simple_equality(self):
        formatted = self.formatter.format('a_var       = 10\n')
        self.assertEquals('a_var = 10\n', formatted)


if __name__ == '__main__':
    unittest.main()
