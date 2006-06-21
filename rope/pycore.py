import compiler
import os
import subprocess
import sys

import rope.exceptions
from rope.exceptions import RopeException


class ModuleNotFoundException(rope.exceptions.RopeException):
    """Module not found exception"""


class PyCore(object):

    def __init__(self, project):
        self.project = project
        self.module_map = {}

    def get_module(self, name):
        results = self.find_module(name)
        if not results:
            raise ModuleNotFoundException('Module %s not found' % name)
        result = results[0]
        return self._create(results[0])

    def get_string_module(self, module_content):
        ast = compiler.parse(module_content)
        return PyModule(self, ast)

    def get_string_scope(self, module_content):
        return self.get_string_module(module_content).get_scope()

    def _invalidate_resource_cache(self, resource):
        if resource in self.module_map:
            del self.module_map[resource]
            resource.remove_change_observer(self._invalidate_resource_cache)

    def _create(self, resource):
        if resource in self.module_map:
            return self.module_map[resource]
        if resource.is_folder():
            result = PyPackage(self, resource)
        else:
            result =  self.get_string_module(resource.read())
        self.module_map[resource] = result
        resource.add_change_observer(self._invalidate_resource_cache)
        return result

    def create_module(self, src_folder, new_module):
        packages = new_module.split('.')
        parent = src_folder
        for package in packages[:-1]:
            parent = parent.get_child(package)
        return parent.create_file(packages[-1] + '.py')

    def create_package(self, src_folder, new_package):
        packages = new_package.split('.')
        parent = src_folder
        for package in packages[:-1]:
            parent = parent.get_child(package)
        created_package = parent.create_folder(packages[-1])
        created_package.create_file('__init__.py')
        return created_package

    def find_module(self, module_name):
        source_folders = self.get_source_folders()
        packages = module_name.split('.')
        result = []
        for src in source_folders:
            module = src
            found = True
            for pkg in packages[:-1]:
                if  module.is_folder() and module.has_child(pkg):
                    module = module.get_child(pkg)
                else:
                    found = False
                    break

            if module.is_folder() and module.has_child(packages[-1]) and\
               module.get_child(packages[-1]).is_folder():
                module = module.get_child(packages[-1])
            elif module.is_folder() and \
                 module.has_child(packages[-1] + '.py') and \
                 not module.get_child(packages[-1] + '.py').is_folder():
                module = module.get_child(packages[-1] + '.py')
            else:
                found = False
            if found:
                result.append(module)
        return result

    def _is_package(self, folder):
        init_dot_py = folder.get_path() + '/__init__.py'
        try:
            init_dot_py_file = self.project.get_resource(init_dot_py)
            if not init_dot_py_file.is_folder():
                return True
        except RopeException:
            pass
        return False

    def _find_source_folders(self, folder):
        for resource in folder.get_folders():
            if self._is_package(resource):
                return [folder]
        result = []
        for resource in folder.get_files():
            if resource.get_name().endswith('.py'):
                result.append(folder)
        for resource in folder.get_folders():
            result.extend(self._find_source_folders(resource))
        return result

    def get_source_folders(self):
        return self._find_source_folders(self.project.get_root_folder())


class PyObject(object):

    def __init__(self, type_):
        if type_ is None:
            type_ = self
        self.type = type_
    
    def get_attributes(self):
        if self.type is self:
            return {}
        return self.type.get_attributes()

    def get_type(self):
        return self.type

    @staticmethod
    def get_base_type(name):
        if not hasattr(PyObject, 'types'):
            PyObject.types = {}
            base_type = PyObject(None)
            PyObject.types['Type'] = base_type
            PyObject.types['Module'] = PyObject(base_type)
            PyObject.types['Function'] = PyObject(base_type)
            PyObject.types['Unknown'] = PyObject(base_type)
        return PyObject.types[name]


class PyDefinedObject(PyObject):

    def __init__(self, type_, pycore, ast_node, parent):
        super(PyDefinedObject, self).__init__(type_)
        self.pycore = pycore
        self.ast_node = ast_node
        self.attributes = None
        self.scope = None
        self.parent = parent

    def get_attributes(self):
        if self.attributes is None:
            self.attributes = self._get_attributes_from_ast()
        return self.attributes

    def get_scope(self):
        if self.scope == None:
            self.scope = self._create_scope()
        return self.scope

    def _get_attributes_from_ast(self):
        pass

    def _get_ast(self):
        return self.ast_node
    
    def _create_scope(self):
        pass


class PyFunction(PyDefinedObject):

    def __init__(self, pycore, ast_node, parent):
        super(PyFunction, self).__init__(PyObject.get_base_type('Function'),
                                         pycore, ast_node, parent)
        self.parameters = self.ast_node.argnames
        self.decorators = self.ast_node.decorators

    def _get_attributes_from_ast(self):
        return {}
    
    def _create_scope(self):
        return FunctionScope(self.pycore, self)

    def _get_parameters(self):
        result = {}
        if len(self.parameters) > 0:
            if self.parent.get_type() == PyObject.get_base_type('Type') and \
               not self.decorators:
                result[self.parameters[0]] = PyName(PyObject(self.parent))
            else:
                result[self.parameters[0]] = PyName()
        if len(self.parameters) > 1:
            for parameter in self.parameters[1:]:
                result[parameter] = PyName()
        return result


class _AttributeListFinder(object):

    def __init__(self):
        self.name_list = []
        
    def visitName(self, node):
        self.name_list.append(node.name)
    
    def visitGetattr(self, node):
        compiler.walk(node.expr, self)
        self.name_list.append(node.attrname)
        
    @staticmethod
    def get_attribute(node, scope):
        finder = _AttributeListFinder()
        compiler.walk(node, finder)
        pyobject = scope.lookup(finder.name_list[0])
        if pyobject != None and len(finder.name_list) > 1:
            for name in finder.name_list[1:]:
                if name in pyobject.get_attributes():
                    pyobject = pyobject.get_attributes()[name].object
                else:
                    pyobject = None
                    break
        return pyobject


class PyClass(PyDefinedObject):

    def __init__(self, pycore, ast_node, parent):
        super(PyClass, self).__init__(PyObject.get_base_type('Type'),
                                      pycore, ast_node, parent)
        self.parent = parent

    def _get_attributes_from_ast(self):
        result = {}
        for base in self._get_bases():
            result.update(base.get_attributes())
        new_visitor = _ClassVisitor(self.pycore, self)
        for n in self.ast_node.getChildNodes():
            compiler.walk(n, new_visitor)
        result.update(new_visitor.names)
        return result

    def _get_bases(self):
        result = []
        for base_name in self.ast_node.bases:
            base = _AttributeListFinder.get_attribute(base_name,
                                                      self.parent.get_scope())
            if base:
                result.append(base)
        return result

    def _create_scope(self):
        return ClassScope(self.pycore, self)


class PyModule(PyDefinedObject):

    def __init__(self, pycore, ast_node):
        super(PyModule, self).__init__(PyObject.get_base_type('Module'),
                                       pycore, ast_node, None)
        self.is_package = False

    def _get_attributes_from_ast(self):
        visitor = _GlobalVisitor(self.pycore, self)
        compiler.walk(self.ast_node, visitor)
        return visitor.names

    def _create_scope(self):
        return GlobalScope(self.pycore, self)


class PyPackage(PyObject):

    def __init__(self, pycore, resource):
        super(PyPackage, self).__init__(PyObject.get_base_type('Module'))
        self.is_package = True
        self.resource = resource
        self.pycore = pycore
        self.attributes = None

    def get_attributes(self):
        if self.attributes is None:
            attributes = {}
            for child in self.resource.get_children():
                if child.is_folder():
                    attributes[child.get_name()] = PyName(self.pycore._create(child))
                elif child.get_name().endswith('.py') and \
                     child.get_name() != '__init__.py':
                    name = child.get_name()[:-3]
                    attributes[name] = PyName(self.pycore._create(child))
            self.attributes = attributes
        return self.attributes


class PyFilteredPackage(PyObject):

    def __init__(self):
        super(PyFilteredPackage, self).__init__(PyObject.get_base_type('Module'))
        self.is_package = True
        self.attributes = {}

    def get_attributes(self):
        return self.attributes

    def _add_attribute(self, name, pyname):
        self.attributes[name] = pyname


class PyName(object):

    def __init__(self, object_=None, is_defined_here=False, lineno=None):
        self.object = object_
        self.is_defined_here = is_defined_here
        self.lineno = lineno
        if self._has_block():
            self.lineno = self._get_ast().lineno

    def update_object(self, object_=None, is_defined_here=False, lineno=None):
        self.__init__(object_, is_defined_here, self.lineno)

    def get_attributes(self):
        if self.object:
            return self.object.get_attributes()
        else:
            return PyObject.get_base_type('Unknown').get_attributes()

    def get_type(self):
        if self.object:
            return self.object.get_type()
        else:
            return PyObject.get_base_type('Unknown')

    def get_definition_location(self):
        return self.lineno

    def _has_block(self):
        return self.is_defined_here and isinstance(self.object,
                                                   PyDefinedObject)
    
    def _get_ast(self):
        return self.object._get_ast()


class Scope(object):

    def __init__(self, pycore, pyobject, parent_scope):
        self.pycore = pycore
        self.pyobject = pyobject
        self.parent = parent_scope
        self.scopes = None
    
    def get_names(self):
        """Returns the names defined in this scope"""
        return self.pyobject.get_attributes()

    def get_scopes(self):
        """Returns the subscopes of this scope.
        
        The returned scopes should be sorted by the order they appear
        """
        if self.scopes == None:
            self.scopes = self._create_scopes()
        return self.scopes

    def _create_scopes(self):
        block_objects = [pyname.object for pyname in
                         self.pyobject.get_attributes().values()
                         if pyname._has_block()]
        def block_compare(x, y):
            return cmp(x._get_ast().lineno, y._get_ast().lineno)
        block_objects.sort(cmp=block_compare)
        result = [block.get_scope() for block in block_objects]
        return result

    def get_lineno(self):
        return self.pyobject._get_ast().lineno

    def get_kind(self):
        pass
    
    def lookup(self, name):
        if name in self.get_names():
            return self.get_names()[name]
        if self.parent is not None:
            return self.parent.lookup(name)
        return None


class GlobalScope(Scope):

    def __init__(self, pycore, module):
        super(GlobalScope, self).__init__(pycore, module, None)

    def get_lineno(self):
        return 1

    def get_kind(self):
        return 'Module'


class FunctionScope(Scope):
    
    def __init__(self, pycore, pyobject):
        super(FunctionScope, self).__init__(pycore, pyobject,
                                            pyobject.parent.get_scope())
        self.names = None
    
    def _get_names(self):
        if self.names == None:
            new_visitor = _FunctionVisitor(self.pycore, self.pyobject)
            for n in self.pyobject._get_ast().getChildNodes():
                compiler.walk(n, new_visitor)
            self.names = new_visitor.names
        return self.names
    
    def get_names(self):
        result = self.pyobject._get_parameters()
        result.update(self._get_names())
        return result

    def _create_scopes(self):
        block_objects = [pyname.object for pyname in self._get_names().values()
                         if pyname._has_block()]
        def block_compare(x, y):
            return cmp(x._get_ast().lineno, y._get_ast().lineno)
        block_objects.sort(cmp=block_compare)
        result = [block.get_scope() for block in block_objects]
        return result

    def get_kind(self):
        return 'Function'


class ClassScope(Scope):

    def __init__(self, pycore, pyobject):
        super(ClassScope, self).__init__(pycore, pyobject,
                                         pyobject.parent.get_scope())
    
    def get_names(self):
        return {}

    def get_kind(self):
        return 'Class'


class _ScopeVisitor(object):

    def __init__(self, pycore, owner_object):
        self.names = {}
        self.pycore = pycore
        self.owner_object = owner_object
    
    def visitClass(self, node):
        self.names[node.name] = PyName(PyClass(self.pycore,
                                               node, self.owner_object), True)

    def visitFunction(self, node):
        pyobject = PyFunction(self.pycore, node, self.owner_object)
        self.names[node.name] = PyName(pyobject, True)

    def visitAssName(self, node):
        if node.name in self.names:
            self.names[node.name].update_object(lineno=node.lineno)
        else:
            self.names[node.name] = PyName(lineno=node.lineno)

    def visitImport(self, node):
        for import_pair in node.names:
            name, alias = import_pair
            imported = name
            if alias is not None:
                imported = alias
            try:
                module = self.pycore.get_module(name)
            except ModuleNotFoundException:
                module = PyObject(PyObject.get_base_type('Module'))
                module.is_package = False
            if alias is None and '.' in imported:
                tokens = imported.split('.')
                if tokens[0] in self.names and \
                   isinstance(self.names[tokens[0]].object, PyFilteredPackage):
                    pypkg = self.names[tokens[0]].object
                else:
                    pypkg = PyFilteredPackage()
                    self.names[tokens[0]] = PyName(pypkg)
                for token in tokens[1:-1]:
                    if token in pypkg.get_attributes() and \
                       isinstance(pypkg.get_attributes()[token].object,
                                  PyFilteredPackage):
                        newpkg = pypkg.get_attributes()[token].object
                    else:
                        newpkg = PyFilteredPackage()
                        pypkg._add_attribute(token, PyName(newpkg))
                    pypkg = newpkg
                pypkg._add_attribute(tokens[-1], PyName(module, False))
            else:
                self.names[imported] = PyName(module, False)

    def visitFrom(self, node):
        try:
            module = self.pycore.get_module(node.modname)
        except ModuleNotFoundException:
            module = PyFilteredPackage()

        if node.names[0][0] == '*':
            if module.is_package:
                return
            for name, pyname in module.get_attributes().iteritems():
                if not name.startswith('_'):
                    self.names[name] = PyName(pyname.object, False)
        else:
            for (name, alias) in node.names:
                imported = name
                if alias is not None:
                    imported = alias
                if module.get_attributes().has_key(name):
                    imported_object = module.get_attributes()[name].object
                    if isinstance(imported_object, PyPackage):
                        self.names[imported] = PyFilteredPackage()
                    else:
                        self.names[imported] = PyName(imported_object, False)
                else:
                    self.names[imported] = PyName()


class _GlobalVisitor(_ScopeVisitor):

    def __init__(self, pycore, owner_object):
        super(_GlobalVisitor, self).__init__(pycore, owner_object)
    

class _ClassVisitor(_ScopeVisitor):

    def __init__(self, pycore, owner_object):
        super(_ClassVisitor, self).__init__(pycore, owner_object)

    def visitFunction(self, node):
        pyobject = PyFunction(self.pycore, node, self.owner_object)
        self.names[node.name] = PyName(pyobject, True)
        if node.name == '__init__':
            new_visitor = _ClassInitVisitor()
            compiler.walk(node, new_visitor)
            self.names.update(new_visitor.names)

    def visitAssName(self, node):
        self.names[node.name] = PyName()

    def visitClass(self, node):
        self.names[node.name] = PyName(PyClass(self.pycore, node,
                                               self.owner_object), True)


class _FunctionVisitor(_ScopeVisitor):

    def __init__(self, pycore, owner_object):
        super(_FunctionVisitor, self).__init__(pycore, owner_object)


class _ClassInitVisitor(object):

    def __init__(self):
        self.names = {}
    
    def visitAssAttr(self, node):
        if node.expr.name == 'self':
            self.names[node.attrname] = PyName()

class PythonFileRunner(object):
    """A class for running python project files"""

    def __init__(self, file, stdin=None, stdout=None):
        self.file = file
        file_path = self.file._get_real_path()
        env = {}
        env.update(os.environ)
        source_folders = []
        for folder in file.get_project().get_pycore().get_source_folders():
            source_folders.append(os.path.abspath(folder._get_real_path()))
        env['PYTHONPATH'] = env.get('PYTHONPATH', '') + os.pathsep + \
                            os.pathsep.join(source_folders)
        self.process = subprocess.Popen(executable=sys.executable,
                                        args=(sys.executable, self.file.get_name()),
                                        cwd=os.path.split(file_path)[0], stdin=stdin,
                                        stdout=stdout, stderr=stdout, env=env)

    def wait_process(self):
        """Wait for the process to finish"""
        self.process.wait()

    def kill_process(self):
        """Stop the process. This does not work on windows."""
        os.kill(self.process.pid, 9)


