import keyword
import sys
import warnings

import rope.base.codeanalyze
import rope.base.evaluate
from rope.base import pyobjects, pynames, builtins, exceptions, worder
from rope.base.codeanalyze import SourceLinesAdapter
from rope.contrib import fixsyntax
from rope.refactor import functionutils


def code_assist(project, source_code, offset, resource=None,
                templates=None, maxfixes=1, later_locals=True):
    """Return python code completions as a list of `CodeAssistProposal`\s

    `resource` is a `rope.base.resources.Resource` object.  If
    provided, relative imports are handled.

    `maxfixes` is the maximum number of errors to fix if the code has
    errors in it.

    If `later_locals` is `False` names defined in this scope and after
    this line is ignored.

    """
    if templates is not None:
        warnings.warn('Codeassist no longer supports templates',
                      DeprecationWarning, stacklevel=2)
    assist = _PythonCodeAssist(
        project, source_code, offset, resource=resource,
        maxfixes=maxfixes, later_locals=later_locals)
    return assist()


def starting_offset(source_code, offset):
    """Return the offset in which the completion should be inserted

    Usually code assist proposals should be inserted like::

        completion = proposal.name
        result = (source_code[:starting_offset] +
                  completion + source_code[offset:])

    Where starting_offset is the offset returned by this function.

    """
    word_finder = worder.Worder(source_code, True)
    expression, starting, starting_offset = \
        word_finder.get_splitted_primary_before(offset)
    return starting_offset


def get_doc(project, source_code, offset, resource=None, maxfixes=1):
    """Get the pydoc"""
    fixer = fixsyntax.FixSyntax(project.pycore, source_code,
                                resource, maxfixes)
    pymodule = fixer.get_pymodule()
    pyname = fixer.pyname_at(offset)
    if pyname is None:
        return None
    pyobject = pyname.get_object()
    return PyDocExtractor().get_doc(pyobject)


def get_calltip(project, source_code, offset, resource=None,
                maxfixes=1, ignore_unknown=False, remove_self=False):
    """Get the calltip of a function

    The format of the returned string is
    ``module_name.holding_scope_names.function_name(arguments)``.  For
    classes `__init__()` and for normal objects `__call__()` function
    is used.

    Note that the offset is on the function itself *not* after the its
    open parenthesis.  (Actually it used to be the other way but it
    was easily confused when string literals were involved.  So I
    decided it is better for it not to try to be too clever when it
    cannot be clever enough).  You can use a simple search like::

        offset = source_code.rindex('(', 0, offset) - 1

    to handle simple situations.

    If `ignore_unknown` is `True`, `None` is returned for functions
    without source-code like builtins and extensions.

    If `remove_self` is `True`, the first parameter whose name is self
    will be removed for methods.
    """
    fixer = fixsyntax.FixSyntax(project.pycore, source_code,
                                resource, maxfixes)
    pymodule = fixer.get_pymodule()
    pyname = fixer.pyname_at(offset)
    if pyname is None:
        return None
    pyobject = pyname.get_object()
    return PyDocExtractor().get_calltip(pyobject, ignore_unknown, remove_self)


def get_definition_location(project, source_code, offset,
                            resource=None, maxfixes=1):
    """Return the definition location of the python name at `offset`

    Return a (`rope.base.resources.Resource`, lineno) tuple.  If no
    `resource` is given and the definition is inside the same module,
    the first element of the returned tuple would be `None`.  If the
    location cannot be determined ``(None, None)`` is returned.

    """
    fixer = fixsyntax.FixSyntax(project.pycore, source_code,
                                resource, maxfixes)
    pymodule = fixer.get_pymodule()
    pyname = fixer.pyname_at(offset)
    if pyname is not None:
        module, lineno = pyname.get_definition_location()
        if module is not None:
            return module.get_module().get_resource(), lineno
    return (None, None)


def find_occurrences(*args, **kwds):
    import rope.contrib.findit
    warnings.warn('Use `rope.contrib.findit.find_occurrences()` instead',
                  DeprecationWarning, stacklevel=2)
    return rope.contrib.findit.find_occurrences(*args, **kwds)


class CodeAssistProposal(object):
    """The base class for proposals reported by `code_assist`

    The `kind` instance variable shows the kind of the proposal and
    can be 'global', 'local', 'builtin', 'attribute', 'keyword',
    'parameter_keyword'.

    """

    def __init__(self, name, kind):
        self.name = name
        self.kind = kind


class CompletionProposal(CodeAssistProposal):
    """A completion proposal

    The `type` instance variable shows the type of the proposal and
    can be 'variable', 'class', 'function', 'imported' , 'paramter'
    and `None`.

    """

    def __init__(self, name, kind, type=None):
        super(CompletionProposal, self).__init__(name, kind)
        self.type = type

    def __str__(self):
        return '%s (%s, %s)' % (self.name, self.kind, self.type)

    def __repr__(self):
        return str(self)


def sorted_proposals(proposals, kindpref=None, typepref=None):
    """Sort a list of proposals

    Return a sorted list of the given `CodeAssistProposal`\s.

    `kindpref` can be a list of proposal kinds.  Defaults to
    ``['local', 'parameter_keyword', 'global', 'attribute',
    'keyword']``.

    `typepref` can be a list of proposal types.  Defaults to
    ``['class', 'function', 'variable', 'parameter', 'imported',
    'builtin', None]``.  (`None` stands for completions with no type
    like keywords.)
    """
    sorter = _ProposalSorter(proposals, kindpref, typepref)
    return sorter.get_sorted_proposal_list()


def starting_expression(source_code, offset):
    """Return the expression to complete"""
    word_finder = worder.Worder(source_code, True)
    expression, starting, starting_offset = \
        word_finder.get_splitted_primary_before(offset)
    if expression:
        return expression + '.' + starting
    return starting


def default_templates():
    warnings.warn('default_templates() is deprecated.',
                  DeprecationWarning, stacklevel=2)
    return {}


class _PythonCodeAssist(object):

    def __init__(self, project, source_code, offset, resource=None,
                 maxfixes=1, later_locals=True):
        self.project = project
        self.pycore = self.project.pycore
        self.code = source_code
        self.resource = resource
        self.maxfixes = maxfixes
        self.later_locals = later_locals
        self.word_finder = worder.Worder(source_code, True)
        self.expression, self.starting, self.offset = \
            self.word_finder.get_splitted_primary_before(offset)

    keywords = keyword.kwlist

    def _find_starting_offset(self, source_code, offset):
        current_offset = offset - 1
        while current_offset >= 0 and (source_code[current_offset].isalnum() or
                                       source_code[current_offset] in '_'):
            current_offset -= 1;
        return current_offset + 1

    def _matching_keywords(self, starting):
        result = []
        for kw in self.keywords:
            if kw.startswith(starting):
                result.append(CompletionProposal(kw, 'keyword'))
        return result

    def __call__(self):
        if self.offset > len(self.code):
            return []
        completions = list(self._code_completions().values())
        if self.expression.strip() == '' and self.starting.strip() != '':
            completions.extend(self._matching_keywords(self.starting))
        return completions

    def _dotted_completions(self, module_scope, holding_scope):
        result = {}
        found_pyname = rope.base.evaluate.eval_str(holding_scope,
                                                   self.expression)
        if found_pyname is not None:
            element = found_pyname.get_object()
            for name, pyname in element.get_attributes().items():
                if name.startswith(self.starting):
                    result[name] = CompletionProposal(
                        name, 'attribute', self._get_pyname_type(pyname))
        return result

    def _undotted_completions(self, scope, result, lineno=None):
        if scope.parent != None:
            self._undotted_completions(scope.parent, result)
        if lineno is None:
            names = scope.get_propagated_names()
        else:
            names = scope.get_names()
        for name, pyname in names.items():
            if name.startswith(self.starting):
                kind = 'local'
                if scope.get_kind() == 'Module':
                    kind = 'global'
                if lineno is None or self.later_locals or \
                   not self._is_defined_after(scope, pyname, lineno):
                    result[name] = CompletionProposal(
                        name, kind, self._get_pyname_type(pyname))

    def _from_import_completions(self, pymodule):
        module_name = self.word_finder.get_from_module(self.offset)
        if module_name is None:
            return {}
        pymodule = self._find_module(pymodule, module_name)
        result = {}
        for name in pymodule:
            if name.startswith(self.starting):
                result[name] = CompletionProposal(name, kind='global',
                                                  type='imported')
        return result

    def _find_module(self, pymodule, module_name):
        dots = 0
        while module_name[dots] == '.':
            dots += 1
        pyname = pynames.ImportedModule(pymodule,
                                        module_name[dots:], dots)
        return pyname.get_object()

    def _is_defined_after(self, scope, pyname, lineno):
        location = pyname.get_definition_location()
        if location is not None and location[1] is not None:
            if location[0] == scope.pyobject.get_module() and \
               lineno <= location[1] <= scope.get_end():
                return True

    def _get_pyname_type(self, pyname):
        if isinstance(pyname, builtins.BuiltinName):
            return 'builtin'
        if isinstance(pyname, pynames.ImportedName) or \
           isinstance(pyname, pynames.ImportedModule):
            return 'imported'
        if isinstance(pyname, pynames.ParameterName):
            return 'parameter'
        if isinstance(pyname, builtins.BuiltinName) or \
           isinstance(pyname, pynames.DefinedName):
            pyobject = pyname.get_object()
            if isinstance(pyobject, pyobjects.AbstractFunction):
                return 'function'
            if isinstance(pyobject, pyobjects.AbstractClass):
                return 'class'
        return 'variable'

    def _code_completions(self):
        lineno = self.code.count('\n', 0, self.offset) + 1
        fixer = fixsyntax.FixSyntax(self.pycore, self.code,
                                    self.resource, self.maxfixes)
        pymodule = fixer.get_pymodule()
        module_scope = pymodule.get_scope()
        code = pymodule.source_code
        lines = code.split('\n')
        result = {}
        start = fixsyntax._logical_start(lines, lineno)
        indents = fixsyntax._get_line_indents(lines[start - 1])
        inner_scope = module_scope.get_inner_scope_for_line(start, indents)
        if self.word_finder.is_a_name_after_from_import(self.offset):
            return self._from_import_completions(pymodule)
        if self.expression.strip() != '':
            result.update(self._dotted_completions(module_scope, inner_scope))
        else:
            result.update(self._keyword_parameters(module_scope.pyobject,
                                                   inner_scope))
            self._undotted_completions(inner_scope, result, lineno=lineno)
        return result

    def _keyword_parameters(self, pymodule, scope):
        offset = self.offset
        if offset == 0:
            return {}
        word_finder = worder.Worder(self.code, True)
        lines = SourceLinesAdapter(self.code)
        lineno = lines.get_line_number(offset)
        if word_finder.is_on_function_call_keyword(offset - 1):
            name_finder = rope.base.evaluate.ScopeNameFinder(pymodule)
            function_parens = word_finder.\
                find_parens_start_from_inside(offset - 1)
            primary = word_finder.get_primary_at(function_parens - 1)
            try:
                function_pyname = rope.base.evaluate.\
                    eval_str(scope, primary)
            except exceptions.BadIdentifierError, e:
                return {}
            if function_pyname is not None:
                pyobject = function_pyname.get_object()
                if isinstance(pyobject, pyobjects.AbstractFunction):
                    pass
                elif isinstance(pyobject, pyobjects.AbstractClass) and \
                     '__init__' in pyobject:
                    pyobject = pyobject['__init__'].get_object()
                elif '__call__' in pyobject:
                    pyobject = pyobject['__call__'].get_object()
                if isinstance(pyobject, pyobjects.AbstractFunction):
                    param_names = []
                    param_names.extend(
                        pyobject.get_param_names(special_args=False))
                    result = {}
                    for name in param_names:
                        if name.startswith(self.starting):
                            result[name + '='] = CompletionProposal(
                                name + '=', 'parameter_keyword')
                    return result
        return {}


class _ProposalSorter(object):
    """Sort a list of code assist proposals"""

    def __init__(self, code_assist_proposals, kindpref=None, typepref=None):
        self.proposals = code_assist_proposals
        if kindpref is None:
            kindpref = ['local', 'parameter_keyword', 'global',
                        'attribute', 'keyword']
        self.kindpref = kindpref
        if typepref is None:
            typepref = ['class', 'function', 'variable',
                        'parameter', 'imported', 'builtin', None]
        self.typerank = dict((type, index)
                              for index, type in enumerate(typepref))

    def get_sorted_proposal_list(self):
        """Return a list of `CodeAssistProposal`"""
        proposals = {}
        for proposal in self.proposals:
            proposals.setdefault(proposal.kind, []).append(proposal)
        result = []
        for kind in self.kindpref:
            kind_proposals = proposals.get(kind, [])
            kind_proposals = [proposal for proposal in kind_proposals
                              if proposal.type in self.typerank]
            kind_proposals.sort(self._proposal_cmp)
            result.extend(kind_proposals)
        return result

    def _proposal_cmp(self, proposal1, proposal2):
        if proposal1.type != proposal2.type:
            return cmp(self.typerank.get(proposal1.type, 100),
                       self.typerank.get(proposal2.type, 100))
        return self._compare_underlined_names(proposal1.name,
                                              proposal2.name)

    def _compare_underlined_names(self, name1, name2):
        def underline_count(name):
            result = 0
            while result < len(name) and name[result] == '_':
                result += 1
            return result
        underline_count1 = underline_count(name1)
        underline_count2 = underline_count(name2)
        if underline_count1 != underline_count2:
            return cmp(underline_count1, underline_count2)
        return cmp(name1, name2)


class PyDocExtractor(object):

    def get_doc(self, pyobject):
        if isinstance(pyobject, pyobjects.AbstractFunction):
            return self._get_function_docstring(pyobject)
        elif isinstance(pyobject, pyobjects.AbstractClass):
            return self._get_class_docstring(pyobject)
        elif isinstance(pyobject, pyobjects.AbstractModule):
            return self._trim_docstring(pyobject.get_doc())
        return None

    def get_calltip(self, pyobject, ignore_unknown=False, remove_self=False):
        try:
            if isinstance(pyobject, pyobjects.AbstractClass):
                pyobject = pyobject['__init__'].get_object()
            if not isinstance(pyobject, pyobjects.AbstractFunction):
                pyobject = pyobject['__call__'].get_object()
        except exceptions.AttributeNotFoundError:
            return None
        if ignore_unknown and not isinstance(pyobject, pyobjects.PyFunction):
            return
        if isinstance(pyobject, pyobjects.AbstractFunction):
            result = self._get_function_signature(pyobject, add_module=True)
            if remove_self and self._is_method(pyobject):
                return result.replace('(self)', '()').replace('(self, ', '(')
            return result

    def _get_class_docstring(self, pyclass):
        contents = self._trim_docstring(pyclass.get_doc(), 2)
        supers = [super.get_name() for super in pyclass.get_superclasses()]
        doc = 'class %s(%s):\n\n' % (pyclass.get_name(), ', '.join(supers)) + contents

        if '__init__' in pyclass:
            init = pyclass['__init__'].get_object()
            if isinstance(init, pyobjects.AbstractFunction):
                doc += '\n\n' + self._get_single_function_docstring(init)
        return doc

    def _get_function_docstring(self, pyfunction):
        functions = [pyfunction]
        if self._is_method(pyfunction):
            functions.extend(self._get_super_methods(pyfunction.parent,
                                                     pyfunction.get_name()))
        return '\n\n'.join([self._get_single_function_docstring(function)
                            for function in functions])

    def _is_method(self, pyfunction):
        return isinstance(pyfunction, pyobjects.PyFunction) and \
               isinstance(pyfunction.parent, pyobjects.PyClass)

    def _get_single_function_docstring(self, pyfunction):
        signature = self._get_function_signature(pyfunction)
        docs = self._trim_docstring(pyfunction.get_doc(), indents=2)
        return signature + ':\n\n' + docs

    def _get_super_methods(self, pyclass, name):
        result = []
        for super_class in pyclass.get_superclasses():
            if name in super_class:
                function = super_class[name].get_object()
                if isinstance(function, pyobjects.AbstractFunction):
                    result.append(function)
            result.extend(self._get_super_methods(super_class, name))
        return result

    def _get_function_signature(self, pyfunction, add_module=False):
        location = self._location(pyfunction, add_module)
        if isinstance(pyfunction, pyobjects.PyFunction):
            info = functionutils.DefinitionInfo.read(pyfunction)
            return location + info.to_string()
        else:
            return '%s(%s)' % (location + pyfunction.get_name(),
                               ', '.join(pyfunction.get_param_names()))

    def _location(self, pyobject, add_module=False):
        location = []
        parent = pyobject.parent
        while parent and not isinstance(parent, pyobjects.AbstractModule):
            location.append(parent.get_name())
            location.append('.')
            parent = parent.parent
        if add_module:
            if isinstance(pyobject, pyobjects.PyFunction):
                module = pyobject.get_module()
                location.insert(0, self._get_module(pyobject))
            if isinstance(parent, builtins.BuiltinModule):
                location.insert(0, parent.get_name() + '.')
        return ''.join(location)

    def _get_module(self, pyfunction):
        module = pyfunction.get_module()
        if module is not None:
            resource = module.get_resource()
            if resource is not None:
                return pyfunction.pycore.modname(resource) + '.'
        return ''

    def _trim_docstring(self, docstring, indents=0):
        """The sample code from :PEP:`257`"""
        if not docstring:
            return ''
        # Convert tabs to spaces (following normal Python rules)
        # and split into a list of lines:
        lines = docstring.expandtabs().splitlines()
        # Determine minimum indentation (first line doesn't count):
        indent = sys.maxint
        for line in lines[1:]:
            stripped = line.lstrip()
            if stripped:
                indent = min(indent, len(line) - len(stripped))
        # Remove indentation (first line is special):
        trimmed = [lines[0].strip()]
        if indent < sys.maxint:
            for line in lines[1:]:
                trimmed.append(line[indent:].rstrip())
        # Strip off trailing and leading blank lines:
        while trimmed and not trimmed[-1]:
            trimmed.pop()
        while trimmed and not trimmed[0]:
            trimmed.pop(0)
        # Return a single string:
        return '\n'.join((' ' * indents + line for line in trimmed))


# Deprecated classes

class TemplateProposal(CodeAssistProposal):
    def __init__(self, name, template):
        warnings.warn('TemplateProposal is deprecated.',
                      DeprecationWarning, stacklevel=2)
        super(TemplateProposal, self).__init__(name, 'template')
        self.template = template


class Template(object):

    def __init__(self, template):
        self.template = template
        warnings.warn('Template is deprecated.',
                      DeprecationWarning, stacklevel=2)

    def variables(self):
        return []

    def substitute(self, mapping):
        return self.template

    def get_cursor_location(self, mapping):
        return len(self.template)
