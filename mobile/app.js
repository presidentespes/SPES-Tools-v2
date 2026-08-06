const state = {
  apiUrl: localStorage.getItem('spesApiUrl') || 'http://127.0.0.1:8000',
  token: sessionStorage.getItem('spesToken') || '',
  user: null,
  mustChangePassword: false,
};

const $ = (id) => document.getElementById(id);
$('apiUrl').value = state.apiUrl;
let deferredPrompt;

function normalizeApiUrl(value) {
  return value.trim().replace(/\/+$/, '');
}

async function api(path, options = {}) {
  const headers = {'Content-Type': 'application/json', ...(options.headers || {})};
  if (state.token) headers.Authorization = `Bearer ${state.token}`;
  const response = await fetch(`${state.apiUrl}${path}`, {...options, headers});
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || `Errore ${response.status}`);
  return body;
}

function logout() {
  state.token = '';
  state.user = null;
  sessionStorage.removeItem('spesToken');
  $('appView').hidden = true;
  $('loginView').hidden = false;
  $('password').value = '';
}

function renderCards(cards) {
  $('stats').replaceChildren(...cards.map((card) => {
    const article = document.createElement('article');
    article.className = 'card';
    article.innerHTML = `<span>${card.icon}</span><strong>${card.value}</strong><small>${card.label}</small>`;
    return article;
  }));
}

function openModule(module) {
  if (module.sensitive === 'true' && state.mustChangePassword) {
    $('passwordDialog').showModal();
    return;
  }
  if (module.url) {
    window.open(module.url, '_blank', 'noopener');
    return;
  }
  const messages = {
    'desktop-only': 'Questa funzione usa file locali ed è disponibile nell’app desktop Windows/macOS.',
    'fgi-results': 'Il pannello risultati FGI mobile sarà collegato all’archivio centrale nel prossimo aggiornamento.',
    'fgi-calendar': 'Il calendario viene scaricato dalla homepage FGI Veneto. Il lettore mobile sarà collegato al backend centrale.',
    'fgi-regulation': 'Il PDF del regolamento sarà distribuito dal server centrale.',
    users: 'La gestione utenti completa è riservata al pannello amministratore.',
    logs: 'Il registro attività sarà disponibile nella sezione amministratore.',
    backup: 'Il backup viene eseguito sul server centrale.',
    updates: 'La PWA si aggiorna automaticamente quando viene pubblicata una nuova versione.',
  };
  alert(messages[module.action] || 'Funzione in preparazione.');
}

function renderModules(items) {
  const grid = $('moduleGrid');
  grid.replaceChildren();
  items.forEach((module) => {
    const button = document.createElement('button');
    button.className = 'tile';
    button.innerHTML = `<span>${module.icon}</span><strong>${module.label}</strong><small>${module.group}</small>`;
    button.addEventListener('click', () => openModule(module));
    grid.appendChild(button);
  });
}

async function loadApp() {
  const [user, dashboard, modules] = await Promise.all([
    api('/api/me'), api('/api/dashboard'), api('/api/modules'),
  ]);
  state.user = user;
  state.mustChangePassword = Boolean(user.must_change_password);
  $('loginView').hidden = true;
  $('appView').hidden = false;
  $('welcomeTitle').textContent = dashboard.greeting;
  $('profileLabel').textContent = user.role === 'admin' ? 'Presidente / Admin' : user.role;
  $('roleLabel').textContent = `${user.display_name} · ${user.role}`;
  $('passwordNotice').hidden = !state.mustChangePassword;
  renderCards(dashboard.cards);
  renderModules(modules.items);
  $('connectionState').textContent = 'Online';
}

$('loginForm').addEventListener('submit', async (event) => {
  event.preventDefault();
  $('loginError').textContent = '';
  state.apiUrl = normalizeApiUrl($('apiUrl').value);
  localStorage.setItem('spesApiUrl', state.apiUrl);
  try {
    const result = await api('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({username: $('username').value, password: $('password').value}),
    });
    state.token = result.token;
    state.mustChangePassword = result.must_change_password;
    sessionStorage.setItem('spesToken', state.token);
    await loadApp();
  } catch (error) {
    $('loginError').textContent = error.message;
  }
});

$('logoutButton').addEventListener('click', logout);
$('changePasswordButton').addEventListener('click', () => $('passwordDialog').showModal());
$('settingsButton').addEventListener('click', () => { logout(); $('apiUrl').focus(); });

$('passwordForm').addEventListener('submit', async (event) => {
  event.preventDefault();
  $('passwordError').textContent = '';
  try {
    await api('/api/auth/change-password', {
      method: 'POST',
      body: JSON.stringify({current_password: $('currentPassword').value, new_password: $('newPassword').value}),
    });
    state.mustChangePassword = false;
    $('passwordNotice').hidden = true;
    $('passwordDialog').close();
    $('currentPassword').value = '';
    $('newPassword').value = '';
  } catch (error) {
    $('passwordError').textContent = error.message;
  }
});

window.addEventListener('beforeinstallprompt', (event) => {
  event.preventDefault();
  deferredPrompt = event;
  $('installButton').hidden = false;
});
$('installButton').addEventListener('click', async () => {
  if (!deferredPrompt) return;
  deferredPrompt.prompt();
  await deferredPrompt.userChoice;
  deferredPrompt = null;
  $('installButton').hidden = true;
});

window.addEventListener('online', () => $('connectionState').textContent = 'Online');
window.addEventListener('offline', () => $('connectionState').textContent = 'Offline');
if ('serviceWorker' in navigator) window.addEventListener('load', () => navigator.serviceWorker.register('service-worker.js'));

if (state.token) loadApp().catch(logout);
