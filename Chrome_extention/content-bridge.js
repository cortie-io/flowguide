// Naito content-bridge — naito.chat ↔ localhost n8n CORS 우회 브릿지
// 웹페이지는 CORS 때문에 localhost에 직접 접근 불가 → 익스텐션이 대신 fetch
//
// 이 파일은 콘텐츠 스크립트로 격리된 world에서 실행되므로 chrome.runtime에
// 접근할 수 있다. naito.chat 페이지 자신의 JS(window.chrome)는 이 API에
// 접근할 수 없으므로 (익스텐션이 externally_connectable을 선언하지 않음),
// 페이지가 window.postMessage로 요청을 보내면 이 스크립트가 대신
// chrome.runtime.sendMessage로 background.js를 호출하고 결과를 다시
// postMessage로 페이지에 돌려준다.
(function () {
  'use strict';

  window.addEventListener('message', (event) => {
    if (event.source !== window) return;

    if (event.data?.type === 'NAITO_GET_CANVAS_JSON') {
      const { requestId } = event.data;
      if (typeof chrome === 'undefined' || !chrome.runtime?.sendMessage) {
        window.postMessage({ type: 'NAITO_CANVAS_JSON_RESPONSE', requestId, success: false, error: 'extension unavailable' }, '*');
        return;
      }
      chrome.runtime.sendMessage({ type: 'GET_CANVAS_JSON' }, (resp) => {
        window.postMessage({ type: 'NAITO_CANVAS_JSON_RESPONSE', requestId, ...(resp || { success: false, error: 'no response' }) }, '*');
      });
      return;
    }

    if (event.data?.type === 'NAITO_INJECT_CANVAS') {
      const { requestId, payload } = event.data;
      if (typeof chrome === 'undefined' || !chrome.runtime?.sendMessage) {
        window.postMessage({ type: 'NAITO_INJECT_CANVAS_RESPONSE', requestId, success: false, error: 'extension unavailable' }, '*');
        return;
      }
      chrome.runtime.sendMessage({ type: 'INJECT_WORKFLOW', payload }, (resp) => {
        window.postMessage({ type: 'NAITO_INJECT_CANVAS_RESPONSE', requestId, ...(resp || { success: false, error: 'no response' }) }, '*');
      });
      return;
    }
  });

  window.addEventListener('message', async (event) => {
    if (event.source !== window) return;
    if (event.data?.type !== 'NAITO_GET_WORKFLOW') return;

    const { n8nUrl, apiKey, messageText, requestId } = event.data;
    const baseUrl = (n8nUrl || 'http://localhost:5678').replace(/\/$/, '');

    try {
      // API 키 있으면 공개 API, 없으면 내부 REST API 시도
      const usePublicApi = !!apiKey;
      const listUrl = usePublicApi
        ? `${baseUrl}/api/v1/workflows`
        : `${baseUrl}/rest/workflows`;
      const headers = usePublicApi ? { 'X-N8N-API-KEY': apiKey } : {};

      const listResp = await fetch(listUrl, {
        headers,
        credentials: usePublicApi ? 'omit' : 'include',
      });

      if (!listResp.ok) {
        window.postMessage({ type: 'NAITO_WORKFLOW_RESPONSE', requestId, workflow: null, error: `list ${listResp.status}` }, '*');
        return;
      }

      const listJson = await listResp.json();
      const workflows = listJson.data ?? (Array.isArray(listJson) ? listJson : []);

      if (!workflows.length) {
        window.postMessage({ type: 'NAITO_WORKFLOW_RESPONSE', requestId, workflow: null }, '*');
        return;
      }

      const msgLower = (messageText || '').toLowerCase();
      let target = workflows.find(w => w.name && msgLower.includes(w.name.toLowerCase()));
      if (!target) {
        target = workflows.reduce((a, b) =>
          (b.updatedAt ?? b.createdAt ?? '') > (a.updatedAt ?? a.createdAt ?? '') ? b : a
        );
      }

      if (!target?.id) {
        window.postMessage({ type: 'NAITO_WORKFLOW_RESPONSE', requestId, workflow: null }, '*');
        return;
      }

      const detailUrl = usePublicApi
        ? `${baseUrl}/api/v1/workflows/${target.id}`
        : `${baseUrl}/rest/workflows/${target.id}`;
      const detailResp = await fetch(detailUrl, {
        headers,
        credentials: usePublicApi ? 'omit' : 'include',
      });

      if (!detailResp.ok) {
        window.postMessage({ type: 'NAITO_WORKFLOW_RESPONSE', requestId, workflow: null }, '*');
        return;
      }

      const workflowJson = await detailResp.text();
      window.postMessage({ type: 'NAITO_WORKFLOW_RESPONSE', requestId, workflow: workflowJson }, '*');

    } catch (e) {
      window.postMessage({ type: 'NAITO_WORKFLOW_RESPONSE', requestId, workflow: null, error: String(e) }, '*');
    }
  });
})();
