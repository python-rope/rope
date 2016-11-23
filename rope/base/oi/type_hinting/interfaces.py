class ITypeHintingFactory(object):

    def make_param_provider(self):
        """
        :rtype: rope.base.oi.type_hinting.providers.interfaces.IParamProvider
        """

    def make_return_provider(self):
        """
        :rtype: rope.base.oi.type_hinting.providers.interfaces.IReturnProvider
        """

    def make_assignment_provider(self):
        """
        :rtype: rope.base.oi.type_hinting.providers.interfaces.IAssignmentProvider
        """
