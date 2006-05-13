import unittest

from rope.codeassist import CodeAssist

class CodeAssistTest(unittest.TestCase):
    def setUp(self):
        super(CodeAssistTest, self).setUp()
        self.assist = CodeAssist()
        
    def tearDown(self):
        super(CodeAssistTest, self).tearDown()

    def test_simple_assist(self):
        self.assist.complete_code('', 0)

    def assert_proposal_in_result(self, completion, kind, result):
        for proposal in result:
            if proposal.completion == completion and proposal.kind == kind:
                return
        self.fail('Completion %s not proposed' % completion)

    def assert_proposal_not_in_result(self, completion, kind, result):
        for proposal in result:
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


if __name__ == '__main__':
    unittest.main()
