
from setuptools import setup, find_packages

import rope



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
    lines = open('README.rst').read().splitlines(False)
    end = lines.index('Getting Started')
    return '\n' + '\n'.join(lines[:end]) + '\n'

setup(
  name='rope',
  version=rope.VERSION,
  description='a python refactoring library...',
  long_description=get_long_description(),
  author='Ali Gholami Rudi',
  author_email='aligrudi@users.sourceforge.net',
  url='https://github.com/python-rope/rope',
  packages=find_packages(exclude=('ropetest.*', 'sample_folder.*')),
  license='GNU GPL',
  classifiers=classifiers,
  test_suite="ropetest.suite",
)
