/* Pure demo-domain functions. No live payment, verification or banking calls. */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.FeesConnectCore = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  const schools = [
    { id:'mazowe', name:'Mazowe High School', location:'Mazowe', country:'Zimbabwe' },
    { id:'faith', name:'St Faith Primary School', location:'Harare', country:'Zimbabwe' },
    { id:'prince', name:'Prince Edward School', location:'Harare', country:'Zimbabwe' },
    { id:'churchill', name:'Churchill School', location:'Harare', country:'Zimbabwe' },
    { id:'peterhouse', name:'Peterhouse Boys School', location:'Marondera', country:'Zimbabwe' }
  ];
  const stages = ['awaiting-transfer','submitted','settled','allocated'];
  const statusNames = { 'awaiting-transfer':'Awaiting demo transfer', submitted:'Order submitted', settled:'Settlement recorded', allocated:'Allocated to pupil' };
  const feeCents = 499;
  function money(cents, currency='USD') {
    return new Intl.NumberFormat('en-GB',{style:'currency',currency,minimumFractionDigits:2}).format(cents/100);
  }
  function parseAmount(input, maximum=65000) {
    const value = String(input).trim();
    if (!/^\d+(?:\.\d{1,2})?$/.test(value)) throw new Error('Enter an amount with no more than two decimal places.');
    const [whole, decimals=''] = value.split('.');
    const cents = Number(whole)*100 + Number(decimals.padEnd(2,'0'));
    if (!Number.isSafeInteger(cents) || cents < 100) throw new Error('The minimum demo amount is US$1.00.');
    if (cents > maximum) throw new Error('Enter an amount no greater than '+money(maximum)+'.');
    return cents;
  }
  function quote(cents) {
    if (!Number.isSafeInteger(cents) || cents < 100) throw new Error('A valid amount in cents is required.');
    const base = Math.round(cents*10/13);
    return {usdCents:cents, baseCents:base, feeCents, totalCents:base+feeCents, rate:'1 GBP = 1.3000 USD'};
  }
  function invoiceId(schoolId, pupilId) { return 'TERM3:'+schoolId+':'+pupilId.trim().toUpperCase(); }
  function balances(records, invoice) {
    const rows = records.filter(r=>r.invoiceId===invoice);
    const allocated = rows.filter(r=>r.status==='allocated').reduce((s,r)=>s+r.usdCents,0);
    const pending = rows.filter(r=>r.status!=='allocated').reduce((s,r)=>s+r.usdCents,0);
    return {invoiceCents:65000, allocated, pending, outstanding:Math.max(0,65000-allocated), available:Math.max(0,65000-allocated-pending)};
  }
  function validateDraft(draft, records, step=4) {
    if (!schools.some(s=>s.id===draft.schoolId && s.country===draft.country)) throw new Error('Choose a school from the selected country.');
    if (step>=2) {
      if (!draft.pupil.trim() || draft.pupil.trim().length>80) throw new Error('Enter a sample pupil name, up to 80 characters.');
      if (!/^[A-Za-z0-9-]{3,30}$/.test(draft.pupilId.trim())) throw new Error('Enter a sample pupil reference using 3–30 letters, numbers or hyphens.');
      if (!['Parent','Guardian','Sibling','Other'].includes(draft.relationship)) throw new Error('Select your relationship to the pupil.');
    }
    if (step>=3) {
      const balance=balances(records,invoiceId(draft.schoolId,draft.pupilId));
      parseAmount(draft.amount,balance.available);
      if (!['card','bank'].includes(draft.method)) throw new Error('Choose a demo payment method.');
    }
    return true;
  }
  function nextStatus(status) {
    const i=stages.indexOf(status);
    if (i<0) throw new Error('Unknown payment status.');
    return stages[Math.min(i+1,stages.length-1)];
  }
  function searchSchools(country, query) {
    const q=query.trim().toLowerCase();
    return schools.filter(s=>s.country===country && (s.name+' '+s.location).toLowerCase().includes(q));
  }
  function supportAnswer(question, context='dashboard') {
    const q=question.toLowerCase();
    if (/\b(cvv|cvc|password|pin|otp)\b/.test(q) || /(?:\d[ -]?){12,19}/.test(q)) return {topic:'privacy',text:'Please do not share passwords, card numbers, security codes or pupil details here. This chat provides general guidance only. You can clear the conversation using the button below.'};
    if (/human|person|agent|contact|call|email/.test(q)) return {topic:'human',text:'Live support is not connected in this preview, and I cannot create or send a support ticket. For a real school-payment issue, use contact details you already know for your school. You can download this conversation to share later.'};
    if (/refund|cancel|chargeback|duplicate|twice/.test(q)) return {topic:'refund',text:'Do not make a second payment to resolve an unclear status. Check the reference and ask the school or your payment provider about the existing payment. I cannot cancel, refund or reverse payments. The demo does not move money.'};
    if (/status|track|pending|settle|allocat|confirm|missing|fail|delay/.test(q)) return {topic:'status',text:'Open Payment activity and choose an order. Its record separates the payment order, settlement and allocation to the pupil. An order submitted is not the same as school allocation. In this preview, “Advance demo status” lets you explore these stages; it does not confirm real funds.',action:'activity',label:'Open payment activity'};
    if (/fee|rate|exchange|currency|gbp|usd|cost/.test(q)) return {topic:'fees',text:'The preview uses an illustrative rate of 1 GBP = 1.3000 USD and a £4.99 example fee, taken from the supplied template. These are not live rates or an approved price offer. The review shows the USD amount, converted GBP amount, fee and total before a demo order is created.'};
    if (/receipt|download|print|export/.test(q)) return {topic:'receipt',text:'Open a payment in Payment activity, then use “Download demo record” or “Print record”. Each record retains its own pupil, school, amount, date and reference. Demo records are clearly labelled and are not proof of payment.',action:'activity',label:'Find a record'};
    if (/partial|custom|amount|balance/.test(q)) return {topic:'amount',text:'In Amount & method, choose the available example balance or enter a custom amount of at least US$1.00. You cannot exceed the amount available for that demo invoice. Pending demo orders are shown separately so you do not reserve the same amount twice.',action:'pay',label:'Open payment flow'};
    if (/school|country|directory|south africa|zambia/.test(q)) return {topic:'school',text:'The directory contains example Zimbabwe school listings from the original template. No school is connected or verified here. South Africa and Zambia currently show an empty directory rather than the wrong schools. For live balances, pupil verification and supported schools, a school integration is required.',action:'schools',label:'Browse sample directory'};
    if (/pupil|student|learner|verif/.test(q)) return {topic:'pupil',text:'The pupil step links a sample name and reference to the selected school. It does not verify enrolment or retrieve school records. Use sample information only. The same school and pupil reference identify the same demo invoice.'};
    if (/bank|card|transfer/.test(q)) return {topic:'method',text:'The template lets you compare a simulated card flow and a simulated bank-transfer flow. It never asks for a real card number or shows bank details to send money to. A bank-transfer demo order begins at “Awaiting demo transfer”.'};
    if (/login|log in|sign|account|profile|save|privacy|data/.test(q)) return {topic:'account',text:'Use the profile button to change your demo display name or reset the preview. This is not a registered account. Sample activity and drafts stay in this browser tab using session storage; chat stays in memory. End the demo session to clear both. No information is sent to a support service.'};
    if (/start|pay|payment|how|help|hello|hi\b/.test(q)) return {topic:'start',text:context==='pay'?'You are in the payment flow. Choose a school, add sample pupil details, review the amount and method, then check the complete order. Your draft is retained in this tab when you visit another section.':'Choose “Make a payment”. The four steps connect the school, pupil, amount and payment order. Review the example fee and total, then create a demo order. No real payment is taken.',action:'pay',label:'Make a demo payment'};
    return {topic:'fallback',text:'I can help with the payment steps, sample school directory, fees, tracking, receipts and demo privacy. I do not have access to live accounts or general-purpose AI. Try one of the suggested topics, or ask “How can I speak to a person?”'};
  }
  return {schools,stages,statusNames,feeCents,money,parseAmount,quote,invoiceId,balances,validateDraft,nextStatus,searchSchools,supportAnswer};
});
