// Public TV. A stable page refreshes only when data changes; page rotation is independent.
if(q('#tv')){
 document.body.classList.add('tv-mode');let rows=[],highlights=[],playoffs=[],page=0,signature='',ranks=new Map();
 let columnMode='auto';try{columnMode=localStorage.getItem('optimus-tv-columns')||'auto'}catch{}if(!['auto','1','2'].includes(columnMode))columnMode='auto';q('#tv-columns').value=columnMode;
 q('#tv-columns').onchange=()=>{columnMode=q('#tv-columns').value;try{localStorage.setItem('optimus-tv-columns',columnMode)}catch{}page=0;draw(true)};
 function draw(force=false){const filtered=rows.filter(r=>!q('#tv-category').value||r.category===q('#tv-category').value),rowHeight=parseFloat(getComputedStyle(q('#tv')).getPropertyValue('--tv-row-height'))||88,columns=columnMode==='2'?2:columnMode==='1'?1:q('#tv-board').clientWidth>=1100?2:1,perColumn=Math.max(1,Math.floor((q('#tv-board').clientHeight+8)/(rowHeight+8))),size=perColumn*columns,athletePages=Math.max(1,Math.ceil(filtered.length/size)),highlightPages=Math.ceil(highlights.length/size),duels=playoffs.filter(d=>!q('#tv-category').value||d.category===q('#tv-category').value),pages=athletePages+highlightPages+duels.length;q('#tv-board').style.gridTemplateColumns=`repeat(${columns}, minmax(0,1fr))`;q('#tv-board').style.gridTemplateRows=`repeat(${perColumn}, ${rowHeight}px)`;q('#tv').dataset.columns=String(columns);page%=pages;if(page>=athletePages+highlightPages){drawPlayoff(duels[page-athletePages-highlightPages],pages);return}q('#tv').dataset.view=page>=athletePages?'highlights':'athletes';q('#tv-highlight-heading').hidden=page<athletePages;if(page>=athletePages){drawHighlights(size,athletePages,pages);return}const visible=filtered.slice(page*size,(page+1)*size);const next=JSON.stringify(visible)+page+':'+columns+':'+perColumn;if(force||next!==signature){signature=next;q('#tv-board').replaceChildren(...visible.map((r,i)=>{const row=node('div',undefined,'tv-row'+(r.rank===1?' leader':''));row.style.animationDelay=`${i*35}ms`;const identity=node('div',undefined,'tv-athlete'),name=node('div');name.append(node('strong',r.name),node('small',`Número ${String(r.bib).padStart(3,'0')}`));name.append(node('small',r.category,'tv-category-inline'));if(r.tie_pending)name.append(node('small','Empate pendiente'));if(r.champion)name.append(node('small','Primer lugar de categoría'));if(r.tiebreak)name.append(node('small','Desempate: '+r.tiebreak.challenge));const avatar=node('span',undefined,'avatar');if(r.photo_url){const photo=node('img');photo.src=r.photo_url;photo.alt='Foto de '+r.name;photo.addEventListener('error',()=>{avatar.textContent=r.name.split(' ').slice(0,2).map(s=>s[0]).join('')},{once:true});avatar.append(photo)}else avatar.textContent=r.name.split(' ').slice(0,2).map(s=>s[0]).join('');if(r.profile_url){const link=node('a');link.href=r.profile_url;link.append(avatar,name);link.className='tv-person-link';identity.append(link)}else identity.append(avatar,name);const completion=node('div',`${r.completed}/${r.test_count||8}`, 'tv-completion');completion.append(dots(r.completed,r.test_count||8));const score=node('div',fmt(r.total),'tv-score');score.append(node('small','/'+(r.maximum??100)));const rank=node('div',r.attendance==='disqualified'?'DQ':r.rank??'—','tv-rank');const previous=ranks.get(r.id);if(previous&&r.rank&&previous>r.rank){name.append(node('small',`↑ ${previous-r.rank} posición${previous-r.rank>1?'es':''}`))}ranks.set(r.id,r.rank);row.append(rank,identity,node('div',r.category,'tv-category'),completion,score);return row}));if(!visible.length)q('#tv-board').append(node('div','Las primeras posiciones aparecerán aquí.','empty-state'))}q('#tv-page').textContent=`${String(page+1).padStart(2,'0')} / ${String(pages).padStart(2,'0')} · ${filtered.length} atletas`}
 function drawHighlights(size,athletePages,pages){
  signature='';
  const visible=highlights.slice((page-athletePages)*size,(page-athletePages+1)*size);
  q('#tv-board').replaceChildren(...visible.map(record=>{
   const row=node('div',undefined,'tv-highlight-row'+(record.kind==='overall'?' tv-highlight-overall':''));
   const station=node('div',undefined,'tv-highlight-station');
   station.append(node('small',record.kind==='overall'?'ACUMULADO':'MEJOR MARCA'),node('strong',record.title));
   const athlete=node('div',undefined,'tv-highlight-athlete');
   athlete.append(node('strong',record.name),node('small',`#${String(record.bib).padStart(3,'0')} · ${record.category}`));
   const value=node('div',fmt(record.value),'tv-highlight-value');value.append(node('small',record.unit));
   row.append(station,athlete,value);return row;
  }));
  q('#tv-page').textContent=`${String(page+1).padStart(2,'0')} / ${String(pages).padStart(2,'0')} · Mejores marcas del evento`;
 }
 function drawPlayoff(duel,pages){
  q('#tv').dataset.view='playoffs';q('#tv-highlight-heading').hidden=true;
  q('#tv-board').style.gridTemplateColumns='1fr';q('#tv-board').style.gridTemplateRows='minmax(0,1fr)';
  const next=JSON.stringify(duel)+page;if(next===signature)return;signature=next;
  const stage=node('section',undefined,'tv-showdown'),heading=node('div',undefined,'tv-showdown-heading');
  heading.append(node('small',duel.status==='resolved'?'PRIMER LUGAR DECIDIDO':duel.status==='pending'?'IGUALES EN PUNTOS · UN SOLO PRIMER LUGAR':'DESEMPATE EN VIVO'),node('h2',duel.category),node('p',duel.test));
  const arena=node('div',undefined,'tv-showdown-arena');
  duel.players.forEach((player,index)=>{
   if(index)arena.append(node('div','VS','tv-showdown-vs'));
   const winner=duel.winner===player.id,card=node('article',undefined,'tv-contender'+(winner?' winner':''));
   const portrait=node('div',undefined,'tv-contender-portrait');
   if(player.photo_url){const photo=node('img');photo.src=player.photo_url;photo.alt=player.name;portrait.append(photo)}else portrait.append(node('span',player.name.split(' ').slice(0,2).map(s=>s[0]).join('')));
   const identity=node('div',undefined,'tv-contender-identity');identity.append(node('small','#'+String(player.bib).padStart(3,'0')),node('h3',player.name));
   const score=node('div',player.value===null?'—':String(player.value),'tv-contender-score');score.append(node('small',winner?'GANADOR':player.value===null?'POR CAPTURAR':duel.unit));
   card.append(portrait,identity,score);arena.append(card);
  });
  const caption=duel.status==='resolved'?'El desempate decide el primer lugar · Puntajes generales intactos':duel.status==='tied'?'Continúa el empate · Se prepara otra prueba':duel.target?'Primero en llegar a '+duel.target+' victorias':duel.status==='pending'?fmt(duel.total)+' puntos · A la espera de la prueba':'La marca de desempate no suma al acumulado';
  stage.append(heading,arena,node('div',caption,'tv-showdown-caption'));q('#tv-board').replaceChildren(stage);
  q('#tv-page').textContent=`${String(page+1).padStart(2,'0')} / ${String(pages).padStart(2,'0')} · Desempates`;
 }
 async function poll(){try{const d=await jsonFetch(q('#tv').dataset.source,{cache:'no-store'});highlights=d.highlights||[];playoffs=d.playoffs||[];rows=d.board.slice().sort((a,b)=>a.category.localeCompare(b.category,'es')||(a.rank??Infinity)-(b.rank??Infinity)||b.total-a.total||a.bib-b.bib);q('#tv-test').textContent=d.active_stations?.length?d.active_stations.map(s=>s.name).join(' · '):d.active_stations?'Sin estaciones abiertas':d.test;q('#tv-status').textContent=d.phase==='closed'?'RESULTADOS FINALES':d.phase!=='live'?'EN ESPERA DE INICIO':d.relative_scoring?'PROVISIONALES · RELATIVOS':'EN VIVO';q('#tv-updated').textContent='Última consulta '+new Date(d.updated).toLocaleTimeString('es-MX',{hour:'2-digit',minute:'2-digit',second:'2-digit'});draw()}catch{q('#tv-status').textContent='SIN CONEXIÓN';q('#tv-updated').textContent='Mostrando última actualización disponible'}finally{setTimeout(poll,5000)}}q('#tv-category').onchange=()=>{page=0;ranks.clear();draw(true)};q('#fullscreen').onclick=async()=>{try{if(document.fullscreenElement)await document.exitFullscreen();else if(q('#tv').requestFullscreen)await q('#tv').requestFullscreen();else toast('Este navegador no permite pantalla completa.')}catch{toast('No se pudo abrir pantalla completa.')}};document.addEventListener('fullscreenchange',()=>draw(true));window.addEventListener('resize',()=>draw(true));setInterval(()=>{page++;draw(true)},10000);function clock(){q('#tv-clock').textContent=new Date().toLocaleTimeString('es-MX',{hour:'2-digit',minute:'2-digit'})}clock();setInterval(clock,1000);poll();
}

