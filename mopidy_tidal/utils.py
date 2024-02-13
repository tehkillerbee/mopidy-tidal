watermark = " [TIDAL]"

def apply_watermark(val):
    return val + watermark


def remove_watermark(watermarked_val):
    if watermarked_val is None:
        return None

    if watermarked_val.endswith(watermark):
        watermarked_val = watermarked_val[: -len(watermark)]

    return watermarked_val
