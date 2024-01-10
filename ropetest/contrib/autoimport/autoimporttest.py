from concurrent.futures import ThreadPoolExecutor
from contextlib import closing, contextmanager
from textwrap import dedent
from unittest.mock import patch

import pytest

from rope.base.project import Project
from rope.base.resources import File, Folder
from rope.contrib.autoimport import models
from rope.contrib.autoimport.sqlite import AutoImport


@pytest.fixture
def autoimport(project: Project):
    with closing(AutoImport(project)) as ai:
        yield ai

def test_init_py(
    autoimport: AutoImport,
    project: Project,
    pkg1: Folder,
    mod1: File,
):
    mod1_init = pkg1.get_child("__init__.py")
    mod1_init.write(dedent("""\
        def foo():
            pass
    """))
    mod1.write(dedent("""\
        foo
    """))
    autoimport.generate_cache([mod1_init])
    results = autoimport.search("foo", True)
    assert [("from pkg1 import foo", "foo")] == results


def test_multithreading(
    autoimport: AutoImport,
    project: Project,
    pkg1: Folder,
    mod1: File,
):
    mod1_init = pkg1.get_child("__init__.py")
    mod1_init.write(dedent("""\
        def foo():
            pass
    """))
    mod1.write(dedent("""\
        foo
    """))
    autoimport = AutoImport(project, memory=False)
    autoimport.generate_cache([mod1_init])

    tp = ThreadPoolExecutor(1)
    results = tp.submit(autoimport.search, "foo", True).result()
    assert [("from pkg1 import foo", "foo")] == results







class TestQueryUsesIndexes:
    def explain(self, autoimport, query):
        explanation = list(autoimport.database._execute(query.explain(), ("abc",)))[0][-1]
        # the explanation text varies, on some sqlite version
        explanation = explanation.replace("TABLE ", "")
        return explanation

    def test_search_by_name_uses_index(self, autoimport):
        query = models.Name.search_by_name.select_star()
        assert (
            self.explain(autoimport, query)
            == "SEARCH names USING INDEX names_name (name=?)"
        )

    def test_search_by_name_like_uses_index(self, autoimport):
        query = models.Name.search_by_name_like.select_star()
        assert (
            self.explain(autoimport, query)
            == "SEARCH names USING INDEX names_name_nocase (name>? AND name<?)"
        )

    def test_search_module_like_uses_index(self, autoimport):
        query = models.Name.search_module_like.select_star()
        assert (
            self.explain(autoimport, query)
            == "SEARCH names USING INDEX names_module_nocase (module>? AND module<?)"
        )

    def test_search_submodule_like_uses_index(self, autoimport):
        query = models.Name.search_submodule_like.select_star()
        assert (
            self.explain(autoimport, query)
            == "SCAN names" # FIXME: avoid full table scan
        )
