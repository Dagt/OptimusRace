// Optional front door. The Django app and all writes stay on Railway.
export default {
  async fetch(request, env) {
    if (!env.ORIGIN_URL || !env.WORKER_PROXY_SECRET) {
      return new Response('Servicio sin configurar', {status: 503});
    }
    const origin = new URL(env.ORIGIN_URL);
    if (origin.protocol !== 'https:') return new Response('Origen inválido', {status: 503});
    const incoming = new URL(request.url), target = new URL(request.url);
    target.host = origin.host;
    target.protocol = 'https:';
    const headers = new Headers(request.headers);
    headers.delete('host');
    headers.delete('x-forwarded-host');
    headers.set('x-forwarded-proto', 'https');
    headers.set('x-optimus-proxy-token', env.WORKER_PROXY_SECRET);
    const upstream = new Request(target, {
      method: request.method, headers, redirect: 'manual',
      body: ['GET', 'HEAD'].includes(request.method) ? undefined : request.body,
      duplex: 'half',
    });
    try {
      const response = await fetch(upstream, {cache: 'no-store'});
      const output = new Response(response.body, response);
      // Never cache sessions, coach writes, CSRF tokens or live results.
      output.headers.set('Cache-Control', 'private, no-store');
      const location = output.headers.get('Location');
      if (location) {
        const redirect = new URL(location, target);
        if (redirect.origin === origin.origin) {
          redirect.host = incoming.host;
          output.headers.set('Location', redirect.href);
        }
      }
      return output;
    } catch {
      return new Response('La plataforma no está disponible temporalmente.', {
        status: 502, headers: {'Cache-Control': 'no-store'},
      });
    }
  },
};
