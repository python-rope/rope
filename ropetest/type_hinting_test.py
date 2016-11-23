try:
    import unittest2 as unittest
except ImportError:
    import unittest


from rope.contrib.codeassist import code_assist
from ropetest import testutils


class AbstractHintingTest(unittest.TestCase):

    def setUp(self):
        super(AbstractHintingTest, self).setUp()
        self.project = testutils.sample_project()

    def tearDown(self):
        testutils.remove_project(self.project)
        super(AbstractHintingTest, self).tearDown()

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

    def run(self, result=None):
        if self.__class__.__name__.startswith('Abstract'):
            return
        super(AbstractHintingTest, self).run(result)


class DocstringParamHintingTest(AbstractHintingTest):

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


class DocstringReturnHintingTest(AbstractHintingTest):

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


class AbstractAssignmentHintingTest(AbstractHintingTest):

    def _make_class_hint(self, type_str):
        raise NotImplementedError

    def _make_constructor_hint(self, type_str):
        raise NotImplementedError

    def test_hint_attr(self):
        code = 'class Sample(object):\n' \
               + self._make_class_hint('threading.Thread') + \
               '    def a_method(self):\n' \
               '        self.a_attr.isA'
        result = self._assist(code)
        self.assert_completion_in_result('isAlive', 'attribute', result)

    def test_hierarchical_hint_attr(self):
        code = 'class ISample(object):\n' \
               + self._make_class_hint('threading.Thread') + \
               '\n\n' \
               'class Sample(ISample):\n' \
               '    a_attr = None\n'\
               '    def a_method(self):\n' \
               '        self.a_attr.isA'
        result = self._assist(code)
        self.assert_completion_in_result('isAlive', 'attribute', result)

    def test_hint_defined_by_constructor(self):
        code = 'class Sample(object):\n' \
               '    def __init__(self, arg):\n' \
               + self._make_constructor_hint('threading.Thread') + \
               '    def a_method(self):\n' \
               '        self.a_attr.isA'
        result = self._assist(code)
        self.assert_completion_in_result('isAlive', 'attribute', result)

    def test_hint_attr_redefined_by_constructor(self):
        code = 'class Sample(object):\n' \
               + self._make_class_hint('threading.Thread') + \
               '    def __init__(self):\n' \
               '        self.a_attr = None\n' \
               '    def a_method(self):\n' \
               '        self.a_attr.isA'
        result = self._assist(code)
        self.assert_completion_in_result('isAlive', 'attribute', result)

    def test_hierarchical_hint_attr_redefined_by_constructor(self):
        code = 'class ISample(object):\n' \
               + self._make_class_hint('threading.Thread') + \
               '\n\n' \
               'class Sample(ISample):\n' \
               '    def __init__(self):\n' \
               '        self.a_attr = None\n' \
               '    def a_method(self):\n' \
               '        self.a_attr.isA'
        result = self._assist(code)
        self.assert_completion_in_result('isAlive', 'attribute', result)

    def test_hint_attr_for_pre_defined_type(self):
        code = 'class Other(object):\n' \
               '    def isAlive(self):\n' \
               '        pass\n' \
               '\n\n' \
               'class Sample(object):\n' \
               + self._make_class_hint('Other') + \
               '    def a_method(self):\n' \
               '        self.a_attr.isA'
        result = self._assist(code)
        self.assert_completion_in_result('isAlive', 'attribute', result)

    def test_hint_attr_for_post_defined_type(self):
        code = 'class Sample(object):\n' \
               + self._make_class_hint('Other') + \
               '    def a_method(self):\n' \
               '        self.a_attr.isA'
        offset = len(code)
        code += '\n\n' \
                'class Other(object):\n' \
                '    def isAlive(self):\n' \
                '        pass\n'
        result = self._assist(code, offset)
        self.assert_completion_in_result('isAlive', 'attribute', result)


class DocstringNoneAssignmentHintingTest(AbstractAssignmentHintingTest):

    def _make_class_hint(self, type_str):
        return '    """:type a_attr: ' + type_str + '"""\n' \
               '    a_attr = None\n'

    def _make_constructor_hint(self, type_str):
        return '        """:type arg: ' + type_str + '"""\n' \
               '        self.a_attr = arg\n'


class DocstringNotImplementedAssignmentHintingTest(AbstractAssignmentHintingTest):

    def _make_class_hint(self, type_str):
        return '    """:type a_attr: ' + type_str + '"""\n' \
               '    a_attr = NotImplemented\n'

    def _make_constructor_hint(self, type_str):
        return '        """:type arg: ' + type_str + '"""\n' \
               '        self.a_attr = arg\n'



class PEP0484CommentNoneAssignmentHintingTest(AbstractAssignmentHintingTest):

    def _make_class_hint(self, type_str):
        return '    a_attr = None  # type: ' + type_str + '\n'

    def _make_constructor_hint(self, type_str):
        return '        self.a_attr = None  # type: ' + type_str + '\n'


class PEP0484CommentNotImplementedAssignmentHintingTest(AbstractAssignmentHintingTest):

    def _make_class_hint(self, type_str):
        return '    a_attr = NotImplemented  # type: ' + type_str + '\n'

    def _make_constructor_hint(self, type_str):
        return '        self.a_attr = NotImplemented  # type: ' + type_str + '\n'


class RegressionHintingTest(AbstractHintingTest):

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


def suite():
    result = unittest.TestSuite()
    result.addTests(unittest.makeSuite(DocstringParamHintingTest))
    result.addTests(unittest.makeSuite(DocstringReturnHintingTest))
    result.addTests(unittest.makeSuite(DocstringNoneAssignmentHintingTest))
    result.addTests(unittest.makeSuite(DocstringNotImplementedAssignmentHintingTest))
    result.addTests(unittest.makeSuite(PEP0484CommentNoneAssignmentHintingTest))
    result.addTests(unittest.makeSuite(PEP0484CommentNotImplementedAssignmentHintingTest))
    result.addTests(unittest.makeSuite(RegressionHintingTest))
    return result


if __name__ == '__main__':
    unittest.main()
