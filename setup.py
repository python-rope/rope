import io
import os.path

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


classifiers = [
    "Development Status :: 4 - Beta",
    "Operating System :: OS Independent",
    "Environment :: X11 Applications",
    "Environment :: Win32 (MS Windows)",
    "Environment :: MacOS X",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)",
    "Natural Language :: English",
    "Programming Language :: Python",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.5",
    "Programming Language :: Python :: 3.6",
    "Programming Language :: Python :: 3.7",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Topic :: Software Development",
]


def get_long_description():
    lines = io.open("README.rst", "r", encoding="utf8").read().splitlines(False)
    end = lines.index("Maintainers")
    return "\n" + "\n".join(lines[:end]) + "\n"


def get_version():
    version = None
    with io.open(
        os.path.join(os.path.dirname(__file__), "rope", "__init__.py")
    ) as inif:
        for line in inif:
            if line.startswith("VERSION"):
                version = line.split("=")[1].strip(" \t\"'\n")
                break
    return version


setup(
    name="rope",
    version=get_version(),
    description="a python refactoring library...",
    long_description=get_long_description(),
    long_description_content_type="text/x-rst",
    author="Ali Gholami Rudi",
    author_email="aligrudi@users.sourceforge.net",
    url="https://github.com/python-rope/rope",
    packages=[
        "rope",
        "rope.base",
        "rope.base.oi",
        "rope.base.oi.type_hinting",
        "rope.base.oi.type_hinting.providers",
        "rope.base.oi.type_hinting.resolvers",
        "rope.base.utils",
        "rope.contrib",
        "rope.refactor",
        "rope.refactor.importutils",
    ],
    license="LGPL-3.0-or-later",
    classifiers=classifiers,
    extras_require={
        "dev": [
            "build",
            "pytest",
            "pytest-timeout",
        ]
    },
    python_requires=">=3",
)
