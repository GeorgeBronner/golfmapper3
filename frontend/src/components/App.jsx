import React from 'react';
import { RouterProvider } from 'react-router-dom';
// Use a relative path instead of the alias
import router from '../router';

function App() {
    return (
        <div className="App">
            <RouterProvider router={router} />
        </div>
    );
}

export default App;