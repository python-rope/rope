import unittest

from rope.base import simplify
from ropetest import testutils


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

    # --- f-string literal/format-spec bracket folding (see CHANGELOG) ---
    # An unmatched ``()[]{}`` in an f-string's *literal* or *format-spec*
    # text must not be counted by the implicit-continuation pass, or every
    # following newline is blanked and later offsets desync.  Each of the
    # following asserts the newline count is preserved (i.e. not folded).

    @testutils.only_for_versions_higher("3.12")
    def test_fstring_literal_open_bracket_not_folded(self):
        code = 'f"[{x}"\ndef g(): pass\n'
        self.assertEqual(code.count("\n"), simplify.real_code(code).count("\n"))

    @testutils.only_for_versions_higher("3.12")
    def test_fstring_literal_open_paren_not_folded(self):
        code = 'f"({n} items"\ndef g(): pass\n'
        self.assertEqual(code.count("\n"), simplify.real_code(code).count("\n"))

    @testutils.only_for_versions_higher("3.12")
    def test_fstring_escaped_brace_not_folded(self):
        code = 'f"{{"\ndef g(): pass\n'
        self.assertEqual(code.count("\n"), simplify.real_code(code).count("\n"))

    @testutils.only_for_versions_higher("3.12")
    def test_fstring_format_spec_bracket_not_folded(self):
        code = 'f"{x:>[}"\ndef g(): pass\n'
        self.assertEqual(code.count("\n"), simplify.real_code(code).count("\n"))

    @testutils.only_for_versions_higher("3.12")
    def test_fstring_ansi_escape_not_folded(self):
        code = 'f"\\x1b[K{x}"\ndef g(): pass\n'
        self.assertEqual(code.count("\n"), simplify.real_code(code).count("\n"))

    @testutils.only_for_versions_higher("3.12")
    def test_fstring_multiline_bracket_not_folded(self):
        code = 'f"""\n[{x}\n"""\ndef g(): pass\n'
        self.assertEqual(code.count("\n"), simplify.real_code(code).count("\n"))

    @testutils.only_for_versions_higher("3.12")
    def test_fstring_nested_bracket_not_folded(self):
        code = 'f"{f\'[{x}\'}"\ndef g(): pass\n'
        self.assertEqual(code.count("\n"), simplify.real_code(code).count("\n"))

    # --- PRESERVED: real expression brackets inside an f-string must stay ---
    # The fix must not over-blank real syntax.

    @testutils.only_for_versions_higher("3.12")
    def test_fstring_real_list_brackets_preserved(self):
        code = 'f"{[1,2][0]}"\ndef g(): pass\n'
        self.assertEqual(code, simplify.real_code(code))

    @testutils.only_for_versions_higher("3.12")
    def test_fstring_nested_string_literal_bracket_blanked(self):
        # A bracket char that is literal data inside a nested string is not
        # real syntax: it is blanked to a space (length preserved) so it
        # cannot sway the continuation count. The structural brackets stay
        # intact and the code below does not fold.
        code = "f\"{d['}']}\"\ndef g(): pass\n"
        expected = "f\"{d[' ']}\"\ndef g(): pass\n"
        result = simplify.real_code(code)
        self.assertEqual(expected, result)
        self.assertEqual(len(code), len(result))

    @testutils.only_for_versions_higher("3.12")
    def test_fstring_format_spec_nested_expr_preserved(self):
        code = 'f"{x:{w}}"\ndef g(): pass\n'
        self.assertEqual(code, simplify.real_code(code))

    def test_unterminated_fstring_falls_back_without_crashing(self):
        # an invalid/incomplete f-string must not crash real_code or
        # over-blank the code that follows it
        code = 'f"[{x}\ndef g(): pass\n'
        result = simplify.real_code(code)
        self.assertIn("def g", result)
