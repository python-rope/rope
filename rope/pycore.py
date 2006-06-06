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
        return Scope()

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

    def __init__(self, object_=None):
        self.object = object_

    def get_attributes(self):
        return self.object.attributes
    
    def get_type(self):
        return self.object.type


class Scope(object):
    def get_names(self):
        return {'sample_func': None}


class _GlobalVisitor(object):

    def __init__(self, pycore):
        self.names = {}
        self.pycore = pycore
    
    def visitClass(self, node):
        self.names[node.name] = PyName(_ClassVisitor.make_class(node))

    def visitFunction(self, node):
        self.names[node.name] = PyName(PyObject(PyType.get_type('Function')))

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


class _ClassVisitor(object):

    def __init__(self):
        self.names = {}

    def visitFunction(self, node):
        self.names[node.name] = PyName(PyObject(PyType.get_type('Function')))
        if node.name == '__init__':
            new_visitor = _ClassInitVisitor()
            compiler.walk(node, new_visitor)
            self.names.update(new_visitor.names)

    def visitAssName(self, node):
        self.names[node.name] = PyName()

    def visitClass(self, node):
        self.names[node.name] = PyName(_ClassVisitor.make_class(node))

    @staticmethod
    def make_class(node):
        new_visitor = _ClassVisitor()
        for n in node.getChildNodes():
            compiler.walk(n, new_visitor)
        return PyType(new_visitor.names)


class _ClassInitVisitor(object):

    def __init__(self):
        self.names = {}
    
    def visitAssAttr(self, node):
        if node.expr.name == 'self':
            self.names[node.attrname] = PyName()

