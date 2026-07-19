/* ---------- scroll reveals ---------- */
const io=new IntersectionObserver(es=>es.forEach(e=>{if(e.isIntersecting){e.target.classList.add('in');io.unobserve(e.target)}}),{threshold:.12});
document.querySelectorAll('.reveal').forEach(el=>io.observe(el));

/* ---------- animated counters ---------- */
const cio=new IntersectionObserver(es=>es.forEach(e=>{
  if(!e.isIntersecting)return;const el=e.target;cio.unobserve(el);
  const end=+el.dataset.count,suf=el.dataset.suffix||'';const t0=performance.now();
  const step=t=>{const p=Math.min((t-t0)/1400,1);el.textContent=Math.round(end*(1-Math.pow(1-p,3)))+suf;if(p<1)requestAnimationFrame(step)};
  requestAnimationFrame(step);
}),{threshold:.5});
document.querySelectorAll('[data-count]').forEach(el=>cio.observe(el));

/* ---------- marquee duplicate ---------- */
const marq=document.getElementById('marq');marq.innerHTML+=marq.innerHTML;

/* ---------- 3D phone tilt ---------- */
const phone=document.getElementById('phone');
const stage=phone.parentElement;
let raf=null;
stage.addEventListener('mousemove',e=>{
  if(matchMedia('(prefers-reduced-motion: reduce)').matches)return;
  const r=stage.getBoundingClientRect();
  const x=(e.clientX-r.left)/r.width-.5,y=(e.clientY-r.top)/r.height-.5;
  if(raf)cancelAnimationFrame(raf);
  raf=requestAnimationFrame(()=>{phone.style.transform=`rotateY(${x*14}deg) rotateX(${-y*10}deg)`});
});
stage.addEventListener('mouseleave',()=>{phone.style.transform='rotateY(-6deg) rotateX(4deg)'});
phone.style.transform='rotateY(-6deg) rotateX(4deg)';

/* ---------- call timer ---------- */
let secs=0;setInterval(()=>{secs++;const m=String(Math.floor(secs/60)).padStart(2,'0'),s=String(secs%60).padStart(2,'0');document.getElementById('timer').textContent=`${m}:${s}`},1000);

/* ---------- conversation loop ---------- */
const chat=document.getElementById('chat'),typing=document.getElementById('typing');
const script=[
  {cls:'agent ar',tag:'Reem · AI',text:'أهلاً بك في عيادة ديفينيا، كيف أقدر أساعدك؟'},
  {cls:'caller',tag:'Caller',text:'أبغى موعد بوتوكس يوم الثلاثاء'},
  {cls:'agent ar',tag:'Reem · AI',text:'أكيد! يناسبك المساء؟ عندنا ٦:٠٠ متاح'},
  {cls:'caller',tag:'Caller',text:'تمام، ٦ المساء'},
  {cls:'agent',tag:'Reem · AI',text:"Perfect — you're booked for Tuesday at 6:00 PM. A confirmation SMS is on its way, and we'll remind you 24 hours before. 💙"},
  {cls:'sms',text:'✓ SMS confirmation sent · Reminder set'}
];
let idx=0,items=[];
function nextMsg(){
  if(idx>=script.length){setTimeout(()=>{items.forEach(el=>el.remove());items=[];idx=0;nextMsg()},4200);return}
  const m=script[idx];
  typing.classList.add('show');chat.appendChild(typing);
  setTimeout(()=>{
    typing.classList.remove('show');
    let el;
    if(m.cls==='sms'){el=document.createElement('div');el.className='sms';el.textContent=m.text}
    else{el=document.createElement('div');el.className='msg '+m.cls;el.innerHTML=`<span class="tag">${m.tag}</span>${m.text}`}
    chat.insertBefore(el,typing);items.push(el);
    requestAnimationFrame(()=>requestAnimationFrame(()=>el.classList.add('show')));
    idx++;setTimeout(nextMsg,600);
  },m.cls==='sms'?500:1100);
}
nextMsg();

/* ---------- FAQ accordion ---------- */
document.querySelectorAll('.qa').forEach(qa=>{
  const btn=qa.querySelector('button'),ans=qa.querySelector('.ans');
  btn.addEventListener('click',()=>{
    const open=qa.classList.contains('open');
    document.querySelectorAll('.qa.open').forEach(o=>{o.classList.remove('open');o.querySelector('.ans').style.maxHeight=null});
    if(!open){qa.classList.add('open');ans.style.maxHeight=ans.scrollHeight+'px'}
  });
});

/* ---------- demo lead modal -> POST /api/v1/leads ---------- */
(function(){
  const modal=document.getElementById('demoModal');
  if(!modal)return;
  const form=document.getElementById('demoForm'),msg=document.getElementById('demoMsg');
  const open=e=>{ if(e)e.preventDefault(); msg.textContent=''; msg.className='msg'; modal.classList.add('open'); };
  const close=()=>modal.classList.remove('open');
  document.querySelectorAll('[data-demo]').forEach(el=>el.addEventListener('click',open));
  document.getElementById('demoClose').addEventListener('click',close);
  modal.addEventListener('click',e=>{ if(e.target===modal)close(); });
  document.addEventListener('keydown',e=>{ if(e.key==='Escape')close(); });

  form.addEventListener('submit',async e=>{
    e.preventDefault();
    const api=(window.ATLASPRIMEX_API||'').replace(/\/$/,'');
    const data={
      name:form.name.value.trim(),
      email:form.email.value.trim(),
      phone:form.phone.value.trim(),
      message:form.message.value.trim(),
      source:'website'
    };
    if(!data.name){ msg.className='msg err'; msg.textContent='Please enter your name.'; return; }
    // No backend configured yet -> fall back to email so the button is never a dead end.
    if(!api){ window.location.href='mailto:hello@atlasprimex.ai?subject=Demo%20request&body='+encodeURIComponent(JSON.stringify(data)); return; }
    msg.className='msg'; msg.textContent='Sending…';
    try{
      const r=await fetch(api+'/api/v1/leads',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
      if(!r.ok)throw new Error('HTTP '+r.status);
      msg.className='msg ok'; msg.textContent='Thanks! We\'ll be in touch shortly.'; form.reset();
    }catch(err){
      msg.className='msg err'; msg.textContent='Could not send right now — email hello@atlasprimex.ai.';
    }
  });
})();
