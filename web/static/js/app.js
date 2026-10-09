function renderChart(id, url, type='line') {
  fetch(url).then(r=>r.json()).then(spec=>{
    const ctx=document.getElementById(id);
    if(!ctx) return;
    new Chart(ctx, spec);
  }).catch(()=>{});
}

window.addEventListener('load', ()=>{
  renderChart('chartUsage','/api/metrics/charts/usage?interval=1h','line');
  renderChart('chartTokens','/api/metrics/charts/tokens?interval=1h','line');
  renderChart('chartStorage','/api/metrics/charts/storage','doughnut');
  renderChart('chartDuration','/api/metrics/charts/duration?interval=1h','line');
  renderChart('chartCache','/api/metrics/charts/cache?interval=1h','bar');
  renderChart('chartOps','/api/metrics/charts/ops','pie');
});

htmx.on('htmx:afterRequest', function(evt){
  if(evt.detail.elt.id==='sessions'){
    try{
      const data=JSON.parse(evt.detail.xhr.response);
      const el=document.getElementById('sessions');
      el.innerHTML = (data.sessions||[]).slice(0,30).map(s=>`<div class="session-item" onclick="loadMsgs(${s.id})">${s.id}: ${s.title||''} [${s.state}]</div>`).join('');
    }catch(e){}
  }
});

window.loadMsgs = function(sid){
  fetch(`/api/chat/sessions/${sid}/messages`).then(r=>r.json()).then(d=>{
    const el=document.getElementById('messages');
    el.innerHTML = (d.messages||[]).map(m=>`<div class="msg ${m.role}"><b>${m.role}</b>: ${m.content}</div>`).join('');
  });
};

fetch('/api/storage/overview').then(r=>r.json()).then(d=>{
  document.getElementById('storageOverview').textContent = JSON.stringify(d,null,2);
});
fetch('/api/storage/tree?limit=60').then(r=>r.json()).then(d=>{
  document.getElementById('storageTree').textContent = JSON.stringify(d.items||[],null,2);
});
