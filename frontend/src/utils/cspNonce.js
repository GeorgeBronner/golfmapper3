// The backend stamps a fresh CSP nonce into a <meta> tag on every SPA-shell
// response (see backend/app/main.py's _serve_spa_shell). The folium map HTML
// we inject via <iframe srcDoc> inherits this page's CSP, so its <script>
// tags need the same nonce attached before we hand it to the iframe.
export function getCspNonce() {
    return document.querySelector('meta[name="csp-nonce"]')?.content || '';
}

// folium always emits exactly this many <script> tags for its own
// boilerplate (CDN links + init script) — independent of how many markers,
// popups, or layers are in the map, since that content is embedded as data
// inside the init script rather than as extra tags (see
// backend/tests/test_map.py::test_*_script_tag_count_matches_frontend_trust_boundary,
// which pins this number against the actual folium output).
//
// We only stamp the nonce onto these first N tags. Popup/layer-name content
// (course names, usernames) is HTML-escaped server-side today, but IF that
// ever regressed, blindly nonce-ing every "<script" found in the fetched
// HTML would let an attacker-injected tag run too — a nonce is only a
// meaningful defense if it isn't handed out to content we don't control.
// Capping at the boilerplate count means anything beyond it is left
// un-nonced and gets blocked by CSP like it would without this whole
// mechanism.
const TRUSTED_MAP_SCRIPT_COUNT = 6;

export function nonceScriptTags(html) {
    const nonce = getCspNonce();
    if (!nonce) return html;
    let count = 0;
    return html.replace(/<script/g, (match) => {
        count += 1;
        return count <= TRUSTED_MAP_SCRIPT_COUNT ? `<script nonce="${nonce}"` : match;
    });
}
