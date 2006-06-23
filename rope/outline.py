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
        if pyname._has_block():
            result.append(PythonOutlineNode(name, pyname))
    result.sort()
    return result
    

class PythonOutline(Outline):

    def __init__(self, project):
        self.project = project
    
    def get_root_nodes(self, source_code):
        mod = self.project.get_pycore().get_string_module(source_code)
        return _get_pyname_children(mod)

