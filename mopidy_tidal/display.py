from string import whitespace
CHAR_TIDAL = u"\U0001F163"
CHAR_FAV = u"\u229B"
CHAR_MASTER = u"\u24C2"
CHAR_LOSSLESS = u"\U0001F1A9"
CHAR_COMPRESSED = u"\u21CA"
CHAR_LOW = u"\u25BC"
CHAR_ALERT = u"\u26A0"

FEAT_CHARS = u"".join({v for k, v in vars().items() if k.startswith('CHAR_')} | set(whitespace))


def tidal_item(s):
    return u"{1} {0}".format(s, CHAR_TIDAL)


def fav_item(s):
    return u"{1} {0}".format(s, CHAR_FAV)


def master_title(s):
    return u"{1} {0}".format(s, CHAR_MASTER)


def lossless_title(s):
    return s


def high_title(s):
    return u"{1} {0}".format(s, CHAR_COMPRESSED)


def low_title(s):
    return u"{1} {0}".format(s, CHAR_LOW)


def alert_item(s):
    return u"{1} {0}".format(s, CHAR_ALERT)


def strip_feat(s):
    return s.strip(FEAT_CHARS)
