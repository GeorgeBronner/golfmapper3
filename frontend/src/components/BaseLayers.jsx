import React, { useState } from 'react';
import { LayersControl, TileLayer, useMapEvents } from 'react-leaflet';

const STREET = {
    name: 'Street map',
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
};
const SATELLITE = {
    name: 'Satellite',
    attribution: 'Imagery &copy; Esri',
    // Esri tiles are addressed {y}/{x}, not the usual {x}/{y}.
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
};
// Transparent state/county lines and place names, drawn over the imagery.
const LABELS = {
    name: 'Labels',
    attribution: 'Boundaries &copy; Esri',
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}',
};

/**
 * Street/satellite base map with a Leaflet layer switcher, plus a Labels
 * overlay for the satellite view. Must be rendered inside a MapContainer.
 *
 * defaultLayer: 'street' | 'satellite'
 * position: Leaflet control corner, e.g. 'topleft' when something else owns the top-right
 */
export default function BaseLayers({ defaultLayer = 'street', position = 'topright' }) {
    // Labels follow the base layer (on for satellite, off for the street map,
    // which has its own) but can still be toggled by hand. Tracking the
    // control's own events keeps this state in step with what's on the map.
    const [labels, setLabels] = useState(defaultLayer === 'satellite');
    useMapEvents({
        baselayerchange: e => setLabels(e.name === SATELLITE.name),
        overlayadd: e => { if (e.name === LABELS.name) setLabels(true); },
        overlayremove: e => { if (e.name === LABELS.name) setLabels(false); },
    });

    return (
        <LayersControl position={position}>
            {[STREET, SATELLITE].map(layer => (
                <LayersControl.BaseLayer
                    key={layer.name}
                    name={layer.name}
                    checked={layer === (defaultLayer === 'satellite' ? SATELLITE : STREET)}
                >
                    <TileLayer attribution={layer.attribution} url={layer.url} maxZoom={19} />
                </LayersControl.BaseLayer>
            ))}
            <LayersControl.Overlay name={LABELS.name} checked={labels}>
                {/* Above the base layers, which are re-added on every switch. */}
                <TileLayer attribution={LABELS.attribution} url={LABELS.url} maxZoom={19} zIndex={10} />
            </LayersControl.Overlay>
        </LayersControl>
    );
}
