import React, { useEffect, useRef, useState, useCallback } from 'react';
import api from '../services/api';
import { useAuth } from './AuthProvider';

function AllUsersMap() {
    const iframeRef = useRef(null);
    const activeCallRef = useRef(null);
    const { token } = useAuth();
    const [status, setStatus] = useState('loading');

    const loadMap = useCallback(async () => {
        const callId = {};
        activeCallRef.current = callId;
        const isCurrent = () => activeCallRef.current === callId;

        setStatus('loading');
        try {
            const response = await api.get('/map/allmap?rand=' + new Date());
            if (!isCurrent()) return;
            const doc = iframeRef.current.contentWindow.document;
            doc.open();
            doc.write(response.data);
            doc.close();
            setStatus('loaded');
        } catch {
            if (isCurrent()) setStatus('error');
        }
    }, []);

    useEffect(() => { loadMap(); }, [token, loadMap]);

    return (
        <div className="map-wrapper">
            <div className="map-overlay-bar">
                <div className="map-title-chip">🗺 All Users Map</div>
                <button className="btn-ghost" onClick={loadMap}>
                    ⟳ Refresh Map
                </button>
            </div>

            {status === 'loading' && <p className="map-status">Loading map…</p>}
            {status === 'error' && <p className="map-status">Failed to load map. Please try again later.</p>}

            <iframe
                ref={iframeRef}
                title="All Users Golf Map"
                className="map-iframe"
                style={{ display: status === 'loaded' ? 'block' : 'none' }}
            />
        </div>
    );
}

export default AllUsersMap;
