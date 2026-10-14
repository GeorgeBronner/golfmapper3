import { describe, it, expect } from 'vitest';
import { COUNTRY_OPTIONS, nominatimToGeoFields, validateGeoFields } from './geoLookup';

describe('nominatimToGeoFields', () => {
    it.each([
        ['US state', { country_code: 'us', state: 'Florida', city: 'Lakeland', 'ISO3166-2-lvl4': 'US-FL' },
            { city: 'Lakeland', state: 'FL', country: 'USA' }],
        ['CA province', { country_code: 'ca', state: 'Nova Scotia', city: 'Halifax', 'ISO3166-2-lvl4': 'CA-NS' },
            { city: 'Halifax', state: 'NS', country: 'CAN' }],
        ['MX state uses the ISO code, not QR', { country_code: 'mx', state: 'Quintana Roo', town: 'Cancún', 'ISO3166-2-lvl4': 'MX-ROO' },
            { city: 'Cancún', state: 'ROO', country: 'MEX' }],
        ['GB uses the county', { country_code: 'gb', village: 'Wisley', 'ISO3166-2-lvl4': 'GB-ENG', 'ISO3166-2-lvl6': 'GB-SRY' },
            { city: 'Wisley', state: 'SRY', country: 'GBR' }],
        ['IE uses the county', { country_code: 'ie', city: 'Dublin', 'ISO3166-2-lvl5': 'IE-L', 'ISO3166-2-lvl6': 'IE-D' },
            { city: 'Dublin', state: 'D', country: 'IRL' }],
        ['no subdivisions', { country_code: 'je', town: 'St Helier' },
            { city: 'St Helier', state: '', country: 'JEY' }],
        ['Sint Maarten reported under nl', { country_code: 'nl', town: 'Philipsburg', 'ISO3166-2-lvl3': 'NL-SX' },
            { city: 'Philipsburg', state: '', country: 'SXM' }],
        ['US territory', { country_code: 'pr', city: 'San Juan' },
            { city: 'San Juan', state: 'PR', country: 'USA' }],
        ['never a full state name', { country_code: 'us', state: 'Florida', city: 'Tampa' },
            { city: 'Tampa', state: '', country: 'USA' }],
    ])('%s', (_, address, expected) => {
        expect(nominatimToGeoFields(address)).toEqual(expected);
    });
});

describe('validateGeoFields', () => {
    it('accepts ISO codes, any case, and a blank state', () => {
        expect(validateGeoFields({ state: 'FL', country: 'USA' })).toEqual({});
        expect(validateGeoFields({ state: 'roo', country: 'mex' })).toEqual({});
        expect(validateGeoFields({ state: '', country: 'JEY' })).toEqual({});
    });

    it.each(['United States', 'US', 'XXX', ''])('rejects country %j', country => {
        expect(validateGeoFields({ state: '', country }).country).toBeTruthy();
    });

    it.each(['Florida', 'Nova Scotia', 'US-FL'])('rejects state %j', state => {
        expect(validateGeoFields({ state, country: 'USA' }).state).toBeTruthy();
    });

    it('rejects a state for a country with no subdivisions', () => {
        expect(validateGeoFields({ state: 'JY', country: 'JEY' }).state).toBeTruthy();
    });
});

describe('COUNTRY_OPTIONS', () => {
    it('lists each alpha-3 code once with a readable name', () => {
        const codes = COUNTRY_OPTIONS.map(o => o.code);
        expect(new Set(codes).size).toBe(codes.length);
        expect(COUNTRY_OPTIONS.find(o => o.code === 'USA').name).toBe('United States');
    });
});
