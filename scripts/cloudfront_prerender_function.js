// CloudFront Function (viewer request) — serve prerendered pages, e.g. /about -> /about/index.html.
// CloudFront console > Functions > Create > paste > Publish > associate with the distribution's
// default behaviour as "Viewer request". Keep the existing 403/404 -> /index.html error pages.
function handler(event) {
  var r = event.request;
  var uri = r.uri;
  if (uri.startsWith('/api/')) { return r; }
  if (uri.endsWith('/')) { r.uri = uri + 'index.html'; }
  else if (uri.lastIndexOf('.') <= uri.lastIndexOf('/')) { r.uri = uri + '/index.html'; }
  return r;
}
