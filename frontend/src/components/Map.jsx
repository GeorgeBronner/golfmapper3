import React, { useEffect, useRef, useState } from 'react';
import { API_BASE_URL } from '../config';

function Map() {
    const iframeRef = useRef(null);
    const token = localStorage.getItem('token');
    const [status, setStatus] = useState('loading');

    useEffect(() => {
        const authHeaders = { 'Authorization': `Bearer ${token}` };

        const loadMap = () => {
            fetch(`${API_BASE_URL}/map/usermap?rand=` + new Date(), { headers: authHeaders })
                .then(response => {
                    if (response.status === 404) {
                        setStatus('generating');
                        return fetch(`${API_BASE_URL}/map/user_map_generate`, {
                            method: 'GET',
                            headers: authHeaders,
                        }).then(genResponse => {
                            if (!genResponse.ok) throw new Error('Generation failed');
                            return fetch(`${API_BASE_URL}/map/usermap`, { headers: authHeaders });
                        });
                    }
                    if (!response.ok) throw new Error('Failed to load map');
                    return response;
                })
                .then(response => response.text())
                .then(html => {
                    const doc = iframeRef.current.contentWindow.document;
                    doc.open();
                    doc.write(html);
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
