// The backend stamps a fresh CSP nonce into a <meta> tag on every SPA-shell
// response (see backend/app/main.py's _serve_spa_shell). The folium map HTML
// we inject via <iframe srcDoc> inherits this page's CSP, so its <script>
// tags need the same nonce attached before we hand it to the iframe.
export function getCspNonce() {
    return document.querySelector('meta[name="csp-nonce"]')?.content || '';
}

export function nonceScriptTags(html) {
    const nonce = getCspNonce();
    return nonce ? html.replace(/<script/g, `<script nonce="${nonce}"`) : html;
}
