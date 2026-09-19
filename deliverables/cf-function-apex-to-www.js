function handler(event) {
    var request = event.request;
    var host = request.headers.host && request.headers.host.value;

    // Only redirect requests hitting the apex (naked) domain.
    // www requests fall through and are served normally by the S3 origin.
    if (host === 'pmcmanagers.com') {
        // Rebuild querystring exactly as received so link params are preserved.
        var qs = '';
        if (request.querystring) {
            var parts = [];
            for (var key in request.querystring) {
                var v = request.querystring[key];
                if (v.multiValue) {
                    for (var i = 0; i < v.multiValue.length; i++) {
                        parts.push(key + '=' + encodeURIComponent(v.multiValue[i].value));
                    }
                } else {
                    parts.push(key + '=' + encodeURIComponent(v.value));
                }
            }
            if (parts.length) qs = '?' + parts.join('&');
        }
        return {
            statusCode: 301,
            statusDescription: 'Moved Permanently',
            headers: {
                'location': { value: 'https://www.pmcmanagers.com' + request.uri + qs },
                'cache-control': { value: 'max-age=3600' }
            }
        };
    }

    return request;
}
