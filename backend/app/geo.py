"""Country/state code normalization shared by the API and the course entry script.

Course convention: ``country`` is ISO 3166-1 alpha-3 (``USA``) and ``state`` is the ISO 3166-2
subdivision code without the country prefix (``FL``, ``NS``, ``ROO``). Countries with no ISO
subdivisions store an empty state. The frontend keeps a matching copy in ``frontend/src/utils/geoLookup.js``.
"""

import re
from typing import Annotated

from pydantic import AfterValidator

# Nominatim's address.country_code (ISO 3166-1 alpha-2, lowercase) -> ISO 3166-1 alpha-3
ALPHA2_TO_ALPHA3 = {
    "af": "AFG", "ax": "ALA", "al": "ALB", "dz": "DZA", "as": "ASM", "ad": "AND", "ao": "AGO", "ai": "AIA",
    "aq": "ATA", "ag": "ATG", "ar": "ARG", "am": "ARM", "aw": "ABW", "au": "AUS", "at": "AUT", "az": "AZE",
    "bs": "BHS", "bh": "BHR", "bd": "BGD", "bb": "BRB", "by": "BLR", "be": "BEL", "bz": "BLZ", "bj": "BEN",
    "bm": "BMU", "bt": "BTN", "bo": "BOL", "bq": "BES", "ba": "BIH", "bw": "BWA", "bv": "BVT", "br": "BRA",
    "io": "IOT", "bn": "BRN", "bg": "BGR", "bf": "BFA", "bi": "BDI", "cv": "CPV", "kh": "KHM", "cm": "CMR",
    "ca": "CAN", "ky": "CYM", "cf": "CAF", "td": "TCD", "cl": "CHL", "cn": "CHN", "cx": "CXR", "cc": "CCK",
    "co": "COL", "km": "COM", "cg": "COG", "cd": "COD", "ck": "COK", "cr": "CRI", "ci": "CIV", "hr": "HRV",
    "cu": "CUB", "cw": "CUW", "cy": "CYP", "cz": "CZE", "dk": "DNK", "dj": "DJI", "dm": "DMA", "do": "DOM",
    "ec": "ECU", "eg": "EGY", "sv": "SLV", "gq": "GNQ", "er": "ERI", "ee": "EST", "sz": "SWZ", "et": "ETH",
    "fk": "FLK", "fo": "FRO", "fj": "FJI", "fi": "FIN", "fr": "FRA", "gf": "GUF", "pf": "PYF", "tf": "ATF",
    "ga": "GAB", "gm": "GMB", "ge": "GEO", "de": "DEU", "gh": "GHA", "gi": "GIB", "gr": "GRC", "gl": "GRL",
    "gd": "GRD", "gp": "GLP", "gu": "GUM", "gt": "GTM", "gg": "GGY", "gn": "GIN", "gw": "GNB", "gy": "GUY",
    "ht": "HTI", "hm": "HMD", "va": "VAT", "hn": "HND", "hk": "HKG", "hu": "HUN", "is": "ISL", "in": "IND",
    "id": "IDN", "ir": "IRN", "iq": "IRQ", "ie": "IRL", "im": "IMN", "il": "ISR", "it": "ITA", "jm": "JAM",
    "jp": "JPN", "je": "JEY", "jo": "JOR", "kz": "KAZ", "ke": "KEN", "ki": "KIR", "kp": "PRK", "kr": "KOR",
    "kw": "KWT", "kg": "KGZ", "la": "LAO", "lv": "LVA", "lb": "LBN", "ls": "LSO", "lr": "LBR", "ly": "LBY",
    "li": "LIE", "lt": "LTU", "lu": "LUX", "mo": "MAC", "mg": "MDG", "mw": "MWI", "my": "MYS", "mv": "MDV",
    "ml": "MLI", "mt": "MLT", "mh": "MHL", "mq": "MTQ", "mr": "MRT", "mu": "MUS", "yt": "MYT", "mx": "MEX",
    "fm": "FSM", "md": "MDA", "mc": "MCO", "mn": "MNG", "me": "MNE", "ms": "MSR", "ma": "MAR", "mz": "MOZ",
    "mm": "MMR", "na": "NAM", "nr": "NRU", "np": "NPL", "nl": "NLD", "nc": "NCL", "nz": "NZL", "ni": "NIC",
    "ne": "NER", "ng": "NGA", "nu": "NIU", "nf": "NFK", "mk": "MKD", "mp": "MNP", "no": "NOR", "om": "OMN",
    "pk": "PAK", "pw": "PLW", "ps": "PSE", "pa": "PAN", "pg": "PNG", "py": "PRY", "pe": "PER", "ph": "PHL",
    "pn": "PCN", "pl": "POL", "pt": "PRT", "pr": "PRI", "qa": "QAT", "re": "REU", "ro": "ROU", "ru": "RUS",
    "rw": "RWA", "bl": "BLM", "sh": "SHN", "kn": "KNA", "lc": "LCA", "mf": "MAF", "pm": "SPM", "vc": "VCT",
    "ws": "WSM", "sm": "SMR", "st": "STP", "sa": "SAU", "sn": "SEN", "rs": "SRB", "sc": "SYC", "sl": "SLE",
    "sg": "SGP", "sx": "SXM", "sk": "SVK", "si": "SVN", "sb": "SLB", "so": "SOM", "za": "ZAF", "gs": "SGS",
    "ss": "SSD", "es": "ESP", "lk": "LKA", "sd": "SDN", "sr": "SUR", "sj": "SJM", "se": "SWE", "ch": "CHE",
    "sy": "SYR", "tw": "TWN", "tj": "TJK", "tz": "TZA", "th": "THA", "tl": "TLS", "tg": "TGO", "tk": "TKL",
    "to": "TON", "tt": "TTO", "tn": "TUN", "tr": "TUR", "tm": "TKM", "tc": "TCA", "tv": "TUV", "ug": "UGA",
    "ua": "UKR", "ae": "ARE", "gb": "GBR", "us": "USA", "um": "UMI", "uy": "URY", "uz": "UZB", "vu": "VUT",
    "ve": "VEN", "vn": "VNM", "vg": "VGB", "vi": "VIR", "wf": "WLF", "eh": "ESH", "ye": "YEM", "zm": "ZMB",
    "zw": "ZWE",
}  # fmt: skip

COUNTRY_CODES = frozenset(ALPHA2_TO_ALPHA3.values())

# Countries stored with an empty state because ISO 3166-2 defines no subdivisions for them
NO_SUBDIVISIONS = frozenset({"JEY", "GGY", "IMN", "CXR", "NFK", "SXM", "ABW", "CUW", "GIB", "VAT"})

# The DB stores GB and IE courses by county (ISO lvl6, e.g. SRY, D); every other country by first-level subdivision
_ISO_LEVELS = {"gb": (6, 4), "ie": (6,)}
_DEFAULT_LEVELS = (4, 6)

# US territories are stored as USA plus the territory code as state, matching the existing rows
_US_TERRITORIES = {"pr": "PR", "gu": "GU", "vi": "VI", "mp": "MP", "as": "AS"}

# Nominatim reports Dutch Caribbean countries under "nl" with only a lvl3 code
_NL_COUNTRIES = {"NL-AW": "ABW", "NL-CW": "CUW", "NL-SX": "SXM"}

_STATE_RE = re.compile(r"^[A-Z0-9]{1,3}$")


def normalize_country(value: str | None) -> str | None:
    """Return the upper-cased alpha-3 code, or raise ValueError if it is not one."""
    if value is None:
        return None
    code = value.strip().upper()
    if code not in COUNTRY_CODES:
        raise ValueError(f"country must be an ISO 3166-1 alpha-3 code such as USA, got {value!r}")
    return code


def normalize_state(value: str | None) -> str | None:
    """Return the upper-cased subdivision code ('' allowed), or raise ValueError if it is not one."""
    if value is None:
        return None
    code = value.strip().upper()
    if code and not _STATE_RE.match(code):
        raise ValueError(f"state must be an ISO 3166-2 subdivision code (1-3 letters/digits, e.g. FL), got {value!r}")
    return code


def check_state_for_country(state: str | None, country: str | None) -> None:
    if country in NO_SUBDIVISIONS and state:
        raise ValueError(f"{country} has no ISO subdivisions; leave state empty")


def nominatim_to_geo(address: dict) -> dict:
    """Convert a Nominatim ``address`` object to ``{city, state, country}`` using DB codes."""
    cc = (address.get("country_code") or "").lower()
    city = address.get("city") or address.get("town") or address.get("village") or address.get("hamlet") or ""

    lvl3 = address.get("ISO3166-2-lvl3") or ""
    if lvl3 in _NL_COUNTRIES:
        return {"city": city, "state": "", "country": _NL_COUNTRIES[lvl3]}
    if cc in _US_TERRITORIES:
        return {"city": city, "state": _US_TERRITORIES[cc], "country": "USA"}

    country = ALPHA2_TO_ALPHA3.get(cc, "")
    state = ""
    if country not in NO_SUBDIVISIONS:
        for level in _ISO_LEVELS.get(cc, _DEFAULT_LEVELS):
            iso = address.get(f"ISO3166-2-lvl{level}") or ""
            code = iso.split("-", 1)[1] if "-" in iso else ""
            if _STATE_RE.match(code):
                state = code
                break
    return {"city": city, "state": state, "country": country}


# Pydantic field types for request bodies; values are trimmed and upper-cased before being stored
CountryCode = Annotated[str | None, AfterValidator(normalize_country)]
StateCode = Annotated[str | None, AfterValidator(normalize_state)]
