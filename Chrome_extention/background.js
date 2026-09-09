// Naito background service worker — Side Panel edition
'use strict';

const AUTO_OPEN_THROTTLE_MS = 4500;
const lastAutoOpenByTab = new Map();

function isN8nUrl(url) {
  if (typeof url !== 'string') return false;
  return (
    url.startsWith('http://localhost:5678') ||
    url.startsWith('http://127.0.0.1:5678') ||
    url.startsWith('https://localhost:5678') ||
    url.startsWith('https://127.0.0.1:5678') ||
    url.startsWith('https://n8n.cortie.io') ||
    url.includes('://app.n8n.cloud/') ||
    url.includes('.n8n.cloud/')
  );
}

function parseUrl(url) {
  try {
    return new URL(url);
  } catch {
    return null;
  }
}

function isWorkflowEditorUrl(url) {
  const parsed = parseUrl(url);
  if (!parsed) return false;
  const path = parsed.pathname || '';
  return /^\/workflow\//i.test(path);
}

function findN8nTab(callback) {
  chrome.tabs.query({}, (tabs) => {
    const tab = tabs.find((t) => isN8nUrl(t.url));
    callback(tab || null);
  });
}

function findN8nEditorTab(callback) {
  chrome.tabs.query({}, (tabs) => {
    const editorTabs = tabs.filter((tab) => isN8nUrl(tab.url) && isWorkflowEditorUrl(tab.url || ''));
    const tab = editorTabs[0] || tabs.find((t) => isN8nUrl(t.url));
    callback(tab || null);
  });
}

function extractWorkflowId(url) {
  const parsed = parseUrl(url);
  if (!parsed) return '';
  const match = parsed.pathname.match(/\/workflow\/([^/?#]+)/i);
  if (!match) return '';
  const workflowId = match[1];
  if (!workflowId || workflowId.toLowerCase() === 'new') return '';
  return workflowId;
}

function autoOpenSidePanel(tabId, url, force = false) {
  if (!isN8nUrl(url)) return;

  if (!force) {
    const now = Date.now();
    const last = lastAutoOpenByTab.get(tabId) || 0;
    if (now - last < AUTO_OPEN_THROTTLE_MS) return;
    lastAutoOpenByTab.set(tabId, now);
  }

  chrome.sidePanel.setOptions({ tabId, path: 'sidepanel.html', enabled: true }, () => {
    void chrome.runtime.lastError;
  });

  try {
    chrome.sidePanel.open({ tabId }, () => { void chrome.runtime.lastError; });
    setTimeout(() => {
      chrome.sidePanel.open({ tabId }, () => { void chrome.runtime.lastError; });
    }, 600);
    setTimeout(() => {
      chrome.sidePanel.open({ tabId }, () => { void chrome.runtime.lastError; });
    }, 1400);
  } catch {
    // Some Chrome versions may reject sidePanel.open without a gesture.
  }
}

// Open side panel when toolbar icon is clicked
chrome.action.onClicked.addListener((tab) => {
  if (!tab?.id) return;
  autoOpenSidePanel(tab.id, tab.url, true);
});

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  const targetUrl = changeInfo.url || tab?.url;
  if (!targetUrl) return;
  if (changeInfo.status === 'complete' || changeInfo.url) {
    autoOpenSidePanel(tabId, targetUrl);
  }
});

chrome.tabs.onActivated.addListener(({ tabId }) => {
  chrome.tabs.get(tabId, (tab) => {
    if (chrome.runtime.lastError || !tab) return;
    autoOpenSidePanel(tabId, tab.url);
  });
});

// ── 메인 메시지 핸들러 ──────────────────────────────────────────
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {

  // ── Canvas JSON capture ─────────────────────────────────────
  if (msg.type === 'GET_CANVAS_JSON') {
    const resolveTargetTab = (done) => {
      // 1) Side panel이 붙어 있는 탭이 있으면 최우선 사용
      if (sender?.tab?.id && isN8nUrl(sender.tab.url || '')) {
        done(sender.tab);
        return;
      }

      // 2) 현재 포커스 윈도우의 active tab 우선
      chrome.tabs.query({ active: true, lastFocusedWindow: true }, (activeTabs) => {
        const active = activeTabs?.[0];
        if (active && isN8nUrl(active.url || '')) {
          if (isWorkflowEditorUrl(active.url || '')) {
            done(active);
            return;
          }
        }

        // 3) 전체 탭에서 workflow 편집 탭 탐색
        findN8nEditorTab((fallbackTab) => done(fallbackTab));
      });
    };

    resolveTargetTab((tab) => {
      if (!tab) {
        sendResponse({ success: false, error: 'n8n 탭이 열려있지 않습니다. n8n.cortie.io 또는 localhost:5678을 먼저 열어주세요.' });
        return;
      }

      console.info('[Naito] GET_CANVAS_JSON target tab:', {
        tabId: tab.id,
        url: tab.url,
      });

      const workflowId = extractWorkflowId(tab.url);

      chrome.scripting.executeScript({
        target: { tabId: tab.id },
        world: 'MAIN',
        func: (workflowIdArg) => {

          // ── Step 1: Pinia 인스턴스 탐지 ──────────────────────
          // n8n v1.x는 Vue3 + Pinia를 사용.
          // Vue app은 #app.__vue_app__ 으로 접근 가능.
          const getVueApp = () => {
            const roots = [
              document.querySelector('#app'),
              document.querySelector('#n8n-app'),
              document.querySelector('[data-test-id="canvas"]')?.closest('*'),
            ].filter(Boolean);

            for (const root of roots) {
              if (root?.__vue_app__) return root.__vue_app__;
            }

            const all = document.querySelectorAll('body *');
            for (const el of all) {
              if (el?.__vue_app__) return el.__vue_app__;
            }
            return null;
          };

          // Symbol 키를 순회해 Pinia 인스턴스 찾기
          // Pinia 인스턴스는 _s (Map), _e (effectScope), install (fn) 을 가짐
          const getPinia = (vueApp) => {
            if (!vueApp) return null;

            // 0) 가장 흔한 위치: globalProperties.$pinia
            const gp = vueApp.config?.globalProperties;
            if (gp?.$pinia?._s instanceof Map) {
              return gp.$pinia;
            }

            if (window.$pinia?._s instanceof Map) {
              return window.$pinia;
            }
            if (window.__PINIA__?._s instanceof Map) {
              return window.__PINIA__;
            }

            const instanceProvides = vueApp._instance?.appContext?.provides ?? {};
            for (const sym of Object.getOwnPropertySymbols(instanceProvides)) {
              const val = instanceProvides[sym];
              if (val && typeof val === 'object' && val._s instanceof Map) {
                return val;
              }
            }

            const provides = vueApp._context?.provides ?? {};

            // 1) Symbol 키로 등록된 provide 값들 탐색
            for (const sym of Object.getOwnPropertySymbols(provides)) {
              const val = provides[sym];
              if (
                val &&
                typeof val === 'object' &&
                val._s instanceof Map
              ) {
                return val;
              }
            }

            // 2) 문자열 키 provide 에 Pinia가 직접 들어가는 케이스 대응
            for (const key of Object.keys(provides)) {
              const val = provides[key];
              if (val && typeof val === 'object' && val._s instanceof Map) {
                return val;
              }
            }

            // 3) window 하위에서 제한적으로 탐색
            const roots = [window, window.n8n, window.app, window.__NUXT__].filter(Boolean);
            const seen = new Set();
            const queue = roots.map((v) => ({ v, d: 0 }));
            while (queue.length) {
              const { v, d } = queue.shift();
              if (!v || typeof v !== 'object' || seen.has(v) || d > 2) continue;
              seen.add(v);
              if (v._s instanceof Map) return v;
              let values = [];
              try {
                values = Object.values(v);
              } catch {
                values = [];
              }
              for (const next of values) {
                if (next && typeof next === 'object') {
                  queue.push({ v: next, d: d + 1 });
                }
              }
            }

            return null;
          };

          // ── Step 2: 현재 라우트 경로 확인 ────────────────────
          const getCurrentPath = (vueApp) => {
            if (!vueApp) return '';
            const provides = vueApp._context?.provides ?? {};
            for (const sym of Object.getOwnPropertySymbols(provides)) {
              const val = provides[sym];
              // Vue Router 인스턴스: currentRoute, push, replace 보유
              if (val && typeof val === 'object' && 'currentRoute' in val && 'push' in val) {
                return val.currentRoute?.value?.path || val.currentRoute?.value?.fullPath || '';
              }
              // 직접 route 객체: path, matched, params 보유
              if (val && typeof val === 'object' && 'path' in val && 'matched' in val) {
                return val.path || val.fullPath || '';
              }
            }
            // fallback: URL에서 직접 추출
            return window.location.pathname;
          };

          // ── Step 3: n8n 워크플로우 스토어 접근 ───────────────
          // n8n v1.x Pinia 스토어 ID 목록 (버전에 따라 다를 수 있음)
          const WORKFLOW_STORE_IDS = [
            'workflows',        // n8n v1.0~v1.4
            'n8n-workflows',    // 구버전
            'workflowStore',    // 일부 빌드
            'workflow',
            'workflow-document',
            'workflowDocument',
            'workflowData',
          ];

          // 워크플로우 데이터가 있는 스토어를 찾는 함수
          const findWorkflowStores = (pinia) => {
            const preferred = [];
            const others = [];

            for (const [id, store] of pinia._s.entries()) {
              if (WORKFLOW_STORE_IDS.includes(id)) preferred.push([id, store]);
              else others.push([id, store]);
            }

            const combined = [...preferred, ...others];
            const scoreStore = (id, store) => {
              if (!store || typeof store !== 'object') return -1;
              let score = 0;
              const idText = String(id || '').toLowerCase();
              if (idText.includes('workflow')) score += 6;
              if (Array.isArray(store.nodes)) score += 6;
              if (store.connections !== undefined) score += 6;
              if (store.workflow && typeof store.workflow === 'object') score += 5;
              if (store.$state && typeof store.$state === 'object') score += 3;
              if (typeof store.getWorkflowData === 'function') score += 4;
              if (typeof store.getCurrentWorkflow === 'function') score += 4;
              return score;
            };

            const scored = [];
            for (const [id, store] of combined) {
              const score = scoreStore(id, store);
              scored.push([id, store, score]);
            }
            scored.sort((a, b) => b[2] - a[2]);
            return scored.map(([id, store]) => [id, store]);
          };

          // ── Step 4: 스토어에서 워크플로우 JSON 추출 ──────────
          const extractWorkflowData = (store, workflowId) => {
            const unref = (v) => {
              if (!v || typeof v !== 'object') return v;
              if ('value' in v) return v.value;
              return v;
            };

            const maybeParseJson = (v) => {
              if (typeof v !== 'string') return v;
              const trimmed = v.trim();
              if (!trimmed.startsWith('{') && !trimmed.startsWith('[')) return v;
              try {
                return JSON.parse(trimmed);
              } catch {
                return v;
              }
            };

            const looksLikeWorkflow = (obj) => {
              const target = maybeParseJson(unref(obj));
              return !!(
                target &&
                typeof target === 'object' &&
                Array.isArray(unref(target.nodes)) &&
                unref(target.connections) !== undefined
              );
            };

            const pick = (obj) => {
              const target = maybeParseJson(unref(obj));
              if (!looksLikeWorkflow(target)) return null;

              const nodes = unref(target.nodes);
              const connections = unref(target.connections);
              const settings = unref(target.settings) || {};

              return {
                id: target.id || unref(store.workflowId) || workflowId || '',
                name: target.name || unref(store.workflowName) || 'Workflow',
                nodes,
                connections,
                settings,
                active: unref(target.active) ?? false,
              };
            };

            // 접근 시도 순서 (n8n 버전에 따라 다름)
            const candidates = [
              // a) store.workflow 직접 객체 (v1.0~)
              store.workflow,
              unref(store.workflow),
              // aa) store.$state 내부
              store.$state,
              store.$state?.workflow,
              store.$state?.workflowData,
              store.$state?.value,
              // b) store.currentWorkflowData
              store.currentWorkflowData,
              store.workflowData,
              store.currentWorkflow,
              unref(store.currentWorkflow),
              store.data,
              store.workflow?.value,
              // c) 노드/연결이 스토어 루트에 있는 경우 조립
              (Array.isArray(unref(store.nodes)) && unref(store.connections) !== undefined)
                ? {
                    id:          workflowId || unref(store.workflowId) || '',
                    name:        unref(store.workflowName) || unref(store.workflow?.name) || 'Workflow',
                    nodes:       unref(store.nodes),
                    connections: unref(store.connections),
                    settings:    unref(store.workflowSettings) || unref(store.workflow?.settings) || {},
                    active:      unref(store.isActive) ?? unref(store.workflow?.active) ?? false,
                  }
                : null,
              // d) getWorkflowData() 메서드
              typeof store.getWorkflowData === 'function' ? store.getWorkflowData() : null,
              typeof store.getCurrentWorkflow === 'function' ? store.getCurrentWorkflow() : null,
              typeof store.getWorkflow === 'function' ? store.getWorkflow() : null,
              // e) toObject() 메서드
              typeof store.toObject === 'function' ? store.toObject() : null,
            ];

            for (const candidate of candidates) {
              const picked = pick(candidate);
              if (picked) {
                return picked;
              }
            }

            // 마지막 fallback: store 전체를 얕게 순회해 workflow 모양 객체 찾기
            const visited = new Set();
            const queue = [store, store?.$state];
            let depth = 0;
            while (queue.length && depth < 4) {
              const size = queue.length;
              for (let i = 0; i < size; i += 1) {
                const cur = queue.shift();
                if (!cur || typeof cur !== 'object' || visited.has(cur)) continue;
                visited.add(cur);

                const picked = pick(cur);
                if (picked) return picked;

                const base = unref(cur);
                const values = (base && typeof base === 'object') ? Object.values(base) : [];
                for (const v of values) {
                  if (v && typeof v === 'object') queue.push(v);
                }
              }
              depth += 1;
            }

            return null;
          };

          // ── 메인 실행 흐름 ────────────────────────────────────
          const vueApp = getVueApp();

          // Vue 앱 없음 → n8n이 아님
          if (!vueApp) {
            return {
              success: false,
              error: 'n8n Vue 앱을 찾을 수 없습니다. 페이지를 새로고침 해보세요.',
              code: 'VUE_APP_NOT_FOUND',
            };
          }

          // 경로 확인 (워크플로우 에디터인지)
          const currentPath = getCurrentPath(vueApp);
          if (!currentPath.includes('/workflow/') && !currentPath.includes('/workflows/')) {
            return {
              success: false,
              error: `워크플로우 편집기 화면이 아닙니다. (현재: ${currentPath || window.location.pathname})\n\nn8n에서 워크플로우를 열고 다시 시도해 주세요.`,
              code: 'NOT_WORKFLOW_EDITOR',
            };
          }

          // Pinia 탐색
          const pinia = getPinia(vueApp);
          if (!pinia) {
            // Pinia 없이 REST API 폴백 경로 안내
            return {
              success: false,
              error: 'Pinia 스토어를 찾을 수 없습니다.',
              fallback: 'clipboard',
              code: 'PINIA_NOT_FOUND',
            };
          }

          // 워크플로우 스토어 탐색
          const workflowStoreEntries = findWorkflowStores(pinia);
          if (!workflowStoreEntries || workflowStoreEntries.length === 0) {
            // 스토어를 못 찾으면 현재 등록된 스토어 ID 목록을 디버그 정보로 반환
            const storeIds = Array.from(pinia._s.keys());
            return {
              success: false,
              error: `워크플로우 스토어를 찾을 수 없습니다. 등록된 스토어: [${storeIds.join(', ')}]`,
              fallback: 'clipboard',
              debug_store_ids: storeIds,
              code: 'WORKFLOW_STORE_NOT_FOUND',
            };
          }

          // 워크플로우 데이터 추출
          let workflowData = null;
          let matchedStoreId = '';
          for (const [storeId, workflowStore] of workflowStoreEntries) {
            const extracted = extractWorkflowData(workflowStore, workflowIdArg);
            if (extracted) {
              workflowData = extracted;
              matchedStoreId = storeId;
              break;
            }
          }

          if (!workflowData) {
            const storeIds = Array.from(pinia._s.keys());
            return {
              success: false,
              error: '등록된 스토어에서 워크플로우 데이터를 추출할 수 없습니다.',
              fallback: 'clipboard',
              debug_store_ids: storeIds,
              code: 'WORKFLOW_DATA_EXTRACT_FAILED',
            };
          }

          // 성공
          return {
            success: true,
            data: JSON.stringify(workflowData),
            method: 'pinia',
            workflow_id: workflowIdArg || workflowData.id || '',
            node_count: workflowData.nodes?.length ?? 0,
            debug_store_id: matchedStoreId,
          };
        },
        args: [workflowId]
      })
      .then(async (results) => {
        const result = results?.[0]?.result;

        if (!result) {
          sendResponse({ success: false, error: 'executeScript 결과가 없습니다.' });
          return;
        }

        // Pinia 성공
        if (result.success) {
          sendResponse(result);
          return;
        }

        // 클립보드/REST API 폴백이 필요한 경우 — 별도 executeScript로 처리
        if (result.fallback === 'clipboard') {
          chrome.scripting.executeScript({
            target: { tabId: tab.id },
            world: 'MAIN',
            func: async (workflowIdArg) => {
              const normalizeWorkflow = (payload) => {
                const candidates = [
                  payload,
                  payload?.data,
                  payload?.workflow,
                  payload?.data?.workflow,
                  payload?.result,
                ];
                for (const c of candidates) {
                  if (c && typeof c === 'object' && Array.isArray(c.nodes) && c.connections !== undefined) {
                    return c;
                  }
                }
                return null;
              };

              const fetchByRestApi = async () => {
                if (!workflowIdArg) return null;
                const endpoints = [
                  `/rest/workflows/${encodeURIComponent(workflowIdArg)}`,
                  `/api/v1/workflows/${encodeURIComponent(workflowIdArg)}`,
                ];

                const failures = [];

                for (const endpoint of endpoints) {
                  try {
                    const resp = await fetch(endpoint, {
                      method: 'GET',
                      credentials: 'include',
                      headers: { Accept: 'application/json' },
                    });
                    if (!resp.ok) {
                      failures.push({ endpoint, status: resp.status });
                      // Unauthorized responses will not recover by repeating the same request.
                      continue;
                    }
                    const json = await resp.json();
                    const workflow = normalizeWorkflow(json);
                    if (workflow) {
                      return {
                        success: true,
                        data: JSON.stringify(workflow),
                        method: 'rest_api',
                        workflow_id: workflow.id || workflowIdArg,
                        node_count: Array.isArray(workflow.nodes) ? workflow.nodes.length : 0,
                      };
                    }
                  } catch {
                    failures.push({ endpoint, status: 'network_error' });
                  }
                }

                return {
                  success: false,
                  code: failures.some((f) => f.status === 401) ? 'REST_401' : 'REST_FAILED',
                  debug_rest_failures: failures,
                };
              };

              const apiResult = await fetchByRestApi();
              if (apiResult?.success) {
                return apiResult;
              }

              return new Promise((resolve) => {
                const canvas = document.querySelector('.canvas-node-renderer, .workflow-canvas, [data-test-id="canvas"], .vue-flow__pane');
                if (canvas) {
                  canvas.setAttribute('tabindex', '-1');
                  canvas.focus();
                  canvas.click();
                }

                // Do not synthesize Cmd/Ctrl+C here.
                // n8n binds copy shortcuts to navigator.clipboard.writeText,
                // which throws when the document is not focused (common from side panel).
                setTimeout(() => {
                  setTimeout(async () => {
                    try {
                      const text = await navigator.clipboard.readText();
                      if (text && text.includes('"nodes"')) {
                        resolve({ success: true, data: text, method: 'clipboard_fallback' });
                      } else {
                        resolve({
                          success: false,
                          error: 'Pinia/REST API 수집 실패. 클립보드에 워크플로우 JSON을 수동 복사(Cmd/Ctrl+C)한 뒤 다시 시도해 주세요.',
                          code: apiResult?.code || 'CLIPBOARD_EMPTY',
                          debug_rest_failures: apiResult?.debug_rest_failures || [],
                        });
                      }
                    } catch (e) {
                      resolve({
                        success: false,
                        error: `클립보드 접근 실패: ${e.message}`,
                        code: apiResult?.code || 'CLIPBOARD_READ_FAILED',
                        debug_rest_failures: apiResult?.debug_rest_failures || [],
                      });
                    }
                  }, 400);
                }, 220);
              });
            },
            args: [workflowId],
          })
          .then(r => sendResponse(r?.[0]?.result || { success: false, error: '클립보드 폴백 실패' }))
          .catch(e => sendResponse({ success: false, error: `클립보드 폴백 오류: ${e.message}` }));
          return;
        }

        // 그 외 실패
        sendResponse(result);
      })
      .catch(e => sendResponse({ success: false, error: `executeScript 오류: ${e.message}` }));
    });
    return true; // 비동기 sendResponse 유지
  }

  // ── Inject workflow JSON into canvas ─────────────────────────
  // n8n's canvas imports nodes on a genuine `paste` ClipboardEvent (the same
  // path used when a user copies node JSON and presses Ctrl/Cmd+V). A
  // synthetic Ctrl+V *keydown* does NOT trigger this — n8n never sees a
  // native paste, so nothing happens. Verified empirically: dispatching a
  // real ClipboardEvent('paste') with a populated DataTransfer reliably
  // imports the nodes, while the old keydown-simulation silently no-ops.
  if (msg.type === 'INJECT_WORKFLOW') {
    findN8nTab((tab) => {
      if (!tab) {
        sendResponse({ success: false, error: 'n8n 탭이 열려있지 않습니다.' });
        return;
      }
      chrome.scripting.executeScript({
        target: { tabId: tab.id },
        func: (jsonStr) => {
          try {
            const target =
              document.querySelector('[data-test-id="canvas"]') ||
              document.querySelector('.vue-flow__pane') ||
              document.body;

            const dt = new DataTransfer();
            dt.setData('text/plain', jsonStr);
            const pasteEvent = new ClipboardEvent('paste', {
              bubbles: true,
              cancelable: true,
              clipboardData: dt,
            });

            // Some builds bind the listener on document/window rather than
            // the canvas node itself — dispatch on all three to be safe.
            target.dispatchEvent(pasteEvent);
            document.dispatchEvent(pasteEvent);
            window.dispatchEvent(pasteEvent);

            // Best-effort: also mirror the payload onto the OS clipboard so
            // a manual Ctrl/Cmd+V by the user works as a fallback.
            navigator.clipboard?.writeText?.(jsonStr).catch(() => {});

            return { success: true, method: 'paste_event' };
          } catch (e) {
            return { success: false, error: e.message };
          }
        },
        args: [msg.payload]
      }).then(r => sendResponse(r?.[0]?.result || { success: false }))
        .catch(e => sendResponse({ success: false, error: e.message }));
    });
    return true;
  }

  // ── 현재 탭 스크린샷 캡처 ────────────────────────────────────
  if (msg.type === 'CAPTURE_SCREENSHOT') {
    // 캡처 대상: n8n 탭 우선, 없으면 현재 활성 탭
    const doCapture = (windowId) => {
      chrome.tabs.captureVisibleTab(
        windowId,
        { format: 'jpeg', quality: 80 },
        (dataUrl) => {
          if (chrome.runtime.lastError || !dataUrl) {
            sendResponse({ success: false, error: chrome.runtime.lastError?.message || '캡처 실패' });
          } else {
            sendResponse({ success: true, dataUrl });
          }
        }
      );
    };

    findN8nTab((tab) => {
      if (tab) {
        doCapture(tab.windowId);
      } else {
        // n8n 탭 없으면 현재 포커스 윈도우 기준 캡처
        chrome.windows.getCurrent((win) => {
          doCapture(win.id);
        });
      }
    });
    return true; // 비동기 sendResponse 유지
  }

  // ── Forward error from content script to side panel ──────────
  if (msg.type === 'N8N_ERROR_DETECTED') {
    chrome.runtime.sendMessage({ type: 'FORWARD_ERROR', error: msg.error }).catch(() => {});
    sendResponse({ ok: true });
    return true;
  }

  // ── 디버그: 현재 n8n Pinia 스토어 ID 목록 반환 ───────────────
  if (msg.type === 'DEBUG_STORE_IDS') {
    findN8nEditorTab((tab) => {
      if (!tab) { sendResponse({ error: 'n8n 탭 없음' }); return; }
      chrome.scripting.executeScript({
        target: { tabId: tab.id },
        world: 'MAIN',
        func: () => {
          const vueApp = document.querySelector('#app')?.__vue_app__;
          if (!vueApp) return { error: 'Vue 앱 없음' };
          const provides = vueApp._context?.provides ?? {};
          for (const sym of Object.getOwnPropertySymbols(provides)) {
            const val = provides[sym];
            if (val?._s instanceof Map && typeof val.install === 'function') {
              const ids = Array.from(val._s.keys());
              const storeDetails = {};
              for (const [id, store] of val._s.entries()) {
                storeDetails[id] = Object.keys(store).filter(k => !k.startsWith('_')).slice(0, 10);
              }
              return { pinia_found: true, store_ids: ids, store_details: storeDetails };
            }
          }
          return { pinia_found: false, symbols_count: Object.getOwnPropertySymbols(provides).length };
        }
      }).then(r => sendResponse(r?.[0]?.result || {}))
        .catch(e => sendResponse({ error: e.message }));
    });
    return true;
  }
});
