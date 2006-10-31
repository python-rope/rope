import compiler
import compiler.ast

class OutlineNode(object):

    def get_name(self):
        pass

    def get_line_number(self):
        pass
    
    def get_children(self):
        pass


class Outline(object):

    def get_root_nodes(self, source_code):
        pass


class NoOutline(object):

    def get_root_nodes(self, source_code):
        return []


class PythonASTOutlineNode(OutlineNode):
    
    def __init__(self, ast_node):
        self.name = ast_node.name
        self.ast_node = ast_node
        self.children = None
        
    def get_name(self):
        return self.name
    
    def get_line_number(self):
        return self.ast_node.lineno

    def get_children(self):
        if self.children is None:
            if isinstance(self.ast_node, compiler.ast.Class):
                self.children = _get_ast_children(self.ast_node)
            else:
                self.children = []
        return self.children

    def __cmp__(self, obj):
        return cmp(self.get_line_number(), obj.get_line_number())
            
class _ASTDefinedVisitor(object):

    def __init__(self):
        self.result = []
    
    def visitFunction(self, node):
        self.result.append(PythonASTOutlineNode(node))
    
    def visitClass(self, node):
        self.result.append(PythonASTOutlineNode(node))

def _get_ast_children(ast_node):
    visitor = _ASTDefinedVisitor()
    for child in ast_node.getChildNodes():
        compiler.walk(child, visitor)
    return visitor.result


class PythonOutline(Outline):

    def __init__(self, project):
        self.project = project
    
    # Note: We don't use PyNames anymore; we don't need imported names
    def _old_get_root_nodes(self, source_code):
        mod = self.project.get_pycore().get_string_module(source_code)
        return _get_pyname_children(mod)

    def get_root_nodes(self, source_code):
        if isinstance(source_code, unicode):
            source_code = source_code.encode('utf-8')
        ast_node = compiler.parse(source_code)
        return _get_ast_children(ast_node)


# Note: This class is no longer used because right now we are not interested
#       in inherited names that this class exposes
class PythonOutlineNode(OutlineNode):
    
    def __init__(self, name, pyname):
        self.name = name
        self.pyname = pyname
        
    def get_name(self):
        return self.name
    
    def get_line_number(self):
        return self.pyname.get_definition_location()[1]

    def get_children(self):
        return _get_pyname_children(self.pyname)

    def __cmp__(self, obj):
        return cmp(self.get_line_number(), obj.get_line_number())

def _get_pyname_children(pyname):
    result = []
    for name, pyname in pyname.get_attributes().iteritems():
        if pyname.has_block():
            result.append(PythonOutlineNode(name, pyname))
    result.sort()
    return result

