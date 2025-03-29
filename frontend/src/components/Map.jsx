import React, { useEffect, useRef } from 'react';

function Map() {
    const iframeRef = useRef(null);

    const token = localStorage.getItem("token")

    useEffect(() => {
        fetch('http://localhost:8000/map/usermap?rand=' + new Date(), {
            headers: {
                'Authorization': `Bearer ${token}`,
                // Add more headers as needed
            },
        })
            .then(response => response.text())
            .then(html => {
                const doc = iframeRef.current.contentWindow.document;
                doc.open();
                doc.write(html);
                doc.close();
            });
    }, [token]);

    return (
        <div className="App">
            <h1>Your Map</h1>
            <iframe
                ref={iframeRef}
                title="HTML Content"
                width="100%"
                height="800px"
                style={{ border: 'none' }}
            />
        </div>
    );
}

export default Map;

