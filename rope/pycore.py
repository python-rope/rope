import compiler


class PyCore(object):

    def __init__(self, project):
        self.project = project

    def get_module(self, name):
        results = self.project.find_module(name)
        result = results[0]
        return self.create(results[0])

    def create(self, resource):
        if resource.is_folder():
            attributes = {}
            for child in resource.get_children():
                if child.is_folder():
                    attributes[child.get_name()] = self.create(child)
                elif child.get_name().endswith('.py') and child.get_name() != '__init__.py':
                    attributes[child.get_name()[:-3]] = self.create(child)
            return PyObject(PyType.get_type('Module'), attributes)
        else:
            attributes = {}
            ast = compiler.parse(resource.read())
            visitor = _GlobalVisitor()
            compiler.walk(ast, visitor)
            attributes.update(visitor.result)
            return PyObject(PyType.get_type('Module'), attributes)

    def create_module(self, contents):
        attributes = {}
        ast = compiler.parse(contents)
        visitor = _GlobalVisitor()
        compiler.walk(ast, visitor)
        attributes.update(visitor.result)
        return PyObject(PyType.get_type('Module'), attributes)



class PyObject(object):

    def __init__(self, py_type, attributes=None):
        self.type = py_type
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


class _GlobalVisitor(object):

    def __init__(self):
        self.result = {}
    
    def visitClass(self, node):
        self.result[node.name] = _ClassVisitor.make_class(node)

    def visitFunction(self, node):
        self.result[node.name] = PyObject(py_type=PyType.get_type('Function'))

    def visitAssName(self, node):
        self.result[node.name] = PyObject(PyType.get_type('Unknown'))


class _ClassVisitor(object):

    def __init__(self):
        self.children = {}

    def visitFunction(self, node):
        self.children[node.name] = PyObject(PyType.get_type('Function'))
        if node.name == '__init__':
            new_visitor = _ClassInitVisitor()
            compiler.walk(node, new_visitor)
            self.children.update(new_visitor.vars)

    def visitAssName(self, node):
        self.children[node.name] = PyObject(PyType.get_type('Unknown'))

    def visitClass(self, node):
        self.children[node.name] = _ClassVisitor.make_class(node)

    @staticmethod
    def make_class(node):
        new_visitor = _ClassVisitor()
        for n in node.getChildNodes():
            compiler.walk(n, new_visitor)
        return PyType(new_visitor.children)


class _ClassInitVisitor(object):

    def __init__(self):
        self.vars = {}
    
    def visitAssAttr(self, node):
        if node.expr.name == 'self':
            self.vars[node.attrname] = PyObject(PyType.get_type('Unknown'))

