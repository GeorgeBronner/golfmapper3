import { describe, it, expect } from 'vitest';
import { pointsFromCompact } from './mapPoints';

describe('pointsFromCompact', () => {
    it('maps compact rows to objects keyed by the field header', () => {
        const fields = ['id', 'lat', 'lon', 'name', 'year'];
        const rows = [
            [1, 27.95, -82.46, 'Tampa Club - North', 2024],
            [2, 25.76, -80.19, 'Miami Club', null],
        ];
        expect(pointsFromCompact(fields, rows)).toEqual([
            { id: 1, lat: 27.95, lon: -82.46, name: 'Tampa Club - North', year: 2024 },
            { id: 2, lat: 25.76, lon: -80.19, name: 'Miami Club', year: null },
        ]);
    });

    it('handles an empty result', () => {
        expect(pointsFromCompact(['id', 'lat', 'lon', 'name'], [])).toEqual([]);
    });
});
