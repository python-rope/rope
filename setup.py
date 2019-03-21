import io
import os.path
import sys

try:
    from setuptools import Command, setup
except ImportError:
    from distutils.core import Command, setup
try:
    import unittest2 as unittest
except ImportError:
    import unittest


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
        import ropetest
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
    'License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)',
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
    lines = io.open('README.rst', 'r',
                    encoding='utf8').read().splitlines(False)
    end = lines.index('Getting Started')
    return '\n' + '\n'.join(lines[:end]) + '\n'


def get_version():
    version = None
    with io.open(os.path.join(
            os.path.dirname(__file__), 'rope', '__init__.py')) as inif:
        for line in inif:
            if line.startswith('VERSION'):
                version = line.split('=')[1].strip(" \n'")
                break
    return version


setup(name='ropee',
      version=get_version(),
      description='a python refactoring library...',
      long_description=get_long_description(),
      author='Harry Papaxenopoulos',
      author_email='hpapaxen@gmail.com',
      url='https://github.com/hpapaxen/rope/tree/ropee',
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
