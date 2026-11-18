"""Source inference agrees with Python's unchanged-value descriptors."""

from textwrap import dedent

import pytest

from rope.base import libutils
from rope.base.project import Project

SOURCE = dedent("""\
    def native(value):
        return value
    class Export:
        def __init__(self, value):
            self._value = value
        def __get__(self, instance, owner=None):
            return self._value
    class Owner:
        exported = Export({argument})
    class Derived(Owner):
        pass
    selected = {access}.exported
""")


@pytest.mark.parametrize("access", ["Owner", "Owner()", "Derived", "Derived()"])
@pytest.mark.parametrize("argument", ["native", "value=native"])
def test_native_value_descriptor_preserves_identity(tmp_path, access, argument):
    source = SOURCE.format(access=access, argument=argument)
    namespace = {}
    exec(source, namespace)
    assert namespace["selected"] is namespace["native"]
    project = Project(str(tmp_path), ropefolder=None)
    try:
        scope = libutils.get_string_scope(project, source)
        assert scope["selected"].get_object() is scope["native"].get_object()
    finally:
        project.close()


@pytest.mark.parametrize("access", ["Owner", "Owner()"])
@pytest.mark.parametrize("transformation", ["getter", "initializer"])
def test_transforming_descriptor_does_not_reuse_constructor_identity(
    tmp_path, access, transformation
):
    source = SOURCE.format(access=access, argument="native")
    if transformation == "getter":
        source = source.replace("return self._value", "return lambda value: value")
    else:
        source = source.replace("self._value = value", "self._value = lambda value: value")
    namespace = {}
    exec(source, namespace)
    assert namespace["selected"] is not namespace["native"]
    project = Project(str(tmp_path), ropefolder=None)
    try:
        scope = libutils.get_string_scope(project, source)
        assert scope["selected"].get_object() is not scope["native"].get_object()
    finally:
        project.close()


@pytest.mark.parametrize("access", ["Owner", "Owner()"])
@pytest.mark.parametrize(
    "rebinding",
    [
        "    __get__ = lambda self, instance, owner=None: str\n",
        "    __init__ = lambda self, value: setattr(self, '_value', str)\n",
    ],
)
def test_rebound_descriptor_method_does_not_reuse_constructor_identity(
    tmp_path, access, rebinding
):
    source = SOURCE.format(access=access, argument="native").replace(
        "        return self._value\n",
        "        return self._value\n" + rebinding,
    )
    namespace = {}
    exec(source, namespace)
    assert namespace["selected"] is not namespace["native"]
    project = Project(str(tmp_path), ropefolder=None)
    try:
        scope = libutils.get_string_scope(project, source)
        assert scope["selected"].get_object() is not scope["native"].get_object()
    finally:
        project.close()


def test_attribute_write_index_tracks_recaptured_native_source(tmp_path):
    project = Project(str(tmp_path), ropefolder=None)
    try:
        resource = project.root.create_file("subject.py")
        source = SOURCE.format(access="Owner", argument="native")
        resource.write(source)
        old = project.get_pymodule(resource).get_source_binding_index()
        assert old.attribute_writes("exported") == ()
        updated = source.replace("selected =", "Owner.exported = native\nselected =")
        namespace = {}
        exec(updated, namespace)
        assert namespace["selected"] is namespace["native"]
        resource.write(updated)
        new = project.get_pymodule(resource).get_source_binding_index()
        assert len(new.attribute_writes("exported")) == 1
        assert old.attribute_writes("exported") == ()
    finally:
        project.close()
