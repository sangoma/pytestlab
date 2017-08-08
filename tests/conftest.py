from .mocks import lab as mocklab


pytest_plugins = ['lab', 'pytester', mocklab.__name__]
