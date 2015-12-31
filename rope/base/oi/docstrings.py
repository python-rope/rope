"""
Hinting the type using docstring of class/function like here
https://www.jetbrains.com/pycharm/help/type-hinting-in-pycharm.html#d290117e333

It's a necessary thing if you are using Dependency Injection
(three ways - Constructor Injection, Setter Injection, and Interface Injection):
http://www.martinfowler.com/articles/injection.html

Some code extracted (or based on code) from:
https://github.com/davidhalter/jedi/blob/b489019f5bd5750051122b94cc767df47751ecb7/jedi/evaluate/docstrings.py
Thanks to @davidhalter for MIT License.
"""
import re
from ast import literal_eval

from rope.base.evaluate import ScopeNameFinder

DOCSTRING_PARAM_PATTERNS = [
    r'\s*:type\s+%s:\s*([^\n]+)',  # Sphinx
    r'\s*:param\s+(\w+)\s+%s:[^\n]+',  # Sphinx param with type
    r'\s*@type\s+%s:\s*([^\n]+)',  # Epydoc
]

DOCSTRING_RETURN_PATTERNS = [
    re.compile(r'\s*:rtype:\s*([^\n]+)', re.M),  # Sphinx
    re.compile(r'\s*@rtype:\s*([^\n]+)', re.M),  # Epydoc
]

REST_ROLE_PATTERN = re.compile(r':[^`]+:`([^`]+)`')


try:
    from numpydoc.docscrape import NumpyDocString
except ImportError:
    def _search_param_in_numpydocstr(docstr, param_str):
        return []
else:
    def _search_param_in_numpydocstr(docstr, param_str):
        """Search `docstr` (in numpydoc format) for type(-s) of `param_str`."""
        params = NumpyDocString(docstr)._parsed_data['Parameters']
        for p_name, p_type, p_descr in params:
            if p_name == param_str:
                m = re.match('([^,]+(,[^,]+)*?)(,[ ]*optional)?$', p_type)
                if m:
                    p_type = m.group(1)

                if p_type.startswith('{'):
                    types = set(type(x).__name__ for x in literal_eval(p_type))
                    return list(types)
                else:
                    return [p_type]
        return []


def _handle_nonfirst_parameters(pyobject, parameters):
    doc_str = pyobject.get_doc()
    if not doc_str:
        return

    for i, (name, val) in enumerate(zip(pyobject.get_param_names(), parameters)):
        if i == 0:
            continue

        type_strs = _search_param_in_docstr(doc_str, name)
        if type_strs:
            type_ = _resolve_type(type_strs[0], pyobject)
            if type_ is not None:
                val.type = type_


def _resolve_type(type_name, pyobject):
    type_ = None
    if '.' not in type_name:
        try:
            type_ = pyobject.get_module().get_scope().get_name(type_name).get_object()
        except Exception:
            pass
    else:
        mod_name, attr_name = type_name.rsplit('.', 1)
        try:
            mod_finder = ScopeNameFinder(pyobject.get_module())
            mod = mod_finder._find_module(mod_name).get_object()
            type_ = mod.get_attribute(attr_name).get_object()
        except Exception:
            pass
    return type_


def _search_param_in_docstr(docstr, param_str):
    """
    Search `docstr` for type(-s) of `param_str`.

    >>> _search_param_in_docstr(':type param: int', 'param')
    ['int']
    >>> _search_param_in_docstr('@type param: int', 'param')
    ['int']
    >>> _search_param_in_docstr(
    ...   ':type param: :class:`threading.Thread`', 'param')
    ['threading.Thread']
    >>> bool(_search_param_in_docstr('no document', 'param'))
    False
    >>> _search_param_in_docstr(':param int param: some description', 'param')
    ['int']

    """
    # look at #40 to see definitions of those params
    patterns = [re.compile(p % re.escape(param_str))
                for p in DOCSTRING_PARAM_PATTERNS]
    for pattern in patterns:
        match = pattern.search(docstr)
        if match:
            return [_strip_rst_role(match.group(1))]

    return (_search_param_in_numpydocstr(docstr, param_str) or
            [])


def _strip_rst_role(type_str):
    """
    Strip off the part looks like a ReST role in `type_str`.

    >>> _strip_rst_role(':class:`ClassName`')  # strip off :class:
    'ClassName'
    >>> _strip_rst_role(':py:obj:`module.Object`')  # works with domain
    'module.Object'
    >>> _strip_rst_role('ClassName')  # do nothing when not ReST role
    'ClassName'

    See also:
    http://sphinx-doc.org/domains.html#cross-referencing-python-objects

    """
    match = REST_ROLE_PATTERN.match(type_str)
    if match:
        return match.group(1)
    else:
        return type_str


def _search_return_in_docstr(code):
    for p in DOCSTRING_RETURN_PATTERNS:
        match = p.search(code)
        if match:
            return _strip_rst_role(match.group(1))
