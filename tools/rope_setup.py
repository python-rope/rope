import glob
import os
import shutil
from distutils.core import setup

import rope


classifiers=[
    'Development Status :: 4 - Beta',
    'Operating System :: OS Independent',
    'Environment :: X11 Applications',
    'Environment :: Win32 (MS Windows)',
    # Have not been tested on MacOS
    # 'Environment :: MacOS X',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: GNU General Public License (GPL)',
    'Natural Language :: English',
    'Programming Language :: Python',
    'Topic :: Software Development',
    'Topic :: Text Editors :: Integrated Development Environments (IDE)']

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
                'rope.refactor.importutils'],
      license='GNU GPL',
      classifiers=classifiers)
