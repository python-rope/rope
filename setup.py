import glob
import os
import shutil

extra_kwargs = {}
try:
    # we don't want to depend on setuptools
    # please don't use any setuptools specific API
    from setuptools import setup
    extra_kwargs['test_suite'] = 'ropetest'
except ImportError:
    from distutils.core import setup

import rope


classifiers=[
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
    lines = open('README.txt').read().splitlines(False)
    end = lines.index('Getting Started')
    return '\n' + '\n'.join(lines[:end]) + '\n'

setup(name='rope',
      version=rope.VERSION,
      description='a python refactoring library...',
      long_description=get_long_description(),
      author='Ali Gholami Rudi',
      author_email='aligrudi@users.sourceforge.net',
      url='http://rope.sf.net/',
      packages=['rope', 'rope.base', 'rope.base.oi', 'rope.refactor',
                'rope.refactor.importutils', 'rope.contrib'],
      license='GNU GPL',
      classifiers=classifiers,
      **extra_kwargs)
