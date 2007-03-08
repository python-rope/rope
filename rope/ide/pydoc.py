import sys

from rope.base import pyobjects
from rope.refactor import functionutils


def get_doc(pyobject):
    return PyDocExtractor().get_doc(pyobject)

class PyDocExtractor(object):

    def get_doc(self, pyobject):
        if isinstance(pyobject, pyobjects.AbstractFunction):
            return self._get_function_docstring(pyobject)
        elif isinstance(pyobject, pyobjects.AbstractClass):
            return self._get_class_docstring(pyobject)
        elif isinstance(pyobject, pyobjects.AbstractModule):
            return self._trim_docstring(pyobject.get_doc())
        return None


    def _get_class_docstring(self, pyclass):
        contents = self._trim_docstring(pyclass.get_doc(), 2)
        supers = [super.get_name() for super in pyclass.get_superclasses()]
        doc = 'class %s(%s)\n\n' % (pyclass.get_name(), ', '.join(supers)) + contents
              
        if '__init__' in pyclass.get_attributes():
            init = pyclass.get_attribute('__init__').get_object()
            if isinstance(init, pyobjects.AbstractFunction):
                doc += '\n\n' + self._get_single_function_docstring(init)
        return doc

    def _get_function_docstring(self, pyfunction):
        functions = [pyfunction]
        if isinstance(pyfunction.parent, pyobjects.PyClass):
            functions.extend(self._get_super_methods(pyfunction.parent,
                                                     pyfunction.get_name()))
        return '\n\n'.join([self._get_single_function_docstring(function)
                            for function in functions])

    def _get_single_function_docstring(self, pyfunction):
        signature = self._get_function_signature(pyfunction)
        if isinstance(pyfunction.parent, pyobjects.PyClass):
            signature = pyfunction.parent.get_name() + '.' + signature
            self._get_super_methods(pyfunction.parent, pyfunction.get_name())
        return signature + '\n\n' + self._trim_docstring(pyfunction.get_doc(),
                                                         indents=2)

    def _get_super_methods(self, pyclass, name):
        result = []
        for super_class in pyclass.get_superclasses():
            if name in super_class.get_attributes():
                function = super_class.get_attribute(name).get_object()
                if isinstance(function, pyobjects.AbstractFunction):
                    result.append(function)
            result.extend(self._get_super_methods(super_class, name))
        return result

    def _get_function_signature(self, pyfunction):
        if isinstance(pyfunction, pyobjects.PyFunction):
            info = functionutils.DefinitionInfo.read(pyfunction)
            return info.to_string()
        else:
            return '%s(%s)' % (pyfunction.get_name(),
                               ', '.join(pyfunction.get_param_names()))

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
