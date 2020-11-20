import inspect
import logging
import traceback
from functools import wraps

logger = logging.getLogger(__name__)

watermark = " [TIDAL]"


def apply_watermark(val):
    return val + watermark


def remove_watermark(watermarked_val):
    if watermarked_val is None:
        return None

    if watermarked_val.endswith(watermark):
        watermarked_val = watermarked_val[:-len(watermark)]

    return watermarked_val


def get_query_param(query, param, should_remove_watermark=True):
    val = None
    if param in query:
        val = query[param]
        if hasattr(val, '__iter__'):
            val = next(iter(val))

    return remove_watermark(val) if should_remove_watermark else val


def catch(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error('%s: %s', e.__class__.__name__, e)
            logger.error('%s(%s, %s)', func.__name__,
                         ', '.join(str(a) for a in args),
                         ', '.join('{}={}'.format(str(k), str(v)) for k, v in kwargs.items()))
            raise
    return wrapper


def inspect_stack(*args, **kwargs):
    return ''.join('{}\n{}'.format(':'.join(str(x) for x in i[1:-2]), ''.join(i[-2]))
                   for i in inspect.stack(*args, **kwargs))
