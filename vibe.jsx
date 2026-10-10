const VIBE_TASK={
 title:'Лимиты запросов для платёжного API',
 grade:'Senior',minutes:60,
 text:'Платёжный API работает на 6 инстансах за балансировщиком. Нужен ограничитель: не больше 100 запросов в минуту на ключ партнёра, общий для всех инстансов. Разрешено и рекомендуется работать вместе с ИИ-ассистентом.',
 checks:['Как вы ставите задачу ассистенту','Находите ли ошибки в сгенерированном коде','Итоговое решение: атомарность, отказ Redis, нагрузка','Сколько итераций понадобилось'],
};
const VIBE_START=`import time
import redis

r = redis.Redis()
LIMIT = 100
WINDOW = 60

def allow(key: str) -> bool:
    # TODO
    ...
`;
const VIBE_SCRIPT=[
 {text:'Предлагаю фиксированное окно на Redis: счётчик на ключ партнёра с TTL 60 с. Это просто и общее для всех инстансов.',code:`def allow(key: str) -> bool:
    k = f"rl:{key}:{int(time.time() // WINDOW)}"
    n = r.incr(k)
    if n == 1:
        r.expire(k, WINDOW)
    return n <= LIMIT`},
 {text:'Верно, INCR и EXPIRE — две команды: если процесс упадёт между ними, ключ останется без TTL. Сделаем атомарно через Lua-скрипт.',code:`LUA = """
local n = redis.call('INCR', KEYS[1])
if n == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end
return n
"""
_script = r.register_script(LUA)

def allow(key: str) -> bool:
    k = f"rl:{key}:{int(time.time() // WINDOW)}"
    n = _script(keys=[k], args=[WINDOW])
    return n <= LIMIT`},
 {text:'Если Redis недоступен, для платёжного API безопаснее пропускать запросы (fail-open) и писать метрику, иначе упадёт приём платежей.',code:`def allow(key: str) -> bool:
    k = f"rl:{key}:{int(time.time() // WINDOW)}"
    try:
        n = _script(keys=[k], args=[WINDOW])
    except redis.RedisError:
        metrics.incr("ratelimit.redis_down")
        return True  # fail-open
    return n <= LIMIT`},
];
const VIBE_SYS='Ты ИИ-ассистент внутри теста на грейд для backend-разработчика (Python). Задача кандидата: распределённый rate limiter 100 запросов/мин на ключ партнёра, 6 инстансов, Redis. Отвечай по-русски, коротко (до 80 слов текста) и, если уместно, один блок кода ```python. Не решай всё сразу без запроса. Иногда допускай правдоподобную неточность (например, неатомарность команд) — проверка умения её заметить входит в тест, но не говори об этом.';

function extractCode(s){const m=s.match(/```(?:\w+)?\n([\s\S]*?)```/);return m?{text:s.replace(m[0],'').replace(/\n{3,}/g,'\n\n').trim(),code:m[1].trimEnd()}:{text:s.trim(),code:null};}

function mergeCode(cur,nw){
  if(/^\s*(import|from)\s/m.test(nw))return nw.trimEnd()+'\n';
  const cut=(s)=>{const i=cur.indexOf(s);return i<0?null:cur.slice(0,i)};
  if(nw.includes('LUA')){const h=cut('LUA')??cut('def allow');if(h!=null)return h+nw.trimEnd()+'\n';}
  if(nw.includes('def allow')){const h=cut('def allow');if(h!=null)return h+nw.trimEnd()+'\n';}
  return cur.trimEnd()+'\n\n'+nw.trimEnd()+'\n';
}
function VibeTest({onExit,onSubmit}){
  const [msgs,setMsgs]=React.useState([{role:'assistant',text:'Я ИИ-ассистент этого теста. Работаем вместе: формулируйте задачу, просите код, проверяйте его. Я могу ошибаться — найти ошибку тоже часть теста.'}]);
  const [input,setInput]=React.useState('');const [busy,setBusy]=React.useState(false);
  const [code,setCode]=React.useState(VIBE_START);
  const [stat,setStat]=React.useState({prompts:0,applied:0,rejected:0,edits:0});
  const [left,setLeft]=React.useState(VIBE_TASK.minutes*60-4*60-31);
  const [taskOpen,setTaskOpen]=React.useState(true);
  const scRef=React.useRef(0);const listRef=React.useRef(null);
  React.useEffect(()=>{const t=setInterval(()=>setLeft(l=>Math.max(0,l-1)),1000);return()=>clearInterval(t)},[]);
  React.useEffect(()=>{if(listRef.current)listRef.current.scrollTop=listRef.current.scrollHeight},[msgs,busy]);
  const send=async(txt)=>{
    const q=(txt||input).trim();if(!q||busy)return;
    setInput('');setBusy(true);setStat(s=>({...s,prompts:s.prompts+1}));
    const hist=[...msgs.filter((m,i)=>i>0),{role:'user',text:q}];
    setMsgs(m=>[...m,{role:'user',text:q}]);
    let reply;
    try{
      const sample=window.claude&&window.claude.use?await window.claude.use('sample'):null;
      if(!sample)throw 0;
      const turns=[{role:'user',content:VIBE_SYS+'\n\nТекущий код кандидата:\n```python\n'+code+'\n```'},{role:'assistant',content:'Вижу код.'},...hist.map(m=>({role:m.role,content:m.text+(m.code?'\n```python\n'+m.code+'\n```':'')}))];
      const r=await sample(turns,{cache:false,modelTier:'quick'});
      reply=extractCode(r.text);
    }catch(e){const s=VIBE_SCRIPT[Math.min(scRef.current,VIBE_SCRIPT.length-1)];scRef.current++;reply={text:s.text,code:s.code};}
    setMsgs(m=>[...m,{role:'assistant',...reply,state:reply.code?'new':null}]);setBusy(false);
  };
  const act=(i,ok)=>{const m=msgs[i];if(ok)setCode(c=>mergeCode(c,m.code));
    setMsgs(ms=>ms.map((x,j)=>j===i?{...x,state:ok?'applied':'rejected'}:x));setStat(s=>({...s,[ok?'applied':'rejected']:s[ok?'applied':'rejected']+1}));};
  const mm=String(Math.floor(left/60)).padStart(2,'0'),ss=String(left%60).padStart(2,'0');
  const lines=code.split('\n').length;
  return <div className="page" style={{maxWidth:1480}}>
    <div className="test-bar">
      <div className="row-12" style={{flexWrap:'wrap'}}><Button variant="ghost" size="sm" onClick={onExit}>← Грейд</Button><ATag>Backend · Senior</ATag><span className="beta">Вайбкодинг · тестовый режим</span><span className="hint">Вариант #V3-0D8</span></div>
      <div className="timer"><span className="cap">Осталось</span><span className="timer-n">{mm}:{ss}</span></div>
    </div>
    <section className="panel">
      <div className="panel-h" style={{cursor:'pointer'}} onClick={()=>setTaskOpen(!taskOpen)}><div><div className="eyebrow">Задача · тест на Senior</div><div className="panel-t">{VIBE_TASK.title}</div></div><span className="hint">{taskOpen?'Свернуть ▲':'Развернуть ▼'}</span></div>
      {taskOpen&&<div className="vibe-task"><p style={{margin:0,fontSize:14,lineHeight:1.6,textWrap:'pretty'}}>{VIBE_TASK.text}</p><div><div className="cap" style={{marginBottom:8}}>Что оценивается</div><ul className="ul">{VIBE_TASK.checks.map(c=><li key={c}>{c}</li>)}</ul></div></div>}
    </section>
    <div className="vibe-grid">
      <section className="panel vibe-chat">
        <div className="panel-h"><div className="row-12"><PixelArt name="bot" px={2}/><div className="panel-t">ИИ-ассистент</div></div><span className="hint">все запросы попадают в отчёт</span></div>
        <div className="vibe-list" ref={listRef}>
          {msgs.map((m,i)=><div key={i} className={'msg '+m.role}>
            <span className="cap">{m.role==='user'?'Вы':'Ассистент'}</span>
            {m.text&&<div className="msg-t">{m.text}</div>}
            {m.code&&<pre className="code-sm" style={{maxHeight:220,overflow:'auto'}}>{m.code}</pre>}
            {m.code&&m.state==='new'&&<div className="row-12"><Button size="sm" onClick={()=>act(i,true)}>Применить в редактор</Button><Button size="sm" variant="ghost" onClick={()=>act(i,false)}>Отклонить</Button></div>}
            {m.state==='applied'&&<span className="hint">✓ применено</span>}{m.state==='rejected'&&<span className="hint">× отклонено</span>}
          </div>)}
          {busy&&<div className="msg assistant"><span className="cap">Ассистент</span><div className="msg-t typing">пишет<span>.</span><span>.</span><span>.</span></div></div>}
        </div>
        <div className="vibe-quick">{['Предложи подход с Redis','Здесь INCR и EXPIRE не атомарны','Что будет, если Redis упадёт?'].map(q=><Chip key={q} small onClick={()=>send(q)}>{q}</Chip>)}</div>
        <div className="vibe-in"><textarea className="inp" rows={2} value={input} placeholder="Опишите, что нужно ассистенту…" onChange={e=>setInput(e.target.value)} onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();send()}}}></textarea><Button size="sm" onClick={()=>send()} disabled={busy||!input.trim()}>→</Button></div>
      </section>
      <section className="panel editor">
        <div className="panel-h"><div className="row-12"><span className="tab on">limiter.py</span><span className="tab">test_limiter.py</span></div><span className="hint">правок вручную: {stat.edits}</span></div>
        <div className="ed">
          <div className="ed-ln">{Array.from({length:Math.max(lines,22)},(_,i)=><div key={i}>{i+1}</div>)}</div>
          <textarea spellCheck="false" value={code} onChange={e=>{setCode(e.target.value);setStat(s=>({...s,edits:s.edits+1}))}}></textarea>
        </div>
        <div className="ed-f">
          <div className="row-12 vibe-stats"><span>запросов <b>{stat.prompts}</b></span><span>принято <b>{stat.applied}</b></span><span>отклонено <b>{stat.rejected}</b></span></div>
          <div className="row-12"><Button variant="secondary" size="sm">Запустить тесты</Button><Button size="sm" onClick={()=>onSubmit(stat)}>Отправить решение</Button></div>
        </div>
      </section>
    </div>
  </div>;
}

function VibeResult({stat,onExit}){
  const rows=[['Постановка задачи ИИ',84,'Задача сформулирована с ограничениями: 6 инстансов, общий лимит'],['Проверка кода ИИ',stat.rejected>0||stat.prompts>1?88:58,stat.rejected>0||stat.prompts>1?'Найдена неатомарность INCR + EXPIRE в предложении ассистента':'Неатомарность INCR + EXPIRE в коде ассистента осталась незамеченной'],['Итоговое решение',79,'Атомарный Lua-скрипт; поведение при отказе Redis — fail-open с метрикой'],['Итерации',stat.prompts<=5?90:72,`${stat.prompts} запросов, ${stat.applied} принято, ${stat.rejected} отклонено`]];
  const total=Math.round(rows.reduce((a,r)=>a+r[1],0)/rows.length);
  return <div className="page">
    <PageHead eyebrow="// вайбкодинг · тестовый режим" title="Решение отправлено"/>
    <div className="grid-2" style={{alignItems:'stretch'}}>
      <Panel><div className="stack-16"><span className="cap">Оценка ИИ</span><StatBlock value={total} label="из 100 · порог Senior — 80" size="sm"/></div></Panel>
      <Panel><div className="stack-16"><span className="cap">Статус</span><div style={{fontSize:20,fontWeight:700}}>Ожидает проверки эксперта</div><div className="hint">В тестовом режиме вайбкодинг не меняет грейд автоматически. Эксперт смотрит решение и журнал работы с ассистентом и выносит итог до 11.10.</div></div></Panel>
    </div>
    <Panel title="Разбор"><div className="stack-16">{rows.map(([k,v,n])=><div key={k} className="eval-row">
      <div style={{fontSize:14,fontWeight:700}}>{k}</div><Bar value={v} color={v<70?'var(--warning)':'var(--accent)'}/><div className="num">{v}</div>
      <div className="hint" style={{gridColumn:'1 / -1'}}>{n}</div></div>)}</div></Panel>
    <div><Button onClick={onExit} iconRight="→">К грейду</Button></div>
  </div>;
}
Object.assign(window,{VibeTest,VibeResult});
