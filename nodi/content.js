// nodi content script — n8n editor error detector
(function () {
  'use strict';
  let lastError = '';

  const scan = () => {
    const selectors = [
      '.execution-error', '[class*="error-message"]',
      '[class*="execution__error"]', '.node-error-indicator',
      '[data-test-id*="error"]', '.el-notification--error'
    ];
    selectors.forEach(sel => {
      document.querySelectorAll(sel).forEach(el => {
        const txt = el.innerText?.trim();
        if (txt && txt.length > 5 && txt !== lastError) {
          lastError = txt;
          chrome.runtime.sendMessage({ type: 'N8N_ERROR_DETECTED', error: txt });
        }
      });
    });
  };

  const observer = new MutationObserver(scan);
  observer.observe(document.body, { childList: true, subtree: true, attributes: true });
  
  // Also scan on DOM load
  if (document.readyState === 'complete') scan();
  else window.addEventListener('load', scan);
})();
