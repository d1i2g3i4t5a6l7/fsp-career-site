function ScoreNum({v,size=28}){return <span className="pix" style={{fontSize:size,lineHeight:1,color:v>=80?'var(--fg-1)':'var(--fg-2)'}}>{v}</span>;}
function inviteOf(invites,id){return invites.find(i=>i.cand===id&&i.company===D.COMPANY.name);}

function CandRow({c,s,rank,need,invites,onOpen,onInvite,starred,onStar}){
  const inv=inviteOf(invites,c.id);
  return <div className="crow" onClick={()=>onOpen(c)}>
    <div className="crow-rank">{String(rank).padStart(2,'0')}</div>
    <div className="stack-8" style={{minWidth:0}}>
      <div className="row-12" style={{flexWrap:'wrap'}}><b style={{fontSize:15}}>{c.name}</b><span className="hint">{D.catLabel(c)} · {c.exp} г. · {c.city}</span>{c.id==='me'&&<ATag>вы</ATag>}</div>
      <ul className="why">{s.reasons.slice(0,2).map(r=><li key={r}>{r}</li>)}</ul>
    </div>
    <div className="crow-score"><ScoreNum v={s.total}/><Bar value={s.total} h={4}/></div>
    <div className="crow-act" onClick={e=>e.stopPropagation()}>
      <button className={'star'+(starred?' on':'')} onClick={()=>onStar(c.id)} title="В избранное">{starred?'★':'☆'}</button>
      {inv?<Status s={inv.status}/>:<Button size="sm" onClick={()=>onInvite(c)}>Пригласить</Button>}
    </div>
  </div>;
}

function useRanked(need,{fspWeight=true,filter=()=>true}={}){
  return React.useMemo(()=>D.CANDIDATES.filter(filter).map(c=>({c,s:D.score(c,need,{fsp:fspWeight})})).sort((a,b)=>b.s.total-a.s.total),[need,fspWeight,filter]);
}

function NeedBar({need,go}){
  return <div className="needbar">
    <div className="row-12" style={{flexWrap:'wrap',minWidth:0}}><span className="cap">Потребность</span><b>{need.title}</b></div>
    <div className="row-12" style={{flexWrap:'wrap'}}><ATag>{D.specLabel(need.spec)} · {D.gradeLabel(need.grade)}</ATag>{need.stack.map(s=><Tag key={s}>{s}</Tag>)}<span className="salary-sm">{D.rub(need.salaryFrom,need.salaryTo)}</span><Button variant="ghost" size="sm" onClick={()=>go('need')}>Изменить</Button></div>
  </div>;
}

const REFINE=[['fsp','Есть достижения ФСП'],['expert','Подтверждено экспертом'],['remote','Готов к удалёнке'],['fresh','Активен за 7 дней']];
function refineFn(r){return c=>(!r.fsp||c.fsp.length)&&(!r.expert||c.expert)&&(!r.remote||c.format==='Удалённо')&&(!r.fresh||c.fresh<=7);}

function Shortlist({variant:initV='A',need,invites,openCand,openInvite,stars,toggleStar,go,me}){
  const [variant,setVariant]=React.useState(()=>{try{return localStorage.getItem('fspk_view')||initV}catch(e){return initV}});
  const pickV=v=>{setVariant(v);try{localStorage.setItem('fspk_view',v)}catch(e){}};
  const [cat,setCat]=React.useState(need.spec+'|'+need.grade);
  const [ref,setRef]=React.useState({});
  // «Вы» — с грейдом и баллом из своих тестов; без подтверждённого грейда в подборку не попадаете
  const meFix=c=>c.id==='me'?me:c;
  const cats=React.useMemo(()=>{
    const g=D.GRADES.map(x=>x.id);const gi=g.indexOf(need.grade);
    const list=[{spec:need.spec,grade:need.grade,note:'Точное совпадение',n:38}];
    if(gi<g.length-1)list.push({spec:need.spec,grade:g[gi+1],note:'Выше бюджета на 30–60%',n:12});
    if(gi>0)list.push({spec:need.spec,grade:g[gi-1],note:'Под рост, ниже бюджета',n:24});
    list.push({spec:need.spec==='backend'?'data':'backend',grade:need.grade,note:'Смежная: пересечение стека',n:9});
    return list;},[need]);
  const [cs,cg]=cat.split('|');
  const all=D.CANDIDATES.map(meFix).filter(c=>c.grade);
  const pool=all.filter(c=>c.spec===cs&&c.grade===cg).filter(refineFn(ref)).map(c=>({c,s:D.score(c,need)})).sort((a,b)=>b.s.total-a.s.total);
  const p={need,invites,onOpen:openCand,onInvite:openInvite};
  const refineBar=<div className="row-12" style={{flexWrap:'wrap'}}><span className="cap">Уточнить</span>{REFINE.map(([k,l])=><Chip key={k} small on={ref[k]} onClick={()=>setRef(r=>({...r,[k]:!r[k]}))}>{l}</Chip>)}{Object.values(ref).some(Boolean)&&<Button variant="ghost" size="sm" onClick={()=>setRef({})}>Сбросить</Button>}<span className="hint" style={{marginLeft:'auto'}}>★ избранное: {stars.length}</span></div>;
  return <div className="page">
    <PageHead eyebrow="// подборка" title="Подборка кандидатов" sub="Категории — по итогам теста, внутри — рейтинг по вашей потребности." action={<div className="role-sw" style={{margin:0,gridTemplateColumns:'repeat(3,1fr)',minWidth:300}} role="group" aria-label="Вид подборки">{[['A','Рейтинг'],['B','Таблица'],['C','Досье']].map(([k,l])=><button key={k} className={variant===k?'on':''} aria-pressed={variant===k} onClick={()=>pickV(k)}>{l}</button>)}</div>}/>
    <NeedBar need={need} go={go}/>
    {variant==='A'&&<div className="sl-a">
      <div className="panel" style={{alignSelf:'start'}}>
        <div className="panel-h"><div className="panel-t">Категории</div></div>
        {cats.map(k=>{const id=k.spec+'|'+k.grade;return <button key={id} className={'cat-i'+(cat===id?' on':'')} onClick={()=>setCat(id)}>
          <div className="row-12" style={{justifyContent:'space-between'}}><b>{D.specLabel(k.spec)} · {D.gradeLabel(k.grade)}</b><span className="num">{k.n}</span></div><span className="hint">{k.note}</span></button>})}
      </div>
      <div className="stack-16">
        {refineBar}
        <div className="panel">{pool.length?pool.map((x,i)=><CandRow key={x.c.id} {...p} c={x.c} s={x.s} rank={i+1} starred={stars.includes(x.c.id)} onStar={toggleStar}/>):<div style={{padding:24}}><Empty title="Никого не осталось" text="Ослабьте уточнения — подборка сохранится."/></div>}</div>
      </div>
    </div>}
    {variant==='B'&&<ShortlistTable pool={pool} cats={cats} cat={cat} setCat={setCat} refineBar={refineBar} {...p} stars={stars} toggleStar={toggleStar}/>}
    {variant==='C'&&<div className="stack-16">
      <div className="tabs">{cats.map(k=>{const id=k.spec+'|'+k.grade;return <button key={id} className={cat===id?'on':''} onClick={()=>setCat(id)}>{D.specLabel(k.spec)} · {D.gradeLabel(k.grade)} <span className="hint">{k.n}</span></button>})}</div>
      {refineBar}
      <div className="cards-3">{pool.map((x,i)=><DossierCard key={x.c.id} {...p} c={x.c} s={x.s} rank={i+1} starred={stars.includes(x.c.id)} onStar={toggleStar}/>)}</div>
    </div>}
  </div>;
}

function ShortlistTable({pool,cats,cat,setCat,refineBar,need,invites,onOpen,onInvite,stars,toggleStar}){
  const [sort,setSort]=React.useState('total');const [sel,setSel]=React.useState([]);
  const key={total:x=>x.s.total,test:x=>x.c.test,stack:x=>x.s.overlap.length,fsp:x=>x.s.parts.fsp,fresh:x=>-x.c.fresh};
  const rows=[...pool].sort((a,b)=>key[sort](b)-key[sort](a));
  const H=({k,children})=><th onClick={()=>setSort(k)} className={'sortable'+(sort===k?' on':'')}>{children}{sort===k?' ▼':''}</th>;
  return <div className="stack-16">
    <div className="row-12" style={{flexWrap:'wrap'}}><span className="cap">Категория</span><Select value={cat} onChange={setCat} options={cats.map(k=>({id:k.spec+'|'+k.grade,label:`${D.specLabel(k.spec)} · ${D.gradeLabel(k.grade)} — ${k.n} · ${k.note}`}))} style={{width:'auto',minWidth:340}}/>
      {sel.length>0&&<><span className="hint">выбрано: {sel.length}</span><Button size="sm" onClick={()=>onInvite(pool.find(x=>x.c.id===sel[0]).c)}>Пригласить выбранных</Button></>}</div>
    {refineBar}
    <div className="panel" style={{overflowX:'auto'}}><table className="tbl">
      <thead><tr><th></th><th>#</th><th>Кандидат</th><H k="total">Итог</H><H k="test">Тест</H><H k="stack">Стек</H><H k="fsp">ФСП</H><H k="fresh">Активность</H><th>Ожидания</th><th></th></tr></thead>
      <tbody>{rows.map((x,i)=>{const c=x.c,inv=inviteOf(invites,c.id);return <tr key={c.id} onClick={()=>onOpen(c)}>
        <td onClick={e=>e.stopPropagation()}><input type="checkbox" checked={sel.includes(c.id)} onChange={()=>setSel(s=>s.includes(c.id)?s.filter(v=>v!==c.id):[...s,c.id])}/></td>
        <td className="num">{i+1}</td>
        <td><b>{c.name}</b><div className="hint">{c.city} · {c.exp} г.</div></td>
        <td><div className="row-12"><span className="num" style={{fontSize:18,fontWeight:700}}>{x.s.total}</span><div style={{width:60}}><Bar value={x.s.total} h={4}/></div></div></td>
        <td><span className="num">{c.test}</span>{c.expert?<span className="ok-dot" title="Подтверждено экспертом">✓</span>:<span className="hint"> ИИ</span>}</td>
        <td>{x.s.overlap.length}/{need.stack.length}<div className="hint">{x.s.overlap.join(', ')||'—'}</div></td>
        <td>{c.fsp.length?<FspBadge fsp={c.fsp} compact/>:<span className="hint">—</span>}</td>
        <td>{c.fresh} дн.</td>
        <td className="hint" style={{whiteSpace:'nowrap'}}>{c.want}</td>
        <td onClick={e=>e.stopPropagation()}><div className="row-12"><button className={'star'+(stars.includes(c.id)?' on':'')} onClick={()=>toggleStar(c.id)}>{stars.includes(c.id)?'★':'☆'}</button>{inv?<Status s={inv.status}/>:<Button size="sm" variant="secondary" onClick={()=>onInvite(c)}>Пригласить</Button>}</div></td>
      </tr>})}</tbody></table></div>
    <div className="hint">Итог = тест 45 · стек 25 · ФСП 15 · активность 10 · экспертная проверка 5. Нажмите на заголовок колонки, чтобы пересортировать.</div>
  </div>;
}

function DossierCard({c,s,rank,need,invites,onOpen,onInvite,starred,onStar}){
  const inv=inviteOf(invites,c.id);
  return <div className="dossier" onClick={()=>onOpen(c)}>
    <div className="row-12" style={{justifyContent:'space-between',alignItems:'flex-start'}}>
      <div><span className="cap">#{rank} в категории</span><div style={{fontWeight:700,fontSize:18,marginTop:4}}>{c.name}</div><div className="hint">{c.exp} г. · {c.city} · {c.format}</div></div>
      <div style={{textAlign:'right'}}><ScoreNum v={s.total} size={48}/><div className="hint">из 100</div></div>
    </div>
    <div className="chips">{c.stack.map(t=><span key={t} className={'stk'+(need.stack.includes(t)?' hit':'')}>{t}</span>)}</div>
    <div className="dossier-parts">{[['Тест',c.test+(c.expert?' ✓':' ИИ')],['ФСП',c.fsp.length?c.fsp[0].place:'—'],['Активность',c.fresh+' дн.']].map(([k,v])=><div key={k}><span className="cap">{k}</span><span style={{fontSize:13}}>{v}</span></div>)}</div>
    <div className="hint" style={{minHeight:36}}>{s.reasons[1]}</div>
    <div className="row-12" style={{justifyContent:'space-between'}} onClick={e=>e.stopPropagation()}>
      <button className={'star'+(starred?' on':'')} onClick={()=>onStar(c.id)}>{starred?'★':'☆'}</button>
      {inv?<Status s={inv.status}/>:<Button size="sm" onClick={()=>onInvite(c)}>Пригласить</Button>}</div>
  </div>;
}

function CandDrawer({c,need,invites,onClose,onInvite}){
  const s=D.score(c,need);const inv=inviteOf(invites,c.id);const open=inv&&inv.status==='accepted';
  return <Drawer onClose={onClose} width={600}>
    <div className="panel-h" style={{position:'sticky',top:0,background:'var(--bg-surface)',zIndex:2}}><div><div className="eyebrow">{D.catLabel(c)}</div><div className="panel-t">{c.name}</div></div><button className="x" onClick={onClose}>×</button></div>
    <div className="stack-24" style={{padding:24}}>
      <div className="row-12" style={{justifyContent:'space-between',alignItems:'flex-end'}}>
        <div><span className="cap">Соответствие потребности</span><div className="pix" style={{fontSize:72,lineHeight:1}}>{s.total}</div></div>
        {inv?<div className="stack-8" style={{alignItems:'flex-end'}}><Status s={inv.status}/><span className="hint">{D.rub(inv.from,inv.to)}</span></div>:<Button onClick={()=>onInvite(c)}>Пригласить</Button>}
      </div>
      <div className="stack-12"><div className="cap">Почему в подборке</div>
        {[['Тест',s.parts.test,45],['Стек',s.parts.stack,25],['ФСП',s.parts.fsp,15],['Активность',s.parts.fresh,10],['Эксперт',s.parts.expert,5]].map(([k,v,m])=><div key={k} className="eval-row"><span style={{fontSize:13}}>{k}</span><Bar value={v} max={m}/><span className="num">{Math.round(v)}/{m}</span></div>)}</div>
      <div className="stack-12"><div className="cap">Тест на {D.gradeLabel(c.grade)} · «{D.TASK.title}»</div>
        <div className="row-12"><Tag tone="neutral">ИИ {Math.max(60,c.test-4)}</Tag><span className="hint">→</span>{c.expert?<Tag discipline="security">Эксперт {c.test}</Tag>:<Tag>ждёт эксперта</Tag>}</div>
        <details><summary className="hint" style={{cursor:'pointer'}}>Показать решение</summary><pre className="code-sm" style={{maxHeight:180,overflow:'auto',marginTop:8}}>{D.TASK.code}</pre></details></div>
      <div className="stack-12"><div className="cap">Достижения ФСП</div><FspBadge fsp={c.fsp}/>{!c.fsp.length&&<div className="hint">Кандидат не участвовал в соревнованиях ФСП. Рейтинг основан на тесте и заданиях.</div>}</div>
      <div className="grid-2"><Kv k="Стек" v={c.stack.join(', ')}/><Kv k="Опыт" v={c.exp+' г.'}/><Kv k="Формат" v={c.format}/><Kv k="Ожидания" v={c.want+' ₽'}/><Kv k="Регулярные задания" v={c.tasks+' решено'}/><Kv k="Город" v={c.city}/></div>
      <div className={'note'+(open?' ok':'')}>{open?<>Контакты открыты: <b>{c.id==='me'?'a.korneev@mail.ru · +7 917 000-12-34':c.id+'@mail.ru · +7 900 000-00-00'}</b></>:'Контакты скрыты. Откроются, когда кандидат примет приглашение или откликнется сам.'}</div>
    </div>
  </Drawer>;
}

function InviteModal({c,need,onClose,onSend}){
  const [f,setF]=React.useState({vac:'',title:need.title,msg:'',from:String(need.salaryFrom),to:String(need.salaryTo),format:need.format,contact:D.COMPANY.contact});
  const set=k=>e=>setF(o=>({...o,[k]:e.target?e.target.value:e}));
  const a=+f.from.replace(/\D/g,''),b=+f.to.replace(/\D/g,'');
  const err=!a||!b?'Укажите зарплату «от» и «до» — это обязательно':a>b?'«От» больше, чем «до»':'';
  return <Modal title={'Приглашение · '+c.name} width={820} onClose={onClose} footer={<><span className="hint" style={{marginRight:'auto',color:err?'var(--fsp-red)':undefined}}>{err||'Кандидат увидит условия до начала общения'}</span><Button variant="ghost" onClick={onClose}>Отмена</Button><Button disabled={!!err} onClick={()=>onSend({...f,from:a,to:b})}>Отправить приглашение</Button></>}>
    <div className="grid-2" style={{alignItems:'start'}}>
      <div className="stack-16">
        <Field label="Вакансия" hint="Можно пригласить без опубликованной вакансии"><Select value={f.vac} onChange={set('vac')} options={[{id:'',label:'Без привязки к вакансии'},...D.VACANCIES.filter(v=>v.own).map(v=>({id:v.id,label:v.title}))]}/></Field>
        <Field label="Предложение"><Input value={f.title} onChange={set('title')}/></Field>
        <div className="grid-2"><Field label="Зарплата от, ₽"><Input value={f.from} onChange={set('from')}/></Field><Field label="до, ₽"><Input value={f.to} onChange={set('to')}/></Field></div>
        <Field label="Сообщение"><Textarea value={f.msg} onChange={set('msg')} placeholder={'Почему пишем именно вам: что в профиле зацепило'}/></Field>
        <div className="grid-2"><Field label="Формат"><Select value={f.format} onChange={set('format')} options={['Удалённо','Гибрид','Офис']}/></Field><Field label="Способ связи"><Input value={f.contact} onChange={set('contact')}/></Field></div>
      </div>
      <div className="stack-12"><span className="cap">Так увидит кандидат</span>
        <div className="preview">
          <span className="cap">{D.COMPANY.name}</span>
          <div style={{fontWeight:700,fontSize:16}}>{f.title||'—'}</div>
          <div className="salary" style={{fontSize:24}}>{a&&b?D.rub(a,b):'— ₽'}</div>
          {f.msg&&<div style={{fontSize:13,color:'var(--fg-2)'}}>{f.msg}</div>}
          <div className="hint">{f.format} · связь откроется после принятия</div>
          <div className="row-12"><span className="fake-btn">Принять</span><span className="fake-btn ghost">Отклонить</span></div>
        </div>
        {c.want&&<div className="hint">Ожидания кандидата: {c.want} ₽</div>}
      </div>
    </div>
  </Modal>;
}
Object.assign(window,{Shortlist,CandDrawer,InviteModal,CandRow,useRanked,refineFn,REFINE});
