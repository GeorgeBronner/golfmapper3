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

// Maps full state/province names to abbreviations, keyed by alpha-2 country code
const STATE_ABBR = {
    us: {
        'Alabama': 'AL', 'Alaska': 'AK', 'Arizona': 'AZ', 'Arkansas': 'AR',
        'California': 'CA', 'Colorado': 'CO', 'Connecticut': 'CT', 'Delaware': 'DE',
        'Florida': 'FL', 'Georgia': 'GA', 'Hawaii': 'HI', 'Idaho': 'ID',
        'Illinois': 'IL', 'Indiana': 'IN', 'Iowa': 'IA', 'Kansas': 'KS',
        'Kentucky': 'KY', 'Louisiana': 'LA', 'Maine': 'ME', 'Maryland': 'MD',
        'Massachusetts': 'MA', 'Michigan': 'MI', 'Minnesota': 'MN', 'Mississippi': 'MS',
        'Missouri': 'MO', 'Montana': 'MT', 'Nebraska': 'NE', 'Nevada': 'NV',
        'New Hampshire': 'NH', 'New Jersey': 'NJ', 'New Mexico': 'NM', 'New York': 'NY',
        'North Carolina': 'NC', 'North Dakota': 'ND', 'Ohio': 'OH', 'Oklahoma': 'OK',
        'Oregon': 'OR', 'Pennsylvania': 'PA', 'Rhode Island': 'RI', 'South Carolina': 'SC',
        'South Dakota': 'SD', 'Tennessee': 'TN', 'Texas': 'TX', 'Utah': 'UT',
        'Vermont': 'VT', 'Virginia': 'VA', 'Washington': 'WA', 'West Virginia': 'WV',
        'Wisconsin': 'WI', 'Wyoming': 'WY', 'District of Columbia': 'DC',
    },
    ca: {
        'Alberta': 'AB', 'British Columbia': 'BC', 'Manitoba': 'MB',
        'New Brunswick': 'NB', 'Newfoundland and Labrador': 'NL', 'Nova Scotia': 'NS',
        'Ontario': 'ON', 'Prince Edward Island': 'PE', 'Quebec': 'QC',
        'Saskatchewan': 'SK', 'Northwest Territories': 'NT', 'Nunavut': 'NU', 'Yukon': 'YT',
    },
    au: {
        'New South Wales': 'NSW', 'Victoria': 'VIC', 'Queensland': 'QLD',
        'Western Australia': 'WA', 'South Australia': 'SA', 'Tasmania': 'TAS',
        'Australian Capital Territory': 'ACT', 'Northern Territory': 'NT',
    },
    mx: {
        'Aguascalientes': 'AGS', 'Baja California': 'BC', 'Baja California Sur': 'BCS',
        'Campeche': 'CAMP', 'Chiapas': 'CHIS', 'Chihuahua': 'CHIH',
        'Coahuila': 'COAH', 'Colima': 'COL', 'Durango': 'DGO',
        'Guanajuato': 'GTO', 'Guerrero': 'GRO', 'Hidalgo': 'HGO',
        'Jalisco': 'JAL', 'Mexico City': 'CDMX', 'México': 'MEX',
        'Michoacán': 'MICH', 'Morelos': 'MOR', 'Nayarit': 'NAY',
        'Nuevo León': 'NL', 'Oaxaca': 'OAX', 'Puebla': 'PUE',
        'Querétaro': 'QRO', 'Quintana Roo': 'QR', 'San Luis Potosí': 'SLP',
        'Sinaloa': 'SIN', 'Sonora': 'SON', 'Tabasco': 'TAB',
        'Tamaulipas': 'TAMPS', 'Tlaxcala': 'TLAX', 'Veracruz': 'VER',
        'Yucatán': 'YUC', 'Zacatecas': 'ZAC',
    },
    // ... add more countries as needed
};

/**
 * Convert a Nominatim address object to { city, state, country } using standard codes.
 * @param {object} a - address field from Nominatim reverse geocode response
 * @returns {{ city: string, state: string, country: string }}
 */
export function nominatimToGeoFields(a) {
    const cc = (a.country_code || '').toLowerCase();
    const fullState = a.state || '';
    const stateMap = STATE_ABBR[cc];
    const state = stateMap ? (stateMap[fullState] || fullState) : fullState;
    const country = ALPHA2_TO_ALPHA3[cc] || a.country || '';
    const city = a.city || a.town || a.village || a.hamlet || '';
    return { city, state, country };
}
