'use strict';
(function () {
  const frame = document.getElementById('frame');
  const offline = document.getElementById('offline');

  frame.addEventListener('error', () => {
    frame.style.display = 'none';
    offline.style.display = 'flex';
  });

  const timer = setTimeout(() => {
    frame.style.display = 'none';
    offline.style.display = 'flex';
  }, 5000);

  frame.addEventListener('load', () => {
    clearTimeout(timer);
    frame.style.display = 'block';
    offline.style.display = 'none';
  });
})();
