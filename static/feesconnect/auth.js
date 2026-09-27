'use strict';
(() => {
  const $ = selector => document.querySelector(selector);
  const kind = document.body.dataset.authScreen;
  const form = $('#auth-form');
  const messages = $('#auth-message');
  const button = form.querySelector('button[type=submit]');
  function show(message, error = false, link) {
    messages.replaceChildren();
    messages.className = 'message' + (error ? ' error' : '');
    messages.textContent = message;
    messages.hidden = false;
    if (link && new URL(link).origin === location.origin) {
      const a = document.createElement('a');
      a.href = link;
      a.textContent = 'Development only: open the verification/reset link';
      messages.append(a);
    }
  }
  document.querySelector('.password-toggle')?.addEventListener('click', event => {
    const input = $('#password');
    const hidden = input.type === 'password';
    input.type = hidden ? 'text' : 'password';
    event.currentTarget.textContent = hidden ? 'Hide' : 'Show';
    event.currentTarget.setAttribute('aria-label', hidden ? 'Hide password' : 'Show password');
  });
  if (location.protocol === 'file:') {
    button.disabled = true;
    form.addEventListener('submit', event => event.preventDefault());
    show('This is the account page preview. Start the websites using the launcher in the package, then open FeesConnect at http://localhost:8081 to create or use your real account.');
    return;
  }
  const actionToken = new URLSearchParams(location.hash.slice(1)).get('token') || '';
  if (actionToken) history.replaceState(null, '', location.pathname);
  if (['verify', 'reset'].includes(kind) && !actionToken) {
    show('Open the complete link in your email. If it expired, request a new link.', true);
    button.disabled = true;
  }
  form.addEventListener('submit', async event => {
    event.preventDefault();
    if (!form.reportValidity()) return;
    button.disabled = true;
    const data = Object.fromEntries(new FormData(form));
    data.agree = data.agree === 'on';
    if (actionToken) data.token = actionToken;
    try {
      const response = await fetch(form.dataset.endpoint, {
        method: 'POST', credentials: 'same-origin',
        headers: {'Content-Type': 'application/json', 'X-FeesConnect-Request': '1'},
        body: JSON.stringify(data)
      });
      if (!response.headers.get('content-type')?.includes('application/json')) {
        throw Error('The account service is unavailable at this address. For local use, start the package launcher and open http://localhost:8081.');
      }
      const result = await response.json();
      if (!response.ok) throw Error(result.error || 'Please try again.');
      if (kind === 'login') { location.assign('account.html'); return; }
      show(result.message, false, result.developmentLink);
      if (['register', 'verify', 'reset'].includes(kind)) form.hidden = true;
      if (['verify', 'reset'].includes(kind)) {
        const a = document.createElement('a');
        a.href = 'login.html'; a.className = 'button'; a.textContent = 'Continue to login';
        messages.append(a);
      }
    } catch (error) {
      show(error instanceof TypeError ? 'We could not reach the account service. Check your connection and that the FeesConnect server is running, then try again.' : error.message, true);
    } finally { button.disabled = false; }
  });
})();
