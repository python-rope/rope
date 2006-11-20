import unittest
import rope.base.exceptions
import rope.base.project
import rope.refactor.change_signature

from ropetest import testutils


class ChangeSignatureTest(unittest.TestCase):

    def setUp(self):
        super(ChangeSignatureTest, self).setUp()
        self.project_root = 'sample_project'
        testutils.remove_recursively(self.project_root)
        self.project = rope.base.project.Project(self.project_root)
        self.pycore = self.project.get_pycore()
        self.refactoring = self.project.get_pycore().get_refactoring()
        self.mod = self.pycore.create_module(self.project.get_root_folder(), 'mod')

    def tearDown(self):
        testutils.remove_recursively(self.project_root)
        super(ChangeSignatureTest, self).tearDown()

    def test_normalizing_parameters_for_trivial_case(self):
        signature = rope.refactor.change_signature.ChangeSignature(self.pycore)


if __name__ == '__main__':
    unittest.main()
