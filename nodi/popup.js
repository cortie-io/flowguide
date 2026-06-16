// ═══════════════════════════════════════════════════════════════
//  nodi _Tutor Agent — popup.js
//  Single Unified Workspace controller
// ═══════════════════════════════════════════════════════════════

'use strict';

const API_BASE  = 'http://localhost:8000';
const WS_URL    = 'ws://localhost:8000/ws/extension';
const SESSION_KEY = 'n9n_session_id';

// ── State ──────────────────────────────────────────────────────
const state = {
  sessionId: null,
  ws: null,
  wsReady: false,
  streaming: false,
  pendingErrorMsg: null,
  lastSnapshotSession: null,
};

// ── DOM refs ───────────────────────────────────────────────────
const $stream    = document.getElementById('chat-stream');
const $input     = document.getElementById('chat-input');
const $sendBtn   = document.getElementById('send-btn');
const $status    = document.getElementById('status-indicator');
const $banner    = document.getElementById('error-banner');
const $bannerTitle = document.getElementById('banner-title');
const $bannerClose = document.getElementById('banner-close');
const $toast     = document.getElementById('toast');
const $fileInput = document.getElementById('json-file-input');
const $emptyState = document.getElementById('empty-state');

if (!$stream || !$input || !$sendBtn || !$status || !$banner || !$bannerTitle || !$bannerClose || !$toast || !$fileInput || !$emptyState) {
  console.warn('popup.js: missing expected DOM nodes, skipping popup init');
} else {

// ── Session ID ─────────────────────────────────────────────────
function getSessionId() {
  let sid = sessionStorage.getItem(SESSION_KEY);
  if (!sid) {
    sid = 'nodi-' + Date.now() + '-' + Math.random().toString(36).slice(2, 7);
    sessionStorage.setItem(SESSION_KEY, sid);
  }
  return sid;
}

// ── Toast ──────────────────────────────────────────────────────
function showToast(msg, duration = 2200) {
  $toast.textContent = msg;
  $toast.classList.add('show');
  setTimeout(() => $toast.classList.remove('show'), duration);
}

// ── Empty state ────────────────────────────────────────────────
function hideEmpty() {
  if ($emptyState) $emptyState.style.display = 'none';
}

// ── Status indicator ───────────────────────────────────────────
function setStatus(connected) {
  $status.className = 'status-dot' + (connected ? '' : ' disconnected');
  $status.textContent = connected ? '⚡ connected' : 'connecting…';
}

// ── WebSocket ──────────────────────────────────────────────────
function connectWS() {
  if (state.ws && state.ws.readyState < 2) return;

  const ws = new WebSocket(`${WS_URL}?session_id=${state.sessionId}`);
  state.ws = ws;

  ws.addEventListener('open', () => {
    state.wsReady = true;
    setStatus(true);
  });

  ws.addEventListener('message', (evt) => {
    let data;
    try { data = JSON.parse(evt.data); } catch { return; }

    switch (data.event) {
      case 'node_inspect_hint':
        renderNodeHint(data.field_hints || []);
        break;
      case 'error_alert_ui':
        showErrorBanner(data.auto_prompt || '에러가 감지됐습니다.');
        break;
      case 'inject_result':
        showToast(data.status === 'ok' ? '✅ 캔버스에 주입됐습니다' : '⚠️ 주입 실패: ' + (data.error || ''));
        break;
      case 'restore_canvas':
        handleRestoreCanvas(data.workflow_json);
        break;
    }
  });

  ws.addEventListener('close', () => {
    state.wsReady = false;
    setStatus(false);
    setTimeout(connectWS, 3000);
  });

  ws.addEventListener('error', () => {
    setStatus(false);
  });
}

function wsSend(payload) {
  if (state.ws && state.ws.readyState === WebSocket.OPEN) {
    state.ws.send(JSON.stringify(payload));
  }
}

// ── Error banner ───────────────────────────────────────────────
function showErrorBanner(msg) {
  state.pendingErrorMsg = msg;
  if ($bannerTitle) {
    $bannerTitle.textContent = '🚑 실시간 에러 감지: ' + msg.slice(0, 60) + (msg.length > 60 ? '…' : '');
  }
  if ($banner) {
    $banner.classList.add('visible');
  }
}

if ($banner) {
  $banner.addEventListener('click', (e) => {
    if (e.target === $bannerClose) {
      $banner.classList.remove('visible');
      state.pendingErrorMsg = null;
      return;
    }
    if (state.pendingErrorMsg) {
      sendMessage(state.pendingErrorMsg, { error_log: state.pendingErrorMsg });
      $banner.classList.remove('visible');
      state.pendingErrorMsg = null;
    }
  });
}

if ($bannerClose) {
  $bannerClose.addEventListener('click', (e) => {
    e.stopPropagation();
    if ($banner) {
      $banner.classList.remove('visible');
    }
    state.pendingErrorMsg = null;
  });
}

// ── chrome.runtime message from content.js ────────────────────
if (typeof chrome !== 'undefined' && chrome.runtime?.onMessage) {
  chrome.runtime.onMessage.addListener((msg) => {
    if (msg.type === 'N8N_ERROR_DETECTED') {
      wsSend({ event: 'error_detected', payload: { error_message: msg.error } });
      showErrorBanner(msg.error);
    }
  });
}

// ── Render helpers ─────────────────────────────────────────────
function appendSep() {
  const sep = document.createElement('div');
  sep.className = 'stream-sep';
  $stream.appendChild(sep);
}

function bindClick(id, handler) {
  const el = document.getElementById(id);
  if (el) {
    el.addEventListener('click', handler);
  }
}

function renderUserBubble(text) {
  hideEmpty();
  const wrap = document.createElement('div');
  wrap.className = 'msg-user';
  wrap.innerHTML = `<div class="msg-user-bubble">${escHtml(text)}</div>`;
  $stream.appendChild(wrap);
  scrollBottom();
}

function createAiBlock(intentLabel) {
  hideEmpty();
  const block = document.createElement('div');
  block.className = 'msg-ai';

  const label = document.createElement('div');
  label.className = 'msg-ai-label';
  label.innerHTML = `nodi <span class="intent-badge badge-${(intentLabel||'general').toLowerCase()}">${intentLabel || 'AI'}</span>`;

  const body = document.createElement('div');
  body.className = 'msg-ai-body typing-cursor';

  block.appendChild(label);
  block.appendChild(body);
  $stream.appendChild(block);
  scrollBottom();
  return { block, body };
}

function escHtml(s) {
  return String(s)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}

function scrollBottom() {
  $stream.scrollTop = $stream.scrollHeight;
}

// ── Skeleton loader ────────────────────────────────────────────
function appendSkeleton() {
  hideEmpty();
  const el = document.createElement('div');
  el.className = 'msg-ai';
  el.id = 'skeleton-loader';
  el.innerHTML = `
    <div class="msg-ai-label">nodi</div>
    <div class="skeleton-line" style="width:90%"></div>
    <div class="skeleton-line" style="width:72%"></div>
    <div class="skeleton-line" style="width:55%"></div>
  `;
  $stream.appendChild(el);
  scrollBottom();
}

function removeSkeleton() {
  document.getElementById('skeleton-loader')?.remove();
}

// ── Curriculum card renderer ───────────────────────────────────
function renderCurriculumCards(cards, parentBlock) {
  const grid = document.createElement('div');
  grid.className = 'curriculum-grid';

  cards.forEach(card => {
    const el = document.createElement('div');
    el.className = 'curriculum-card';
    el.innerHTML = `
      <div class="cc-week">${escHtml(card.week || '주차')}</div>
      <div class="cc-title">${escHtml(card.title || '')}</div>
      <div class="cc-desc">${escHtml(card.description || '')}</div>
      <div class="cc-inject-btn" data-code-id="${escHtml(card.canvas_code_id || '')}">
        ⚡ 실습 코드 주입
      </div>
    `;

    el.querySelector('.cc-inject-btn').addEventListener('click', (e) => {
      e.stopPropagation();
      const codeId = e.target.dataset.codeId;
      if (codeId) injectByCodeId(codeId);
      else showToast('⚠️ 주입 가능한 코드가 없습니다');
    });

    grid.appendChild(el);
  });

  parentBlock.appendChild(grid);
  scrollBottom();
}

// ── Accordion report renderer ──────────────────────────────────
function renderAccordion(layers, parentBlock) {
  const block = document.createElement('div');
  block.className = 'accordion-block';

  const defs = [
    { id: 'summary',    icon: '📋', title: '전체 요약' },
    { id: 'node_roles', icon: '🔗', title: '노드별 역할' },
    { id: 'expressions',icon: '💡', title: 'Expression 수식 해설' },
  ];

  defs.forEach(({ id, icon, title }) => {
    const layer = document.createElement('div');
    layer.className = 'accordion-layer';

    const header = document.createElement('div');
    header.className = 'accordion-header';
    header.innerHTML = `
      <span class="accordion-title">${icon} ${title}</span>
      <span class="accordion-icon">›</span>
    `;

    const content = document.createElement('div');
    content.className = 'accordion-content';

    const raw = layers[id] || '데이터 없음';
    if (id === 'expressions') {
      content.innerHTML = `<div class="expression-label">수식 목록</div><pre>${escHtml(raw)}</pre>`;
    } else {
      content.textContent = raw;
    }

    header.addEventListener('click', () => {
      const open = content.classList.toggle('open');
      header.querySelector('.accordion-icon').classList.toggle('open', open);
    });

    layer.appendChild(header);
    layer.appendChild(content);
    block.appendChild(layer);
  });

  parentBlock.appendChild(block);
  scrollBottom();
}

// ── Action card (inject / patch) ───────────────────────────────
function renderActionCard({ type, label, payload }, parentBlock) {
  const card = document.createElement('div');
  card.className = 'action-card';

  const isError = type === 'error_patch_apply';
  card.innerHTML = `
    <div class="action-card-title">${isError ? '🔧 자동 수정 준비됨' : '🚀 캔버스에 바로 적용'}</div>
    <button class="action-card-btn ${isError ? 'btn-red' : 'btn-orange'}" id="apply-btn">
      ⚡ ${escHtml(label || 'Apply Fix')}
    </button>
    <button class="action-card-btn btn-ghost" id="copy-btn">📋 클립보드</button>
  `;

  card.querySelector('#apply-btn').addEventListener('click', () => {
    injectWorkflow(JSON.stringify(payload));
  });

  card.querySelector('#copy-btn').addEventListener('click', () => {
    navigator.clipboard.writeText(JSON.stringify(payload, null, 2))
      .then(() => showToast('📋 클립보드에 복사됐습니다'))
      .catch(() => showToast('⚠️ 복사 실패'));
  });

  parentBlock.appendChild(card);
  scrollBottom();
}

// ── Expression block ───────────────────────────────────────────
function renderExpressionBlock(data, parentBlock) {
  const el = document.createElement('div');
  el.className = 'expression-block';
  el.innerHTML = `
    <div class="expression-label">Expression 수식</div>
    <div class="expression-code">${escHtml(data.expression || data)}</div>
  `;
  parentBlock.appendChild(el);
  scrollBottom();
}

// ── REG warning ────────────────────────────────────────────────
function renderRegWarning(data, parentBlock) {
  const el = document.createElement('div');
  el.className = 'reg-warning';
  const flagged = (data.flagged || []).join(', ');
  el.textContent = `⚠️ 미검증 속성 감지: ${flagged}`;
  parentBlock.appendChild(el);
  scrollBottom();
}

// ── Node hint ─────────────────────────────────────────────────
function renderNodeHint(hints) {
  const el = document.createElement('div');
  el.className = 'msg-ai';
  el.innerHTML = `
    <div class="msg-ai-label">nodi <span class="intent-badge badge-expression">HINT</span></div>
    <div class="expression-block" style="margin-top:0">
      <div class="expression-label">선택된 노드 필드 힌트</div>
      <div class="expression-code">${hints.map(h => escHtml(h)).join('\n')}</div>
    </div>
  `;
  $stream.appendChild(el);
  scrollBottom();
}

// ── SSE streaming core ─────────────────────────────────────────
async function sendMessage(userText, extraPayload = {}) {
  if (state.streaming) return;
  if (!userText.trim()) return;

  state.streaming = true;
  setInputEnabled(false);
  renderUserBubble(userText);
  appendSkeleton();

  const body = {
    session_id: state.sessionId,
    message: userText,
    node_data:  extraPayload.node_data  || null,
    error_log:  extraPayload.error_log  || null,
    raw_json:   extraPayload.raw_json   || null,
    model: 'gemma4-e4b:latest',
  };

  let currentBlock = null;
  let currentBody  = null;
  let intentLabel  = 'AI';
  let fullText     = '';

  try {
    const resp = await fetch(`${API_BASE}/api/workspace/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

    removeSkeleton();
    const created = createAiBlock(intentLabel);
    currentBlock = created.block;
    currentBody  = created.body;

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buf = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });

      const lines = buf.split('\n');
      buf = lines.pop();

      for (const line of lines) {
        if (!line.startsWith('data:') && !line.startsWith('event:')) continue;

        if (line.startsWith('event:')) {
          const evtName = line.slice(6).trim();
          // next data line will be handled in next iteration
          continue;
        }

        // data line — parse multi-event SSE properly
        const raw = line.slice(5).trim();
        if (!raw) continue;

        let parsed;
        try { parsed = JSON.parse(raw); } catch { continue; }

        const evtType = parsed.type || parsed.event;

        switch (evtType) {
          case 'intent':
            intentLabel = parsed.intent || 'AI';
            if (currentBlock) {
              const badge = currentBlock.querySelector('.intent-badge');
              if (badge) {
                badge.className = `intent-badge badge-${intentLabel.toLowerCase()}`;
                badge.textContent = intentLabel;
              }
            }
            break;

          case 'token':
            fullText += parsed.data || parsed.token || '';
            if (currentBody) {
              currentBody.textContent = fullText;
              currentBody.classList.add('typing-cursor');
            }
            scrollBottom();
            break;

          case 'card':
            if (currentBody) currentBody.classList.remove('typing-cursor');
            renderActionCard(parsed.data || parsed, currentBlock);
            break;

          case 'expression':
            if (currentBody) currentBody.classList.remove('typing-cursor');
            renderExpressionBlock(parsed.data || parsed, currentBlock);
            break;

          case 'report':
            if (currentBody) currentBody.classList.remove('typing-cursor');
            renderAccordion(parsed.data || {}, currentBlock);
            break;

          case 'curriculum':
            if (currentBody) currentBody.classList.remove('typing-cursor');
            renderCurriculumCards(parsed.data?.cards || [], currentBlock);
            break;

          case 'error_alert':
            if (currentBody) currentBody.classList.remove('typing-cursor');
            break;

          case 'reg_warning':
            renderRegWarning(parsed.data || {}, currentBlock);
            break;

          case 'done':
            if (currentBody) currentBody.classList.remove('typing-cursor');
            appendSep();
            break;
        }
      }
    }

    if (currentBody) currentBody.classList.remove('typing-cursor');

  } catch (err) {
    removeSkeleton();
    if (!currentBlock) {
      const created = createAiBlock('ERROR');
      currentBlock = created.block;
      currentBody  = created.body;
    }
    if (currentBody) {
      currentBody.classList.remove('typing-cursor');
      currentBody.textContent = `연결 오류: 백엔드가 응답하지 않습니다.\n(${err.message})`;
    }
    setStatus(false);
  } finally {
    state.streaming = false;
    setInputEnabled(true);
    scrollBottom();
  }
}

// ── Input helpers ──────────────────────────────────────────────
function setInputEnabled(enabled) {
  $input.disabled = !enabled;
  $sendBtn.disabled = !enabled;
}

function autoResize() {
  $input.style.height = 'auto';
  $input.style.height = Math.min($input.scrollHeight, 96) + 'px';
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

  // Detect if user pasted raw n8n workflow JSON
  let raw_json = null;
  if (text.includes('"connections"') && text.includes('"nodes"')) {
    raw_json = text;
  }

  sendMessage(text, { raw_json });
  $input.value = '';
  autoResize();
}

// ── Chips ──────────────────────────────────────────────────────
bindClick('chip-canvas', async () => {
  showToast('🔍 캔버스 JSON 수집 중…');
  chrome.runtime.sendMessage({ type: 'GET_CANVAS_JSON' }, (resp) => {
    if (resp?.success && resp.data) {
      sendMessage('현재 캔버스 워크플로우를 분석해줘', { raw_json: resp.data });
    } else {
      showToast('⚠️ n8n 탭을 먼저 열어주세요');
    }
  });
});

bindClick('chip-json', () => {
  $fileInput.click();
});

$fileInput.addEventListener('change', (e) => {
  const file = e.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = (ev) => {
    const text = ev.target.result;
    sendMessage('이 워크플로우 JSON을 분석해줘', { raw_json: text });
  };
  reader.readAsText(file);
  $fileInput.value = '';
});

bindClick('chip-curriculum', () => {
  sendMessage('n8n 학습 커리큘럼 로드맵을 보여줘');
});

// ── Inject workflow ────────────────────────────────────────────
function injectWorkflow(jsonStr) {
  if (typeof chrome === 'undefined' || !chrome.runtime?.sendMessage) {
    navigator.clipboard.writeText(jsonStr)
      .then(() => showToast('📋 클립보드에 복사됐습니다. n8n에서 붙여넣기 하세요'))
      .catch(() => showToast('⚠️ 복사 실패'));
    return;
  }

  // Save snapshot before inject
  fetch(`${API_BASE}/api/workflow/inject`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: state.sessionId,
      inject_payload: JSON.parse(jsonStr),
      current_workflow: {},
      operation: 'inject',
    }),
  }).catch(() => {});

  chrome.runtime.sendMessage({ type: 'INJECT_WORKFLOW', payload: jsonStr }, (resp) => {
    if (resp?.success) {
      showToast('✅ 캔버스에 주입됐습니다');
    } else {
      navigator.clipboard.writeText(jsonStr)
        .then(() => showToast('📋 클립보드에 복사됐습니다. n8n에서 Ctrl+V 하세요'))
        .catch(() => showToast('⚠️ 주입 실패'));
    }
  });
}

function injectByCodeId(codeId) {
  fetch(`${API_BASE}/api/curriculum/code/${encodeURIComponent(codeId)}`)
    .then(r => r.json())
    .then(data => {
      if (data.workflow_json) injectWorkflow(JSON.stringify(data.workflow_json));
      else showToast('⚠️ 실습 코드를 찾을 수 없습니다');
    })
    .catch(() => showToast('⚠️ 실습 코드 로드 실패'));
}

// ── Restore canvas (rollback) ──────────────────────────────────
function handleRestoreCanvas(workflowJson) {
  if (!workflowJson) { showToast('⚠️ 복원할 스냅샷이 없습니다'); return; }
  injectWorkflow(typeof workflowJson === 'string' ? workflowJson : JSON.stringify(workflowJson));
  showToast('↩️ 이전 캔버스로 복원됐습니다');
}

// ── Backend health check ───────────────────────────────────────
async function checkBackend() {
  try {
    const resp = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(3000) });
    if (resp.ok) setStatus(true);
    else setStatus(false);
  } catch {
    setStatus(false);
  }
}

// ── Init ───────────────────────────────────────────────────────
(function init() {
  state.sessionId = getSessionId();
  checkBackend();
  connectWS();
  $input.focus();
})();

}
