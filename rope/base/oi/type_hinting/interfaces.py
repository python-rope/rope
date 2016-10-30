class ITypeHintingFactory(object):

    def make_param_provider(self):
        """
        :rtype: rope.base.oi.type_hinting.providers.interfaces.IParamProvider
        """

    def make_attr_provider(self):
        """
        :rtype: rope.base.oi.type_hinting.providers.interfaces.IAttrProvider
        """

    def make_return_provider(self):
        """
        :rtype: rope.base.oi.type_hinting.providers.interfaces.IReturnProvider
        """

    def make_assignment_provider(self):
        """
        :rtype: rope.base.oi.type_hinting.providers.interfaces.IAssignmentProvider
        """
