import React, { useEffect, useRef, useState } from 'react';
import api from '../services/api';
import { useAuth } from './AuthProvider';

function Map() {
    const iframeRef = useRef(null);
    const { token } = useAuth();
    const [status, setStatus] = useState('loading');
    const blobUrlRef = useRef(null);

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
                    if (blobUrlRef.current) {
                        URL.revokeObjectURL(blobUrlRef.current);
                    }
                    const blob = new Blob([response.data], { type: 'text/html' });
                    blobUrlRef.current = URL.createObjectURL(blob);
                    iframeRef.current.src = blobUrlRef.current;
                    setStatus('loaded');
                })
                .catch(() => setStatus('error'));
        };

        loadMap();

        return () => {
            if (blobUrlRef.current) {
                URL.revokeObjectURL(blobUrlRef.current);
            }
        };
    }, [token]);

    return (
        <div className="App">
            <h1>Your Map</h1>
            {status === 'generating' && <p>Generating your map...</p>}
            {status === 'error' && <p>Failed to load map. Please try again later.</p>}
            <iframe
                ref={iframeRef}
                title="Golf Course Map"
                width="100%"
                height="800px"
                style={{ border: 'none', display: status === 'loaded' ? 'block' : 'none' }}
            />
        </div>
    );
}

export default Map;
