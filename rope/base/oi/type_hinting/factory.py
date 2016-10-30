from rope.base.oi.type_hinting import interfaces
from rope.base.oi.type_hinting.providers import (
    composite, inheritance, docstrings, numpydocstrings, pep0484_type_comments
)
from rope.base import utils


class TypeHintingFactory(interfaces.ITypeHintingFactory):

    @utils.saveit
    def make_param_provider(self):
        providers = [
            docstrings.ParamProvider(docstrings.DocstringParamParser()),
            docstrings.ParamProvider(numpydocstrings.NumPyDocstringParamParser()),
        ]
        return inheritance.ParamProvider(composite.ParamProvider(*providers))

    @utils.saveit
    def make_attr_provider(self):
        providers = [
            docstrings.AttrProvider(docstrings.DocstringParamParser()),
            docstrings.AttrProvider(numpydocstrings.NumPyDocstringParamParser()),
        ]
        return inheritance.AttrProvider(composite.AttrProvider(*providers))

    @utils.saveit
    def make_return_provider(self):
        return inheritance.ReturnProvider(docstrings.ReturnProvider(docstrings.DocstringReturnParser()))

    @utils.saveit
    def make_assignment_provider(self):
        return pep0484_type_comments.AssignmentProvider()

default_type_hinting_factory = TypeHintingFactory()


class TypeHintingFactoryAccessor(object):

    def __call__(self, project):
        """
        :type project: rope.base.project.Project
        :rtype: rope.base.oi.type_hinting.interfaces.ITypeHintingFactory
        """
        factory_location = project.get_prefs().get(
            'type_hinting_factory',
            'rope.base.oi.type_hinting.factory.default_type_hinting_factory'
        )
        return self._get_factory(factory_location)

    @utils.cached(10)
    def _get_factory(self, factory_location):
        """
        :type factory_location: str
        :rtype: rope.base.oi.type_hinting.interfaces.ITypeHintingFactory
        """
        return utils.resolve(factory_location)

get_type_hinting_factory = TypeHintingFactoryAccessor()
