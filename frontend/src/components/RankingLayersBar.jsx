import React from 'react';
import { ALL_STATES, layerKey, stateName } from '../utils/useRankingLayers';

// The controls for the ranking layers: a checkbox and edition picker per list, and one
// Best in State control (all states or one, an edition and a Public only filter).
// `ui` comes from useRankingLayers.
function RankingLayersBar({ ui }) {
    const {
        rankingLists, layers, setLayer, stateLists, stateLayer, patchState,
        selectedState, stateEditions, stateEdition, failed, stateKey,
    } = ui;
    if (rankingLists.length === 0 && stateLists.length === 0) return null;

    return (
        <div className="map-rankings-bar">
            <strong>Rankings</strong>
            {rankingLists.map(list => (
                <div key={list.id} className="map-rankings-layer">
                    <label>
                        <input
                            type="checkbox"
                            checked={!!layers[list.id]?.on}
                            onChange={e => setLayer(list.id, { on: e.target.checked })}
                        />{' '}
                        {list.name}
                    </label>
                    <select
                        aria-label={`${list.name} edition`}
                        value={layers[list.id]?.editionId ?? ''}
                        onChange={e => setLayer(list.id, { editionId: Number(e.target.value) })}
                    >
                        {list.editions.map(ed => <option key={ed.id} value={ed.id}>{ed.label}</option>)}
                    </select>
                    {layers[list.id]?.on && failed.has(layerKey(list.id, layers[list.id].editionId)) && (
                        <span role="alert">⚠ couldn't load</span>
                    )}
                </div>
            ))}
            {stateLists.length > 0 && (
                <div className="map-rankings-layer">
                    <label>
                        <input
                            type="checkbox"
                            checked={stateLayer.on}
                            onChange={e => patchState({ on: e.target.checked })}
                        />{' '}
                        Best in State
                    </label>
                    <select
                        aria-label="Best in State state"
                        value={selectedState ? selectedState.id : ALL_STATES}
                        onChange={e => patchState({ state: e.target.value })}
                    >
                        <option value={ALL_STATES}>All states</option>
                        {stateLists.map(l => <option key={l.id} value={l.id}>{stateName(l)}</option>)}
                    </select>
                    <select
                        aria-label="Best in State edition"
                        value={stateEdition ?? ''}
                        onChange={e => patchState({ edition: e.target.value })}
                    >
                        {stateEditions.map(label => <option key={label} value={label}>{label}</option>)}
                    </select>
                    <label>
                        <input
                            type="checkbox"
                            checked={stateLayer.publicOnly}
                            onChange={e => patchState({ publicOnly: e.target.checked })}
                        />{' '}
                        Public only
                    </label>
                    {stateLayer.on && stateKey && failed.has(stateKey) && <span role="alert">⚠ couldn't load</span>}
                </div>
            )}
        </div>
    );
}

export default RankingLayersBar;
