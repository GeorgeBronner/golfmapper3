import React, { useEffect, useRef, useState } from 'react';
import api from '../services/api';
import { useAuth } from './AuthProvider';

function Map() {
    const iframeRef = useRef(null);
    const { token } = useAuth();
    const [status, setStatus] = useState('loading');

    const loadMap = async () => {
        setStatus('loading');
        try {
            const coursesRes = await api.get('/user_courses/readall_ids_w_year');
            if (coursesRes.data.length === 0) {
                setStatus('empty');
                return;
            }
        } catch {
            setStatus('error');
            return;
        }

        api.get('/map/usermap?rand=' + new Date())
            .catch(error => {
                if (error.response?.status === 404) {
                    setStatus('generating');
                    return api.get('/map/user_map_generate')
                        .then(() => api.get('/map/usermap'));
                }
                throw error;
            })
            .then(response => {
                const doc = iframeRef.current.contentWindow.document;
                doc.open();
                doc.write(response.data);
                doc.close();
                setStatus('loaded');
            })
            .catch(() => setStatus('error'));
    };

    useEffect(() => { loadMap(); }, [token]);

    return (
        <div className="map-wrapper">
            <div className="map-overlay-bar">
                <div className="map-title-chip">🗺 Your Golf Map</div>
                <button className="btn-ghost" onClick={loadMap}>
                    ⟳ Regenerate Map
                </button>
            </div>

            {status === 'loading' && <p className="map-status">Loading map…</p>}
            {status === 'generating' && <p className="map-status">Generating your map, this may take a moment…</p>}
            {status === 'empty' && (
                <p className="map-status">
                    You haven't added any courses yet.{' '}
                    <a href="/course_search" style={{ color: 'var(--primary)' }}>Search for courses to add.</a>
                </p>
            )}
            {status === 'error' && <p className="map-status">Failed to load map. Please try again later.</p>}

            <iframe
                ref={iframeRef}
                title="Golf Course Map"
                className="map-iframe"
                style={{ display: status === 'loaded' ? 'block' : 'none' }}
            />
        </div>
    );
}

export default Map;
