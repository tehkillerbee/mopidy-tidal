from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import partial

TIDAL_PAGE_SIZE = 50  # Highly recommended


def paginated(call, limit=TIDAL_PAGE_SIZE, total=None):
    if total:
        pages = (total // limit) + min(1, total % limit)
        for items in sorted_threaded(*(
            partial(call, limit=limit, offset=limit * idx)
            for idx in range(pages)
        )):
            yield items
    else:
        idx = 0
        while True:
            results = call(limit=limit, offset=limit * idx)
            yield results
            if len(results) < limit:
                break
            idx += 1


def _threaded(*args, max_workers=None):
    thread_count = len(args)
    with ThreadPoolExecutor(
            max_workers=min(max_workers, thread_count) if max_workers else thread_count,
            thread_name_prefix=f"mopidy-tidal-split-",
    ) as executor:
        futures = {executor.submit(call): call for call in args}
        for future in as_completed(futures):
            yield futures[future], future.result()


def threaded(*args, **kwargs):
    for _, result in _threaded(*args, **kwargs):
        yield result


def sorted_threaded(*args, **kwargs):
    results = dict(_threaded(*args, **kwargs))
    return [results[call] for call in args]
