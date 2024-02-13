import datetime


def to_timestamp(dt):
    if not dt:
        return 0
    if isinstance(dt, str):
        if dt.lower() == "today":
            dt = datetime.datetime.combine(
                datetime.datetime.now().date(),
                datetime.time.min
            ).timestamp()
        else:
            dt = datetime.datetime.fromisoformat(dt)
    if isinstance(dt, datetime.datetime):
        dt = dt.timestamp()
    return int(dt)

def return_none(*args, **kwargs):
    return None
