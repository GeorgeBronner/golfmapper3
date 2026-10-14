// Maps Nominatim's address.country_code (ISO 3166-1 alpha-2, lowercase) to ISO 3166-1 alpha-3
const ALPHA2_TO_ALPHA3 = {
      'af': 'AFG', 'ax': 'ALA', 'al': 'ALB', 'dz': 'DZA',
      'as': 'ASM', 'ad': 'AND', 'ao': 'AGO', 'ai': 'AIA',
      'aq': 'ATA', 'ag': 'ATG', 'ar': 'ARG', 'am': 'ARM',
      'aw': 'ABW', 'au': 'AUS', 'at': 'AUT', 'az': 'AZE',
      'bs': 'BHS', 'bh': 'BHR', 'bd': 'BGD', 'bb': 'BRB',
      'by': 'BLR', 'be': 'BEL', 'bz': 'BLZ', 'bj': 'BEN',
      'bm': 'BMU', 'bt': 'BTN', 'bo': 'BOL', 'bq': 'BES',
      'ba': 'BIH', 'bw': 'BWA', 'bv': 'BVT', 'br': 'BRA',
      'io': 'IOT', 'bn': 'BRN', 'bg': 'BGR', 'bf': 'BFA',
      'bi': 'BDI', 'cv': 'CPV', 'kh': 'KHM', 'cm': 'CMR',
      'ca': 'CAN', 'ky': 'CYM', 'cf': 'CAF', 'td': 'TCD',
      'cl': 'CHL', 'cn': 'CHN', 'cx': 'CXR', 'cc': 'CCK',
      'co': 'COL', 'km': 'COM', 'cg': 'COG', 'cd': 'COD',
      'ck': 'COK', 'cr': 'CRI', 'ci': 'CIV', 'hr': 'HRV',
      'cu': 'CUB', 'cw': 'CUW', 'cy': 'CYP', 'cz': 'CZE',
      'dk': 'DNK', 'dj': 'DJI', 'dm': 'DMA', 'do': 'DOM',
      'ec': 'ECU', 'eg': 'EGY', 'sv': 'SLV', 'gq': 'GNQ',
      'er': 'ERI', 'ee': 'EST', 'sz': 'SWZ', 'et': 'ETH',
      'fk': 'FLK', 'fo': 'FRO', 'fj': 'FJI', 'fi': 'FIN',
      'fr': 'FRA', 'gf': 'GUF', 'pf': 'PYF', 'tf': 'ATF',
      'ga': 'GAB', 'gm': 'GMB', 'ge': 'GEO', 'de': 'DEU',
      'gh': 'GHA', 'gi': 'GIB', 'gr': 'GRC', 'gl': 'GRL',
      'gd': 'GRD', 'gp': 'GLP', 'gu': 'GUM', 'gt': 'GTM',
      'gg': 'GGY', 'gn': 'GIN', 'gw': 'GNB', 'gy': 'GUY',
      'ht': 'HTI', 'hm': 'HMD', 'va': 'VAT', 'hn': 'HND',
      'hk': 'HKG', 'hu': 'HUN', 'is': 'ISL', 'in': 'IND',
      'id': 'IDN', 'ir': 'IRN', 'iq': 'IRQ', 'ie': 'IRL',
      'im': 'IMN', 'il': 'ISR', 'it': 'ITA', 'jm': 'JAM',
      'jp': 'JPN', 'je': 'JEY', 'jo': 'JOR', 'kz': 'KAZ',
      'ke': 'KEN', 'ki': 'KIR', 'kp': 'PRK', 'kr': 'KOR',
      'kw': 'KWT', 'kg': 'KGZ', 'la': 'LAO', 'lv': 'LVA',
      'lb': 'LBN', 'ls': 'LSO', 'lr': 'LBR', 'ly': 'LBY',
      'li': 'LIE', 'lt': 'LTU', 'lu': 'LUX', 'mo': 'MAC',
      'mg': 'MDG', 'mw': 'MWI', 'my': 'MYS', 'mv': 'MDV',
      'ml': 'MLI', 'mt': 'MLT', 'mh': 'MHL', 'mq': 'MTQ',
      'mr': 'MRT', 'mu': 'MUS', 'yt': 'MYT', 'mx': 'MEX',
      'fm': 'FSM', 'md': 'MDA', 'mc': 'MCO', 'mn': 'MNG',
      'me': 'MNE', 'ms': 'MSR', 'ma': 'MAR', 'mz': 'MOZ',
      'mm': 'MMR', 'na': 'NAM', 'nr': 'NRU', 'np': 'NPL',
      'nl': 'NLD', 'nc': 'NCL', 'nz': 'NZL', 'ni': 'NIC',
      'ne': 'NER', 'ng': 'NGA', 'nu': 'NIU', 'nf': 'NFK',
      'mk': 'MKD', 'mp': 'MNP', 'no': 'NOR', 'om': 'OMN',
      'pk': 'PAK', 'pw': 'PLW', 'ps': 'PSE', 'pa': 'PAN',
      'pg': 'PNG', 'py': 'PRY', 'pe': 'PER', 'ph': 'PHL',
      'pn': 'PCN', 'pl': 'POL', 'pt': 'PRT', 'pr': 'PRI',
      'qa': 'QAT', 're': 'REU', 'ro': 'ROU', 'ru': 'RUS',
      'rw': 'RWA', 'bl': 'BLM', 'sh': 'SHN', 'kn': 'KNA',
      'lc': 'LCA', 'mf': 'MAF', 'pm': 'SPM', 'vc': 'VCT',
      'ws': 'WSM', 'sm': 'SMR', 'st': 'STP', 'sa': 'SAU',
      'sn': 'SEN', 'rs': 'SRB', 'sc': 'SYC', 'sl': 'SLE',
      'sg': 'SGP', 'sx': 'SXM', 'sk': 'SVK', 'si': 'SVN',
      'sb': 'SLB', 'so': 'SOM', 'za': 'ZAF', 'gs': 'SGS',
      'ss': 'SSD', 'es': 'ESP', 'lk': 'LKA', 'sd': 'SDN',
      'sr': 'SUR', 'sj': 'SJM', 'se': 'SWE', 'ch': 'CHE',
      'sy': 'SYR', 'tw': 'TWN', 'tj': 'TJK', 'tz': 'TZA',
      'th': 'THA', 'tl': 'TLS', 'tg': 'TGO', 'tk': 'TKL',
      'to': 'TON', 'tt': 'TTO', 'tn': 'TUN', 'tr': 'TUR',
      'tm': 'TKM', 'tc': 'TCA', 'tv': 'TUV', 'ug': 'UGA',
      'ua': 'UKR', 'ae': 'ARE', 'gb': 'GBR', 'us': 'USA',
      'um': 'UMI', 'uy': 'URY', 'uz': 'UZB', 'vu': 'VUT',
      've': 'VEN', 'vn': 'VNM', 'vg': 'VGB', 'vi': 'VIR',
      'wf': 'WLF', 'eh': 'ESH', 'ye': 'YEM', 'zm': 'ZMB',
      'zw': 'ZWE',
};

// Country/state rules — keep in sync with backend/app/geo.py.
// country = ISO 3166-1 alpha-3 (USA); state = ISO 3166-2 subdivision code without the country prefix (FL, NS, ROO).
export const COUNTRY_CODES = new Set(Object.values(ALPHA2_TO_ALPHA3));

// Countries stored with an empty state because ISO 3166-2 defines no subdivisions for them
export const NO_SUBDIVISIONS = new Set(['JEY', 'GGY', 'IMN', 'CXR', 'NFK', 'SXM', 'ABW', 'CUW', 'GIB', 'VAT']);

// The DB stores GB and IE courses by county (ISO lvl6, e.g. SRY, D); every other country by first-level subdivision
const ISO_LEVELS = { gb: [6, 4], ie: [6] };
const DEFAULT_LEVELS = [4, 6];

// US territories are stored as USA plus the territory code as state, matching the existing rows
const US_TERRITORIES = { pr: 'PR', gu: 'GU', vi: 'VI', mp: 'MP', as: 'AS' };

// Nominatim reports Dutch Caribbean countries under "nl" with only a lvl3 code
const NL_COUNTRIES = { 'NL-AW': 'ABW', 'NL-CW': 'CUW', 'NL-SX': 'SXM' };

const STATE_RE = /^[A-Z0-9]{1,3}$/;

const regionNames = typeof Intl.DisplayNames === 'function' ? new Intl.DisplayNames(['en'], { type: 'region' }) : null;

// [{ code: 'USA', name: 'United States' }, ...] sorted by name, for country pickers
export const COUNTRY_OPTIONS = Object.entries(ALPHA2_TO_ALPHA3)
    .map(([a2, code]) => ({ code, name: regionNames?.of(a2.toUpperCase()) || code }))
    .sort((a, b) => a.name.localeCompare(b.name));

export const normalizeCode = value => (value || '').trim().toUpperCase();

/**
 * Check state/country against the DB convention.
 * @returns {{ state?: string, country?: string }} an error message per invalid field (empty when valid)
 */
export function validateGeoFields({ state, country }) {
    const errors = {};
    const c = normalizeCode(country);
    const s = normalizeCode(state);
    if (!c) errors.country = 'Country is required.';
    else if (!COUNTRY_CODES.has(c)) errors.country = `"${country}" is not an ISO 3-letter country code (e.g. USA, GBR, CAN).`;
    if (s && !STATE_RE.test(s)) errors.state = 'Use the ISO subdivision code (1–3 letters/digits, e.g. FL, NS, ROO), or leave blank.';
    else if (s && NO_SUBDIVISIONS.has(c)) errors.state = `${c} has no subdivisions — leave state blank.`;
    return errors;
}

/**
 * Convert a Nominatim address object to { city, state, country } using the DB codes.
 * @param {object} a - address field from a Nominatim reverse geocode response
 * @returns {{ city: string, state: string, country: string }}
 */
export function nominatimToGeoFields(a) {
    const cc = (a.country_code || '').toLowerCase();
    const city = a.city || a.town || a.village || a.hamlet || '';

    const lvl3 = a['ISO3166-2-lvl3'] || '';
    if (NL_COUNTRIES[lvl3]) return { city, state: '', country: NL_COUNTRIES[lvl3] };
    if (US_TERRITORIES[cc]) return { city, state: US_TERRITORIES[cc], country: 'USA' };

    const country = ALPHA2_TO_ALPHA3[cc] || '';
    let state = '';
    if (!NO_SUBDIVISIONS.has(country)) {
        for (const level of ISO_LEVELS[cc] || DEFAULT_LEVELS) {
            const iso = a[`ISO3166-2-lvl${level}`] || '';
            const code = iso.includes('-') ? iso.slice(iso.indexOf('-') + 1) : '';
            if (STATE_RE.test(code)) { state = code; break; }
        }
    }
    return { city, state, country };
}
