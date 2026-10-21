import React from 'react';
import { LayersControl, TileLayer } from 'react-leaflet';

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

/**
 * Street/satellite base map with a Leaflet layer switcher.
 * Must be rendered inside a MapContainer.
 *
 * defaultLayer: 'street' | 'satellite'
 * position: Leaflet control corner, e.g. 'topleft' when something else owns the top-right
 */
export default function BaseLayers({ defaultLayer = 'street', position = 'topright' }) {
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
        </LayersControl>
    );
}
