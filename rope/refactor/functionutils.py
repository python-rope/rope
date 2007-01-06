import rope.base.exceptions
import rope.base.pyobjects
from rope.base import codeanalyze


class _FunctionParser(object):

    def __init__(self, call, is_method):
        self.call = call
        self.is_method = is_method
        self.word_finder = rope.base.codeanalyze.WordRangeFinder(self.call)
        self.last_parens = self.call.rindex(')')
        self.first_parens = self.word_finder._find_parens_start(self.last_parens)

    def get_parameters(self):
        keywords = []
        args = []
        current = self.last_parens - 1
        current = self.word_finder._find_last_non_space_char(current)
        while current > self.first_parens:
            primary_start = current
            current = self.word_finder._find_primary_start(current)
            while current != self.first_parens and self.call[current] not in '=,':
                current = self.word_finder._find_last_non_space_char(current - 1)
            primary = self.call[current + 1:primary_start + 1].strip()
            if self.call[current] == '=':
                primary_start = current - 1
                current -= 1
                while current != self.first_parens and self.call[current] not in ',':
                    current = self.word_finder._find_last_non_space_char(current - 1)
                param_name = self.call[current + 1:primary_start + 1].strip()
                keywords.append((param_name, primary))
            else:
                args.append(primary)
            current = self.word_finder._find_last_non_space_char(current - 1)
        if self.is_called_as_a_method():
            args.append(self.word_finder.get_primary_at(
                        self.call.rindex('.', 0, self.first_parens) - 1))
        args.reverse()
        keywords.reverse()
        return args, keywords

    def get_instance(self):
        if self.is_called_as_a_method():
            return self.word_finder.get_primary_at(
                self.call.rindex('.', 0, self.first_parens) - 1)

    def get_function_name(self):
        if self.is_called_as_a_method():
            return self.word_finder.get_word_at(self.first_parens - 1)
        else:
            return self.word_finder.get_primary_at(self.first_parens - 1)

    def is_called_as_a_method(self):
        return self.is_method and '.' in self.call[:self.first_parens]


class DefinitionInfo(object):

    def __init__(self, function_name, is_method, args_with_defaults, args_arg,
                 keywords_arg):
        self.function_name = function_name
        self.is_method = is_method
        self.args_with_defaults = args_with_defaults
        self.args_arg = args_arg
        self.keywords_arg = keywords_arg

    def to_string(self):
        params = []
        for arg, default in self.args_with_defaults:
            if default is not None:
                params.append('%s=%s' % (arg, default))
            else:
                params.append(arg)
        if self.args_arg is not None:
            params.append('*' + self.args_arg)
        if self.keywords_arg:
            params.append('**' + self.keywords_arg)
        return '%s(%s)' % (self.function_name, ', '.join(params))

    @staticmethod
    def _read(pyfunction, code):
        scope = pyfunction.get_scope()
        parent = scope.parent
        parameter_names = pyfunction.parameters
        is_method = len(parameter_names) > 0 and \
                    (parent.pyobject == pyfunction.
                     get_parameters()[parameter_names[0]].get_object().get_type()) and \
                     parent is not None and \
                     (parent.pyobject.get_type() ==
                      rope.base.pyobjects.PyObject.get_base_type('Type'))
        info = _FunctionParser(code, is_method)
        args, keywords = info.get_parameters()
        args_arg = None
        keywords_arg = None
        if args and args[-1].startswith('**'):
            keywords_arg = args[-1][2:]
            del args[-1]
        if args and args[-1].startswith('*'):
            args_arg = args[-1][1:]
            del args[-1]
        args_with_defaults = [(name, None) for name in args]
        args_with_defaults.extend(keywords)
        return DefinitionInfo(info.get_function_name(), is_method,
                               args_with_defaults, args_arg, keywords_arg)

    @staticmethod
    def read(pyfunction):
        pymodule = pyfunction.get_module()
        source = pymodule.source_code
        lines = pymodule.lines
        line_finder = codeanalyze.LogicalLineFinder(lines)
        start_line, end_line = line_finder.get_logical_line_in(pyfunction._get_ast().lineno)
        start = lines.get_line_start(start_line)
        end = lines.get_line_end(end_line)
        start = pymodule.source_code.find('def', start) + 4
        end = pymodule.source_code.rfind(':', start, end)
        return DefinitionInfo._read(pyfunction, pymodule.source_code[start:end])


class CallInfo(object):

    def __init__(self, function_name, args, keywords, args_arg,
                 keywords_arg, is_method_call):
        self.function_name = function_name
        self.args = args
        self.keywords = keywords
        self.args_arg = args_arg
        self.keywords_arg = keywords_arg
        self.is_method_call = is_method_call

    def to_string(self):
        function = self.function_name
        if self.is_method_call:
            function = self.args[0] + '.' + self.function_name
        params = []
        start = 0
        if self.is_method_call:
            start = 1
        if self.args[start:]:
            params.extend(self.args[start:])
        if self.keywords:
            params.extend(['%s=%s' % (name, value) for name, value in self.keywords])
        if self.args_arg is not None:
            params.append('*' + self.args_arg)
        if self.keywords_arg:
            params.append('**' + self.keywords_arg)
        return '%s(%s)' % (function, ', '.join(params))

    @staticmethod
    def read(definition_info, code):
        info = _FunctionParser(code, definition_info.is_method)
        args, keywords = info.get_parameters()
        args_arg = None
        keywords_arg = None
        if args and args[-1].startswith('**'):
            keywords_arg = args[-1][2:]
            del args[-1]
        if args and args[-1].startswith('*'):
            args_arg = args[-1][1:]
            del args[-1]
        return CallInfo(info.get_function_name(), args, keywords, args_arg,
                         keywords_arg, info.is_called_as_a_method())

class ArgumentMapping(object):

    def __init__(self, definition_info, call_info):
        self.call_info = call_info
        self.param_dict = {}
        self.keyword_args = []
        self.args_arg = []
        for index, value in enumerate(call_info.args):
            if index < len(definition_info.args_with_defaults):
                name = definition_info.args_with_defaults[index][0]
                self.param_dict[name] = value
            else:
                self.args_arg.append(value)
        for name, value in call_info.keywords:
            index = -1
            for pair in definition_info.args_with_defaults:
                if pair[0] == name:
                    self.param_dict[name] = value
                    break
            else:
                self.keyword_args.append((name, value))

    def to_call_info(self, definition_info):
        args = []
        keywords = []
        for index in range(len(definition_info.args_with_defaults)):
            name = definition_info.args_with_defaults[index][0]
            if name in self.param_dict:
                args.append(self.param_dict[name])
            else:
                for i in range(index, len(definition_info.args_with_defaults)):
                    name = definition_info.args_with_defaults[i][0]
                    if name in self.param_dict:
                        keywords.append((name, self.param_dict[name]))
                break
        args.extend(self.args_arg)
        keywords.extend(self.keyword_args)
        return CallInfo(self.call_info.function_name, args, keywords,
                         self.call_info.args_arg, self.call_info.keywords_arg,
                         self.call_info.is_method_call)
