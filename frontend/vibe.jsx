// Вайбкодинг-тест: задача, файлы, ИИ-ассистент, правки и тесты — с бэкенда (workspace, api.js)
const VIBE_HELLO='Я ИИ-ассистент этого теста. Работаем вместе: формулируйте задачу, просите код, проверяйте его. Я могу ошибаться — найти ошибку тоже часть теста.';
const VIBE_QUICK=['Какие файлы в задаче?','Запусти тесты','Исправь код, чтобы тесты прошли'];
// Что кандидат может делать на тесте — показывается рядом с условием задачи
const VIBE_CAN=['Спрашивать ассистента о задаче и коде','Просить у него код и спорить с ним — он может ошибаться','Принимать или отклонять его правки','Править файлы вручную','Запускать тесты задачи сколько угодно раз','Когда всё готово — нажать «Отправить решение»: ИИ проверит работу по критериям, результат появится сразу'];
const VIBE_RUNNER='run_tests.py'; // файл запуска тестов кладёт платформа, кандидату он не нужен
const EDIT_STATE={accepted:'✓ применено',rejected:'× отклонено',stale:'устарела: файл изменился после предложения'};
const isTestFile=p=>/(^|\/)test_[^/]*\.py$/.test(p);
// Цитата-доказательство; служебные метки материалов («<итоговые_файлы>») ничего не доказывают — не показываем
const quote=e=>e&&!/^<[^>]+>$/.test(e.trim())?' · «'+(e.length>160?e.slice(0,160)+'…':e)+'»':'';
const times=n=>n%10>=2&&n%10<=4&&(n%100<10||n%100>=20)?'раза':'раз';

// Условие задачи: блоки через пустую строку; короткая первая строка без точки — заголовок блока, строки «- …» — пункты
function TaskText({text}){
  return <div className="stack-16">{text.split(/\n\s*\n/).map((block,i)=>{
    const lines=block.split('\n').map(l=>l.trim()).filter(Boolean);
    const head=lines.length>1&&!lines[0].startsWith('- ')&&lines[0].length<40&&!/[.!?:;,]$/.test(lines[0])?lines.shift():null;
    const list=lines.every(l=>l.startsWith('- '));
    return <div key={i}>{head&&<div className="cap" style={{marginBottom:8}}>{head}</div>}
      {list?<ul className="ul">{lines.map(l=><li key={l} style={{fontSize:14,color:'var(--fg-1)',lineHeight:1.6}}>{l.slice(2)}</li>)}</ul>
        :<p style={{margin:0,fontSize:14,lineHeight:1.6,textWrap:'pretty'}}>{lines.join(' ')}</p>}</div>})}</div>;
}

function VibeTest({category,level,onExit,onBack,onSubmit,inline}){
  const [att,setAtt]=React.useState(null);const [err,setErr]=React.useState('');
  const [files,setFiles]=React.useState({});const [cur,setCur]=React.useState('');
  const [input,setInput]=React.useState('');const [busy,setBusy]=React.useState(false);const [pending,setPending]=React.useState('');
  const [askErr,setAskErr]=React.useState('');const [editErr,setEditErr]=React.useState({});
  const [run,setRun]=React.useState(null);const [testing,setTesting]=React.useState(false);
  const [left,setLeft]=React.useState(0);
  const [taskOpen,setTaskOpen]=React.useState(true);
  const listRef=React.useRef(null);const dirty=React.useRef(new Set());const saveT=React.useRef(null);const done=React.useRef(false);
  const filesRef=React.useRef(files);filesRef.current=files;
  const id=att&&att.id;
  const load=a=>{setAtt(a);setLeft(a.remaining_s);return a};
  const refresh=()=>WS.attempt(id).then(load).catch(()=>{});
  React.useEffect(()=>{startOrResume(category,level).then(a=>{
    if(a.status!=='active'){onSubmit(a.id);return}
    // Сначала открываем файл, о котором говорит условие, а не первый по алфавиту
    const at=p=>{const i=a.task.statement.indexOf(p);return i<0?1e9:i};
    load(a);setFiles(a.files);setCur(Object.keys(a.files).filter(p=>p!==VIBE_RUNNER&&!isTestFile(p)).sort((x,y)=>at(x)-at(y)||x.localeCompare(y))[0]||'');
  }).catch(e=>setErr(e.status===404?'Для направления «'+category+'» тест на '+D.gradeLabel(level)+' пока недоступен. В демо-версии задача есть только для Backend со стеком Python и PostgreSQL на грейд Middle: она несложная и нужна, чтобы показать, как работает сервис.':e.message))},[]);
  React.useEffect(()=>{if(!id)return;const t=setInterval(()=>setLeft(l=>Math.max(0,l-1)),1000);return()=>clearInterval(t)},[id]);
  React.useEffect(()=>{if(id&&left===0)finish()},[left]);
  // Уход со вкладки запрещён: каждый уход и возврат уходят на сервер и отмечаются в результате
  React.useEffect(()=>{if(!id)return;
    const away=l=>()=>WS.focus(id,l).then(r=>{if(r.recorded&&!l)refresh()}).catch(()=>{});
    const out=away(true),back=away(false),vis=()=>document.hidden?out():back();
    window.addEventListener('blur',out);window.addEventListener('focus',back);document.addEventListener('visibilitychange',vis);
    return()=>{window.removeEventListener('blur',out);window.removeEventListener('focus',back);document.removeEventListener('visibilitychange',vis)}},[id]);
  React.useEffect(()=>{if(listRef.current)listRef.current.scrollTop=listRef.current.scrollHeight},[att&&att.chat.length,busy,pending]);
  // Правки руками сохраняются на сервер через секунду тишины и перед любым действием
  const flush=async()=>{clearTimeout(saveT.current);const paths=[...dirty.current];dirty.current.clear();
    for(const p of paths)await WS.save(id,p,filesRef.current[p]);if(paths.length)await refresh()};
  const type=v=>{setFiles(f=>({...f,[cur]:v}));dirty.current.add(cur);clearTimeout(saveT.current);saveT.current=setTimeout(()=>flush().catch(()=>{}),800)};
  const send=async(txt)=>{
    const q=(txt||input).trim();if(!q||busy||!id)return;
    setInput('');setBusy(true);setPending(q);setAskErr('');
    try{await flush();await WS.ask(id,q)}catch(e){if(e.status!==502)setAskErr(e.message)}
    await refresh();setPending('');setBusy(false);
  };
  const act=async(editId,ok)=>{setEditErr(x=>({...x,[editId]:''}));
    try{await flush();await WS.edit(id,editId,ok);if(ok){const a=await WS.attempt(id);load(a);setFiles(a.files)}else await refresh()}
    catch(e){setEditErr(x=>({...x,[editId]:e.message}));await refresh()}};
  const runTests=async()=>{setTesting(true);try{await flush();setRun(await WS.tests(id))}catch(e){setRun({passed:false,output:e.message})}await refresh();setTesting(false)};
  const finish=async()=>{if(done.current)return;done.current=true;try{await flush()}catch(e){}try{await WS.submit(id)}catch(e){}onSubmit(id)};
  const exit=async()=>{try{await flush()}catch(e){}onExit()};
  const wrap=inline?{className:'test'}:{className:'page',style:{maxWidth:1480}};
  if(err) return <div {...wrap}><Panel title="Тест не начался"><div className="stack-16"><div className="note" role="alert" style={{borderColor:'var(--fsp-red)',color:'var(--fg-1)'}}>{err}</div>{(onBack||onExit)&&<div><Button variant="secondary" onClick={onBack||onExit}>{onBack?'← К опросу':'← Грейд'}</Button></div>}</div></Panel></div>;
  if(!att) return <div {...wrap}><Panel><span className="hint">Готовим задачу…</span></Panel></div>;
  const edits=Object.fromEntries(att.edits.map(e=>[e.id,e]));
  const msgs=[{role:'assistant',text:VIBE_HELLO},
    ...att.chat.map(m=>({role:m.role==='user'?'user':'assistant',text:m.text,err:m.role==='error',edits:(m.edit_ids||[]).map(i=>edits[i]).filter(Boolean)})),
    ...(pending?[{role:'user',text:pending}]:[]),...(askErr?[{role:'assistant',text:askErr,err:true}]:[])];
  const names=Object.keys(files).filter(p=>p!==VIBE_RUNNER).sort((x,y)=>isTestFile(x)-isTestFile(y)||x.localeCompare(y));
  const st=att.stats;
  const mm=String(Math.floor(left/60)).padStart(2,'0'),ss=String(left%60).padStart(2,'0');
  const lines=(files[cur]||'').split('\n').length;
  return <div {...wrap}>
    <div className="test-bar">
      <div className="row-12" style={{flexWrap:'wrap'}}>{onExit&&<Button variant="ghost" size="sm" onClick={exit}>← Грейд</Button>}<ATag>{att.category} · {D.gradeLabel(att.level)}</ATag><span className="beta">Вайбкодинг</span><span className="hint">Вариант #{att.task.id}</span></div>
      <div className="timer"><span className="cap">Осталось</span><span className="timer-n">{mm}:{ss}</span></div>
    </div>
    <section className="panel">
      <div className="panel-h" style={{cursor:'pointer'}} onClick={()=>setTaskOpen(!taskOpen)}><div><div className="eyebrow">Задача · тест на {D.gradeLabel(att.level)}</div><div className="panel-t">{att.task.title}</div></div><span className="hint">{taskOpen?'Свернуть ▲':'Развернуть ▼'}</span></div>
      {taskOpen&&<div className="vibe-task"><div className="stack-16">
        <TaskText text={att.task.statement}/>
        <div className="note test-acc"><div className="cap" style={{color:'var(--warning)'}}>Важно</div><div>В решении используется API GigaChat для физических лиц: параллельные запросы к ассистенту встают в очередь. Поэтому <b>не рекомендуется</b> тестировать одновременно нескольким экспертам.</div></div>
      </div><div className="stack-16">
        <div><div className="cap" style={{marginBottom:8}}>Что оценивается</div><ul className="ul">{att.task.assessed.map(c=><li key={c}>{c}</li>)}</ul></div>
        <div><div className="cap" style={{marginBottom:8}}>Что можно делать</div><ul className="ul">{VIBE_CAN.map(c=><li key={c}>{c}</li>)}</ul></div>
        <div className="hint">Уход со вкладки запрещён: каждый уход отмечается в результате, проверяющий может аннулировать попытку.</div>
      </div></div>}
    </section>
    <div className="vibe-grid">
      <section className="panel vibe-chat">
        <div className="panel-h"><div className="row-12"><PixelArt name="bot" px={2}/><div className="panel-t">ИИ-ассистент</div></div><span className="hint">все запросы попадают в отчёт</span></div>
        <div className="vibe-list" ref={listRef}>
          {msgs.map((m,i)=><div key={i} className={'msg '+m.role}>
            <span className="cap">{m.role==='user'?'Вы':'Ассистент'}</span>
            {m.text&&<div className="msg-t" style={m.err?{borderColor:'var(--fsp-red)'}:undefined}>{m.text}</div>}
            {(m.edits||[]).map(e=><div key={e.id} className="stack-8">
              <span className="hint">Правка {e.path} · +{e.added} −{e.removed}</span>
              <pre className="code-sm" style={{maxHeight:220,overflow:'auto'}}>{e.diff}</pre>
              {e.status==='pending'?<div className="row-12"><Button size="sm" onClick={()=>act(e.id,true)}>Применить в редактор</Button><Button size="sm" variant="ghost" onClick={()=>act(e.id,false)}>Отклонить</Button></div>:<span className="hint">{EDIT_STATE[e.status]||e.status}</span>}
              {editErr[e.id]&&<span className="hint" style={{color:'var(--fsp-red)'}}>{editErr[e.id]}</span>}
            </div>)}
          </div>)}
          {busy&&<div className="msg assistant"><span className="cap">Ассистент</span><div className="msg-t typing">пишет<span>.</span><span>.</span><span>.</span></div></div>}
        </div>
        <div className="vibe-quick">{VIBE_QUICK.map(q=><Chip key={q} small onClick={()=>send(q)}>{q}</Chip>)}</div>
        <div className="vibe-in"><textarea className="inp" rows={2} value={input} placeholder="Опишите, что нужно ассистенту…" onChange={e=>setInput(e.target.value)} onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();send()}}}></textarea><Button size="sm" onClick={()=>send()} disabled={busy||!input.trim()}>→</Button></div>
      </section>
      <section className="panel editor">
        <div className="panel-h"><div className="row-12" style={{flexWrap:'wrap'}}>{names.map(p=><span key={p} className={'tab'+(p===cur?' on':'')} style={{cursor:'pointer'}} onClick={()=>setCur(p)}>{p}</span>)}</div><span className="hint">правок вручную: {st.manual_edits}</span></div>
        <div className="ed">
          <div className="ed-ln">{Array.from({length:Math.max(lines,22)},(_,i)=><div key={i}>{i+1}</div>)}</div>
          <textarea spellCheck="false" value={files[cur]||''} onChange={e=>type(e.target.value)}></textarea>
        </div>
        {run&&<div className="stack-8" style={{padding:'12px 16px',borderTop:'1px solid var(--border-1)'}}>
          <div className="row-12"><Tag discipline={run.passed?'security':'red'}>{run.passed?'Тесты прошли':'Тесты не прошли'}</Tag>{run.duration_ms!=null&&<span className="hint">{(run.duration_ms/1000).toFixed(1)} с</span>}</div>
          <pre className="code-sm" style={{maxHeight:200,overflow:'auto'}}>{run.output}</pre>
        </div>}
        <div className="ed-f">
          <div className="row-12 vibe-stats"><span>запросов <b>{st.assistant_requests}</b></span><span>принято <b>{st.edits_accepted}</b></span><span>отклонено <b>{st.edits_rejected}</b></span>{st.tab_leaves>0&&<span style={{color:'var(--fsp-red)'}}>уходов со вкладки <b style={{color:'var(--fsp-red)'}}>{st.tab_leaves}</b></span>}</div>
          <div className="row-12"><Button variant="secondary" size="sm" onClick={runTests} disabled={testing}>{testing?'Тесты идут…':'Запустить тесты'}</Button><Button size="sm" onClick={finish}>Отправить решение</Button></div>
        </div>
      </section>
    </div>
  </div>;
}

const VERDICT={yes:'Да',partial:'Частично',no:'Нет'};
// Разбор по критериям: вердикт ИИ, баллы, комментарий и цитата из решения
function ResultRows({res}){
  return <div className="stack-16">{res.criteria.map(c=><div key={c.id} className="eval-row">
    <div style={{fontSize:14,fontWeight:700}}>{VERDICT[c.verdict]||c.verdict}</div><Bar value={c.earned} max={c.points} color={c.earned<c.points?'var(--warning)':'var(--accent)'}/><div className="num">{c.earned}/{c.points}</div>
    <div className="hint" style={{gridColumn:'1 / -1'}}><span style={{color:'var(--fg-1)'}}>{c.text}</span>{c.comment?' — '+c.comment:''}{quote(c.evidence)}{c.corrected?' · исправлено экспертом, ИИ: '+VERDICT[c.ai_verdict]:''}</div></div>)}</div>;
}
// Балл: оценка ИИ или итог после правки человека, порог грейда, на который тест
function ResultScore({res,level}){
  const th=res.thresholds.find(t=>t.grade===level),fx=res.correction;
  return <div className="stack-16"><span className="cap">{fx?'Оценка после проверки':'Оценка ИИ'}</span><StatBlock value={fx?fx.score:res.ai_score} label={'из 100'+(fx?' · ИИ — '+res.ai_score:'')+(th?' · порог '+D.gradeLabel(level)+' — '+th.min_score:'')} size="sm"/></div>;
}
// Уход со вкладки и решение человека по попытке
function ResultCheck({res}){
  const v=res.violations||{count:0},rv=res.review;
  const red={borderColor:'var(--fsp-red)',color:'var(--fg-1)'};
  if(rv&&rv.annulled) return <div className="note" style={red}>Попытка аннулирована{rv.comment?': '+rv.comment:''}. Грейд, полученный ею, снят, тесты заморожены на 30 дней.</div>;
  return <>
    {v.count>0&&<div className="note" style={red}>Уход со вкладки: {v.count} {times(v.count)}{v.away_s?', всего '+v.away_s+' с':''}. {rv?'Проверяющий засчитал попытку.':'Попытку проверит человек и может аннулировать: тогда грейд снимется, а тесты будут заморожены на 30 дней.'}</div>}
    {res.correction?<div className="note">Эксперт исправил оценку: ИИ {res.ai_score} → {res.correction.score}{rv&&rv.comment?'. '+rv.comment:''}</div>
      :rv&&!v.count?<div className="note">Эксперт подтвердил оценку ИИ{rv.comment?': '+rv.comment:''}.</div>:null}
  </>;
}
// Решение на проверке: грейд ещё не выдан. Заметная плашка с этапами вместо строки-подсказки.
// status — grading_status бэкенда: pending (очередь к ИИ) | running | failed; compact — для шапки профиля
function GradingBanner({status,err,level,compact}){
  const failed=status==='failed';
  const steps=[['Решение сдано','done'],[status==='pending'?'Ждёт очереди к ИИ':'ИИ проверяет по критериям',failed?'fail':'now'],['Грейд'+(level?' '+D.gradeLabel(level):''),'wait']];
  return <section className={'grading'+(failed?' fail':'')+(compact?' compact':'')} role="status" aria-live="polite">
    <div className="grading-top"><span className="grading-dot" aria-hidden="true"></span><span className="cap">{failed?'Проверка не удалась':'Идёт проверка'}</span></div>
    <div className="grading-title">{failed?'Решение сохранено, но проверка не завершилась':'Решение на проверке. Грейд пока не выдан'}</div>
    {!compact&&<ol className="grading-steps">{steps.map(([t,s],i)=><li key={i} className={s}><span aria-hidden="true">{s==='done'?'✓':s==='fail'?'×':s==='now'?'…':String(i+1).padStart(2,'0')}</span>{t}</li>)}</ol>}
    {!failed&&<div className="grading-bar" aria-hidden="true"><i></i></div>}
    <div className="hint">{failed?'Решение не потеряется: откройте результат позже.':err||'Обычно около минуты. Можно уйти со страницы: итог появится в разделе «Грейд и тесты».'}</div>
  </section>;
}
function VibeResult({attemptId,onExit}){
  const [att,setAtt]=React.useState(null);const [res,err]=useAttemptResult(attemptId);
  React.useEffect(()=>{WS.attempt(attemptId).then(setAtt).catch(()=>{})},[attemptId]);
  const level=att?att.level:'';const done=res&&res.status==='done';
  const annulled=done&&res.review&&res.review.annulled,passed=done&&!annulled&&res.final&&res.final.passed;
  return <div className="page">
    <PageHead eyebrow="// вайбкодинг" title="Решение отправлено"/>
    {!done?<GradingBanner status={res?res.status:'pending'} err={err} level={level}/>:<>
      <div className="grid-2" style={{alignItems:'stretch'}}>
        <Panel><ResultScore res={res} level={level}/></Panel>
        <Panel><div className="stack-16"><span className="cap">Статус</span><div style={{fontSize:20,fontWeight:700}}>{annulled?'Попытка аннулирована':passed?'Тест пройден':'Тест не пройден'}</div><div className="hint">{annulled?'Тесты заморожены на 30 дней.':passed?'Грейд — '+att.category+' · '+D.gradeLabel(level)+'. Следующая смена — через 3 месяца. Эксперт может скорректировать оценку ИИ.':'Грейд не меняется. Тест на уровень ниже доступен сразу, на этот же — через 30 дней.'}</div></div></Panel>
      </div>
      <ResultCheck res={res}/>
      <Panel title="Разбор"><ResultRows res={res}/></Panel>
    </>}
    <div><Button onClick={onExit} iconRight="→">К грейду</Button></div>
  </div>;
}
Object.assign(window,{VibeTest,VibeResult,GradingBanner,ResultRows,ResultCheck,ResultScore,VERDICT,VIBE_RUNNER,isTestFile,times,quote});
