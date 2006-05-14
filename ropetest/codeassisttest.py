import unittest

from rope.codeassist import CodeAssist, RopeSyntaxError

class CodeAssistTest(unittest.TestCase):
    def setUp(self):
        super(CodeAssistTest, self).setUp()
        self.assist = CodeAssist()
        
    def tearDown(self):
        super(CodeAssistTest, self).tearDown()

    def test_simple_assist(self):
        self.assist.complete_code('', 0)

    def assert_proposal_in_result(self, completion, kind, result):
        for proposal in result.proposals:
            if proposal.completion == completion and proposal.kind == kind:
                return
        self.fail('Completion %s not proposed' % completion)

    def assert_proposal_not_in_result(self, completion, kind, result):
        for proposal in result.proposals:
            if proposal.completion == completion and proposal.kind == kind:
                self.fail('Completion %s was proposed' % completion)

    def test_completing_global_variables(self):
        code = 'my_global = 10\nt = my'
        result = self.assist.complete_code(code, len(code))
        self.assert_proposal_in_result('my_global', 'global_variable', result)

    def test_not_proposing_unmatched_vars(self):
        code = 'my_global = 10\nt = you'
        result = self.assist.complete_code(code, len(code))
        self.assert_proposal_not_in_result('my_global', 'global_variable', result)

    def test_not_proposing_unmatched_vars_with_underlined_starting(self):
        code = 'my_global = 10\nt = you_'
        result = self.assist.complete_code(code, len(code))
        self.assert_proposal_not_in_result('my_global', 'global_variable', result)

    def test_not_proposing_local_assigns_as_global_completions(self):
        code = 'def f():    my_global = 10\nt = my_'
        result = self.assist.complete_code(code, len(code))
        self.assert_proposal_not_in_result('my_global', 'global_variable', result)

    def test_proposing_functions(self):
        code = 'def my_func():    return 2\nt = my_'
        result = self.assist.complete_code(code, len(code))
        self.assert_proposal_in_result('my_func', 'function', result)

    def test_proposing_classes(self):
        code = 'class Sample(object):    pass\nt = Sam'
        result = self.assist.complete_code(code, len(code))
        self.assert_proposal_in_result('Sample', 'class', result)

    def test_proposing_each_name_at_most_once(self):
        code = 'variable = 10\nvariable = 20\nt = vari'
        result = self.assist.complete_code(code, len(code))
        count = len([x for x in result.proposals
                     if x.completion == 'variable' and x.kind == 'global_variable'])
        self.assertEquals(1, count)

    def test_throwing_exception_in_case_of_syntax_errors(self):
        code = 'sample (sdf\n'
        self.assertRaises(RopeSyntaxError, 
                          lambda: self.assist.complete_code(code, len(code)))
    
    def test_ignoring_errors_in_current_line(self):
        code = 'def my_func():    return 2\nt = '
        result = self.assist.complete_code(code, len(code))
        self.assert_proposal_in_result('my_func', 'function', result)

    def test_not_reporting_variables_in_current_line(self):
        code = 'def my_func():    return 2\nt = my_'
        result = self.assist.complete_code(code, len(code))
        self.assert_proposal_not_in_result('my_', 'global_variable', result)

    def test_completion_result(self):
        code = 'my_global = 10\nt = my'
        result = self.assist.complete_code(code, len(code))
        self.assertEquals(len(code) - 2, result.start_offset)
        self.assertEquals(len(code), result.end_offset)


if __name__ == '__main__':
    unittest.main()
