// web/app.js
(function () {
  'use strict';
  const $ = (id) => document.getElementById(id);
  const NATIVE = !!(window.Capacitor && window.Capacitor.isNativePlatform && window.Capacitor.isNativePlatform());
  function base() {
    try { return (localStorage.getItem('binksServer') || '').replace(/\/+$/, ''); } catch (e) { return ''; }
  }
  const api = (p, opt) => fetch(base() + p, opt).then((r) => r.json());
  let cams = [], current = null, stream = null, realCam = false;

  function esc(s) {
    return String(s).replace(/[&<>"']/g, (c) =>
      ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  }
  function toast(m) {
    const t = $('toast'); t.textContent = m; t.style.display = 'block';
    clearTimeout(t._h); t._h = setTimeout(() => (t.style.display = 'none'), 2200);
  }

  async function loadCams() {
    try {
      const d = await api('/api/cameras');
      cams = d.cameras || [];
      $('connBadge').textContent = 'LOCAL'; $('connBadge').classList.remove('off');
    } catch (e) {
      cams = []; $('connBadge').textContent = 'OFFLINE'; $('connBadge').classList.add('off');
    }
    renderCams();
  }
  function renderCams() {
    $('camGrid').innerHTML = cams.map((c) => `
      <button class="cam" data-id="${esc(c.id)}">
        <div class="view">
          <img src="${base()}/api/cameras/${encodeURIComponent(c.id)}/snapshot?t=${Date.now()}"
               onerror="this.style.display='none'">
          <span class="rec">● ${c.live ? 'LIVE' : 'SIM'}</span>
        </div>
        <div class="meta"><span>${esc(c.name)}<small>${esc(c.loc || c.kind)}</small></span>
          <span class="${c.live ? 'ok' : 'warn'}" style="font-size:.72rem">${c.live ? 'Live' : 'Test'}</span>
        </div>
      </button>`).join('') || ('<p class="sub">' + (NATIVE && !base()
        ? 'Set your Binks server address in Settings to connect.'
        : 'No cameras yet — add one in Settings.') + '</p>');
    document.querySelectorAll('.cam').forEach((b) =>
      b.addEventListener('click', () => openViewer(cams.find((c) => c.id === b.dataset.id))));
  }

  async function loadEvents() {
    let evs = [];
    try { evs = (await api('/api/events')).events || []; } catch (e) {}
    $('evList').innerHTML = evs.map((e) => {
      const when = e.ts ? new Date(e.ts * 1000).toLocaleString() : (e.t || '');
      return `<div class="ev"><div class="thumb">🎞</div><div>
        <b>${esc(e.msg)}</b><small>${esc(e.cam)} • ${esc(when)}</small></div></div>`;
    }).join('') || '<p class="sub">No events yet.</p>';
  }

  // tabs
  document.querySelectorAll('.tabbar button').forEach((b) =>
    b.addEventListener('click', () => {
      document.querySelectorAll('.tabbar button').forEach((x) => x.classList.toggle('on', x === b));
      document.querySelectorAll('.page').forEach((p) =>
        p.classList.toggle('on', p.id === 'page-' + b.dataset.page));
      $('viewTitle').textContent = b.lastChild.textContent.trim();
      if (b.dataset.page === 'events') loadEvents();
      if (b.dataset.page === 'cams') loadCams();
    }));

  // viewer — live MJPEG stream from the server
  function openViewer(cam) {
    if (!cam) return;
    current = cam;
    $('viewer').classList.add('on');
    $('vtitle').textContent = cam.name + ' — ' + (cam.loc || cam.kind);
    if (realCam && stream) {
      $('vvideo').srcObject = stream; $('vvideo').style.display = 'block';
      $('vstream').style.display = 'none'; $('vph').style.display = 'none';
      $('vvideo').play().catch(() => {});
    } else {
      $('vstream').src = base() + '/api/cameras/' + encodeURIComponent(cam.id) + '/stream';
      $('vstream').style.display = 'block'; $('vvideo').style.display = 'none';
      $('vph').style.display = 'none';
    }
  }
  $('closeBtn').addEventListener('click', () => {
    $('viewer').classList.remove('on');
    $('vstream').src = ''; $('vvideo').pause && $('vvideo').pause();
  });

  // snapshot — from the device camera if granted, else from the server feed
  $('snapBtn').addEventListener('click', async () => {
    if (realCam && stream && $('vvideo').videoWidth) {
      const v = $('vvideo'), c = document.createElement('canvas');
      c.width = v.videoWidth; c.height = v.videoHeight;
      c.getContext('2d').drawImage(v, 0, 0);
      c.toBlob((b) => download(b, 'binks-snapshot-' + Date.now() + '.jpg'));
      toast('Snapshot saved to downloads');
    } else if (current) {
      try {
        const r = await fetch(base() + '/api/cameras/' + encodeURIComponent(current.id) + '/snapshot');
        download(await r.blob(), 'binks-' + current.id + '-' + Date.now() + '.jpg');
        toast('Snapshot saved to downloads');
      } catch (e) { toast('Snapshot failed'); }
    }
  });
  async function download(blob, name) {
    const P = NATIVE && window.Capacitor.Plugins;
    if (P && P.Filesystem && P.Share) {
      const b64 = await new Promise((res) => {
        const fr = new FileReader();
        fr.onload = () => res(String(fr.result).split(',')[1]); fr.readAsDataURL(blob);
      });
      const f = await P.Filesystem.writeFile({ path: name, data: b64, directory: 'CACHE' });
      await P.Share.share({ title: name, url: f.uri });
      return;
    }
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob); a.download = name; a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 4000);
  }

  // settings: add camera
  $('addBtn').addEventListener('click', async () => {
    const body = {
      name: $('f-name').value.trim(), kind: $('f-kind').value, url: $('f-url').value.trim(),
    };
    if (!body.name) { $('addMsg').textContent = 'Name is required.'; return; }
    try {
      await api('/api/cameras', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
      });
      $('addMsg').textContent = '✓ Added "' + body.name + '".';
      $('f-name').value = ''; $('f-url').value = ''; loadCams();
    } catch (e) { $('addMsg').textContent = 'Could not add camera.'; }
  });

  // settings: discover
  $('discoverBtn').addEventListener('click', async () => {
    $('discoverOut').textContent = 'Scanning…';
    try {
      const d = await api('/api/discover', { method: 'POST' });
      $('discoverOut').innerHTML = (d.devices && d.devices.length)
        ? d.devices.map((x) => '• ' + esc(x.address) + ' — ' + esc(x.xaddr)).join('<br>')
        : 'No ONVIF cameras answered on this network.';
    } catch (e) { $('discoverOut').textContent = 'Scan failed.'; }
  });

  // settings: device camera permission
  $('permBtn').addEventListener('click', async () => {
    try {
      stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
      realCam = true;
      $('permMsg').textContent = '✓ Camera ready — open any camera to view it live on this phone.';
    } catch (e) {
      $('permMsg').textContent = 'Camera unavailable: ' + (e.name || 'blocked') + '.';
    }
  });

  // settings: server address (needed by the native app; optional in a browser)
  $('f-server').value = base();
  $('serverBtn').addEventListener('click', async () => {
    let v = $('f-server').value.trim().replace(/\/+$/, '');
    if (v && !/^https?:\/\//.test(v)) v = 'http://' + v;
    try { localStorage.setItem('binksServer', v); } catch (e) {}
    $('f-server').value = v;
    $('serverMsg').textContent = 'Checking…';
    await loadCams();
    $('serverMsg').textContent = $('connBadge').classList.contains('off')
      ? 'Could not reach ' + (v || 'this server') + '. Same Wi-Fi? Server running?'
      : '✓ Connected — ' + cams.length + ' camera(s).';
  });

  if (!NATIVE && 'serviceWorker' in navigator) navigator.serviceWorker.register('sw.js').catch(() => {});
  loadCams();
  setInterval(() => { if ($('page-cams').classList.contains('on')) loadCams(); }, 15000);
})();
