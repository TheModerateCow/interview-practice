// Backend calls: every request carries the X-ILab header the server requires.
export async function api(path, opts = {}, raw) {
  opts.headers = Object.assign({ 'X-ILab': '1' }, opts.headers || {});
  let r;
  try { r = await fetch('/api' + path, opts); }
  catch (e) { throw new Error('Cannot reach the server: ' + e.message); }
  if (!r.ok) {
    let m = r.status + ' ' + r.statusText;
    try { m = (await r.json()).error || m; } catch (e) {}
    throw new Error(m);
  }
  return raw ? r : r.json();
}
export const enc = p => p.split('/').map(encodeURIComponent).join('/');
