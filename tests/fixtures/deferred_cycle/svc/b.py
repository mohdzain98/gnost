def helper():
    from svc.a import run  # deferred: only runs when helper() is called

    return run
