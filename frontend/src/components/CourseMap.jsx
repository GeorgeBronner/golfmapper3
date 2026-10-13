import React, { memo, useEffect, useMemo, useState } from 'react';
import L from 'leaflet';
import { MapContainer, TileLayer, ScaleControl, CircleMarker, Marker, Popup, useMap } from 'react-leaflet';
import MarkerClusterGroup from 'react-leaflet-cluster';
import 'leaflet/dist/leaflet.css';
import 'react-leaflet-cluster/dist/assets/MarkerCluster.css';
import 'react-leaflet-cluster/dist/assets/MarkerCluster.Default.css';

// Above this many visible points, cluster by default — thousands of
// individual markers make panning/zooming sluggish even on canvas.
export const AUTO_CLUSTER_THRESHOLD = 3000;

const DEFAULT_CENTER = [40, -90];
const DEFAULT_ZOOM = 4;

// Clustering only works with Markers, not CircleMarkers, so clustered mode
// draws each point as a small colored-dot divIcon instead. Colors come from
// our own palette (never user input), so building the HTML string is safe.
const dotIcons = {};
function dotIcon(color) {
    if (!dotIcons[color]) {
        dotIcons[color] = L.divIcon({
            className: 'course-dot-icon',
            html: `<span style="background:${color}"></span>`,
            iconSize: [14, 14],
        });
    }
    return dotIcons[color];
}

function FitToPoints({ points }) {
    const map = useMap();
    useEffect(() => {
        if (points.length === 0) return;
        const bounds = L.latLngBounds(points.map(p => [p.lat, p.lon]));
        map.fitBounds(bounds, { padding: [30, 30], maxZoom: 12 });
    }, [points, map]);
    return null;
}

// Course names are user-supplied: render them as React text, never as HTML.
export function CoursePopupContent({ point }) {
    return (
        <div className="course-popup">
            <div className="course-popup-name">{point.name}</div>
            <div className="course-popup-meta">
                {point.year ? `${point.year} · ` : ''}#{point.id}
            </div>
        </div>
    );
}

// One group's markers, memoized so that unrelated re-renders (opening a popup,
// toggling another group) don't touch them. react-leaflet compares
// position/pathOptions/eventHandlers by reference and re-applies them on any
// change; inside a cluster group each setLatLng is a remove+re-add, so a
// careless re-render of ~15k markers freezes the page.
const GroupMarkers = memo(function GroupMarkers({ group, clustered, onSelect }) {
    return useMemo(() => {
        const pathOptions = { color: group.color, fillColor: group.color, fillOpacity: 0.7, opacity: 0.9 };
        const icon = dotIcon(group.color);
        return group.points.map(point => {
            const position = [point.lat, point.lon];
            const eventHandlers = { click: () => onSelect({ point, position }) };
            return clustered ? (
                <Marker key={point.id} position={position} icon={icon} eventHandlers={eventHandlers} />
            ) : (
                <CircleMarker
                    key={point.id}
                    center={position}
                    radius={7}
                    pathOptions={pathOptions}
                    eventHandlers={eventHandlers}
                />
            );
        });
    }, [group, clustered, onSelect]);
});

function Legend({ groups, hidden, onToggle }) {
    return (
        <div className="course-map-legend">
            {groups.map(group => (
                <label key={group.name} className="course-map-legend-item">
                    <input
                        type="checkbox"
                        checked={!hidden.has(group.name)}
                        onChange={() => onToggle(group.name)}
                    />
                    <span className="course-map-legend-dot" style={{ background: group.color }} />
                    <span>{group.name}</span>
                    <span className="course-map-legend-count">{group.points.length}</span>
                </label>
            ))}
        </div>
    );
}

/**
 * Renders groups of course points on a canvas-backed Leaflet map.
 *
 * groups: [{ name, color, points: [{ id, lat, lon, name, year? }] }]
 * cluster: force clustering on/off; defaults to on above AUTO_CLUSTER_THRESHOLD points.
 */
export default function CourseMap({ groups, cluster, fitToPoints = false, showLegend = false }) {
    const [hidden, setHidden] = useState(() => new Set());
    // A single shared popup rather than one per marker — at 15k markers,
    // per-marker Popup instances are a real memory/mount cost. Each click
    // stores a fresh object: Leaflet closes the popup on the click's
    // preclick, so re-clicking the same marker must still change state for
    // the popup to reopen.
    const [selected, setSelected] = useState(null);

    const visible = useMemo(
        () => groups.filter(group => !hidden.has(group.name)),
        [groups, hidden],
    );
    const allPoints = useMemo(() => groups.flatMap(group => group.points), [groups]);
    const visibleCount = visible.reduce((n, group) => n + group.points.length, 0);
    const clustered = cluster ?? visibleCount > AUTO_CLUSTER_THRESHOLD;

    const toggle = name => {
        setSelected(null);
        setHidden(prev => {
            const next = new Set(prev);
            if (next.has(name)) next.delete(name);
            else next.add(name);
            return next;
        });
    };

    const markers = visible.map(group => (
        <GroupMarkers key={group.name} group={group} clustered={clustered} onSelect={setSelected} />
    ));

    return (
        <div className="course-map">
            <MapContainer preferCanvas center={DEFAULT_CENTER} zoom={DEFAULT_ZOOM} className="course-map-canvas">
                <TileLayer
                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                />
                <ScaleControl />
                {clustered ? (
                    <MarkerClusterGroup chunkedLoading>{markers}</MarkerClusterGroup>
                ) : (
                    markers
                )}
                {selected && (
                    // No close handler clearing `selected`: a closed popup left
                    // mounted is harmless, and clearing on Leaflet's remove
                    // event can race the next marker's click.
                    <Popup position={selected.position}>
                        <CoursePopupContent point={selected.point} />
                    </Popup>
                )}
                {fitToPoints && <FitToPoints points={allPoints} />}
            </MapContainer>
            {showLegend && groups.length > 0 && <Legend groups={groups} hidden={hidden} onToggle={toggle} />}
        </div>
    );
}
