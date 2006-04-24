import unittest

from ropetest.mockeditortest import GraphicalEditorFactory, MockEditorFactory
from rope.indenter import PythonCodeIndenter

class PythonCodeIndenterTest(unittest.TestCase):
    __factory = MockEditorFactory()
    def setUp(self):
        unittest.TestCase.setUp(self)
        self.editor = self.__factory.create()
        self.indenter = PythonCodeIndenter(self.editor)
    
    def tearDown(self):
        unittest.TestCase.tearDown(self)

    def test_python_indenter(self):
        self.editor.set_text('print "hello"\n')
        self.indenter.indent_line(self.editor.get_start())
        self.assertEquals('print "hello"\n', self.editor.get_text())

    def test_indenting_lines_with_indented_previous_line(self):
        self.editor.set_text('def f():\n    g()\nh()\n')
        self.indenter.indent_line(self.editor.get_relative(self.editor.get_end(), -2))
        self.assertEquals('def f():\n    g()\n    h()\n', self.editor.get_text())

    def test_indenting_lines_with_indented_previous_line(self):
        self.editor.set_text('def f():\n    g()\nh()\n')
        self.indenter.indent_line(self.editor.get_relative(self.editor.get_end(), -2))
        self.assertEquals('def f():\n    g()\n    h()\n', self.editor.get_text())

    def test_indenting_lines_when_prev_line_ends_with_a_colon(self):
        self.editor.set_text('def f():\ng()')
        self.indenter.indent_line(self.editor.get_relative(self.editor.get_end(), -2))
        self.assertEquals('def f():\n    g()', self.editor.get_text())

    def test_empty_prev_line(self):
        self.editor.set_text('    \nprint "hello"\n')
        self.indenter.indent_line(self.editor.get_index(10))
        self.assertEquals('    \nprint "hello"\n', self.editor.get_text())

    def test_indenting_lines_with_indented_previous_line_with_empty_line(self):
        self.editor.set_text('def f():\n    g()\n\nh()\n')
        self.indenter.indent_line(self.editor.get_relative(self.editor.get_end(), -2))
        self.assertEquals('def f():\n    g()\n\n    h()\n', self.editor.get_text())

    def test_indenting_lines_when_prev_line_ends_with_a_colon_with_empty_line(self):
        self.editor.set_text('def f():\n\ng()')
        self.indenter.indent_line(self.editor.get_relative(self.editor.get_end(), -2))
        self.assertEquals('def f():\n\n    g()', self.editor.get_text())

    def test_indenting_lines_at_start(self):
        self.editor.set_text('    g()\n')
        self.indenter.indent_line(self.editor.get_start())
        self.assertEquals('g()\n', self.editor.get_text())

    def test_indenting_lines_with_start_previous_line(self):
        self.editor.set_text('\n    g()\n')
        self.indenter.indent_line(self.editor.get_relative(self.editor.get_end(), -1))
        self.assertEquals('\ng()\n', self.editor.get_text())

    def test_deindenting_after_pass(self):
        self.editor.set_text('def f():\n    pass\n    f()')
        self.indenter.indent_line(self.editor.get_end())
        self.assertEquals('def f():\n    pass\nf()', self.editor.get_text())
        
    def test_explicit_line_continuation(self):
        self.editor.set_text('c = a + \\\nb')
        self.indenter.indent_line(self.editor.get_end())
        self.assertEquals('c = a + \\\n    b', self.editor.get_text())

    def test_returning_after_backslashes(self):
        self.editor.set_text('c = \\\n    b\\\n+ a')
        self.indenter.indent_line(self.editor.get_end())
        self.assertEquals('c = \\\n    b\\\n    + a', self.editor.get_text())

    def test_returning_after_backslashes(self):
        self.editor.set_text('c = \\\n    b\na')
        self.indenter.indent_line(self.editor.get_end())
        self.assertEquals('c = \\\n    b\na', self.editor.get_text())

    def test_backslash_should_indent_relative_to_the_first_word(self):
        self.editor.set_text('print a, \\\nb')
        self.indenter.indent_line(self.editor.get_end())
        self.assertEquals('print a, \\\n      b', self.editor.get_text())

    def test_backslash_indenting_on_indented_blocks(self):
        self.editor.set_text('def f():\n    c = a + \\\nb')
        self.indenter.indent_line(self.editor.get_end())
        self.assertEquals('def f():\n    c = a + \\\n        b', self.editor.get_text())

    def test_backslash_indenting_on_indented_blocks2(self):
        self.editor.set_text('def f():\n    print a, \\\nb')
        self.indenter.indent_line(self.editor.get_end())
        self.assertEquals('def f():\n    print a, \\\n          b', self.editor.get_text())

    def test_deindenting_when_encountering_else(self):
        self.editor.set_text('if True:\n    print "hello"\n    else:')
        self.indenter.indent_line(self.editor.get_end())
        self.assertEquals('if True:\n    print "hello"\nelse:', self.editor.get_text())

    def test_deindenting_when_encountering_except(self):
        self.editor.set_text('try:\n    print "hello"\n    except Exception:')
        self.indenter.indent_line(self.editor.get_end())
        self.assertEquals('try:\n    print "hello"\nexcept Exception:', self.editor.get_text())
    
    def test_deindenting_when_encountering_finally(self):
        self.editor.set_text('try:\n    print "hello"\n    finally:')
        self.indenter.indent_line(self.editor.get_end())
        self.assertEquals('try:\n    print "hello"\nfinally:', self.editor.get_text())
    
    def test_deindenting_after_return(self):
        self.editor.set_text('def f():\n    return "hello"\n    b\n')
        self.indenter.indent_line(self.editor.get_relative(self.editor.get_end(), -1))
        self.assertEquals('def f():\n    return "hello"\nb\n', self.editor.get_text())

    def test_deindenting_after_raise(self):
        self.editor.set_text('def f():\n    raise Exception()\n    b\n')
        self.indenter.indent_line(self.editor.get_relative(self.editor.get_end(), -1))
        self.assertEquals('def f():\n    raise Exception()\nb\n', self.editor.get_text())

    def test_multiple_indents(self):
        self.editor.set_text('def f():\n')
        self.indenter.indent_line(self.editor.get_end())
        self.indenter.indent_line(self.editor.get_end())
        self.assertEquals('def f():\n    ', self.editor.get_text())

    def test_implicit_continuation(self):
        self.editor.set_text('def f(a,\nb):')
        self.indenter.indent_line(self.editor.get_end())
        self.assertEquals('def f(a,\n      b):', self.editor.get_text())

    def test_double_parens(self):
        self.editor.set_text('def f(a, (c, b),\ne):')
        self.indenter.indent_line(self.editor.get_end())
        self.assertEquals('def f(a, (c, b),\n      e):', self.editor.get_text())

    def test_double_parens(self):
        self.editor.set_text('def f(a, (c, \nb), e):')
        self.indenter.indent_line(self.editor.get_end())
        self.assertEquals('def f(a, (c, \n          b), e):', self.editor.get_text())

    def test_implicit_continuation2(self):
        self.editor.set_text('d = {"age" : 20, \n"name" : "Ali"}')
        self.indenter.indent_line(self.editor.get_end())
        self.assertEquals('d = {"age" : 20, \n     "name" : "Ali"}', self.editor.get_text())

    def test_deindents_after_implicit_continuation(self):
        self.editor.set_text('f(a,\n      b)\na = 10')
        self.indenter.indent_line(self.editor.get_end())
        self.assertEquals('f(a,\n      b)\na = 10', self.editor.get_text())

    def test_deindents_after_implicit_continuation_after_double_parens(self):
        self.editor.set_text('def f(a, (c, \nb), e):\na=b')
        self.indenter.indent_line(self.editor.get_relative(self.editor.get_end(), - 5))
        self.indenter.indent_line(self.editor.get_end())
        self.assertEquals('def f(a, (c, \n          b), e):\n    a=b', self.editor.get_text())

    def test_implicit_continuation_after_return(self):
        self.editor.set_text('def f():\n    return (2,\n3)')
        self.indenter.indent_line(self.editor.get_end())
        self.assertEquals('def f():\n    return (2,\n            3)', self.editor.get_text())

    # TODO: handle this case
    def xxx_test_deindenting_after_implicit_continuation_after_return(self):
        self.editor.set_text('def f():\n    return (2,\n3)\na = 10')
        self.indenter.indent_line(self.editor.get_end())
        self.assertEquals('def f():\n    return (2,\n            3)\na = 10', self.editor.get_text())


if __name__ == '__main__':
    unittest.main()

