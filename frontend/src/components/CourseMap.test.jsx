import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import CourseMap, { CoursePopupContent } from './CourseMap';

// happy-dom has no canvas, so real Leaflet can't mount; stub the map pieces
// down to plain elements to test the component's own logic.
const markerRenders = vi.hoisted(() => ({ count: 0 }));
vi.mock('react-leaflet', () => {
    const StubMarker = ({ center, position, eventHandlers }) => {
        markerRenders.count += 1;
        const [lat] = center || position;
        return <button type="button" data-testid="marker" data-lat={lat} onClick={eventHandlers.click} />;
    };
    return {
        MapContainer: ({ children }) => <div>{children}</div>,
        TileLayer: () => null,
        LayersControl: Object.assign(({ children }) => <div>{children}</div>, {
            BaseLayer: ({ children }) => <div>{children}</div>,
            Overlay: ({ children }) => <div>{children}</div>,
        }),
        ScaleControl: () => null,
        Popup: ({ children }) => <div data-testid="popup">{children}</div>,
        CircleMarker: StubMarker,
        Marker: StubMarker,
        useMap: () => ({ fitBounds: vi.fn() }),
        useMapEvents: () => null,
    };
});
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

    it('shows the course rank when one is given', () => {
        render(
            <CoursePopupContent
                point={{ id: 7, lat: 1, lon: 2, name: 'A' }}
                rank={{ rank: 12, label: 'Golf Digest 2025-26' }}
            />
        );
        expect(screen.getByText('Golf Digest 2025-26: #12')).toBeInTheDocument();
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

describe('CourseMap selection', () => {
    const groups = [
        { name: 'alice', color: '#e74c3c', points: [{ id: 1, lat: 30, lon: -88, name: 'Magnolia', year: 2024 }] },
        { name: 'bob', color: '#3498db', points: [{ id: 2, lat: 31, lon: -87, name: 'West' }] },
    ];

    it('opens the popup without re-rendering any markers', async () => {
        render(<CourseMap groups={groups} />);
        const [first] = screen.getAllByTestId('marker');
        markerRenders.count = 0;
        await userEvent.click(first);
        expect(screen.getByTestId('popup')).toHaveTextContent('Magnolia');
        // Re-rendering (re-applying position/handlers to) every marker on
        // each click is what froze the 15k-point clustered map.
        expect(markerRenders.count).toBe(0);
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
