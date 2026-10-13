import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import CourseMap, { CoursePopupContent } from './CourseMap';

// happy-dom has no canvas, so real Leaflet can't mount; stub the map pieces
// down to plain elements to test the component's own logic.
vi.mock('react-leaflet', () => ({
    MapContainer: ({ children }) => <div>{children}</div>,
    TileLayer: () => null,
    ScaleControl: () => null,
    Popup: ({ children }) => <div>{children}</div>,
    CircleMarker: ({ center }) => <span data-testid="marker" data-lat={center[0]} />,
    Marker: ({ position }) => <span data-testid="marker" data-lat={position[0]} />,
    useMap: () => ({ fitBounds: vi.fn() }),
}));
vi.mock('react-leaflet-cluster', () => ({ default: ({ children }) => <div data-testid="cluster">{children}</div> }));

const XSS_NAME = '<img src=x onerror="window.__xss = true">';

describe('CoursePopupContent', () => {
    it('renders course names as text, not HTML', () => {
        const { container } = render(
            <CoursePopupContent point={{ id: 7, lat: 1, lon: 2, name: XSS_NAME, year: 2024 }} />
        );
        expect(screen.getByText(XSS_NAME)).toBeInTheDocument();
        expect(container.querySelector('img')).toBeNull();
        expect(screen.getByText('2024 · #7')).toBeInTheDocument();
    });
});

describe('CourseMap legend', () => {
    const groups = [
        { name: 'alice', color: '#e74c3c', points: [{ id: 1, lat: 30, lon: -88, name: 'A' }] },
        { name: XSS_NAME, color: '#3498db', points: [{ id: 2, lat: 31, lon: -87, name: 'B' }] },
    ];

    it('lists each group (names as text) and toggles visibility', async () => {
        const { container } = render(<CourseMap groups={groups} showLegend />);
        expect(screen.getByText('alice')).toBeInTheDocument();
        expect(screen.getByText(XSS_NAME)).toBeInTheDocument();
        expect(container.querySelector('.course-map-legend img')).toBeNull();
        expect(screen.getAllByTestId('marker')).toHaveLength(2);

        const [aliceBox] = screen.getAllByRole('checkbox');
        expect(aliceBox).toBeChecked();
        await userEvent.click(aliceBox);
        expect(aliceBox).not.toBeChecked();
        const markers = screen.getAllByTestId('marker');
        expect(markers).toHaveLength(1);
        expect(markers[0]).toHaveAttribute('data-lat', '31');
    });
});

describe('CourseMap clustering', () => {
    const manyPoints = n => Array.from({ length: n }, (_, i) => ({ id: i, lat: 30, lon: -90, name: `C${i}` }));

    it('clusters automatically above the threshold', () => {
        render(<CourseMap groups={[{ name: 'all', color: '#000', points: manyPoints(3001) }]} />);
        expect(screen.getByTestId('cluster')).toBeInTheDocument();
    });

    it('does not cluster small sets unless asked', () => {
        const { rerender } = render(<CourseMap groups={[{ name: 'few', color: '#000', points: manyPoints(5) }]} />);
        expect(screen.queryByTestId('cluster')).toBeNull();
        rerender(<CourseMap cluster groups={[{ name: 'few', color: '#000', points: manyPoints(5) }]} />);
        expect(screen.getByTestId('cluster')).toBeInTheDocument();
    });
});
