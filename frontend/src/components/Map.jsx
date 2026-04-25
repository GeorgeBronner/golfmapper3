import React, { useEffect, useRef, useState } from 'react';
import api from '../services/api';
import { useAuth } from './AuthProvider';

function Map() {
    const iframeRef = useRef(null);
    const { token } = useAuth();
    const [status, setStatus] = useState('loading');

    useEffect(() => {
        const loadMap = () => {
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

        loadMap();
    }, [token]);

    return (
        <div className="App">
            <h1>Your Map</h1>
            {status === 'generating' && <p>Generating your map...</p>}
            {status === 'error' && <p>Failed to load map. Please try again later.</p>}
            <iframe
                ref={iframeRef}
                title="HTML Content"
                width="100%"
                height="800px"
                style={{ border: 'none', display: status === 'loaded' ? 'block' : 'none' }}
            />
        </div>
    );
}

export default Map;
