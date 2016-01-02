import unittest

from rope.contrib.codeassist import code_assist
from ropetest import testutils


class HintingTest(unittest.TestCase):

    def setUp(self):
        super(HintingTest, self).setUp()
        self.project = testutils.sample_project()

    def tearDown(self):
        testutils.remove_project(self.project)
        super(HintingTest, self).tearDown()

    def _assist(self, code, resource=None, **kwds):
        return code_assist(self.project, code, len(code), resource, **kwds)

    def assert_completion_in_result(self, name, scope, result):
        for proposal in result:
            if proposal.name == name and proposal.scope == scope:
                return
        self.fail('completion <%s> not proposed' % name)

    def assert_completion_not_in_result(self, name, scope, result):
        for proposal in result:
            if proposal.name == name and proposal.scope == scope:
                self.fail('completion <%s> was proposed' % name)

    def test_hint_param(self):
        code = 'class Sample(object):\n' \
               '    def a_method(self, a_arg):\n' \
               '        """:type a_arg: threading.Thread"""\n' \
               '        a_arg.isA'
        result = self._assist(code)
        self.assert_completion_in_result('isAlive', 'attribute', result)

    def test_hierarchical_hint_param(self):
        code = 'class ISample(object):\n' \
               '    def a_method(self, a_arg):\n' \
               '        """:type a_arg: threading.Thread"""\n' \
               '\n\n' \
               'class Sample(ISample):\n' \
               '    def a_method(self, a_arg):\n' \
               '        a_arg.isA'
        result = self._assist(code)
        self.assert_completion_in_result('isAlive', 'attribute', result)

    def test_hierarchical_hint_rtype(self):
        code = 'class ISample(object):\n' \
               '    def b_method(self):\n' \
               '        """:rtype: threading.Thread"""\n' \
               '\n\n' \
               'class Sample(ISample):\n' \
               '    def a_method(self):\n' \
               '        self.b_method().isA'
        result = self._assist(code)
        self.assert_completion_in_result('isAlive', 'attribute', result)

    def test_hint_attr(self):
        code = 'class Sample(object):\n' \
               '    """:type a_attr: threading.Thread"""\n' \
               '    a_attr = None\n'\
               '    def a_method(self):\n' \
               '        self.a_attr.isA'
        result = self._assist(code)
        self.assert_completion_in_result('isAlive', 'attribute', result)

    def test_hierarchical_hint_attr(self):
        code = 'class ISample(object):\n' \
               '    """:type a_attr: threading.Thread"""\n' \
               '    a_attr = None\n'\
               '\n\n' \
               'class Sample(ISample):\n' \
               '    def a_method(self):\n' \
               '        self.a_attr.isA'
        result = self._assist(code)
        self.assert_completion_in_result('isAlive', 'attribute', result)


def suite():
    result = unittest.TestSuite()
    result.addTests(unittest.makeSuite(HintingTest))
    return result


if __name__ == '__main__':
    unittest.main()
