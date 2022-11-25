import unittest

from rope.base import simplify


class SimplifyTest(unittest.TestCase):
    def test_trivial_case(self):
        self.assertEqual("", simplify.real_code(""))

    def test_empty_strs(self):
        code = 's = ""\n'
        self.assertEqual(code, simplify.real_code(code))

    def test_blanking_strs(self):
        code = 's = "..."\n'
        self.assertEqual('s = "   "\n', simplify.real_code(code))

    def test_changing_to_double_quotes(self):
        code = "s = ''\n"
        self.assertEqual('s = ""\n', simplify.real_code(code))

    def test_changing_to_double_quotes2(self):
        code = 's = """\n"""\n'
        self.assertEqual('s = "     "\n', simplify.real_code(code))

    def test_removing_comments(self):
        code = "# c\n"
        self.assertEqual("   \n", simplify.real_code(code))

    def test_removing_comments_that_contain_strings(self):
        code = '# "c"\n'
        self.assertEqual("     \n", simplify.real_code(code))

    def test_removing_strings_containing_comments(self):
        code = '"#c"\n'
        self.assertEqual('"  "\n', simplify.real_code(code))

    def test_joining_implicit_continuations(self):
        code = "(\n)\n"
        self.assertEqual("( )\n", simplify.real_code(code))

    def test_joining_explicit_continuations(self):
        code = "1 + \\\n 2\n"
        self.assertEqual("1 +    2\n", simplify.real_code(code))

    def test_replacing_tabs(self):
        code = "1\t+\t2\n"
        self.assertEqual("1 + 2\n", simplify.real_code(code))

    def test_replacing_semicolons(self):
        code = "a = 1;b = 2\n"
        self.assertEqual("a = 1\nb = 2\n", simplify.real_code(code))

    def test_simplifying_f_string(self):
        code = 's = f"..{hello}.."\n'
        self.assertEqual('s = f"..{hello}.."\n', simplify.real_code(code))

    def test_simplifying_f_string_containing_quotes(self):
        code = """s = f"..'{hello}'.."\n"""
        self.assertEqual("""s = f"..'{hello}'.."\n""", simplify.real_code(code))

    def test_simplifying_uppercase_f_string_containing_quotes(self):
        code = """s = Fr"..'{hello}'.."\n"""
        self.assertEqual("""s = Fr"..'{hello}'.."\n""", simplify.real_code(code))
