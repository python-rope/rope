# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys

sys.path.insert(0, os.path.abspath(".."))


# -- Project information -----------------------------------------------------
import rope

project = "rope"
copyright = "2023, Rope Contributors"
author = "Rope Contributors"

# The full version, including alpha/beta/rc tags
version = release = rope.VERSION


# -- General configuration ---------------------------------------------------

pygments_style = "sphinx"
# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosectionlabel",
    "sphinx.ext.autosummary",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    "sphinx_autodoc_typehints",
    "pytoolconfig.documentation",
    "sphinx_rtd_theme",
    "autoapi.extension",
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "sphinx_rtd_theme"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]
html_css_files = ["rope.css"]

# Make sure the target is unique
autosectionlabel_prefix_document = True

# suppress third-party generated warnings
suppress_warnings = [
    "docutils",
    # rope.base.ast re-exports the stdlib ast with ``from ast import *``,
    # which sphinx-autoapi cannot follow.
    "autoapi.python_import_resolution",
]

# -- Automatically generated API reference (sphinx-autoapi) ------------------

autoapi_dirs = ["../rope"]
autoapi_root = "api"
# The entry point is added explicitly to the toctree in api.rst.
autoapi_add_toctree_entry = False
# Document the public interface, including members inherited from
# private base classes such as rope.base.project._Project.  Imported
# members are left out, otherwise e.g. rope.base.ast would document
# the whole stdlib ast again.
autoapi_options = [
    "members",
    "undoc-members",
    "show-inheritance",
    "inherited-members",
    "show-module-summary",
]


_documented_objects = {}


def _reset_documented_objects(app):
    _documented_objects.clear()


def _skip_redefinitions(app, what, name, obj, skip, options):
    """Document only the first of repeated definitions of one name

    Some modules define the same name more than once on purpose
    (e.g. fallbacks in ``try``/``except`` blocks or the operator
    handlers in ``rope.base.oi.type_hinting.evaluate``), which would
    otherwise produce duplicate object descriptions.
    """
    if skip:
        return None
    first = _documented_objects.setdefault(name, obj)
    return True if first is not obj else None


def setup(app):
    # Run before sphinx-autoapi, which renders its pages on builder-inited.
    app.connect("builder-inited", _reset_documented_objects, priority=100)
    app.connect("autoapi-skip-member", _skip_redefinitions)


# -- Intersphinx -------------------------------------------------------------

intersphinx_mapping = {"python": ("https://docs.python.org/3", None)}
