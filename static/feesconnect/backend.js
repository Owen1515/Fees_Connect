/* Payment status comes from Django; redirects never decide success. */
(() => {
  const poll = document.querySelector('[data-payment-poll]');
  if (poll) {
    let tries = 0;
    const update = async () => {
      try {
        const response = await fetch(poll.dataset.paymentPoll, {credentials: 'same-origin'});
        if (!response.ok) throw new Error('Status unavailable');
        const data = await response.json();
        if (data.complete) { window.location.assign(data.url); return; }
        if (data.redirect_url) {
          const link = document.getElementById('provider-link');
          const url = new URL(data.redirect_url);
          if (url.protocol === 'https:') { link.href = url.href; link.hidden = false; }
        }
      } catch (_) { document.getElementById('payment-note').textContent = 'Status is temporarily unavailable. Your payment is still being checked.'; }
      if (++tries < 120) window.setTimeout(update, 5000);
      else document.getElementById('payment-note').textContent = 'You can safely return to payment history later.';
    };
    update();
  }
  const chat = document.getElementById('backend-chat');
  let conversation = null;
  if (chat) chat.addEventListener('submit', async (event) => {
    event.preventDefault();
    const button = chat.querySelector('button'); button.disabled = true;
    const body = {message: chat.elements.message.value, request_id: crypto.randomUUID()};
    if (conversation) body.conversation_id = conversation;
    try {
      const response = await fetch(chat.dataset.endpoint, {method:'POST',credentials:'same-origin',
        headers:{'Content-Type':'application/json','X-CSRFToken':chat.elements.csrfmiddlewaretoken.value},body:JSON.stringify(body)});
      if (!response.ok) throw new Error('Support unavailable');
      const data = await response.json(); conversation = data.conversation_id;
      document.getElementById('chat-response').textContent = data.reply;
    } catch (_) { document.getElementById('chat-response').textContent = 'Please use the support request form below.'; }
    finally { button.disabled = false; }
  });
})();
