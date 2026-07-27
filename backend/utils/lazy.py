def _lazy_proxy(factory):
    class LazyProxy:
        def __init__(self):
            self._factory = factory
            self._obj = None

        def _get(self):
            if self._obj is None:
                self._obj = self._factory()
            return self._obj

        def __getattr__(self, name):
            return getattr(self._get(), name)

        def __call__(self, *args, **kwargs):
            return self._get()(*args, **kwargs)

        def __repr__(self):
            return f"<LazyProxy {self._factory.__name__}>"

        def __dir__(self):
            return dir(self._get())

    return LazyProxy()


def _is_initialized(proxy) -> bool:
    """True if the underlying object has already been created."""
    return object.__getattribute__(proxy, "_obj") is not None
