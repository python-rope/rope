import compiler

import rope.exceptions


class ModuleNotFoundException(rope.exceptions.RopeException):
    """Module not found exception"""


class PyCore(object):

    def __init__(self, project):
        self.project = project

    def get_module(self, name):
        results = self.project.find_module(name)
        if not results:
            raise ModuleNotFoundException('Module %s not found' % name)
        result = results[0]
        return self._create(results[0])

    def get_string_module(self, module_content):
        attributes = {}
        ast = compiler.parse(module_content)
        visitor = _GlobalVisitor(self)
        compiler.walk(ast, visitor)
        attributes.update(visitor.names)
        result = PyObject(PyType.get_type('Module'), attributes)
        result.is_package = False
        return result

    def get_string_scope(self, module_content):
        module = self.get_string_module(module_content)
        return GlobalScope(self, module)

    def _create(self, resource):
        if resource.is_folder():
            attributes = {}
            for child in resource.get_children():
                if child.is_folder():
                    attributes[child.get_name()] = PyName(self.create(child))
                elif child.get_name().endswith('.py') and child.get_name() != '__init__.py':
                    name = child.get_name()[:-3]
                    attributes[name] = PyName(self._create(child))
            result = PyObject(PyType.get_type('Module'), attributes)
            result.is_package = True
            return result
        else:
            return self.get_string_module(resource.read())


class PyObject(object):

    def __init__(self, type_, attributes=None):
        self.type = type_
        if attributes is None:
            attributes = {}
        self.object_attributes = attributes
    
    def get_attributes(self):
        return self.object_attributes
    
    attributes = property(fget=get_attributes)


class PyType(PyObject):

    def __init__(self, attributes=None, bases=None, is_base_type=False):
        if attributes is None:
            attributes = {}
        if bases is None:
            bases = []
        py_type = self
        if not is_base_type:
            py_type = PyType.get_type('Type')
        super(PyType, self).__init__(py_type, attributes)
        self.bases = bases

    @staticmethod
    def get_type(name):
        if not hasattr(PyType, 'types'):
            PyType.types = {}
            PyType.types['Type'] = PyType(is_base_type=True)
            PyType.types['Module'] = PyType()
            PyType.types['Function'] = PyType()
            PyType.types['Unknown'] = PyType()
        return PyType.types[name]


class PyName(object):

    def __init__(self, object_=None, ast=None):
        self.object = object_
        self.ast = ast

    def get_attributes(self):
        return self.object.attributes
    
    def get_type(self):
        if self.object:
            return self.object.type
        else:
            return PyType.get_type('Unknown')

    def _has_block(self):
        return self.ast is not None
    
    def _get_ast(self):
        return self.ast


class Scope(object):

    def __init__(self, pycore, pyname):
        self.pycore = pycore
        self.pyname = pyname
    
    def get_names(self):
        return self.pyname.get_attributes()

    def get_scopes(self):
        '''Returns the subscopes of this scope.
        
        The returned scopes should be sorted by the order they appear
        '''
        block_objects = [pyname for pyname in self.pyname.get_attributes().values()
                         if pyname._has_block()]
        def block_compare(x, y):
            return cmp(x._get_ast().lineno, y._get_ast().lineno)
        block_objects.sort(cmp=block_compare)
        result = []
        for block in block_objects:
            if block.get_type() == PyType.get_type('Function'):
                result.append(FunctionScope(self.pycore, block))
            elif block.get_type() == PyType.get_type('Type'):
                result.append(ClassScope(self.pycore, block))
            else:
                result.append(GlobalScope(self.pycore, block))
        return result

    def get_lineno(self):
        return self.pyname._get_ast().lineno

    def get_kind(self):
        pass


class GlobalScope(Scope):

    def __init__(self, pycore, module):
        super(GlobalScope, self).__init__(pycore, module)

    def get_lineno(self):
        return 1

    def get_kind(self):
        return 'Module'

class FunctionScope(Scope):
    
    def __init__(self, pycore, pyname):
        super(FunctionScope, self).__init__(pycore, pyname)
    
    def get_names(self):
        result = {}
        for name in self.pyname.object.parameters:
            result[name] = PyName()
        new_visitor = _FunctionVisitor(self.pycore)
        for n in self.pyname._get_ast().getChildNodes():
            compiler.walk(n, new_visitor)
        result.update(new_visitor.names)
        return result

    def get_scopes(self):
        new_visitor = _FunctionVisitor(self.pycore)
        for n in self.pyname._get_ast().getChildNodes():
            compiler.walk(n, new_visitor)
        return []

    def get_kind(self):
        return 'Function'


class ClassScope(Scope):

    def get_names(self):
        return {}

    def get_kind(self):
        return 'Class'


class _ScopeVisitor(object):

    def __init__(self, pycore):
        self.names = {}
        self.pycore = pycore
    
    def visitClass(self, node):
        self.names[node.name] = PyName(_ClassVisitor.make_class(self.pycore, node), node)

    def visitFunction(self, node):
        pyobject = PyObject(PyType.get_type('Function'))
        pyobject.parameters = node.argnames
        self.names[node.name] = PyName(pyobject, node)

    def visitAssName(self, node):
        self.names[node.name] = PyName()

    def visitImport(self, node):
        for import_pair in node.names:
            name, alias = import_pair
            imported = name
            if alias is not None:
                imported = alias
            try:
                module = self.pycore.get_module(name)
            except ModuleNotFoundException:
                module = PyObject(PyType.get_type('Module'))
            self.names[imported] = PyName(module)

    def visitFrom(self, node):
        try:
            module = self.pycore.get_module(node.modname)
        except ModuleNotFoundException:
            module = PyObject(PyType.get_type('Module'))

        if node.names[0][0] == '*':
            if module.is_package:
                return
            for name, pyname in module.attributes.iteritems():
                if not name.startswith('_'):
                    self.names[name] = pyname
        else:
            for (name, alias) in node.names:
                imported = name
                if alias is not None:
                    imported = alias
                if module.attributes.has_key(name):
                    self.names[imported] = module.attributes[name]
                else:
                    self.names[imported] = PyName()


class _GlobalVisitor(_ScopeVisitor):

    def __init__(self, pycore):
        super(_GlobalVisitor, self).__init__(pycore)
    

class _ClassVisitor(_ScopeVisitor):

    def __init__(self, pycore):
        super(_ClassVisitor, self).__init__(pycore)

    def visitFunction(self, node):
        pyobject = PyObject(PyType.get_type('Function'))
        self.names[node.name] = PyName(pyobject, node)
        pyobject.parameters = node.argnames
        if node.name == '__init__':
            new_visitor = _ClassInitVisitor()
            compiler.walk(node, new_visitor)
            self.names.update(new_visitor.names)

    def visitAssName(self, node):
        self.names[node.name] = PyName()

    def visitClass(self, node):
        self.names[node.name] = PyName(_ClassVisitor.make_class(self.pycore, node), node)

    @staticmethod
    def make_class(pycore, node):
        new_visitor = _ClassVisitor(pycore)
        for n in node.getChildNodes():
            compiler.walk(n, new_visitor)
        return PyType(new_visitor.names)


class _FunctionVisitor(_ScopeVisitor):

    def __init__(self, pycore):
        super(_FunctionVisitor, self).__init__(pycore)


class _ClassInitVisitor(object):

    def __init__(self):
        self.names = {}
    
    def visitAssAttr(self, node):
        if node.expr.name == 'self':
            self.names[node.attrname] = PyName()

