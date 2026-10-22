'use strict';
const $ = (selector) => document.querySelector(selector);
const state = { user: null, profile: null, measurements: [], measurePage: 1, measureTotal: 0,
  plans: [], plansPage: 1, plansTotal: 0, latest: null, selected: null, authMode: 'login' };
let noticeTimer;

function notify(message, error = false) {
  clearTimeout(noticeTimer);
  $('#status').textContent = message;
  $('#status').classList.toggle('error', error);
  $('#status').hidden = false;
  if (!error) noticeTimer = setTimeout(() => { $('#status').hidden = true; }, 6000);
}

async function api(path, { method = 'GET', data } = {}) {
  let response;
  try {
    response = await fetch(path, { method, credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-Memely-Client': 'web' },
      body: data === undefined ? undefined : JSON.stringify(data),
    });
  } catch { throw new Error('No pudimos conectar. Revisa tu conexión y vuelve a intentar.'); }
  if (response.status === 204) return null;
  let result;
  try { result = await response.json(); }
  catch { throw new Error('El servidor no respondió como esperábamos. Intenta de nuevo.'); }
  if (!response.ok) {
    if (response.status === 401 && state.user) showWelcome();
    const error = new Error(result.message || result.error || 'No pudimos completar la solicitud.');
    error.status = response.status;
    throw error;
  }
  return result;
}

function localISO(date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
}
function dateLabel(value, options = {}) {
  if (!value) return '—';
  const date = value.length === 10 ? new Date(`${value}T12:00:00`) : new Date(value);
  return new Intl.DateTimeFormat('es', { day: 'numeric', month: 'short', year: 'numeric', ...options }).format(date);
}
function node(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}
function button(text, className, action) {
  const element = node('button', className, text);
  element.type = 'button';
  element.addEventListener('click', action);
  return element;
}
async function busy(form, action) {
  const controls = [...form.querySelectorAll('button, input, select')];
  const previous = controls.map((control) => control.disabled);
  controls.forEach((control) => { control.disabled = true; });
  try { await action(); }
  catch (error) { notify(error.message, true); }
  finally { controls.forEach((control, index) => { control.disabled = previous[index]; }); }
}

function showWelcome() {
  state.user = null;
  state.profile = null;
  state.latest = null;
  state.selected = null;
  state.plans = [];
  state.measurements = [];
  state.latestMeasurement = null;
  $('.skip-link').href = '#auth-form';
  $('#application').hidden = true;
  $('#loading').hidden = true;
  $('#welcome').hidden = false;
  $('#auth-password').value = '';
}

function showView(view, focus = true) {
  const names = { overview: 'Resumen', profile: 'Mi perfil', measurements: 'Mis medidas', plans: 'Menú semanal' };
  document.querySelectorAll('[data-panel]').forEach((panel) => { panel.hidden = panel.dataset.panel !== view; });
  document.querySelectorAll('nav [data-view]').forEach((item) => {
    if (item.dataset.view === view) item.setAttribute('aria-current', 'page');
    else item.removeAttribute('aria-current');
  });
  $('#breadcrumb').textContent = `Mi espacio / ${names[view]}`;
  if (focus) $('#main').focus();
}
document.querySelectorAll('[data-view]').forEach((item) => item.addEventListener('click', () => showView(item.dataset.view)));

document.querySelectorAll('[data-auth]').forEach((item) => item.addEventListener('click', () => {
  state.authMode = item.dataset.auth;
  const register = state.authMode === 'register';
  $('#register-name').hidden = !register;
  $('#auth-name').required = register;
  $('#auth-password').autocomplete = register ? 'new-password' : 'current-password';
  $('#auth-title').textContent = register ? 'Empecemos algo bueno.' : 'Qué bueno verte.';
  $('#auth-description').textContent = register ? 'Crea tu cuenta para guardar tu información.' : 'Entra a tu espacio personal.';
  $('#auth-submit').textContent = register ? 'Crear mi cuenta ↗' : 'Entrar a mi espacio ↗';
  document.querySelectorAll('[data-auth]').forEach((tab) => tab.setAttribute('aria-pressed', String(tab === item)));
}));

$('#auth-form').addEventListener('submit', (event) => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(event.target));
  busy(event.target, async () => {
    const result = await api(state.authMode === 'register' ? '/api/usuarios' : '/api/login', { method: 'POST', data });
    state.user = result.usuario;
    $('#auth-password').value = '';
    await loadWorkspace();
    notify('Tu espacio está listo.');
  });
});

$('#logout').addEventListener('click', async () => {
  $('#logout').disabled = true;
  try { await api('/api/logout', { method: 'POST', data: {} }); showWelcome(); notify('Sesión cerrada.'); }
  catch (error) { notify(error.message, true); }
  finally { $('#logout').disabled = false; }
});

async function loadMeasurements() {
  const data = await api(`/api/measurements?page=${state.measurePage}`);
  state.measurements = data.measurements;
  state.measureTotal = data.total;
  renderMeasurements();
}
async function loadPlans() {
  const data = await api(`/api/plans?page=${state.plansPage}`);
  state.plans = data.plans;
  state.plansTotal = data.total;
  renderPlanList();
}

async function loadWorkspace() {
  state.measurePage = 1;
  state.plansPage = 1;
  const [profile, latest] = await Promise.all([api('/api/profile'), api('/api/plans/latest')]);
  state.profile = profile.profile;
  state.latest = latest.plan;
  state.selected = latest.plan;
  await Promise.all([loadMeasurements(), loadPlans()]);
  $('#sidebar-name').textContent = state.user.nombre;
  $('#avatar').textContent = state.user.nombre[0].toUpperCase();
  $('#greeting').textContent = `Hola, ${state.user.nombre.split(' ')[0]}.`;
  if (state.profile) {
    for (const [key, value] of Object.entries(state.profile)) {
      const field = $('#profile-form').elements.namedItem(key);
      if (field) field.value = value ?? 'no_indicado';
    }
  } else $('#profile-form').reset();
  renderOverview();
  renderPlanDetail();
  updatePlanRequirement();
  $('#welcome').hidden = true;
  $('#loading').hidden = true;
  $('.skip-link').href = '#main';
  $('#application').hidden = false;
  showView('overview', false);
}

function renderWeeklyOverview() {
  const plan = state.latest;
  const meals = plan ? plan.days.flatMap((day) => day.meals) : [];
  const completed = meals.filter((meal) => meal.completed).length;
  const percent = meals.length ? Math.round(completed / meals.length * 100) : 0;
  $('#week-percent').textContent = plan ? `${percent}%` : '—';
  $('#week-ring-fill').setAttribute('stroke-dasharray', `${percent} 100`);
  $('#week-ring-fill').setAttribute('stroke-opacity', completed ? '1' : '0');
  $('#week-ring-chart').setAttribute('aria-label', plan
    ? `${completed} de ${meals.length} comidas realizadas (${percent}%)` : 'Seguimiento semanal: sin menú');
  $('#week-focus-title').textContent = plan ? 'Tu semana en marcha.' : 'Tu próxima semana.';
  $('#week-focus-description').textContent = plan
    ? `${completed} de ${meals.length} comidas marcadas. Cada pequeño paso tiene su lugar.`
    : 'Organiza tus comidas y consulta tu seguimiento en un solo lugar.';
  const strip = $('#week-strip');
  strip.replaceChildren();
  const labels = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'];
  labels.forEach((label, index) => {
    const day = plan?.days[index];
    const done = day ? day.meals.filter((meal) => meal.completed).length : 0;
    const cell = node('div', `mini-day${done ? ' has-completion' : ''}`);
    const dayNumber = day ? String(new Date(`${day.date}T12:00:00`).getDate()).padStart(2, '0') : '—';
    cell.setAttribute('aria-label', day ? `${day.day}: ${done} de ${day.meals.length} comidas realizadas` : `${label}: sin menú`);
    cell.append(node('span', '', label), node('strong', '', dayNumber),
      node('small', '', day ? `${done}/${day.meals.length}` : 'sin plan'));
    strip.append(cell);
  });
  $('#week-caption').textContent = plan
    ? `Semana del ${dateLabel(plan.fecha_inicio)} · Tus marcas se guardan automáticamente.`
    : 'Crea un menú para empezar tu seguimiento.';
}

function renderOverview() {
  renderWeeklyOverview();
  const latest = state.latestMeasurement || state.measurements[0];
  $('#metric-weight').textContent = latest ? Number(latest.peso_kg).toLocaleString('es', { maximumFractionDigits: 2 }) : '—';
  $('#metric-height').textContent = latest ? Number(latest.estatura_cm).toLocaleString('es', { maximumFractionDigits: 2 }) : '—';
  $('#metric-age').textContent = state.profile ? state.profile.edad : '—';
  $('#metric-plans').textContent = state.plansTotal;
  const next = !state.profile ? ['Completa tu perfil.', 'Guarda tu fecha de nacimiento y elige tu preferencia de menú.', 'Completar perfil ↗', 'profile']
    : !state.measureTotal ? ['Tu primer registro.', 'Agrega una medición para empezar a construir tu historial.', 'Registrar medidas ↗', 'measurements']
    : ['Una semana con más orden.', 'Organiza tus comidas con un menú de ejemplo y consúltalo cuando quieras.', 'Organizar mi semana ↗', 'plans'];
  $('#next-title').textContent = next[0];
  $('#next-description').textContent = next[1];
  $('#next-action').textContent = next[2];
  $('#next-action').onclick = () => showView(next[3]);
  const summary = $('#latest-summary');
  summary.replaceChildren();
  summary.className = state.latest ? '' : 'summary-empty';
  if (!state.latest) { summary.textContent = 'Todavía no has creado un menú.'; return; }
  const meals = state.latest.days.flatMap((day) => day.meals);
  const done = meals.filter((meal) => meal.completed).length;
  const track = node('div', 'progress-track');
  const progress = node('progress');
  progress.max = meals.length;
  progress.value = done;
  progress.setAttribute('aria-label', 'Comidas marcadas como realizadas');
  track.append(progress);
  summary.append(node('p', 'latest-name', state.latest.nombre),
    node('p', 'latest-dates', `Semana del ${dateLabel(state.latest.fecha_inicio)}`), track,
    node('p', 'field-help', `${done} de ${meals.length} comidas marcadas`));
}

function updatePlanRequirement() {
  $('#plan-form button').disabled = !state.profile;
  $('#plan-requirement').textContent = state.profile
    ? `Se usará tu preferencia: ${state.profile.preferencia === 'vegetarian' ? 'vegetariano' : 'variado'}. Elige un lunes.`
    : 'Primero guarda tu perfil en la sección Mi perfil.';
}

$('#profile-form').addEventListener('submit', (event) => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(event.target));
  busy(event.target, async () => {
    const result = await api('/api/profile', { method: 'POST', data });
    state.profile = result.profile;
    renderOverview();
    updatePlanRequirement();
    notify('Perfil actualizado. Los menús anteriores conservan su preferencia original.');
  });
});

function renderMeasurements() {
  if (state.measurePage === 1) state.latestMeasurement = state.measurements[0] || null;
  const rows = $('#measurement-rows');
  rows.replaceChildren();
  $('#measurement-empty').hidden = state.measurements.length > 0;
  $('#measurement-count').textContent = `${state.measureTotal} registros`;
  $('#measure-page').textContent = `Página ${state.measurePage}`;
  $('#measure-prev').disabled = state.measurePage <= 1;
  $('#measure-next').disabled = state.measurePage * 20 >= state.measureTotal;
  for (const measurement of state.measurements) {
    const row = node('tr');
    row.append(node('td', '', dateLabel(measurement.registrada_en, { hour: '2-digit', minute: '2-digit' })),
      node('td', '', measurement.peso_kg), node('td', '', measurement.estatura_cm));
    const actions = node('td');
    actions.append(button('Eliminar', 'danger-button', async (event) => {
      if (!confirm('¿Eliminar esta medición de tu historial?')) return;
      event.target.disabled = true;
      try {
        await api(`/api/measurements/${measurement.id}`, { method: 'DELETE' });
        if (state.measurements.length === 1 && state.measurePage > 1) state.measurePage--;
        await loadMeasurements();
        // Fetch the latest record for the dashboard even while browsing older pages.
        if (state.measurePage !== 1) state.latestMeasurement = (await api('/api/measurements')).measurements[0] || null;
        renderOverview(); notify('Medición eliminada.');
      } catch (error) { notify(error.message, true); event.target.disabled = false; }
    }));
    row.append(actions);
    rows.append(row);
  }
}

$('#measurement-form').addEventListener('submit', (event) => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(event.target));
  busy(event.target, async () => {
    await api('/api/measurements', { method: 'POST', data });
    state.measurePage = 1;
    await loadMeasurements();
    renderOverview();
    event.target.reset();
    notify('Medición guardada en tu historial.');
  });
});

function renderPlanList() {
  const list = $('#plan-list');
  list.replaceChildren();
  if (!state.plans.length) list.append(node('p', 'field-help', 'Tus planes aparecerán aquí.'));
  for (const plan of state.plans) {
    const item = button('', 'plan-choice', async () => {
      item.disabled = true;
      try { state.selected = (await api(`/api/plans/${plan.id}`)).plan; renderPlanDetail(); renderPlanList(); }
      catch (error) { notify(error.message, true); item.disabled = false; }
    });
    item.setAttribute('aria-pressed', String(state.selected?.id === plan.id));
    item.append(node('strong', '', plan.nombre), node('small', '', dateLabel(plan.fecha_inicio)));
    list.append(item);
  }
  $('#plans-page').textContent = `${state.plansPage}`;
  $('#plans-prev').disabled = state.plansPage <= 1;
  $('#plans-next').disabled = state.plansPage * 10 >= state.plansTotal;
}

function renderPlanDetail() {
  const container = $('#plan-days');
  const heading = $('#plan-detail-heading');
  container.replaceChildren(); heading.replaceChildren();
  const plan = state.selected;
  if (!plan) {
    const empty = node('div', 'empty-state');
    empty.append(node('span', '', '▦'), node('h2', '', 'Tu semana empieza aquí.'), node('p', '', 'Completa tu perfil y crea tu primer menú.'));
    container.append(empty); return;
  }
  heading.append(node('h2', '', plan.nombre), button('Eliminar plan', 'danger-button', async (event) => {
    if (!confirm('¿Eliminar este plan y sus comidas?')) return;
    event.target.disabled = true;
    try {
      await api(`/api/plans/${plan.id}`, { method: 'DELETE' });
      if (state.plans.length === 1 && state.plansPage > 1) state.plansPage--;
      state.latest = (await api('/api/plans/latest')).plan;
      state.selected = state.latest;
      await loadPlans(); renderPlanDetail(); renderOverview(); notify('Plan eliminado.');
    } catch (error) { notify(error.message, true); event.target.disabled = false; }
  }));
  for (const day of plan.days) {
    const card = node('article', 'day');
    const title = node('div', 'day-heading');
    title.append(node('h3', '', day.day), node('small', '', dateLabel(day.date, { year: undefined })));
    card.append(title);
    for (const meal of day.meals) {
      const block = node('div', 'meal');
      const check = document.createElement('input');
      check.type = 'checkbox'; check.id = `meal-${meal.id}`; check.checked = meal.completed;
      const label = node('label', 'meal-label');
      label.htmlFor = check.id;
      label.append(node('span', '', meal.label), node('strong', '', meal.title));
      check.addEventListener('change', async () => {
        const completed = check.checked;
        check.disabled = true;
        try {
          await api(`/api/plans/${plan.id}/meals/${meal.id}`, { method: 'PATCH', data: { completed } });
          meal.completed = completed;
          if (state.latest?.id === plan.id) state.latest = plan;
          renderOverview();
        } catch (error) { check.checked = !completed; notify(error.message, true); }
        finally { check.disabled = false; }
      });
      block.append(check, label); card.append(block);
    }
    container.append(card);
  }
}

$('#plan-form').addEventListener('submit', (event) => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(event.target));
  busy(event.target, async () => {
    const result = await api('/api/plans', { method: 'POST', data });
    state.latest = result.plan; state.selected = result.plan; state.plansPage = 1;
    await loadPlans(); renderPlanDetail(); renderOverview(); notify('Menú semanal creado.');
  });
});

for (const [id, key, change, load] of [
  ['measure-prev', 'measurePage', -1, loadMeasurements], ['measure-next', 'measurePage', 1, loadMeasurements],
  ['plans-prev', 'plansPage', -1, loadPlans], ['plans-next', 'plansPage', 1, loadPlans],
]) {
  $(`#${id}`).addEventListener('click', async () => {
    $(`#${id}`).disabled = true;
    state[key] += change;
    try { await load(); }
    catch (error) { state[key] -= change; $(`#${id}`).disabled = false; notify(error.message, true); }
  });
}

async function initialize() {
  const today = new Date();
  $('#today').textContent = dateLabel(localISO(today), { weekday: 'long' });
  $('#birth-date').max = localISO(today);
  const monday = new Date(today);
  monday.setDate(today.getDate() - (today.getDay() + 6) % 7);
  $('#plan-start').value = localISO(monday);
  try {
    state.user = (await api('/api/me')).usuario;
    await loadWorkspace();
  } catch (error) {
    showWelcome();
    if (error.status !== 401) notify(error.message, true);
  }
}
initialize();

// Prueba temporal: error de sintaxis deliberado
const ciFailureDemo = ;