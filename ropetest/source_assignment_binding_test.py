"""Source binding identity for assignment targets and call keywords."""

from textwrap import dedent

from rope.base import codeanalyze, evaluate
from rope.base.project import Project


def test_unpack_targets_resolve_to_later_references_and_preserve_keywords(tmp_path):
    project = Project(str(tmp_path), save_objectdb=False, save_history=False)
    try:
        source = dedent('''\
            def receive(option=None):
                return option

            def process(value):
                título = "á"
                first, second = value, value
                (left, (middle,
                        last)) = (value, (value, value))
                receive(option=last)
                return first, second, left, middle, last, título
        ''')
        resource = project.root.create_file('subject.py')
        resource.write(source)
        module = project.get_pymodule(resource)
        for name, target in (
            ('second', 'second = value'),
            ('last', 'last)) ='),
            ('título', 'título ='),
        ):
            declared = evaluate.eval_location(module, source.index(target))
            used = evaluate.eval_location(module, source.rindex(name))
            assert declared is not None
            assert declared is used
        parameter = evaluate.eval_location(module, source.index('option=None'))
        keyword = evaluate.eval_location(module, source.index('option=last'))
        assert parameter is not None
        assert keyword is parameter
    finally:
        project.close()


def test_name_offsets_exclude_literals_and_comments_and_include_fstrings():
    source = 'árvore = 1  # árvore\ntext = "árvore"\nprint(fr"{árvore}")\n'
    assert codeanalyze.name_offsets(source, 'árvore') == (
        source.index('árvore'),
        source.rindex('árvore'),
    )
