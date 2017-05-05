import weakref
import functools


class HashedSeq(list):
    """ This class guarantees that hash() will be called no more than once
        per element.  This is important because the lru_cache() will hash
        the key multiple times on a cache miss.
    """

    __slots__ = 'hashvalue'

    def __init__(self, tup):
        self[:] = tup
        self.hashvalue = hash(tup)

    def __hash__(self):
        return self.hashvalue


def make_key(args, kwds, kwd_mark=(object(),),
             fasttypes={int, str, frozenset, type(None)}):
    key = args
    if kwds:
        key += kwd_mark
        for item in kwds.iteritems():
            key += item
    if len(key) == 1 and type(key[0]) in fasttypes:
        return key[0]
    return HashedSeq(key)


def weakref_cache(function):
    sentinel = object()
    cache = weakref.WeakValueDictionary()

    def wrapper(*args, **kwargs):
        key = make_key(args, kwargs)
        result = cache.get(key, sentinel)
        if result is sentinel:
            result = function(*args, **kwargs)
            cache[key] = result
        return result

    functools.update_wrapper(wrapper, function)
    return wrapper
