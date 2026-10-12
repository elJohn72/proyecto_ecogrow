/* EcoGrow remote client. No device tokens and no deferred command queue. */
(() => {
  'use strict';
  const byId = (id) => document.getElementById(id);
  const root = byId('grow-console');
  if (!root) return;
  const state = { csrf: null, towerId: null, detail: null, controller: null, generation: 0, busy: false, reading: false, timer: null, networkOK: navigator.onLine, irrigationDirty: false };
  const text = (id, value) => { byId(id).textContent = value; };
  const notice = (message, error = false) => { text('notice', message); byId('notice').dataset.error = String(error); };
  const number = (value) => typeof value === 'number' && Number.isFinite(value) ? new Intl.NumberFormat('es-EC', { maximumFractionDigits: 2 }).format(value) : 'SIN_DATO';
  const when = (value) => {
    if (!value) return 'SIN_DATO';
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? 'SIN_DATO' : date.toLocaleString('es-EC');
  };
  const pump = (value) => ({ on: 'Encendida', off: 'Apagada' }[value] || 'SIN_DATO');
  async function api(path, options = {}) {
    const controller = new AbortController();
    const abort = () => controller.abort();
    options.signal?.addEventListener('abort', abort, { once: true });
    if (options.signal?.aborted) controller.abort();
    let timedOut = false;
    const timeout = setTimeout(() => { timedOut = true; controller.abort(); }, 10000);
    let response;
    try { response = await fetch(`/api/mobile${path}`, { credentials: 'same-origin', cache: 'no-store', ...options, signal: controller.signal }); }
    catch (error) { if (timedOut) throw new Error('El servidor tardó demasiado en responder.'); throw error; }
    finally { clearTimeout(timeout); options.signal?.removeEventListener('abort', abort); }
    if (!response.headers.get('Content-Type')?.includes('application/json')) throw new Error('La sesión o la respuesta del servidor no es válida. Vuelve a ingresar.');
    const data = await response.json();
    if (!response.ok) {
      if (response.status === 401) { state.csrf = null; state.detail = null; byId('tower-detail').hidden = true; byId('tower-select').disabled = true; }
      throw new Error(data.message || 'No se pudo completar la solicitud.');
    }
    return data;
  }
  function controls() {
    const detail = state.detail;
    const unavailable = !state.networkOK || !navigator.onLine || state.busy || state.reading || !detail || !state.csrf || !detail.capabilities?.pump_control;
    byId('pump-on').disabled = unavailable || detail?.stale;
    byId('pump-off').disabled = unavailable;
    byId('save-irrigation').disabled = !state.networkOK || !navigator.onLine || state.busy || state.reading || !state.csrf || !detail?.capabilities?.irrigation_edit;
    byId('refresh').disabled = state.busy || state.reading;
    byId('tower-select').disabled = state.busy || !state.csrf || !byId('tower-select').options.length;
  }
  function list(id, entries, empty, format) {
    const element = byId(id);
    element.replaceChildren();
    if (!entries?.length) { const li = document.createElement('li'); li.textContent = empty; element.append(li); return; }
    for (const entry of entries) {
      const li = document.createElement('li');
      const timestamp = entry.created_at || entry.updated_at;
      if (timestamp) { const time = document.createElement('time'); time.textContent = when(timestamp); time.dateTime = timestamp; li.append(time); }
      const label = document.createElement('span'); label.textContent = format(entry); li.append(label); element.append(li);
    }
  }
  function render(detail) {
    text('tower-title', detail.name || 'Depósito');
    text('tower-location', detail.code || '');
    const sensors = detail.sensors || {};
    for (const [id, key] of Object.entries({ level: 'nivel_pct', liters: 'litros', ph: 'ph', tds: 'tds_ppm', temperature: 'temperatura_agua_c', ec: 'ec_ms_cm' })) {
      const value = number(sensors[key]); text(id, value); byId(id).dataset.missing = String(value === 'SIN_DATO');
    }
    const validLevel = typeof sensors.nivel_pct === 'number' && Number.isFinite(sensors.nivel_pct);
    byId('level-progress').hidden = !validLevel;
    if (validLevel) byId('level-progress').value = Math.min(100, Math.max(0, sensors.nivel_pct));
    byId('legacy-ec').hidden = sensors.ec_ms_cm == null;
    text('connection', detail.stale ? 'Lectura antigua / sin enlace reciente' : 'Telemetría reciente');
    byId('connection').dataset.tone = detail.stale ? 'warning' : 'normal';
    if (byId('live-dot')) byId('live-dot').dataset.tone = detail.stale ? 'warning' : 'normal';
    text('reading-time', `Última actualización: ${when(detail.updated_at)}`);
    text('pump-reported', pump(detail.pump?.reported));
    text('pump-desired', pump(detail.pump?.desired));
    text('pump-command', { pending: 'Pendiente de confirmación', unconfirmed: 'Sin acuse del dispositivo', unknown: 'Sin orden', confirmed: 'Confirmada por el dispositivo', rejected: 'Rechazada', expired: 'Vencida' }[detail.pump?.status] || 'SIN_DATO');
    text('pump-blocked', detail.stale ? 'Encendido bloqueado: se necesita telemetría reciente. Puedes solicitar el apagado.' : detail.capabilities?.pump_control ? 'El servidor valida el nivel mínimo configurado. La torre debe recibir la orden y reportar su estado.' : 'Control no disponible para esta torre.');
    text('recipe', detail.recipe ? [detail.recipe.crop, detail.recipe.phase].filter(Boolean).join(' · ') || 'Receta sin nombre' : 'Sin receta disponible.');
    text('recipe-note', detail.recipe?.notes || 'La edición de recetas requiere integración confirmada con el dispositivo.');
    text('timer', detail.irrigation ? `${detail.irrigation.enabled ? 'Programación habilitada' : 'Programación deshabilitada'} · riego ${number(detail.irrigation.on_minutes)} min / reposo ${number(detail.irrigation.off_minutes)} min` : 'Temporizador sin datos disponibles.');
    byId('irrigation-form').hidden = !detail.capabilities?.irrigation_edit;
    if (!state.irrigationDirty) {
      byId('irrigation-enabled').checked = detail.irrigation?.enabled || false;
      byId('on-minutes').value = detail.irrigation?.on_minutes || '';
      byId('off-minutes').value = detail.irrigation?.off_minutes || '';
    }
    text('alert-count', String(detail.alerts?.length || 0));
    list('alerts', detail.alerts, 'Sin alertas registradas. Esto no verifica el estado físico de la torre.', (alert) => alert.message || 'Alerta sin detalle');
    list('history', detail.history?.slice(0, 12), 'Todavía no hay lecturas en el historial.', (entry) => `pH ${number(entry.sensors?.ph)} · TDS ${number(entry.sensors?.tds_ppm)} ppm · Agua ${number(entry.sensors?.temperatura_agua_c)} °C`);
    byId('tower-detail').hidden = false;
    controls();
  }
  async function loadDetail() {
    if (!state.towerId || state.busy || document.hidden) return;
    state.controller?.abort();
    const controller = new AbortController(); state.controller = controller;
    const generation = ++state.generation; const towerId = state.towerId;
    state.reading = true; controls(); root.setAttribute('aria-busy', 'true');
    try {
      const detail = await api(`/towers/${encodeURIComponent(towerId)}`, { signal: controller.signal });
      if (generation !== state.generation || towerId !== state.towerId) return;
      state.detail = detail; state.networkOK = true; render(detail);
      notice(detail.stale ? 'Los datos almacenados pueden estar desactualizados. Encendido bloqueado hasta recibir una lectura reciente.' : 'Lecturas disponibles. Los controles muestran la orden y el reporte por separado.');
    } catch (error) {
      if (error.name === 'AbortError' || generation !== state.generation) return;
      state.networkOK = false; notice(`${error.message} No se enviarán órdenes mientras no se restablezca la conexión.`, true);
      text('connection', 'Sin conexión al servidor'); byId('connection').dataset.tone = 'warning';
    } finally {
      if (generation === state.generation) { state.reading = false; root.setAttribute('aria-busy', 'false'); controls(); }
    }
  }
  async function init() {
    state.reading = true; controls();
    try {
      const session = await api('/session');
      if (!session.authenticated) throw new Error('Tu sesión venció. Vuelve a ingresar para consultar tus torres.');
      state.csrf = session.csrf_token;
      const result = await api('/towers');
      byId('tower-select').replaceChildren();
      for (const tower of result.towers || []) { const option = document.createElement('option'); option.value = String(tower.id); option.textContent = tower.name || tower.code || `Torre ${tower.id}`; byId('tower-select').append(option); }
      if (!result.towers?.length) { state.csrf = null; notice('Aún no tienes torres disponibles. Registra o selecciona una torre desde la sección Torres.'); return; }
      state.towerId = String(result.towers[0].id);
    } catch (error) { state.networkOK = false; notice(error.message, true); }
    finally { state.reading = false; controls(); }
    await loadDetail();
  }
  async function sendPump(value) {
    if (byId(`pump-${value}`).disabled || state.busy) return;
    const towerId = state.towerId;
    state.busy = true; controls();
    notice('Enviando orden de bomba…');
    try {
      const result = await api(`/towers/${encodeURIComponent(towerId)}/pump`, { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': state.csrf }, body: JSON.stringify({ state: value }) });
      text('pump-desired', pump(result.desired)); text('pump-command', 'Pendiente de confirmación');
      notice(result.message || 'Orden recibida por el servidor. Actuación del dispositivo pendiente de confirmación.');
    } catch (error) { notice(`${error.message} La orden no se reintentará automáticamente. Actualiza antes de volver a operar.`, true); state.networkOK = false; }
    finally { state.busy = false; controls(); }
  }
  byId('tower-select').addEventListener('change', () => { state.towerId = byId('tower-select').value; state.detail = null; state.irrigationDirty = false; byId('tower-detail').hidden = true; loadDetail(); });
  byId('refresh').addEventListener('click', () => state.towerId ? loadDetail() : init());
  byId('pump-on').addEventListener('click', () => sendPump('on'));
  byId('pump-off').addEventListener('click', () => sendPump('off'));
  byId('irrigation-form').addEventListener('input', () => { state.irrigationDirty = true; });
  byId('irrigation-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    if (byId('save-irrigation').disabled || !event.target.reportValidity()) return;
    const towerId = state.towerId;
    state.busy = true; controls();
    try {
      const result = await api(`/towers/${encodeURIComponent(towerId)}/irrigation`, { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': state.csrf }, body: JSON.stringify({ enabled: byId('irrigation-enabled').checked, on_minutes: Number(byId('on-minutes').value), off_minutes: Number(byId('off-minutes').value) }) });
      state.irrigationDirty = false;
      if (state.detail) { state.detail.irrigation = result.irrigation; render(state.detail); }
      notice(result.message || 'Programación guardada en servidor; aplicación en la torre sin confirmar.');
    } catch (error) { notice(`${error.message} No se reintentará automáticamente.`, true); state.networkOK = false; }
    finally { state.busy = false; controls(); }
  });
  window.addEventListener('offline', () => { state.networkOK = false; state.controller?.abort(); notice('Sin conexión. Conservamos la última lectura; las órdenes están bloqueadas.', true); controls(); });
  window.addEventListener('online', () => { notice('Conexión disponible. Verificando telemetría…'); loadDetail(); });
  const poll = () => { clearInterval(state.timer); if (!document.hidden) state.timer = setInterval(loadDetail, 15000); };
  document.addEventListener('visibilitychange', () => { if (document.hidden) state.controller?.abort(); else loadDetail(); poll(); });
  window.addEventListener('pagehide', () => { clearInterval(state.timer); state.controller?.abort(); });
  init(); poll();
})();
