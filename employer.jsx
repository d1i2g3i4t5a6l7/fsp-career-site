function EmpNeed({need,setNeed,go,toast}){
  const [f,setF]=React.useState(need);
  const set=(k,v)=>setF(o=>({...o,[k]:v}));
  const tog=s=>set('stack',f.stack.includes(s)?f.stack.filter(x=>x!==s):[...f.stack,s]);
  const n=D.CANDIDATES.filter(c=>c.spec===f.spec&&c.grade===f.grade).length;
  return <div className="page">
    <PageHead eyebrow="// потребность" title="Кого ищете" sub="Опишите специалиста и команду. Подборка строится по категориям кандидатов и пересчитывается сразу."/>
    <div className="split-r">
      <Panel><div className="stack-24">
        <Field label="Название потребности"><Input value={f.title} onChange={e=>set('title',e.target.value)}/></Field>
        <Field label="Специализация"><div className="chips">{D.SPECS.map(s=><Chip key={s.id} on={f.spec===s.id} onClick={()=>{set('spec',s.id);set('stack',[])}}>{s.label}</Chip>)}</div></Field>
        <Field label="Грейд"><div className="chips">{D.GRADES.map(g=><Chip key={g.id} on={f.grade===g.id} onClick={()=>set('grade',g.id)}>{g.label}</Chip>)}</div></Field>
        <Field label="Стек"><div className="chips">{D.STACKS[f.spec].map(s=><Chip key={s} on={f.stack.includes(s)} onClick={()=>tog(s)}>{s}</Chip>)}</div></Field>
        <div className="grid-3"><Field label="Зарплата от, ₽"><Input value={f.salaryFrom} onChange={e=>set('salaryFrom',+e.target.value.replace(/\D/g,''))}/></Field><Field label="до, ₽"><Input value={f.salaryTo} onChange={e=>set('salaryTo',+e.target.value.replace(/\D/g,''))}/></Field><Field label="Формат"><Select value={f.format} onChange={v=>set('format',v)} options={['Удалённо','Гибрид','Офис']}/></Field></div>
        <Field label="Чем занимается команда"><Textarea value={f.team} onChange={e=>set('team',e.target.value)}/></Field>
      </div></Panel>
      <div className="stack-16" style={{position:'sticky',top:24}}>
        <Panel title="Предпросмотр подборки"><div className="stack-16">
          <StatBlock value={n} label={`кандидатов в базе в категории ${D.specLabel(f.spec)} · ${D.gradeLabel(f.grade)}`} size="sm"/>
          <div className="hint">+ смежные категории: грейд выше и ниже, соседняя специализация</div>
          <Button fullWidth onClick={()=>{setNeed(f);toast('Подборка обновлена');go('shortlist')}} iconRight="→">Показать подборку</Button>
        </div></Panel>
        <Panel title="Регулярное задание"><div className="stack-12"><div className="hint">Задача из работы команды уйдёт кандидатам этой категории. Ответы помогут оценить подход.</div><Button variant="secondary" size="sm" onClick={()=>toast('Задание отправлено в категорию')}>Предложить задание</Button></div></Panel>
      </div>
    </div>
  </div>;
}

function EmpBank({need,invites,openCand,openInvite,stars,toggleStar,hasFsp}){
  const [q,setQ]=React.useState({spec:'',grade:'',stack:[],fsp:false,expert:false,text:''});
  const set=(k,v)=>setQ(o=>({...o,[k]:v}));
  const rows=D.CANDIDATES.map(c=>c.id==='me'&&!hasFsp?{...c,fsp:[]}:c).filter(c=>(!q.spec||c.spec===q.spec)&&(!q.grade||c.grade===q.grade)&&q.stack.every(s=>c.stack.includes(s))&&(!q.fsp||c.fsp.length)&&(!q.expert||c.expert)&&(!q.text||(c.name+c.stack.join(' ')+c.city).toLowerCase().includes(q.text.toLowerCase())))
    .map(c=>({c,s:D.score(c,need)})).sort((a,b)=>b.s.total-a.s.total);
  const allStack=[...new Set(Object.values(D.STACKS).flat())].slice(0,12);
  return <div className="page">
    <PageHead eyebrow="// банк кандидатов" title="Банк кандидатов" sub="Вся база. Сортировка — по соответствию вашей текущей потребности."/>
    <div className="bank">
      <Panel title="Фильтры" style={{alignSelf:'start'}} action={<Button variant="ghost" size="sm" onClick={()=>setQ({spec:'',grade:'',stack:[],fsp:false,expert:false,text:''})}>Сброс</Button>}><div className="stack-16">
        <Input placeholder="Поиск: стек, город…" value={q.text} onChange={e=>set('text',e.target.value)}/>
        <Field label="Специализация"><Select value={q.spec} onChange={v=>set('spec',v)} options={[{id:'',label:'Все'},...D.SPECS]}/></Field>
        <Field label="Грейд"><Select value={q.grade} onChange={v=>set('grade',v)} options={[{id:'',label:'Все'},...D.GRADES]}/></Field>
        <Field label="Стек"><div className="chips">{allStack.map(s=><Chip small key={s} on={q.stack.includes(s)} onClick={()=>set('stack',q.stack.includes(s)?q.stack.filter(x=>x!==s):[...q.stack,s])}>{s}</Chip>)}</div></Field>
        <label className="check"><input type="checkbox" checked={q.fsp} onChange={e=>set('fsp',e.target.checked)}/><span>Есть достижения ФСП</span></label>
        <label className="check"><input type="checkbox" checked={q.expert} onChange={e=>set('expert',e.target.checked)}/><span>Тест подтверждён экспертом</span></label>
      </div></Panel>
      <div className="stack-12"><div className="hint">Найдено: {rows.length}</div>
        <div className="panel">{rows.length?rows.map((x,i)=><CandRow key={x.c.id} c={x.c} s={x.s} rank={i+1} need={need} invites={invites} onOpen={openCand} onInvite={openInvite} starred={stars.includes(x.c.id)} onStar={toggleStar}/>):<div style={{padding:24}}><Empty title="Никого не нашли" text="Уберите часть фильтров."/></div>}</div></div>
    </div>
  </div>;
}

function EmpInvites({invites,openCand}){
  const [f,setF]=React.useState('all');
  const own=invites.filter(i=>i.company===D.COMPANY.name);
  const counts=['sent','viewed','accepted','declined'].map(s=>[s,own.filter(i=>i.status===s).length]);
  const rows=own.filter(i=>f==='all'||i.status===f);
  return <div className="page">
    <PageHead eyebrow="// приглашения" title="Приглашения"/>
    <div className="funnel">{counts.map(([s,n])=><button key={s} className={f===s?'on':''} onClick={()=>setF(f===s?'all':s)}><span className="pix" style={{fontSize:40}}>{n}</span><Status s={s}/></button>)}</div>
    <div className="panel" style={{overflowX:'auto'}}><table className="tbl">
      <thead><tr><th>Кандидат</th><th>Предложение</th><th>Зарплата</th><th>Дата</th><th>Статус</th><th>Контакты</th></tr></thead>
      <tbody>{rows.map(i=>{const c=D.CANDIDATES.find(x=>x.id===i.cand);return <tr key={i.id} onClick={()=>openCand(c)}>
        <td><b>{c.name}</b><div className="hint">{D.catLabel(c)}</div></td><td>{i.title}</td><td className="salary-sm" style={{whiteSpace:'nowrap'}}>{D.rub(i.from,i.to)}</td><td className="hint">{i.date}</td><td><Status s={i.status}/></td>
        <td style={{fontSize:13}}>{i.status==='accepted'?(c.id==='me'?'a.korneev@mail.ru':c.id+'@mail.ru'):<span className="hint">скрыты</span>}</td></tr>})}</tbody></table></div>
  </div>;
}

function EmpVacancies({openCand,toast}){
  const own=D.VACANCIES.filter(v=>v.own);
  const [sel,setSel]=React.useState(own[0].id);const [resp,setResp]=React.useState(D.VAC_RESPONSES);const [edit,setEdit]=React.useState(false);
  const v=own.find(x=>x.id===sel);const rs=resp.filter(r=>r.vac===sel);
  return <div className="page">
    <PageHead eyebrow="// вакансии" title="Вакансии" action={<Button size="sm" onClick={()=>setEdit(true)}>+ Новая вакансия</Button>}/>
    <div className="split">
      <div className="panel" style={{alignSelf:'start'}}>{own.map(x=><div key={x.id} className={'list-row col'+(sel===x.id?' sel':'')} onClick={()=>setSel(x.id)}>
        <b style={{fontSize:14}}>{x.title}</b><div className="salary-sm">{D.rub(x.from,x.to)}</div><span className="hint">{x.posted} · откликов: {resp.filter(r=>r.vac===x.id).length}</span></div>)}</div>
      <div className="stack-16">
        <Panel eyebrow={D.catLabel(v)} title={v.title} action={<Button variant="secondary" size="sm" onClick={()=>setEdit(true)}>Редактировать</Button>}>
          <div className="row-12" style={{flexWrap:'wrap'}}>{v.stack.map(s=><Tag key={s}>{s}</Tag>)}<span className="salary-sm">{D.rub(v.from,v.to)}</span><span className="hint">{v.format} · {v.city}</span></div>
        </Panel>
        <Panel title={'Отклики · '+rs.length} pad={0}>{rs.length?rs.map(r=>{const c=D.CANDIDATES.find(x=>x.id===r.cand);const s=D.score(c,{stack:v.stack});return <div key={r.id} className="list-row" onClick={()=>openCand(c)}>
          <div style={{minWidth:0}}><b style={{fontSize:14}}>{c.name}</b><div className="hint">{D.catLabel(c)} · тест {c.test} · {r.date}</div></div>
          <span className="num">{s.total}</span><Status s={r.status}/>
          <div className="row-12" onClick={e=>e.stopPropagation()}>{r.status!=='declined'&&<><Button size="sm" onClick={()=>{setResp(x=>x.map(y=>y.id===r.id?{...y,status:'accepted'}:y));toast('Кандидат приглашён на интервью')}}>На интервью</Button><Button size="sm" variant="ghost" onClick={()=>setResp(x=>x.map(y=>y.id===r.id?{...y,status:'declined'}:y))}>Отказ</Button></>}</div></div>}):<div style={{padding:24}}><Empty title="Откликов пока нет"/></div>}</Panel>
      </div>
    </div>
    {edit&&<Modal title="Вакансия" onClose={()=>setEdit(false)} footer={<><Button variant="ghost" onClick={()=>setEdit(false)}>Отмена</Button><Button onClick={()=>{setEdit(false);toast('Вакансия опубликована')}}>Опубликовать</Button></>}>
      <div className="stack-16"><Field label="Название"><Input defaultValue={v.title}/></Field>
        <div className="grid-2"><Field label="Зарплата от, ₽"><Input defaultValue={v.from}/></Field><Field label="до, ₽"><Input defaultValue={v.to}/></Field></div>
        <Field label="Описание" hint="По описанию вакансий категории система собирает задачи для тестов"><Textarea defaultValue={D.NEED.team}/></Field></div>
    </Modal>}
  </div>;
}

function EmpReview({toast}){
  const queue=[{c:'k4410',ai:74},{c:'k0954',ai:79},{c:'k5133',ai:77}];
  const [i,setI]=React.useState(0);const [scores,setScores]=React.useState(D.AI_EVAL.map(e=>e.v));const [done,setDone]=React.useState([]);
  const cur=queue[i];const c=D.CANDIDATES.find(x=>x.id===cur.c);
  const total=Math.round(scores.reduce((a,b)=>a+b,0)/scores.length);
  const finish=(ok)=>{setDone(d=>[...d,cur.c]);toast(ok?'Оценка подтверждена':'Оценка скорректирована: '+total);setI((i+1)%queue.length);setScores(D.AI_EVAL.map(e=>e.v))};
  return <div className="page">
    <PageHead eyebrow="// экспертиза" title="Проверка оценок ИИ" sub="Инженер компании проверяет решение и подтверждает или корректирует оценку ИИ. Только после этого тест получает статус «Подтверждено»."/>
    <div className="row-12">{queue.map((q,k)=><Chip key={q.c} on={k===i} onClick={()=>setI(k)} small>{D.CANDIDATES.find(x=>x.id===q.c).name}{done.includes(q.c)?' ✓':''}</Chip>)}</div>
    <div className="test-grid">
      <section className="panel editor">
        <div className="panel-h"><div><div className="eyebrow">{D.catLabel(c)} · вариант #B2-9C4</div><div className="panel-t">{D.TASK.title}</div></div><span className="hint">решено за 31:40</span></div>
        <pre className="code-big">{D.TASK.code}</pre>
        <div className="ed-f"><span className="hint">Журнал: 0 вставок из буфера · 1 уход со вкладки (12 с) · 4 запуска тестов</span></div>
      </section>
      <Panel title="Оценка"><div className="stack-16">
        {D.AI_EVAL.map((e,k)=><div key={e.k} className="stack-8">
          <div className="row-12" style={{justifyContent:'space-between'}}><b style={{fontSize:13}}>{e.k}</b><span className="hint">ИИ {e.v} → <b style={{color:scores[k]!==e.v?'var(--fsp-red)':'var(--fg-1)'}}>{scores[k]}</b></span></div>
          <input type="range" min="0" max="100" value={scores[k]} onChange={ev=>setScores(s=>s.map((x,j)=>j===k?+ev.target.value:x))}/>
          <span className="hint">{e.note}</span></div>)}
        <div className="row-12" style={{justifyContent:'space-between',borderTop:'1px solid var(--border-1)',paddingTop:16}}><span className="cap">Итог</span><span className="pix" style={{fontSize:40}}>{total}</span></div>
        <Textarea rows={3} placeholder="Комментарий кандидату (необязательно)"/>
        <div className="row-12"><Button onClick={()=>finish(true)}>Подтвердить</Button><Button variant="secondary" onClick={()=>finish(false)}>Сохранить правку</Button></div>
      </div></Panel>
    </div>
  </div>;
}

function EmpCompany({toast}){
  const C=D.COMPANY;
  return <div className="page">
    <PageHead eyebrow="// компания" title="Профиль компании" sub="Эти данные кандидат видит в каждом приглашении."/>
    <Panel><div className="stack-24">
      <div className="grid-2"><Field label="Название"><Input defaultValue={C.name}/></Field><Field label="Направление"><Input defaultValue={C.field}/></Field>
        <Field label="Размер"><Input defaultValue={C.size}/></Field><Field label="Сайт"><Input defaultValue={C.site}/></Field>
        <Field label="Контакт для кандидатов"><Input defaultValue={C.contact}/></Field></div>
      <Field label="О компании"><Textarea defaultValue={C.about}/></Field>
      <div><Button onClick={()=>toast('Сохранено')}>Сохранить</Button></div>
    </div></Panel>
  </div>;
}
Object.assign(window,{EmpNeed,EmpBank,EmpInvites,EmpVacancies,EmpReview,EmpCompany});
