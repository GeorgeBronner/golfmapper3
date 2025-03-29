import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import App from './components/App';

describe('App', () => {
  it('renders learn react link', () => {
    render(<App />);
    const linkElement = screen.getByText(/learn react/i);
    expect(linkElement).toBeInTheDocument();
  });
});