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
        self.fail('completion <%s> not proposed' % completion)

    def assert_proposal_not_in_result(self, completion, kind, result):
        for proposal in result.proposals:
            if proposal.completion == completion and proposal.kind == kind:
                self.fail('completion <%s> was proposed' % completion)

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
        code = 'sample (sdf+)\n'
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

    def test_completing_imported_names(self):
        code = 'import sys\na = sy'
        result = self.assist.complete_code(code, len(code))
        self.assert_proposal_in_result('sys', 'module', result)

    def test_completing_imported_names_with_as(self):
        code = 'import sys as mysys\na = mys'
        result = self.assist.complete_code(code, len(code))
        self.assert_proposal_in_result('mysys', 'module', result)

    def test_not_completing_imported_names_with_as(self):
        code = 'import sys as mysys\na = sy'
        result = self.assist.complete_code(code, len(code))
        self.assert_proposal_not_in_result('sys', 'module', result)

    def test_including_matching_builtins_types(self):
        code = 'my_var = Excep'
        result = self.assist.complete_code(code, len(code))
        self.assert_proposal_in_result('Exception', 'class', result)
        
    def test_including_matching_builtins_functions(self):
        code = 'my_var = zi'
        result = self.assist.complete_code(code, len(code))
        self.assert_proposal_in_result('zip', 'builtin_function', result)
        
    def test_including_keywords(self):
        code = 'fo'
        result = self.assist.complete_code(code, len(code))
        self.assert_proposal_in_result('for', 'keyword', result)

    def test_not_reporting_proposals_after_dot(self):
        code = 'a_dict = {}\nkey = 3\na_dict.ke'
        result = self.assist.complete_code(code, len(code))
        self.assert_proposal_not_in_result('key', 'global_variable', result)

    def test_proposing_local_variables_in_functions(self):
        code = 'def f(self):\n    my_var = 10\n    my_'
        result = self.assist.complete_code(code, len(code))
        self.assert_proposal_in_result('my_var', 'local_variable', result)

    def test_local_variables_override_global_ones(self):
        code = 'my_var = 20\ndef f(self):\n    my_var = 10\n    my_'
        result = self.assist.complete_code(code, len(code))
        self.assert_proposal_in_result('my_var', 'local_variable', result)

    def test_not_including_class_body_variables(self):
        code = 'class C(object):\n    my_var = 20\n    def f(self):\n        a = 20\n        my_'
        result = self.assist.complete_code(code, len(code))
        self.assert_proposal_not_in_result('my_var', 'local_variable', result)

    def test_nested_functions(self):
        code = "def my_func():\n    func_var = 20\n    def inner_func():\n        a = 20\n        func"
        result = self.assist.complete_code(code, len(code))
        self.assert_proposal_in_result('func_var', 'local_variable', result)

    def test_scope_endpoint_selection(self):
        code = "def my_func():\n    func_var = 20\n"
        result = self.assist.complete_code(code, len(code))
        self.assert_proposal_not_in_result('func_var', 'local_variable', result)

    def test_imports_inside_function(self):
        code = "def f():\n    import sys\n    sy"
        result = self.assist.complete_code(code, len(code))
        self.assert_proposal_in_result('sys', 'module', result)

    def test_imports_inside_function_dont_mix_with_globals(self):
        code = "def f():\n    import sys\nsy"
        result = self.assist.complete_code(code, len(code))
        self.assert_proposal_not_in_result('sys', 'module', result)

    def test_nested_classes_local_names(self):
        code = "global_var = 10\ndef my_func():\n    func_var = 20\n    class C(object):\n" + \
               "        def another_func(self):\n            local_var = 10\n            func"
        result = self.assist.complete_code(code, len(code))
        self.assert_proposal_in_result('func_var', 'local_variable', result)

    def test_nested_classes_global(self):
        code = "global_var = 10\ndef my_func():\n    func_var = 20\n    class C(object):\n" + \
               "        def another_func(self):\n            local_var = 10\n            globa"
        result = self.assist.complete_code(code, len(code))
        self.assert_proposal_in_result('global_var', 'global_variable', result)

    def test_nested_classes_global_function(self):
        code = "global_var = 10\ndef my_func():\n    func_var = 20\n    class C(object):\n" + \
               "        def another_func(self):\n            local_var = 10\n            my_f"
        result = self.assist.complete_code(code, len(code))
        self.assert_proposal_in_result('my_func', 'function', result)

    def test_proposing_function_parameters_in_functions(self):
        code = "def my_func(my_param):\n    my_var = 20\n    my_"
        result = self.assist.complete_code(code, len(code))
        self.assert_proposal_in_result('my_param', 'local_variable', result)

    def test_proposing_function_keyword_parameters_in_functions(self):
        code = "def my_func(my_param, *my_list, **my_kws):\n    my_var = 20\n    my_"
        result = self.assist.complete_code(code, len(code))
        self.assert_proposal_in_result('my_param', 'local_variable', result)
        self.assert_proposal_in_result('my_list', 'local_variable', result)
        self.assert_proposal_in_result('my_kws', 'local_variable', result)

    def test_not_proposing_unmatching_function_parameters_in_functions(self):
        code = "def my_func(my_param):\n    my_var = 20\n    you_"
        result = self.assist.complete_code(code, len(code))
        self.assert_proposal_not_in_result('my_param', 'local_variable', result)

    def test_ignoring_current_statement(self):
        code = "my_var = 10\nmy_tuple = (10, \n           my_"
        result = self.assist.complete_code(code, len(code))
        self.assert_proposal_in_result('my_var', 'global_variable', result)

    def test_ignoring_current_statement_brackets_continuation(self):
        code = "my_var = 10\n'hello'[10:\n        my_"
        result = self.assist.complete_code(code, len(code))
        self.assert_proposal_in_result('my_var', 'global_variable', result)

    def test_ignoring_current_statement_explicit_continuation(self):
        code = "my_var = 10\nmy_var2 = 2 + \\\n          my_"
        result = self.assist.complete_code(code, len(code))
        self.assert_proposal_in_result('my_var', 'global_variable', result)

    def test_ignoring_current_statement_while_the_first_statement_of_the_block(self):
        code = "my_var = 10\ndef f():\n    my_"
        result = self.assist.complete_code(code, len(code))
        self.assert_proposal_in_result('my_var', 'global_variable', result)

    def test_ignoring_current_statement_while_current_line_ends_with_a_colon(self):
        code = "my_var = 10\nif my_:\n    pass"
        result = self.assist.complete_code(code, 18)
        self.assert_proposal_in_result('my_var', 'global_variable', result)

    def test_ignoring_string_contents(self):
        code = "my_var = '('\nmy_"
        result = self.assist.complete_code(code, len(code))
        self.assert_proposal_in_result('my_var', 'global_variable', result)

    def test_ignoring_comment_contents(self):
        code = "my_var = 10 #(\nmy_"
        result = self.assist.complete_code(code, len(code))
        self.assert_proposal_in_result('my_var', 'global_variable', result)

    def test_ignoring_string_contents_backslash_plus_quotes(self):
        code = "my_var = '\\''\nmy_"
        result = self.assist.complete_code(code, len(code))
        self.assert_proposal_in_result('my_var', 'global_variable', result)

    def test_ignoring_string_contents_backslash_plus_backslash(self):
        code = "my_var = '\\\\'\nmy_"
        result = self.assist.complete_code(code, len(code))
        self.assert_proposal_in_result('my_var', 'global_variable', result)


if __name__ == '__main__':
    unittest.main()
