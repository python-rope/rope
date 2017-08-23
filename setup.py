import sys

try:
    from setuptools import Command, setup
except ImportError:
    from distutils.core import Command, setup
try:
    import unittest2 as unittest
except ImportError:
    import unittest

import rope

import ropetest
import ropetest.contrib
import ropetest.refactor


class RunTests(Command):
    """New setup.py command to run all tests for the package.
    """
    description = "run all tests for the package"

    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        tests = unittest.TestSuite(ropetest.suite())
        runner = unittest.TextTestRunner(verbosity=2)
        results = runner.run(tests)
        sys.exit(0 if results.wasSuccessful() else 1)


classifiers = [
    'Development Status :: 4 - Beta',
    'Operating System :: OS Independent',
    'Environment :: X11 Applications',
    'Environment :: Win32 (MS Windows)',
    'Environment :: MacOS X',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: GNU General Public License (GPL)',
    'Natural Language :: English',
    'Programming Language :: Python',
    'Programming Language :: Python :: 2',
    'Programming Language :: Python :: 2.6',
    'Programming Language :: Python :: 2.7',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.2',
    'Programming Language :: Python :: 3.3',
    'Programming Language :: Python :: 3.4',
    'Topic :: Software Development']


def get_long_description():
    lines = open('README.rst', 'rb').read().splitlines(False)
    end = lines.index(b'Getting Started')
    return '\n' + str(b'\n'.join(lines[:end])) + '\n'

setup(name='rope',
      version=rope.VERSION,
      description='a python refactoring library...',
      long_description=get_long_description(),
      author='Ali Gholami Rudi',
      author_email='aligrudi@users.sourceforge.net',
      url='https://github.com/python-rope/rope',
      packages=['rope',
                'rope.base',
                'rope.base.oi',
                'rope.base.oi.type_hinting',
                'rope.base.oi.type_hinting.providers',
                'rope.base.oi.type_hinting.resolvers',
                'rope.base.utils',
                'rope.contrib',
                'rope.refactor',
                'rope.refactor.importutils'],
      license='GNU GPL',
      classifiers=classifiers,
      cmdclass={
          'test': RunTests,
      })
