import React from 'react';
import { Form } from 'react-bootstrap';
import { COUNTRY_CODES, COUNTRY_OPTIONS } from '../utils/geoLookup';

/**
 * Country picker limited to ISO 3166-1 alpha-3 codes. A legacy value that is not a valid code
 * is still shown (flagged) so editing an old course doesn't silently change it.
 */
export function CountrySelect({ value, onChange, error, name = 'country', ...props }) {
    const legacy = value && !COUNTRY_CODES.has(value);
    return (
        <>
            <Form.Select name={name} value={value || ''} onChange={onChange} isInvalid={!!error} aria-label="Country" {...props}>
                <option value="">Select a country…</option>
                {legacy && <option value={value}>{value} (not a valid code)</option>}
                {COUNTRY_OPTIONS.map(({ code, name: label }) => (
                    <option key={code} value={code}>{code} — {label}</option>
                ))}
            </Form.Select>
            {error && <Form.Control.Feedback type="invalid">{error}</Form.Control.Feedback>}
        </>
    );
}

/** State/province input: upper-cases as you type and takes ISO 3166-2 codes (blank allowed). */
export function StateInput({ value, onChange, error, name = 'state', ...props }) {
    const handleChange = e => onChange({ target: { name, value: e.target.value.toUpperCase() } });
    return (
        <>
            <Form.Control
                name={name}
                value={value || ''}
                onChange={handleChange}
                isInvalid={!!error}
                placeholder="ISO code, e.g. FL (blank if none)"
                {...props}
            />
            {error && <Form.Control.Feedback type="invalid">{error}</Form.Control.Feedback>}
        </>
    );
}
