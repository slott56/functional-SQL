# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import sys
sys.path.insert(0, "../src")

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'Functional SQL'
copyright = '2024, S.Lott'
author = 'S.Lott'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration


extensions = [
    "sphinxcontrib.plantuml",
    "sphinx.ext.mathjax",
    "sphinx.ext.autodoc",
    "sphinx.ext.todo",
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'alabaster'
html_static_path = ['_static']


# -- Options for Autodoc -------------------------------------------------

autodoc_member_order = 'bysource'

# -- Options for todo

todo_include_todos = True
