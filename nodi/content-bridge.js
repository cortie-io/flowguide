// Naito content-bridge — naito.chat ↔ localhost n8n CORS 우회 브릿지
// 웹페이지는 CORS 때문에 localhost에 직접 접근 불가 → 익스텐션이 대신 fetch
(function () {
  'use strict';

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
