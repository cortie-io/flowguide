// ═══════════════════════════════════════════════════════════════
//  Naito _Tutor Agent — sidepanel.js  (Side Panel Edition v2)
//  Enterprise-grade single workspace controller
// ═══════════════════════════════════════════════════════════════

'use strict';

const API_BASE   = 'https://naito.chat/naito';
const WS_URL     = 'wss://naito.chat/naito/ws/extension';
const SESSION_KEY = 'n9n_sp_session';
const AUTH_TOKEN_KEY = 'n9n_auth_token';

// ── State ──────────────────────────────────────────────────────
const state = {
  sessionId:         null,
  ws:                null,
  wsConnected:       false,
  backendConnected:   false,
  streaming:         false,
  pendingErrorMsg:   null,
  msgCount:          0,
  authToken:         '',
  user:              null,
  authMode:          'login',
};

const ICON_SVG = {
  alert: '<svg class="icon-inline" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><path d="M12 9v4"/><path d="M12 17h.01"/></svg>',
  rocket: '<svg class="icon-inline" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4.5 16.5c-1.5 1.26-2.5 3-2.5 5.5 2.5 0 4.24-1 5.5-2.5"/><path d="M14 4l6 6"/><path d="M10 14L21 3"/><path d="M7.5 13.5 3 18"/><path d="M10.5 16.5 6 21"/></svg>',
  wrench: '<svg class="icon-inline" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.7 6.3a4 4 0 0 0 3 6.8L9.2 21.6a2 2 0 1 1-2.8-2.8l8.5-8.5a4 4 0 0 0 6.8-3"/></svg>',
  copy: '<svg class="icon-inline" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>',
};

// ══════════════════════════════════════════════════════════════
//  UTILITIES
// ══════════════════════════════════════════════════════════════
function esc(s) {
  return String(s ?? '')
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;')
    .replace(/'/g,'&#39;');
}

function escHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// ══════════════════════════════════════════════════════════════
//  MARKDOWN RENDERER (regex-based simple parser)
// ══════════════════════════════════════════════════════════════
function renderMarkdown(mdText) {
  if (!mdText) return '';

  // ── 1. 코드 블록 추출 (치환 전 보호) ────────────────────────
  const codeBlocks = [];
  let src = String(mdText).replace(/```([\w]*)\n?([\s\S]*?)```/g, (_, lang, code) => {
    const idx = codeBlocks.length;
    const langLabel = lang ? `<span class="code-lang">${esc(lang)}</span>` : '';
    const copyBtn = `<button class="code-copy-btn" data-code-copy>복사</button>`;
    codeBlocks.push(`<div class="code-block-wrapper">${langLabel}<pre><code>${escHtml(code.trim())}</code></pre>${copyBtn}</div>`);
    return `\x00CODE${idx}\x00`;
  });

  // ── 2. 라인 단위 파싱 ────────────────────────────────────────
  const lines = src.split('\n');
  const out   = [];
  let   i     = 0;

  const inlineFormat = (s) => {
    s = escHtml(s);
    s = s.replace(/`([^`]+)`/g,    '<code>$1</code>');
    s = s.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    s = s.replace(/\*([^*]+)\*/g,  '<em>$1</em>');
    s = s.replace(/__([\s\S]+?)__/g,'<strong>$1</strong>');
    s = s.replace(/_([^_]+)_/g,    '<em>$1</em>');
    s = s.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>');
    return s;
  };

  while (i < lines.length) {
    const line = lines[i];

    // 코드 블록 플레이스홀더
    if (/^\x00CODE\d+\x00$/.test(line.trim())) {
      const idx = parseInt(line.trim().slice(5));
      out.push(codeBlocks[idx]);
      i++; continue;
    }

    // 헤더
    const hm = line.match(/^(#{1,4})\s+(.+)/);
    if (hm) {
      const lvl = Math.min(hm[1].length + 1, 4); // h2~h4 (h1은 너무 큼)
      out.push(`<h${lvl} class="md-h${lvl}">${inlineFormat(hm[2])}</h${lvl}>`);
      i++; continue;
    }

    // 수평선
    if (/^---+$/.test(line.trim())) {
      out.push('<hr class="md-hr">');
      i++; continue;
    }

    // 인용
    if (line.startsWith('> ')) {
      const bqLines = [];
      while (i < lines.length && lines[i].startsWith('> ')) {
        bqLines.push(inlineFormat(lines[i].slice(2)));
        i++;
      }
      out.push(`<blockquote class="md-bq">${bqLines.join('<br>')}</blockquote>`);
      continue;
    }

    // 순서없는 리스트 (- 또는 * 또는 •)
    if (/^[\-\*\•]\s/.test(line)) {
      const items = [];
      while (i < lines.length && /^[\-\*\•]\s/.test(lines[i])) {
        items.push(`<li>${inlineFormat(lines[i].replace(/^[\-\*\•]\s/, ''))}</li>`);
        i++;
      }
      out.push(`<ul class="md-ul">${items.join('')}</ul>`);
      continue;
    }

    // 순서있는 리스트 (1. 2. 등)
    if (/^\d+\.\s/.test(line)) {
      const items = [];
      while (i < lines.length && /^\d+\.\s/.test(lines[i])) {
        items.push(`<li>${inlineFormat(lines[i].replace(/^\d+\.\s/, ''))}</li>`);
        i++;
      }
      out.push(`<ol class="md-ol">${items.join('')}</ol>`);
      continue;
    }

    // 빈 줄
    if (line.trim() === '') {
      i++; continue;
    }

    // 일반 단락 — 연속 줄들을 하나의 <p>로 묶음
    const paraLines = [];
    while (
      i < lines.length &&
      lines[i].trim() !== '' &&
      !/^[\-\*\•#>]/.test(lines[i]) &&
      !/^\d+\./.test(lines[i]) &&
      !/^\x00CODE/.test(lines[i].trim()) &&
      !/^---+$/.test(lines[i].trim())
    ) {
      paraLines.push(inlineFormat(lines[i]));
      i++;
    }
    if (paraLines.length) {
      out.push(`<p class="md-p">${paraLines.join('<br>')}</p>`);
    }
  }

  return out.join('\n');
}

// ── DOM refs ──────────────────────────────────────────────────
const $stream      = document.getElementById('chat-stream');
const $input       = document.getElementById('chat-input');
const $sendBtn     = document.getElementById('send-btn');
const $status      = document.getElementById('status-indicator');
const $statusText  = document.getElementById('status-text');
const $banner      = document.getElementById('error-banner');
const $bannerTitle = document.getElementById('banner-title');
const $bannerClose = document.getElementById('banner-close');
const $toast       = document.getElementById('toast');
const $fileInput   = document.getElementById('json-file-input');
const $emptyState  = document.getElementById('empty-state');
const $charCount   = document.getElementById('char-count');
const $authBtn     = document.getElementById('btn-auth');
const $authModal   = document.getElementById('auth-modal');
const $authTitle   = document.getElementById('auth-title');
const $authClose   = document.getElementById('auth-close');
const $authNameRow = document.getElementById('auth-name-row');
const $authName    = document.getElementById('auth-name');
const $authEmail   = document.getElementById('auth-email');
const $authPass    = document.getElementById('auth-password');
const $authSubmit  = document.getElementById('auth-submit');
const $authSwitch  = document.getElementById('auth-switch');
const $authLogout  = document.getElementById('auth-logout');
const $docsModal   = document.getElementById('docs-modal');
const $docsClose   = document.getElementById('docs-close');
const $docsSearch  = document.getElementById('docs-search');
const $docsList    = document.getElementById('docs-list');
const $docsView    = document.getElementById('docs-view');

// ══════════════════════════════════════════════════════════════
//  SESSION
// ══════════════════════════════════════════════════════════════
function getSessionId() {
  let sid = sessionStorage.getItem(SESSION_KEY);
  if (!sid) {
    sid = `naito-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    sessionStorage.setItem(SESSION_KEY, sid);
  }
  return sid;
}

// ══════════════════════════════════════════════════════════════
//  AUTH
// ══════════════════════════════════════════════════════════════
function getAuthHeaders(extra = {}) {
  const headers = { ...extra };
  if (state.authToken) headers.Authorization = `Bearer ${state.authToken}`;
  return headers;
}

function setAuthMode(mode) {
  state.authMode = mode;
  const signup = mode === 'signup';
  $authTitle.textContent = signup ? '회원가입' : '로그인';
  $authSubmit.textContent = signup ? '회원가입' : '로그인';
  $authSwitch.textContent = signup ? '이미 계정이 있나요? 로그인' : '계정이 없나요? 회원가입';
  $authNameRow.classList.toggle('hidden', !signup);
}

function openAuthModal(mode = 'login') {
  setAuthMode(mode);
  $authModal.classList.add('open');
  $authModal.setAttribute('aria-hidden', 'false');
  if (mode === 'signup') $authName.focus();
  else $authEmail.focus();
}

function closeAuthModal() {
  $authModal.classList.remove('open');
  $authModal.setAttribute('aria-hidden', 'true');
}

function renderAuthState() {
  if (state.user) {
    $authBtn.textContent = '계정';
    $authBtn.classList.add('logged');
    $authBtn.title = `${state.user.name} (${state.user.email})`;
    $authLogout.classList.add('show');
  } else {
    $authBtn.textContent = '로그인';
    $authBtn.classList.remove('logged');
    $authBtn.title = '로그인';
    $authLogout.classList.remove('show');
  }
}

function persistAuth(token, user) {
  state.authToken = token || '';
  state.user = user || null;
  if (state.authToken) localStorage.setItem(AUTH_TOKEN_KEY, state.authToken);
  else localStorage.removeItem(AUTH_TOKEN_KEY);
  renderAuthState();
}

async function restoreAuthSession() {
  const token = localStorage.getItem(AUTH_TOKEN_KEY) || '';
  if (!token) {
    persistAuth('', null);
    return;
  }
  state.authToken = token;
  try {
    const resp = await fetch(`${API_BASE}/api/auth/me`, { headers: getAuthHeaders() });
    if (!resp.ok) throw new Error('invalid_session');
    const data = await resp.json();
    persistAuth(token, data.user || null);
  } catch {
    persistAuth('', null);
  }
}

async function authRequest(path, payload) {
  const resp = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) {
    throw new Error(data.detail || '인증 요청에 실패했습니다');
  }
  return data;
}

async function submitAuth() {
  const mode = state.authMode;
  const name = $authName.value.trim();
  const email = $authEmail.value.trim();
  const password = $authPass.value;

  if (!email || !password || (mode === 'signup' && !name)) {
    showToast('입력값을 확인하세요');
    return;
  }
  if (password.length < 8) {
    showToast('비밀번호는 8자 이상이어야 합니다');
    return;
  }

  $authSubmit.disabled = true;
  try {
    const endpoint = mode === 'signup' ? '/api/auth/signup' : '/api/auth/login';
    const payload = mode === 'signup' ? { name, email, password } : { email, password };
    const data = await authRequest(endpoint, payload);
    persistAuth(data.token || '', data.user || null);
    closeAuthModal();
    showToast(mode === 'signup' ? '회원가입 완료' : '로그인 완료');
  } catch (err) {
    showToast(err.message || '로그인 실패');
  } finally {
    $authSubmit.disabled = false;
  }
}

async function logoutAuth() {
  try {
    if (state.authToken) {
      await fetch(`${API_BASE}/api/auth/logout`, { method: 'POST', headers: getAuthHeaders() });
    }
  } catch {}
  persistAuth('', null);
  $authName.value = '';
  $authEmail.value = '';
  $authPass.value = '';
  showToast('로그아웃되었습니다');
}

// ══════════════════════════════════════════════════════════════
//  TOAST
// ══════════════════════════════════════════════════════════════
let toastTimer = null;

function showToast(msg, duration = 2400) {
  $toast.textContent = msg;
  $toast.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => $toast.classList.remove('show'), duration);
}

// ══════════════════════════════════════════════════════════════
//  DOCS
// ══════════════════════════════════════════════════════════════
function openDocsModal() {
  $docsModal.classList.add('open');
  $docsModal.setAttribute('aria-hidden', 'false');
  if (!$docsList.dataset.loaded) {
    loadDocs('');
  }
  $docsSearch.focus();
}

function closeDocsModal() {
  $docsModal.classList.remove('open');
  $docsModal.setAttribute('aria-hidden', 'true');
}

function renderDocsList(items = []) {
  if (!items.length) {
    $docsList.innerHTML = '<div class="docs-empty">검색 결과가 없습니다.</div>';
    $docsView.innerHTML = '<div class="docs-empty">왼쪽에서 문서를 선택하세요.</div>';
    return;
  }

  $docsList.innerHTML = '';
  items.forEach((it, idx) => {
    const btn = document.createElement('button');
    btn.className = 'docs-item';
    btn.dataset.id = String(it.id);
    btn.innerHTML = `<div class="docs-item-title">${esc(it.title || '')}</div>`;
    btn.addEventListener('click', () => selectDoc(it.id));
    $docsList.appendChild(btn);
    if (idx === 0) btn.classList.add('active');
  });

  selectDoc(items[0].id);
}

function markActiveDoc(docId) {
  $docsList.querySelectorAll('.docs-item').forEach(el => {
    el.classList.toggle('active', el.dataset.id === String(docId));
  });
}

async function loadDocs(query = '') {
  $docsList.innerHTML = '<div class="docs-empty">문서를 불러오는 중...</div>';
  try {
    const q = encodeURIComponent(query.trim());
    const resp = await fetch(`${API_BASE}/api/docs/search?q=${q}&limit=40`, { headers: getAuthHeaders() });
    if (!resp.ok) throw new Error('docs_search_failed');
    const data = await resp.json();
    $docsList.dataset.loaded = '1';
    renderDocsList(data.items || []);
  } catch {
    $docsList.innerHTML = '<div class="docs-empty">문서를 불러오지 못했습니다.</div>';
    $docsView.innerHTML = '<div class="docs-empty">백엔드 연결과 docs 인덱스를 확인하세요.</div>';
  }
}

async function selectDoc(docId) {
  markActiveDoc(docId);
  $docsView.innerHTML = '<div class="docs-empty">문서를 불러오는 중...</div>';
  try {
    const resp = await fetch(`${API_BASE}/api/docs/${docId}`, { headers: getAuthHeaders() });
    if (!resp.ok) throw new Error('docs_detail_failed');
    const d = await resp.json();
    const excerpt = String(d.content || '').slice(0, 14000);
    const renderedHtml = renderMarkdown(excerpt);
    $docsView.innerHTML = `
      <div class="docs-view-title">${esc(d.title || '')}</div>
      <div class="docs-view-meta">${esc(d.path || '')}</div>
      <div class="docs-view-content">${renderedHtml}</div>
    `;
  } catch {
    $docsView.innerHTML = '<div class="docs-empty">문서 본문을 가져오지 못했습니다.</div>';
  }
}

let docsSearchTimer = null;

// ══════════════════════════════════════════════════════════════
//  STATUS
// ══════════════════════════════════════════════════════════════
function setStatus(mode) {
  const safeMode = mode === 'connected' ? 'connected' : mode === 'connecting' ? 'connecting' : 'disconnected';
  $status.className = `conn-mini ${safeMode}`;
  if (safeMode === 'connected') $statusText.textContent = 'connected';
  else if (safeMode === 'connecting') $statusText.textContent = 'connecting';
  else $statusText.textContent = 'offline';
}

// ══════════════════════════════════════════════════════════════
//  WEBSOCKET
// ══════════════════════════════════════════════════════════════
function connectWS() {
  if (state.ws && state.ws.readyState < 2) return;

  try {
    const ws = new WebSocket(`${WS_URL}?session_id=${state.sessionId}`);
    state.ws = ws;

    ws.addEventListener('open', () => {
      state.wsConnected = true;
      setStatus(state.backendConnected ? 'connected' : 'connecting');
    });

    ws.addEventListener('message', ({ data }) => {
      let msg;
      try { msg = JSON.parse(data); } catch { return; }
      handleWSMessage(msg);
    });

    ws.addEventListener('close', () => {
      state.wsConnected = false;
      setStatus(state.backendConnected ? 'connected' : 'offline');
      setTimeout(connectWS, 3500);
    });

    ws.addEventListener('error', () => {
      state.wsConnected = false;
      setStatus(state.backendConnected ? 'connected' : 'offline');
    });

  } catch {
    state.wsConnected = false;
    setStatus(state.backendConnected ? 'connected' : 'offline');
    setTimeout(connectWS, 3500);
  }
}

function wsSend(payload) {
  if (state.ws?.readyState === WebSocket.OPEN) {
    state.ws.send(JSON.stringify(payload));
  }
}

function handleWSMessage(msg) {
  switch (msg.event) {
    case 'node_inspect_hint':
      renderNodeHint(msg.field_hints || []);
      break;
    case 'error_alert_ui':
      showErrorBanner(msg.auto_prompt || '에러가 감지됐습니다.');
      break;
    case 'inject_result':
      showToast(msg.status === 'ok' ? '캔버스에 주입 완료' : `주입 실패: ${msg.error || '알 수 없는 오류'}`);
      break;
    case 'restore_canvas':
      handleRestoreCanvas(msg.workflow_json);
      break;
  }
}

// Forward error from background (content.js relay)
if (typeof chrome !== 'undefined' && chrome.runtime?.onMessage) {
  chrome.runtime.onMessage.addListener((msg) => {
    if (msg.type === 'FORWARD_ERROR') {
      wsSend({ event: 'error_detected', payload: { error_message: msg.error } });
      showErrorBanner(msg.error);
    }
  });
}

// ══════════════════════════════════════════════════════════════
//  ERROR BANNER
// ══════════════════════════════════════════════════════════════
function showErrorBanner(msg) {
  state.pendingErrorMsg = msg;
  const short = msg.length > 70 ? msg.slice(0, 70) + '…' : msg;
  $bannerTitle.textContent = short;
  $banner.classList.add('visible');
}

$banner.addEventListener('click', (e) => {
  if (e.target.closest('#banner-close')) return;
  if (state.pendingErrorMsg) {
    sendMessage(state.pendingErrorMsg, { error_log: state.pendingErrorMsg });
    dismissBanner();
  }
});

$bannerClose.addEventListener('click', (e) => {
  e.stopPropagation();
  dismissBanner();
});

function dismissBanner() {
  $banner.classList.remove('visible');
  state.pendingErrorMsg = null;
}

// ══════════════════════════════════════════════════════════════
//  EMPTY STATE
// ══════════════════════════════════════════════════════════════
function hideEmpty() {
  if ($emptyState && $emptyState.style.display !== 'none') {
    $emptyState.style.transition = 'opacity 0.2s';
    $emptyState.style.opacity = '0';
    setTimeout(() => { $emptyState.style.display = 'none'; }, 200);
  }
}

document.getElementById('empty-shortcuts')?.addEventListener('click', (e) => {
  const item = e.target.closest('.shortcut-item');
  if (!item) return;
  const action = item.dataset.action;
  if (action === 'canvas')     handleChipCanvas();
  if (action === 'curriculum') sendMessage('n8n 학습 커리큘럼 로드맵을 보여줘');
  if (action === 'json')       $fileInput.click();
  if (action === 'docs')       openDocsModal();
});

// ══════════════════════════════════════════════════════════════
//  RENDER — USER BUBBLE
// ══════════════════════════════════════════════════════════════
function renderUserBubble(text) {
  hideEmpty();
  const el = document.createElement('div');
  el.className = 'msg-user';
  el.innerHTML = `<div class="msg-user-bubble">${esc(text)}</div>`;
  $stream.appendChild(el);
  scrollBottom();
}

// ══════════════════════════════════════════════════════════════
//  RENDER — AI BLOCK FACTORY
// ══════════════════════════════════════════════════════════════
function createAiBlock(intentLabel = 'AI') {
  hideEmpty();
  const block = document.createElement('div');
  block.className = 'msg-ai';

  const badgeClass = `badge-${(intentLabel || 'general').toLowerCase().replace(/ /g,'_')}`;

  block.innerHTML = `
    <div class="msg-ai-header">
      <div class="ai-avatar">
        <svg width="12" height="12" viewBox="0 0 28 28" fill="none">
          <circle cx="14" cy="5.5" r="2.8" fill="#C4B5FD"/>
          <circle cx="5.5" cy="19.5" r="2.8" fill="#C4B5FD" opacity="0.7"/>
          <circle cx="22.5" cy="19.5" r="2.8" fill="#C4B5FD" opacity="0.7"/>
          <line x1="14" y1="8.3" x2="6.8" y2="17.3" stroke="#C4B5FD" stroke-width="1.5" stroke-linecap="round" opacity="0.5"/>
          <line x1="14" y1="8.3" x2="21.2" y2="17.3" stroke="#C4B5FD" stroke-width="1.5" stroke-linecap="round" opacity="0.5"/>
        </svg>
      </div>
      <div class="ai-meta">
        <span class="ai-name">Naito</span>
        <span class="intent-badge ${badgeClass}" data-badge>${esc(intentLabel)}</span>
      </div>
    </div>
    <div class="msg-ai-body typing-cursor" data-body></div>
  `;

  $stream.appendChild(block);
  scrollBottom();

  return {
    block,
    body:  block.querySelector('[data-body]'),
    badge: block.querySelector('[data-badge]'),
  };
}

// ══════════════════════════════════════════════════════════════
//  RENDER — SKELETON
// ══════════════════════════════════════════════════════════════
function appendSkeleton() {
  hideEmpty();
  const el = document.createElement('div');
  el.id = 'skeleton';
  el.className = 'msg-ai';
  el.innerHTML = `
    <div class="msg-ai-header">
      <div class="ai-avatar">
        <svg width="12" height="12" viewBox="0 0 28 28" fill="none">
          <circle cx="14" cy="5.5" r="2.8" fill="#C4B5FD"/>
          <circle cx="5.5" cy="19.5" r="2.8" fill="#C4B5FD" opacity="0.7"/>
          <circle cx="22.5" cy="19.5" r="2.8" fill="#C4B5FD" opacity="0.7"/>
        </svg>
      </div>
      <span class="ai-name">Naito</span>
    </div>
    <div class="skeleton-wrap">
      <div class="skeleton-line" style="width:88%"></div>
      <div class="skeleton-line" style="width:65%"></div>
      <div class="skeleton-line" style="width:76%"></div>
    </div>
  `;
  $stream.appendChild(el);
  scrollBottom();
}

function removeSkeleton() {
  document.getElementById('skeleton')?.remove();
}

// ══════════════════════════════════════════════════════════════
//  RENDER — CURRICULUM CARDS
// ══════════════════════════════════════════════════════════════
// ══════════════════════════════════════════════════════════════
//  RENDER — NODE PROPERTY CARD  (node_property_card event)
// ══════════════════════════════════════════════════════════════
function renderNodePropertyCard(data, afterEl) {
  if (!data || !Array.isArray(data.properties) || data.properties.length === 0) return;

  const nodeName  = data.node_name || 'Node';
  const props     = data.properties;
  const initials  = nodeName.replace(/[^A-Z0-9]/g, '').slice(0, 2) || nodeName.slice(0, 2).toUpperCase();

  const wrapper = document.createElement('div');
  wrapper.className = 'npc-wrapper';

  const card = document.createElement('div');
  card.className = 'npc-card';

  const header = document.createElement('div');
  header.className = 'npc-header';
  header.innerHTML = `
    <div class="npc-node-name">
      <span class="npc-node-icon">${esc(initials)}</span>
      ${esc(nodeName)} <span style="color:var(--text-muted);font-weight:400;font-size:11px">노드 속성</span>
    </div>
    <span class="npc-badge">n8n_properties_spec · LEG</span>
  `;
  card.appendChild(header);

  const list = document.createElement('div');
  list.className = 'npc-prop-list';

  props.forEach(p => {
    const row = document.createElement('div');
    row.className = 'npc-prop-row';

    const defaultHtml = p.default !== '' && p.default !== undefined
      ? `<div class="npc-prop-default">기본값: <span>${esc(String(p.default))}</span></div>`
      : '';

    row.innerHTML = `
      <div class="npc-prop-name">${esc(p.displayName || p.name)}<br><span style="font-size:10px;color:var(--text-muted);font-weight:400">${esc(p.name)}</span></div>
      <div class="npc-prop-type" style="color:${esc(p.color || '#94A3B8')};border-color:${esc(p.color || '#94A3B8')}33">${esc(p.type)}</div>
      <div>
        <div class="npc-prop-desc">${esc(p.description || '—')}</div>
        ${defaultHtml}
      </div>
    `;
    list.appendChild(row);
  });

  card.appendChild(list);

  const leg = document.createElement('div');
  leg.className = 'npc-leg';
  leg.textContent = '※ 이 속성 정보는 n8n_properties_spec.txt에 의거한 팩트입니다. (LEG)';
  card.appendChild(leg);

  wrapper.appendChild(card);
  afterEl.insertAdjacentElement('afterend', wrapper);
  scrollBottom();
}

// ══════════════════════════════════════════════════════════════
//  RENDER — CURRICULUM CARDS  (enhanced)
// ══════════════════════════════════════════════════════════════
function renderCurriculumCards(cards, parentBlock) {
  const LEVEL_ORDER = { beginner: 0, intermediate: 1, advanced: 2 };
  const levelMap = { beginner: '입문', intermediate: '중급', advanced: '심화' };
  const durationPct = { beginner: 25, intermediate: 55, advanced: 85 };

  const grid = document.createElement('div');
  grid.className = 'curriculum-grid';

  (cards || []).forEach((card, idx) => {
    const levelEn  = (card.level || 'beginner').toLowerCase();
    const levelKo  = levelMap[levelEn] || card.level || '';
    const pct      = durationPct[levelEn] || 40;
    const nodes    = Array.isArray(card.nodes) ? card.nodes.join(', ') : '';

    const el = document.createElement('div');
    el.className = 'curriculum-card';
    el.innerHTML = `
      <div class="cc-top">
        <span class="cc-week">${esc(card.week || `Week ${idx + 1}`)}</span>
        <span class="cc-level level-${esc(levelEn)}">${esc(levelKo)}</span>
      </div>
      <div class="cc-title">${esc(card.title || '')}</div>
      <div class="cc-desc">${esc(card.description || '')}</div>
      ${nodes ? `<div style="font-size:10.5px;color:var(--text-muted);margin-bottom:8px">📦 ${esc(nodes)}</div>` : ''}
      <div class="cc-footer">
        <div class="cc-inject-btn" data-code-id="${esc(card.canvas_code_id || '')}">
          ⚡ 실습 코드 주입
        </div>
        ${card.duration ? `<span class="cc-duration">⏱ ${esc(card.duration)}</span>` : ''}
      </div>
      <div class="cc-progress-bar">
        <div class="cc-progress-fill" style="width:${pct}%"></div>
      </div>
    `;

    el.querySelector('.cc-inject-btn').addEventListener('click', (e) => {
      e.stopPropagation();
      const cid = e.currentTarget.dataset.codeId;
      cid ? injectByCodeId(cid) : showToast('연결된 실습 코드가 없습니다');
    });

    grid.appendChild(el);
  });

  parentBlock.insertAdjacentElement('afterend', grid);
  scrollBottom();
}

// ══════════════════════════════════════════════════════════════
//  RENDER — ACCORDION REPORT
// ══════════════════════════════════════════════════════════════
function renderAccordion(layers, afterEl) {
  const wrapper = document.createElement('div');
  wrapper.className = 'accordion-wrapper';
  const block = document.createElement('div');
  block.className = 'accordion-block';
  const diagKeys = (layers && typeof layers === 'object') ? Object.keys(layers).slice(0, 12) : [];

  // ── 레이어 데이터 정규화 ─────────────────────────────────────
  let summaryContent = '';
  let nodeItems      = [];
  let exprItems      = [];

  if (Array.isArray(layers)) {
    layers.forEach((item) => {
      const layer = item?.layer || item?.id || '';
      if (layer === 'summary') {
        summaryContent = item?.content || item?.summary || '';
      } else if (layer === 'nodes' || layer === 'node_roles') {
        nodeItems = item?.items || item?.nodeRoles || item?.node_roles || [];
      } else if (layer === 'expressions') {
        exprItems = item?.items || item?.expressions || [];
      }
    });
  } else if (layers && typeof layers === 'object') {
    const deepPick = (obj, key, maxDepth = 4, depth = 0) => {
      if (!obj || typeof obj !== 'object' || depth > maxDepth) return undefined;
      if (Object.prototype.hasOwnProperty.call(obj, key)) return obj[key];
      for (const v of Object.values(obj)) {
        if (v && typeof v === 'object') {
          const found = deepPick(v, key, maxDepth, depth + 1);
          if (found !== undefined) return found;
        }
      }
      return undefined;
    };

    const normalizeFromLayerArray = (arr) => {
      if (!Array.isArray(arr)) return;
      arr.forEach((item) => {
        const layer = item?.layer || item?.id || '';
        if (layer === 'summary' && !summaryContent) {
          summaryContent = item?.content || item?.summary || '';
        } else if ((layer === 'nodes' || layer === 'node_roles') && (!Array.isArray(nodeItems) || nodeItems.length === 0)) {
          nodeItems = item?.items || item?.nodeRoles || item?.node_roles || [];
        } else if (layer === 'expressions' && (!Array.isArray(exprItems) || exprItems.length === 0)) {
          exprItems = item?.items || item?.expressions || [];
        }
      });
    };

    const tryParseJsonLike = (rawValue) => {
      if (rawValue == null) return null;
      if (typeof rawValue === 'object') return rawValue;
      if (typeof rawValue !== 'string') return null;

      let text = rawValue.trim();
      if (!text) return null;
      const fenced = text.match(/```json\s*([\s\S]*?)\s*```/i);
      if (fenced?.[1]) text = fenced[1].trim();
      try {
        return JSON.parse(text);
      } catch {
        return null;
      }
    };

    // payload가 data/report로 중첩될 수 있어 단계적으로 언랩
    let base = layers;
    if (base?.data && typeof base.data === 'object') base = base.data;
    if (base?.report && typeof base.report === 'object') base = base.report;
    if (base?.report && typeof base.report === 'object') base = base.report;

    const topologyCandidates = [
      layers?.topology_summary,
      layers?.data?.topology_summary,
      layers?.report?.topology_summary,
      layers?.data?.report?.topology_summary,
      base?.topology_summary,
    ];
    const topology = topologyCandidates.find((x) => x && typeof x === 'object') || null;

    summaryContent = base?.summary || base?.overview || base?.content || '';
    nodeItems      = base?.node_roles || base?.nodeRoles || base?.nodes?.items || base?.nodes || [];
    exprItems      = base?.expressions?.items || base?.expressions || [];

    // 최종 안전장치: 중첩 구조 어디에 있든 핵심 필드 재귀 추출
    if (!summaryContent) {
      summaryContent =
        deepPick(layers, 'summary')
        || deepPick(layers, 'overview')
        || deepPick(layers, 'content')
        || '';
    }
    if (!Array.isArray(nodeItems) || nodeItems.length === 0) {
      const pickedNodes =
        deepPick(layers, 'node_roles')
        || deepPick(layers, 'nodeRoles')
        || deepPick(layers, 'nodes');
      nodeItems = Array.isArray(pickedNodes)
        ? pickedNodes
        : (Array.isArray(pickedNodes?.items) ? pickedNodes.items : []);
    }
    if (!Array.isArray(exprItems) || exprItems.length === 0) {
      const pickedExpr =
        deepPick(layers, 'expressions')
        || deepPick(layers, 'expression')
        || deepPick(layers, 'expressions_found');
      exprItems = Array.isArray(pickedExpr)
        ? pickedExpr
        : (Array.isArray(pickedExpr?.items) ? pickedExpr.items : []);
    }

    // raw/raw_report 또는 중첩 객체에 들어온 리포트 파싱 시도
    const rawCandidates = [
      base?.raw_report?.raw,
      base?.raw_report,
      base?.raw,
      layers?.raw_report?.raw,
      layers?.raw_report,
      layers?.raw,
      layers?.data?.raw_report?.raw,
      layers?.data?.raw_report,
      layers?.data?.raw,
    ];

    if (!summaryContent || !Array.isArray(nodeItems) || !Array.isArray(exprItems) || nodeItems.length === 0 || exprItems.length === 0) {
      for (const cand of rawCandidates) {
        const parsed = tryParseJsonLike(cand);
        if (!parsed) continue;

        if (Array.isArray(parsed)) {
          normalizeFromLayerArray(parsed);
          break;
        }

        if (parsed && typeof parsed === 'object') {
          const nested = parsed.report && typeof parsed.report === 'object' ? parsed.report : parsed;
          if (!summaryContent) {
            summaryContent = nested.summary || nested.overview || nested.content || summaryContent;
          }
          if (!Array.isArray(nodeItems) || nodeItems.length === 0) {
            nodeItems = nested.node_roles || nested.nodeRoles || nested.nodes?.items || nested.nodes || nodeItems;
          }
          if (!Array.isArray(exprItems) || exprItems.length === 0) {
            exprItems = nested.expressions?.items || nested.expressions || exprItems;
          }

          const nestedRaw = tryParseJsonLike(nested.raw_report?.raw || nested.raw_report || nested.raw);
          if (Array.isArray(nestedRaw)) {
            normalizeFromLayerArray(nestedRaw);
          }
          break;
        }
      }
    }

    // 최소 폴백: topology summary가 있으면 전체 요약은 비워두지 않음
    if (!summaryContent && topology) {
      const total = topology.total_nodes ?? 0;
      const trigger = topology.layers?.trigger ?? 0;
      const processing = topology.layers?.processing ?? 0;
      const sink = topology.layers?.sink ?? 0;
      const exprCount = topology.expressions_count ?? 0;
      summaryContent = `총 ${total}개 노드, 트리거 ${trigger}개, 처리 ${processing}개, 적재 ${sink}개, 표현식 ${exprCount}개`;
    }

    if (!Array.isArray(nodeItems)) nodeItems = [];
    if (!Array.isArray(exprItems)) exprItems = [];
  }

  // ── 레이어 정의 ───────────────────────────────────────────────
  const defs = [
    { id: 'summary',     title: '전체 요약',         badge: 'Overview' },
    { id: 'node_roles',  title: '노드별 역할',       badge: 'Nodes' },
    { id: 'expressions', title: 'Expression 수식',   badge: 'Expr' },
  ];

  defs.forEach(({ id, title, badge }) => {
    const layer   = document.createElement('div');
    layer.className = 'accordion-layer';

    const header  = document.createElement('div');
    header.className = 'accordion-header';
    header.innerHTML = `
      <span class="accordion-title">
        ${esc(title)}
        <span class="accordion-badge">${badge}</span>
      </span>
      <svg class="accordion-chevron" width="13" height="13" viewBox="0 0 24 24"
           fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="9 18 15 12 9 6"></polyline>
      </svg>
    `;

    const content = document.createElement('div');
    content.className = 'accordion-content';

    // ── 섹션별 렌더링 ─────────────────────────────────────────
    if (id === 'summary') {
      // 전체 요약: 마크다운 줄바꿈 처리 + 단락 분리
      const text = summaryContent || '요약 정보가 없습니다.';
      content.innerHTML = `<div class="summary-text">${esc(text).replace(/\n\n/g, '</p><p>').replace(/\n/g, '<br>')}</div>`;

    } else if (id === 'node_roles') {
      // 노드별 역할: 각 노드를 카드로 렌더링
      const items = Array.isArray(nodeItems) ? [...nodeItems] : [];
      items.sort((a, b) => {
        const an = String(a?.node_name || a?.name || '');
        const bn = String(b?.node_name || b?.name || '');
        const am = an.match(/^\s*(\d+)\./);
        const bm = bn.match(/^\s*(\d+)\./);
        if (am && bm) return Number(am[1]) - Number(bm[1]);
        if (am && !bm) return -1;
        if (!am && bm) return 1;
        return an.localeCompare(bn, 'ko');
      });
      if (items.length === 0) {
        content.innerHTML = '<p style="color:var(--text-muted);font-size:12px">노드 정보가 없습니다.</p>';
      } else {
        const LAYER_BADGE = {
          trigger:    { label: '트리거',    color: '#7c3aed' },
          processing: { label: '처리',      color: '#0ea5e9' },
          sink:       { label: '적재',      color: '#16a34a' },
        };
        const TYPE_ICON = {
          webhook:       '🔗', scheduleTrigger: '⏰', manualTrigger: '▶️',
          httpRequest:   '🌐', set:             '✏️', code:          '💻',
          splitOut:      '✂️', merge:           '🔀', if:            '🔀',
          postgres:      '🗄️', mysql:           '🗄️', googleSheets:  '📊',
          slack:         '💬', gmail:           '📧', emailSend:     '📧',
          stickyNote:    '📝', function:        '⚙️', executWorkflow:'🔄',
          airtable:      '📋', s3:              '☁️',
        };

        const getIcon = (type) => {
          const key = type.split('.').pop();
          for (const [k, v] of Object.entries(TYPE_ICON)) {
            if (key.toLowerCase().includes(k.toLowerCase())) return v;
          }
          return '⚙️';
        };

        const LAYER_CLASS = { trigger: 'layer-trigger', processing: 'layer-processing', sink: 'layer-sink' };
        const LAYER_KO    = { trigger: '트리거', processing: '처리', sink: '적재' };

        const html = items.map((row, idx) => {
          if (!row || typeof row !== 'object') return '';

          const rawName   = String(row.node_name || row.name || `Node ${idx + 1}`);
          const name      = esc(rawName.replace(/^\s*\d+\.\s*/, ''));
          const type      = row.type || '';
          const typeShort = esc(type.split('.').pop() || type);
          const role      = esc(row.role || row.description || '역할 정보 없음');
          const nodeLayer = row.layer || '';
          const icon      = getIcon(type);
          const warning   = row.warning || null;

          const layerClass = LAYER_CLASS[nodeLayer] || 'layer-processing';
          const layerKo    = LAYER_KO[nodeLayer] || nodeLayer;

          const keyParams  = Array.isArray(row.key_params) ? row.key_params : [];
          const paramsHtml = keyParams.length > 0
            ? `<div class="node-params">` +
              keyParams.map(p => {
                const k = esc(String(p?.k || ''));
                const v = esc(String(p?.v || ''));
                return `<span class="node-param-item"><span class="node-param-key">${k}:</span><span class="node-param-val"> ${v}</span></span>`;
              }).join('') + `</div>`
            : '';

          const warningHtml = warning
            ? `<div class="nrc-warning">⚠️ ${esc(warning)}</div>` : '';

          return `
            <div class="node-role-card">
              <div class="nrc-header">
                <span style="font-size:14px">${icon}</span>
                <span class="nrc-name">${name}</span>
                <span style="font-size:9.5px;color:var(--text-muted);font-family:var(--font-mono)">${typeShort}</span>
                <span class="nrc-layer-badge ${layerClass}">${layerKo}</span>
              </div>
              <div class="nrc-role">${role.replace(/\n/g, '<br>')}</div>
              ${paramsHtml}
              ${warningHtml}
            </div>`;
        }).join('');

        content.innerHTML = `<div style="padding:6px 4px">${html}</div>`;
      }

    } else if (id === 'expressions') {
      // 수식 해설
      const items = Array.isArray(exprItems) ? exprItems : [];
      if (items.length === 0) {
        content.innerHTML = `
          <div class="expression-label" style="margin-bottom:8px">수식 목록</div>
          <div style="color:var(--text-muted);font-size:12px;font-style:italic">감지된 표현식이 없습니다.</div>`;
      } else {
        const html = items.map((row) => {
          if (!row || typeof row !== 'object') return `<pre class="expr-pre">${esc(String(row))}</pre>`;
          const expr = esc(row.expression || row.expr || '');
          const node = row.node ? `<span class="expr-node">${esc(row.node)}</span>` : '';
          const expl = esc(row.explanation || row.description || '');
          return `
            <div class="expr-item">
              <code class="expr-code">${expr}</code>
              ${node}
              <div class="expr-explanation">${expl}</div>
            </div>`;
        }).join('');
        content.innerHTML = `<div class="expression-label" style="margin-bottom:8px">수식 목록</div><div class="expr-list">${html}</div>`;
      }
    }

    header.addEventListener('click', () => {
      const isOpen = content.classList.toggle('open');
      header.querySelector('.accordion-chevron').classList.toggle('open', isOpen);
    });

    // 전체 요약은 기본 열림
    if (id === 'summary' && summaryContent) {
      content.classList.add('open');
      setTimeout(() => header.querySelector('.accordion-chevron')?.classList.add('open'), 0);
    }

    layer.appendChild(header);
    layer.appendChild(content);
    block.appendChild(layer);
  });

  wrapper.appendChild(block);
  afterEl.insertAdjacentElement('afterend', wrapper);
  scrollBottom();
}

// ══════════════════════════════════════════════════════════════
//  RENDER — ACTION CARD
// ══════════════════════════════════════════════════════════════
function renderActionCard({ type, label, payload }, afterEl) {
  const isError = type === 'error_patch_apply';
  const wrapper = document.createElement('div');
  wrapper.className = 'action-card-wrapper';

  wrapper.innerHTML = `
    <div class="action-card ${isError ? 'error-type' : ''}">
      <div class="action-card-header">
        <div class="action-card-icon ${isError ? 'icon-patch' : 'icon-inject'}">
          ${isError ? ICON_SVG.wrench : ICON_SVG.rocket}
        </div>
        <div class="action-card-info">
          <div class="action-card-title">${isError ? 'AI 처방전 준비됨' : '캔버스에 바로 적용'}</div>
          <div class="action-card-sub">${esc(label || (isError ? '자동 패치 적용' : '워크플로우 주입'))}</div>
        </div>
      </div>
      <div class="action-card-btns">
        <button class="ac-btn ${isError ? 'ac-btn-danger' : 'ac-btn-primary'}" data-inject>
          ${isError ? 'Apply Fix' : '캔버스 주입'}
        </button>
        <button class="ac-btn ac-btn-ghost" data-copy title="클립보드 복사">
          ${ICON_SVG.copy}
        </button>
      </div>
    </div>
  `;

  const payloadStr = typeof payload === 'string' ? payload : JSON.stringify(payload, null, 2);

  wrapper.querySelector('[data-inject]').addEventListener('click', () => {
    injectWorkflow(payloadStr);
  });

  wrapper.querySelector('[data-copy]').addEventListener('click', () => {
    navigator.clipboard.writeText(payloadStr)
      .then(() => showToast('클립보드에 복사됐습니다'))
      .catch(() => showToast('복사 실패'));
  });

  afterEl.insertAdjacentElement('afterend', wrapper);
  scrollBottom();
}

// ══════════════════════════════════════════════════════════════
//  RENDER — EXPRESSION BLOCK
// ══════════════════════════════════════════════════════════════
function renderExpressionBlock(data, afterEl) {
  const wrapper = document.createElement('div');
  wrapper.className = 'expression-wrapper';

  // raw_expression에서 수식 토큰 추출
  const raw = typeof data === 'string' ? data : (data.raw_expression || data.expression || JSON.stringify(data));
  const nodeType = data.node_type ? `<span style="font-size:10px;color:var(--text-muted);margin-left:6px">${esc(data.node_type)}</span>` : '';
  const hint     = data.insert_hint || '클릭하여 복사';

  // 수식 목록 추출 ({{ ... }} 패턴)
  const matches = [...raw.matchAll(/\{\{[^}]+\}\}/g)].map(m => m[0]);
  const chipHtml = matches.length > 0
    ? matches.map(m => `
        <div class="expression-chip" title="${esc(hint)}" data-expr="${esc(m)}">
          <span>${esc(m)}</span>
          <span class="expression-chip-copy">복사</span>
        </div>`).join('')
    : `<div class="expression-chip" data-expr="${esc(raw)}"><span>${esc(raw.slice(0, 80))}</span><span class="expression-chip-copy">복사</span></div>`;

  wrapper.innerHTML = `
    <div class="expression-block">
      <div class="expression-label">
        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor"
             stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="16 18 22 12 16 6"></polyline>
          <polyline points="8 6 2 12 8 18"></polyline>
        </svg>
        Expression 수식 ${nodeType}
      </div>
      <div style="display:flex;flex-direction:column;gap:5px;margin-top:6px">${chipHtml}</div>
    </div>
  `;

  wrapper.querySelectorAll('.expression-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      const expr = chip.dataset.expr;
      navigator.clipboard.writeText(expr)
        .then(() => showToast(`복사됨: ${expr.slice(0, 40)}`))
        .catch(() => {});
    });
  });

  afterEl.insertAdjacentElement('afterend', wrapper);
  scrollBottom();
}

// ══════════════════════════════════════════════════════════════
//  RENDER — REG WARNING
// ══════════════════════════════════════════════════════════════
function renderRegWarning(data, afterEl) {
  const wrapper = document.createElement('div');
  wrapper.className = 'reg-warning-wrapper';

  // 새 포맷(corrections 배열) + 구 포맷(flagged 배열) 모두 지원
  const corrections = Array.isArray(data.corrections) ? data.corrections : [];
  const flagged     = Array.isArray(data.flagged) ? data.flagged : [];

  let detailHtml = '';
  if (corrections.length > 0) {
    const rows = corrections.map(c =>
      `<div class="reg-row">
         <code class="reg-orig">${esc(c.original)}</code>
         <span class="reg-arrow">→</span>
         <code class="reg-fix">${esc(c.corrected)}</code>
         <span class="reg-dist">d=${c.distance ?? '?'}</span>
       </div>`
    ).join('');
    detailHtml = `<div class="reg-detail">${rows}</div>`;
  } else if (flagged.length > 0) {
    detailHtml = `<div class="reg-detail"><span style="font-family:var(--font-mono);font-size:11px">${esc(flagged.join(', '))}</span></div>`;
  }

  const msg = data.message || `⚠️ REG 검증: ${corrections.length || flagged.length}개 속성명 자동 수정됨`;

  wrapper.innerHTML = `
    <div class="reg-warning">
      <span style="flex-shrink:0;display:inline-flex;align-items:center;color:#B45309">${ICON_SVG.alert}</span>
      <span>${esc(msg)}</span>
    </div>
    ${detailHtml}
  `;
  afterEl.insertAdjacentElement('afterend', wrapper);
  scrollBottom();
}

// ══════════════════════════════════════════════════════════════
//  RENDER — NODE HINT
// ══════════════════════════════════════════════════════════════
function renderNodeHint(hints) {
  const refs = createAiBlock('HINT');
  refs.body.classList.remove('typing-cursor');
  refs.body.textContent = '선택된 노드의 Expression 힌트:';

  const wrapper = document.createElement('div');
  wrapper.className = 'node-hint-wrapper';

  const block = document.createElement('div');
  block.className = 'node-hint-block';

  const labelEl = document.createElement('div');
  labelEl.className = 'node-hint-label';
  labelEl.textContent = '필드 힌트';

  const list = document.createElement('div');
  list.className = 'node-hint-list';

  (hints || []).forEach(hint => {
    const item = document.createElement('div');
    item.className = 'node-hint-item';
    item.innerHTML = `<span>${esc(hint)}</span><span class="hint-copy-icon">copy</span>`;
    item.addEventListener('click', () => {
      navigator.clipboard.writeText(hint)
        .then(() => showToast(`${hint} 복사됨`))
        .catch(() => {});
    });
    list.appendChild(item);
  });

  block.appendChild(labelEl);
  block.appendChild(list);
  wrapper.appendChild(block);

  refs.block.insertAdjacentElement('afterend', wrapper);
  appendSep();
  scrollBottom();
}

// ══════════════════════════════════════════════════════════════
//  SEPARATOR
// ══════════════════════════════════════════════════════════════
function appendSep() {
  const sep = document.createElement('div');
  sep.className = 'stream-sep';
  $stream.appendChild(sep);
}

function scrollBottom() {
  requestAnimationFrame(() => {
    $stream.scrollTop = $stream.scrollHeight;
  });
}

// ══════════════════════════════════════════════════════════════
//  SSE STREAMING CORE
// ══════════════════════════════════════════════════════════════
async function sendMessage(userText, extraPayload = {}) {
  if (state.streaming || !userText.trim()) return;

  state.streaming = true;
  state.msgCount++;
  setInputEnabled(false);
  renderUserBubble(userText);
  appendSkeleton();

  const requestBody = {
    session_id: state.sessionId,
    message:    userText,
    node_data:  extraPayload.node_data  ?? null,
    error_log:  extraPayload.error_log  ?? null,
    raw_json:   extraPayload.raw_json   ?? null,
    model:      'gemma4-e4b:latest',
  };

  let refs       = null;   // { block, body, badge }
  let fullText   = '';
  let lastIntent = 'AI';

  try {
    const resp = await fetch(`${API_BASE}/api/workspace/stream`, {
      method:  'POST',
      headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
      body:    JSON.stringify(requestBody),
    });

    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

    removeSkeleton();
    refs = createAiBlock(lastIntent);

    // AI SDK 데이터 스트림 프로토콜 파서
    // 포맷: PREFIX:DATA\n
    //   0:"token"           → 텍스트 토큰 (JSON 인코딩된 문자열)
    //   2:[{type,...}]      → 구조화 데이터 파트 배열
    //   d:{"finishReason"}  → 스트림 완료
    const reader  = resp.body.getReader();
    const decoder = new TextDecoder();
    let   buf     = '';

    outer: while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buf += decoder.decode(value, { stream: true });
      const lines = buf.split('\n');
      buf = lines.pop();

      for (const line of lines) {
        const rawLine = line.replace(/\r$/, '').trim();
        if (!rawLine) continue;

        const colonIdx = rawLine.indexOf(':');
        if (colonIdx === -1) continue;

        const prefix  = rawLine.slice(0, colonIdx);
        const rawData = rawLine.slice(colonIdx + 1);

        // ─── 0: 텍스트 토큰 ───────────────────────────────────
        if (prefix === '0') {
          let token;
          try { token = JSON.parse(rawData); } catch { token = rawData; }
          if (typeof token !== 'string') continue;
          fullText += token;
          if (refs?.body) {
            refs.body.textContent = fullText;
            refs.body.classList.add('typing-cursor');
          }
          scrollBottom();
          continue;
        }

        // ─── 2: 구조화 데이터 파트 배열 ───────────────────────
        if (prefix === '2') {
          let parts;
          try { parts = JSON.parse(rawData); } catch { continue; }
          if (!Array.isArray(parts)) continue;

          for (const part of parts) {
            switch (part.type) {

              case 'intent': {
                lastIntent = part.intent || 'AI';
                if (refs?.badge) {
                  refs.badge.className = `intent-badge badge-${lastIntent.toLowerCase()}`;
                  refs.badge.textContent = lastIntent;
                }
                const lvl = part.curriculum_level;
                if (lvl && refs?.body) {
                  const levelKoMap = { beginner: '입문', intermediate: '중급', advanced: '심화' };
                  const wks = part.weeks || '';
                  const levelTag = document.createElement('div');
                  levelTag.className = `cc-level level-${lvl}`;
                  levelTag.style.cssText = 'display:inline-block;margin-bottom:8px;';
                  levelTag.textContent = `${levelKoMap[lvl] || lvl} 과정${wks ? ' ' + wks + '주' : ''}`;
                  refs.body.appendChild(levelTag);
                }
                break;
              }

              case 'card': {
                fullText = '';
                if (refs?.block) refs.block.innerHTML = '';
                if (refs?.body) { refs.body.classList.remove('typing-cursor'); refs.body.innerHTML = ''; }
                renderActionCard(part.data ?? part, refs.block);
                break;
              }

              case 'node_property_card': {
                renderNodePropertyCard(part.data ?? part, refs.block);
                break;
              }

              case 'curriculum': {
                fullText = '';
                if (refs?.block) refs.block.innerHTML = '';
                if (refs?.body) { refs.body.classList.remove('typing-cursor'); refs.body.innerHTML = ''; }
                const cards = part.data?.cards ?? part.cards ?? [];
                renderCurriculumCards(cards, refs.block);
                break;
              }

              case 'expression': {
                fullText = '';
                if (refs?.block) refs.block.innerHTML = '';
                if (refs?.body) { refs.body.classList.remove('typing-cursor'); refs.body.innerHTML = ''; }
                renderExpressionBlock(part.data ?? part, refs.block);
                break;
              }

              case 'report': {
                fullText = '';
                if (refs?.block) refs.block.innerHTML = '';
                if (refs?.body) { refs.body.classList.remove('typing-cursor'); refs.body.innerHTML = ''; }
                const reportPayload = part.data?.report ?? part.data ?? part.report ?? part ?? {};
                renderAccordion(reportPayload, refs.block);
                break;
              }

              case 'error_alert': {
                if (refs?.body) refs.body.classList.remove('typing-cursor');
                const alertData = part.data ?? {};
                if (alertData.type === 'interrupt' && alertData.message) {
                  showErrorBanner(alertData.message);
                }
                break;
              }

              case 'reg_warning': {
                renderRegWarning(part.data ?? {}, refs.block);
                break;
              }
            }
          }
          continue;
        }

        // ─── d: 스트림 완료 ────────────────────────────────────
        if (prefix === 'd') {
          if (refs?.body) {
            refs.body.classList.remove('typing-cursor');
            if (fullText && fullText.trim()) {
              refs.body.innerHTML = renderMarkdown(fullText);
            }
          }
          appendSep();
          break outer;
        }
      }
    }

    if (refs?.body) refs.body.classList.remove('typing-cursor');

  } catch (err) {
    removeSkeleton();
    if (!refs) refs = createAiBlock('ERROR');
    if (refs.body) {
      refs.body.classList.remove('typing-cursor');
      refs.body.style.color = 'var(--red)';
      refs.body.textContent =
        `응답 처리 실패\n(${err.message})\n\n백엔드/네트워크 또는 프론트 파서 이슈일 수 있습니다.`;
    }
    setStatus('offline');
  } finally {
    state.streaming = false;
    setInputEnabled(true);
    scrollBottom();
  }
}

// ══════════════════════════════════════════════════════════════
//  INPUT HELPERS
// ══════════════════════════════════════════════════════════════
function setInputEnabled(enabled) {
  $input.disabled    = !enabled;
  $sendBtn.disabled  = !enabled;
  if (enabled) $input.focus();
}

function autoResize() {
  $input.style.height = 'auto';
  $input.style.height = Math.min($input.scrollHeight, 100) + 'px';
  // char count
  const len = $input.value.length;
  $charCount.textContent = len > 50 ? `${len}` : '';
}

$input.addEventListener('input', autoResize);

$input.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    handleSend();
  }
});

$sendBtn.addEventListener('click', handleSend);

function handleSend() {
  const text = $input.value.trim();
  if (!text || state.streaming) return;

  // Auto-detect pasted n8n JSON
  if (text.includes('"connections"') && text.includes('"nodes"')) {
    sendMessage(text, { raw_json: text });
    $input.value = '';
    autoResize();
    return;
  }

  // 현재 워크플로우 관련 요청이면 캔버스 JSON 자동 첨부
  const needsCanvas = /현재|이\s*워크플로우|캔버스|분석|설명|봐줘|해줘|흐름/.test(text);
  if (needsCanvas && typeof chrome !== 'undefined' && chrome.runtime?.sendMessage) {
    $input.value = '';
    autoResize();
    chrome.runtime.sendMessage({ type: 'GET_CANVAS_JSON' }, (resp) => {
      if (resp?.success && resp.data) {
        sendMessage(text, { raw_json: resp.data });
      } else {
        sendMessage(text, {});
      }
    });
    return;
  }

  sendMessage(text, {});
  $input.value = '';
  autoResize();
}

// ══════════════════════════════════════════════════════════════
//  CHIP ACTIONS
// ══════════════════════════════════════════════════════════════
document.getElementById('chip-canvas').addEventListener('click', handleChipCanvas);

function handleChipCanvas() {
  if (typeof chrome === 'undefined' || !chrome.runtime?.sendMessage) {
    showToast('Chrome Extension 환경이 아닙니다');
    return;
  }

  showToast('캔버스 분석 중...');

  chrome.runtime.sendMessage({ type: 'GET_CANVAS_JSON' }, (resp) => {
    if (chrome.runtime.lastError) {
      showToast('익스텐션 통신 오류: ' + (chrome.runtime.lastError.message || ''));
      return;
    }

    if (!resp) {
      showToast('응답 없음 — 익스텐션을 재로드 해보세요');
      return;
    }

    // 성공 (Pinia 직접 접근 또는 클립보드 폴백)
    if (resp.success && resp.data) {
      const method = resp.method === 'clipboard_fallback' ? '(클립보드)' : '(Pinia)';
      const nodeCount = resp.node_count != null ? ` ${resp.node_count}개 노드` : '';
      showToast(`캔버스 수집 완료${nodeCount} ${method}`);
      sendMessage('현재 n8n 캔버스 워크플로우를 분석해줘', { raw_json: resp.data });
      return;
    }

    // 디버그 정보가 있으면 콘솔에 출력
    if (resp.debug_store_ids) {
      console.warn('[Naito] 스토어 ID 목록:', resp.debug_store_ids);
    }

    // 실패 메시지 표시
    const errMsg = resp.error || 'n8n 에디터 탭을 먼저 열어주세요 (localhost:5678)';
    showToast(errMsg);

    // 스토어 ID를 못 찾은 경우 → 디버그 모드 안내
    if (resp.debug_store_ids) {
      console.info(
        '[Naito] 캔버스 수집 실패 — background.js에 스토어 ID를 추가해야 할 수 있습니다.\n' +
        '발견된 스토어 ID: ' + resp.debug_store_ids.join(', ') + '\n' +
        'DEBUG_STORE_IDS 메시지로 상세 정보를 확인하세요.'
      );
    }
  });
}

document.getElementById('chip-json').addEventListener('click', () => $fileInput.click());

document.getElementById('chip-curriculum').addEventListener('click', () => {
  sendMessage('n8n 학습 커리큘럼 전체 로드맵을 주차별 카드로 보여줘');
});

document.getElementById('chip-debug').addEventListener('click', () => {
  sendMessage('현재 n8n 워크플로우에서 흔히 발생하는 에러 유형과 디버깅 방법을 알려줘');
});

document.getElementById('chip-docs').addEventListener('click', () => {
  openDocsModal();
});

$fileInput.addEventListener('change', (e) => {
  const file = e.target.files?.[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = (ev) => {
    sendMessage('이 워크플로우 JSON을 역추적 분석해줘', { raw_json: ev.target.result });
  };
  reader.readAsText(file);
  $fileInput.value = '';
});

// ── 코드 블록 복사 이벤트 위임 ────────────────────────────────
$stream.addEventListener('click', (e) => {
  const btn = e.target.closest('[data-code-copy]');
  if (!btn) return;
  const code = btn.previousElementSibling?.textContent ?? '';
  navigator.clipboard.writeText(code)
    .then(() => {
      const orig = btn.textContent;
      btn.textContent = '✓ 복사됨';
      setTimeout(() => { btn.textContent = orig; }, 1500);
    })
    .catch(() => {});
});

// ══════════════════════════════════════════════════════════════
//  WORKFLOW INJECT
// ══════════════════════════════════════════════════════════════
function injectWorkflow(jsonStr) {
  if (typeof chrome === 'undefined' || !chrome.runtime?.sendMessage) {
    // Fallback: clipboard copy
    navigator.clipboard.writeText(jsonStr)
      .then(() => showToast('클립보드 복사 완료. n8n에서 Ctrl+V 하세요'))
      .catch(() => showToast('복사 실패'));
    return;
  }

  // Pre-save snapshot
  fetch(`${API_BASE}/api/workflow/inject`, {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify({
      session_id:     state.sessionId,
      inject_payload: (() => { try { return JSON.parse(jsonStr); } catch { return {}; } })(),
      current_workflow: {},
      operation: 'inject',
    }),
  }).catch(() => {});

  chrome.runtime.sendMessage({ type: 'INJECT_WORKFLOW', payload: jsonStr }, (resp) => {
    if (chrome.runtime.lastError) {
      showToast('익스텐션 통신 오류');
      return;
    }
    if (resp?.success) {
      showToast('캔버스에 워크플로우가 주입됐습니다');
    } else {
      navigator.clipboard.writeText(jsonStr)
        .then(() => showToast('클립보드 복사 완료. n8n에서 Ctrl+V 하세요'))
        .catch(() => showToast('주입 실패: ' + (resp?.error || '')));
    }
  });
}

function injectByCodeId(codeId) {
  showToast('실습 코드 로딩 중');
  const encoded = encodeURIComponent(codeId);
  const candidates = [
    `${API_BASE}/api/curriculum/code/${encoded}`,
    `${API_BASE}/api/workflow/curriculum/code/${encoded}`,
  ];

  const tryFetch = (idx = 0) => {
    if (idx >= candidates.length) {
      showToast('실습 코드 로드 실패. 백엔드 연결을 확인하세요');
      return;
    }
    fetch(candidates[idx])
      .then(r => {
        if (!r.ok) throw new Error(String(r.status));
        return r.json();
      })
      .then(data => {
        if (data?.workflow_json) {
          injectWorkflow(JSON.stringify(data.workflow_json));
        } else {
          showToast('실습 코드를 찾을 수 없습니다');
        }
      })
      .catch(() => tryFetch(idx + 1));
  };

  tryFetch(0);
}

// ══════════════════════════════════════════════════════════════
//  ROLLBACK (restore canvas)
// ══════════════════════════════════════════════════════════════
function handleRestoreCanvas(workflowJson) {
  if (!workflowJson) { showToast('복원할 스냅샷이 없습니다'); return; }
  const str = typeof workflowJson === 'string'
    ? workflowJson
    : JSON.stringify(workflowJson);
  injectWorkflow(str);
  showToast('이전 캔버스로 복원됐습니다');
}

// ══════════════════════════════════════════════════════════════
//  HEADER BUTTONS
// ══════════════════════════════════════════════════════════════
document.getElementById('btn-clear').addEventListener('click', () => {
  // Remove all messages except empty state
  const children = [...$stream.children];
  children.forEach(c => {
    if (c.id !== 'empty-state') c.remove();
  });
  $emptyState.style.display = '';
  $emptyState.style.opacity = '';
  $emptyState.style.transition = '';
  state.msgCount = 0;
  showToast('대화가 초기화됐습니다');
});

document.getElementById('btn-settings').addEventListener('click', () => {
  showToast('브라우저 설정에서 사이드패널 위치를 왼쪽으로 변경할 수 있습니다');
});

$authBtn.addEventListener('click', () => {
  if (state.user) {
    logoutAuth();
    return;
  }
  openAuthModal('login');
});

$authClose.addEventListener('click', closeAuthModal);
$authModal.addEventListener('click', (e) => {
  if (e.target === $authModal) closeAuthModal();
});

$authSwitch.addEventListener('click', () => {
  setAuthMode(state.authMode === 'login' ? 'signup' : 'login');
});

$authSubmit.addEventListener('click', submitAuth);

$authPass.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') submitAuth();
});

$authLogout.addEventListener('click', logoutAuth);

$docsClose.addEventListener('click', closeDocsModal);
$docsModal.addEventListener('click', (e) => {
  if (e.target === $docsModal) closeDocsModal();
});

$docsSearch.addEventListener('input', () => {
  clearTimeout(docsSearchTimer);
  docsSearchTimer = setTimeout(() => {
    loadDocs($docsSearch.value || '');
  }, 260);
});

// ══════════════════════════════════════════════════════════════
//  BACKEND HEALTH CHECK
// ══════════════════════════════════════════════════════════════
async function checkBackend() {
  try {
    const resp = await fetch(`${API_BASE}/openapi.json`, {
      signal: AbortSignal.timeout(3000),
    });
    state.backendConnected = resp.ok;
    setStatus(resp.ok || state.wsConnected ? 'connected' : 'offline');
  } catch {
    state.backendConnected = false;
    setStatus(state.wsConnected ? 'connected' : 'offline');
  }
}

// ══════════════════════════════════════════════════════════════
//  INIT
// ══════════════════════════════════════════════════════════════
(function init() {
  state.sessionId = getSessionId();
  setStatus('connecting');
  restoreAuthSession();
  renderAuthState();
  checkBackend();
  connectWS();
  $input.focus();

  // Re-check periodically
  setInterval(checkBackend, 30_000);
})();
