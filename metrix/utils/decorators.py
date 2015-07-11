def memorized(f):
    @wraps(f)
    def _wrapped(*args, **kwargs):
        if not hasattr(f, '__cached_result'):
            f.__cached_result = {}
        cache_key = hash((tuple(args), tuple(kwargs.items())))
        if cache_key not in f.__cached_result:
            f.__cached_result[cache_key] = f(*args, **kwargs)
        return f.__cached_result[cache_key]
    return _wrapped
