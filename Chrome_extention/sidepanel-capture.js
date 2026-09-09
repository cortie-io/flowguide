'use strict';

// ── 스크린샷 캡처 & naito.chat iframe 전달 ──────────────────────
(function () {
  const btn = document.getElementById('screenshot-btn');
  const toast = document.getElementById('capture-toast');
  const toastMsg = document.getElementById('capture-toast-msg');
  const toastDot = toast?.querySelector('.dot');
  let toastTimer = null;

  function showToast(msg, isError) {
    if (!toast) return;
    if (toastTimer) clearTimeout(toastTimer);
    toastMsg.textContent = msg;
    if (toastDot) {
      toastDot.classList.toggle('err', !!isError);
    }
    toast.classList.add('show');
    toastTimer = setTimeout(() => toast.classList.remove('show'), 3500);
  }

  if (!btn) return;

  btn.addEventListener('click', async () => {
    if (btn.classList.contains('loading')) return;
    btn.classList.add('loading');

    try {
      const resp = await chrome.runtime.sendMessage({ type: 'CAPTURE_SCREENSHOT' });

      if (!resp?.success || !resp.dataUrl) {
        showToast(resp?.error || '캡처 실패', true);
        return;
      }

      // iframe(naito.chat)에 postMessage로 전달
      const frame = document.getElementById('frame');
      if (frame?.contentWindow) {
        frame.contentWindow.postMessage(
          { type: 'naito_screenshot', dataUrl: resp.dataUrl },
          'https://naito.chat'
        );
        showToast('캡처 완료 — 채팅창에 전달됨', false);
      } else {
        showToast('naito.chat이 로드되지 않았습니다', true);
      }
    } catch (err) {
      showToast('오류: ' + (err.message || '알 수 없음'), true);
    } finally {
      btn.classList.remove('loading');
    }
  });
})();
