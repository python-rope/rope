try:
    import unittest2 as unittest
except ImportError:
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

    def _assist(self, code, offset=None, resource=None, **kwds):
        if offset is None:
            offset = len(code)
        return code_assist(self.project, code, offset, resource, **kwds)

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
               '    def b_method(self):\n' \
               '        pass\n' \
               '    def a_method(self):\n' \
               '        self.b_method().isA'
        result = self._assist(code)
        self.assert_completion_in_result('isAlive', 'attribute', result)

    def test_hierarchical_hint_for_mutable_attr_type(self):
        """Test for #157, AttributeError: 'PyObject' object has no attribute 'get_doc'"""
        code = 'class SuperClass(object):\n' \
               '    def __init__(self):\n' \
               '        self.foo = None\n' \
               '\n\n' \
               'class SubClass(SuperClass):\n' \
               '    def __init__(self):\n' \
               '        super(SubClass, self).__init__()\n' \
               '        self.bar = 3\n' \
               '\n\n' \
               '    def foo(self):\n' \
               '        return self.bar'
        result = self._assist(code)
        self.assert_completion_in_result('bar', 'attribute', result)

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
               '\n\n' \
               'class Sample(ISample):\n' \
               '    a_attr = None\n'\
               '    def a_method(self):\n' \
               '        self.a_attr.isA'
        result = self._assist(code)
        self.assert_completion_in_result('isAlive', 'attribute', result)

    def test_hint_attr_defined_by_notimplemented(self):
        code = 'class Sample(object):\n' \
               '    """:type a_attr: threading.Thread"""\n' \
               '    a_attr = NotImplemented\n'\
               '    def a_method(self):\n' \
               '        self.a_attr.isA'
        result = self._assist(code)
        self.assert_completion_in_result('isAlive', 'attribute', result)

    def test_hierarchical_hint_attr_defined_by_notimplemented(self):
        code = 'class ISample(object):\n' \
               '    """:type a_attr: threading.Thread"""\n' \
               '\n\n' \
               'class Sample(ISample):\n' \
               '    a_attr = NotImplemented\n'\
               '    def a_method(self):\n' \
               '        self.a_attr.isA'
        result = self._assist(code)
        self.assert_completion_in_result('isAlive', 'attribute', result)

    def test_hint_attr_defined_by_constructor(self):
        code = 'class Sample(object):\n' \
               '    """:type a_attr: threading.Thread"""\n' \
               '    def __init__(self):\n' \
               '        self.a_attr = None\n' \
               '    def a_method(self):\n' \
               '        self.a_attr.isA'
        result = self._assist(code)
        self.assert_completion_in_result('isAlive', 'attribute', result)

    def test_hierarchical_hint_attr_defined_by_constructor(self):
        code = 'class ISample(object):\n' \
               '    """:type a_attr: threading.Thread"""\n' \
               '\n\n' \
               'class Sample(ISample):\n' \
               '    def __init__(self):\n' \
               '        self.a_attr = None\n' \
               '    def a_method(self):\n' \
               '        self.a_attr.isA'
        result = self._assist(code)
        self.assert_completion_in_result('isAlive', 'attribute', result)

    def test_hint_attr_defined_by_notimplemented_in_constructor(self):
        code = 'class Sample(object):\n' \
               '    """:type a_attr: threading.Thread"""\n' \
               '    def __init__(self):\n' \
               '        self.a_attr = NotImplemented\n' \
               '    def a_method(self):\n' \
               '        self.a_attr.isA'
        result = self._assist(code)
        self.assert_completion_in_result('isAlive', 'attribute', result)

    def test_hierarchical_hint_attr_defined_by_notimplemented_in_constructor(self):
        code = 'class ISample(object):\n' \
               '    """:type a_attr: threading.Thread"""\n' \
               '\n\n' \
               'class Sample(ISample):\n' \
               '    def __init__(self):\n' \
               '        self.a_attr = NotImplemented\n' \
               '    def a_method(self):\n' \
               '        self.a_attr.isA'
        result = self._assist(code)
        self.assert_completion_in_result('isAlive', 'attribute', result)

    def test_hint_pep0484_attr(self):
        code = 'class Sample(object):\n' \
               '    a_attr = None  # type: threading.Thread\n'\
               '    def a_method(self):\n' \
               '        self.a_attr.isA'
        result = self._assist(code)
        self.assert_completion_in_result('isAlive', 'attribute', result)

    def test_hint_pep0484_attr_defined_by_constructor(self):
        code = 'class Sample(object):\n' \
               '    def __init__(self):\n' \
               '        self.a_attr = None  # type: threading.Thread\n' \
               '    def a_method(self):\n' \
               '        self.a_attr.isA'
        result = self._assist(code)
        self.assert_completion_in_result('isAlive', 'attribute', result)

    def test_hint_pep0484_attr_defined_by_notimplemented(self):
        code = 'class Sample(object):\n' \
               '    a_attr = NotImplemented  # type: threading.Thread\n'\
               '    def a_method(self):\n' \
               '        self.a_attr.isA'
        result = self._assist(code)
        self.assert_completion_in_result('isAlive', 'attribute', result)

    def test_hint_pep0484_attr_defined_by_notimplemented_in_constructor(self):
        code = 'class Sample(object):\n' \
               '    def __init__(self):\n' \
               '        self.a_attr = NotImplemented  # type: threading.Thread\n' \
               '    def a_method(self):\n' \
               '        self.a_attr.isA'
        result = self._assist(code)
        self.assert_completion_in_result('isAlive', 'attribute', result)

    def test_hint_pep0484_attr_for_pre_defined_object(self):
        code = 'class Other(object):\n' \
               '    def isAlive(self):\n' \
               '        pass\n' \
               '\n\n' \
               'class Sample(object):\n' \
               '    a_attr = None  # type: Other\n'\
               '    def a_method(self):\n' \
               '        self.a_attr.isA'
        result = self._assist(code)
        self.assert_completion_in_result('isAlive', 'attribute', result)

    def test_hint_pep0484_attr_for_post_defined_object(self):
        code = 'class Sample(object):\n' \
               '    a_attr = None  # type: Other\n'\
               '    def a_method(self):\n' \
               '        self.a_attr.isA'
        offset = len(code)
        code += '\n\n' \
                'class Other(object):\n' \
                '    def isAlive(self):\n' \
                '        pass\n'
        result = self._assist(code, offset)
        self.assert_completion_in_result('isAlive', 'attribute', result)

def suite():
    result = unittest.TestSuite()
    result.addTests(unittest.makeSuite(HintingTest))
    return result


if __name__ == '__main__':
    unittest.main()
