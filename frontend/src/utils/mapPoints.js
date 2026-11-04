// The map points endpoints return rows as compact arrays alongside a `fields`
// header (e.g. ["id", "lat", "lon", "name"]) to keep 15k-course payloads
// small. Turn them into objects keyed by those field names.
export function pointsFromCompact(fields, rows) {
    return rows.map(row => {
        const point = {};
        fields.forEach((field, i) => { point[field] = row[i]; });
        return point;
    });
}

// Colors for ranking-list groups on the all-users map, by list order; gold first.
export const RANKING_COLORS = ['#d4a017', '#0b7285', '#a61e4d'];
// Ranked courses the user has played, on their own map: a third color next to the layer's
// color (not yet played) and red (My courses).
export const PLAYED_COLOR = '#2f9e44';
// The Best in State layer (all states or one) has its own color.
export const STATE_RANKING_COLOR = '#5f3dc4';

// Per-user colors on the all-users map, in user-id order.
export const USER_COLORS = [
    '#e74c3c',
    '#3498db',
    '#2ecc71',
    '#9b59b6',
    '#f39c12',
    '#1abc9c',
    '#e67e22',
    '#e91e8c',
    '#00bcd4',
    '#8d6e63',
];
