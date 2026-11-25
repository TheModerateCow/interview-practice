<script>
  // Docker and runner-image warnings, checked every 15 s.
  import { onMount } from 'svelte';
  import { api } from '../../lib/api.js';

  let msg = $state('');
  async function check() {
    try {
      const h = await api('/health'); const m = [];
      if (!h.docker) m.push(h.error || 'Docker is unreachable. Start Docker, then reload this page.');
      Object.entries(h.images || {}).forEach(([k, v]) => {
        if (v === 'pulling') m.push('Preparing the ' + k + ' runner image…');
        else if (v === 'missing') m.push('The ' + k + ' runner image is missing. Run deploy/install.sh.');
      });
      msg = m.join(' ');
    } catch (e) { msg = e.message; }
  }
  onMount(() => { check(); const t = setInterval(check, 15000); return () => clearInterval(t); });
</script>

<div id="health" class="health" class:hidden={!msg} role="alert">{msg}</div>
