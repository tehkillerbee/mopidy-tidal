import datetime


def to_timestamp(dt):
    if not dt:
        return 0
    if isinstance(dt, str):
        dt = datetime.datetime.fromisoformat(dt)
    if isinstance(dt, datetime.datetime):
        dt = dt.timestamp()
    return int(dt)
