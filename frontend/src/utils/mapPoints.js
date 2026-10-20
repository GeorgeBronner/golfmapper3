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
