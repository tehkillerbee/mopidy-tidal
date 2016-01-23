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
