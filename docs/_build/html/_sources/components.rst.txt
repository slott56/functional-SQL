###########
Components
###########

This isn't in PYPI, so you can't simply PIP-install it.

You need to clone the GitHub repo.
There are two ways to make use of this:

1.  ``python -m pip install -e /path/to/src``

2.  ``export PYTHONPATH=/path/to/src``

Both work. Choose one.

Your applications will look like this.

..  uml::

    @startuml

    [my app]
    [funcsql]

    [my app] --> [funcsql] : imports

    @enduml

That's about it.  We look at app code in the :ref:`demo` and :ref:`tutorial` sections.

We'll look at the :py:mod:`funcsql` code in the :ref:`funcsql` section.

