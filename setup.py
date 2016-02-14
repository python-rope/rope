from distutils.core import setup, Command
import sys
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
    'Topic :: Software Development']


def get_long_description():
    lines = open('README.rst').read().splitlines(False)
    end = lines.index('Getting Started')
    return '\n' + '\n'.join(lines[:end]) + '\n'

setup(name='rope',
      version=rope.VERSION,
      description='a python refactoring library...',
      long_description=get_long_description(),
      author='Ali Gholami Rudi',
      author_email='aligrudi@users.sourceforge.net',
      url='https://github.com/sergeyglazyrindev/rope',
      packages=['rope', 'rope.base', 'rope.base.oi', 'rope.refactor',
                'rope.refactor.importutils', 'rope.contrib'],
      license='GNU GPL',
      classifiers=classifiers,
      cmdclass={
          'test': RunTests,
      })
