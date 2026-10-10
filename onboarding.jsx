const OB_STEPS=['Аккаунт','Почта','ФСП ID','Опрос','Грейд','Тест','Категория'];
const INDUSTRIES=['Финтех','Госсектор','E-commerce','Медиа','Промышленность','Игры','Телеком','Образование'];

function Onboarding({hasFsp,onDone,onExit,onEmployer,onHome,step=0,setStep}){
  const [f,setF]=React.useState({email:'a.korneev@mail.ru',pass:'fsp-test-2026',consent:true,code:'',fsp:null,spec:'backend',stack:['Python','PostgreSQL'],exp:'3',ind:['Финтех'],grade:'middle'});
  const set=(k,v)=>setF(o=>({...o,[k]:v}));
  const next=()=>setStep(step+1);
  const tog=(k,v)=>set(k,f[k].includes(v)?f[k].filter(x=>x!==v):[...f[k],v]);
  const wide=step===5;
  return <div className="ob">
    <header className="ob-h">
      <button className="brand brand-btn" style={{padding:0,border:0}} onClick={onHome} aria-label="На главную"><img src="assets/fsp-mark-dark.png" alt="ФСП"/><div><div className="brand-1">ФСП</div><div className="brand-2">КАРЬЕРА</div></div></button>
      <ol className="stepper">{OB_STEPS.map((s,i)=><li key={s} className={i===step?'on':i<step?'done':''} aria-current={i===step?'step':undefined}><span>{String(i+1).padStart(2,'0')}</span>{s}</li>)}</ol>
      <div className="row-12"><div className="role-sw" style={{margin:0,width:220}}><button className="on">Кандидат</button><button onClick={onEmployer}>Работодатель</button></div><Button variant="ghost" size="sm" onClick={onExit}>Пропустить →</Button></div>
    </header>
    <div className="ob-body" style={{maxWidth:wide?1280:720}}>
      {step===0&&<ObAccount f={f} set={set} next={next}/>}
      {step===1&&<ObCode f={f} set={set} next={next}/>}
      {step===2&&<ObFsp hasFsp={hasFsp} f={f} set={set} next={next}/>}
      {step===3&&<ObSurvey f={f} set={set} tog={tog} next={next}/>}
      {step===4&&<ObGrade f={f} set={set} next={next}/>}
      {step===5&&<ObTest f={f} next={next}/>}
      {step===6&&<ObResult f={f} onDone={()=>onDone(f)}/>}
    </div>
    {step===0&&<div className="strip"></div>}
  </div>;
}

function ObAccount({f,set,next}){
  return <div className="stack-24">
    <ArtHead art="account"><SectionTitle level={1} eyebrow="{•} регистрация соискателя">Работодатели придут к вам сами</SectionTitle></ArtHead>
    <p className="sub">Пройдите опрос и тест на грейд — система определит вашу категорию. Компании видят категорию и результат теста, а не резюме, и приходят с конкретным предложением и зарплатой.</p>
    <Panel>
      <div className="stack-16">
        <Field label="Электронная почта"><Input value={f.email} onChange={e=>set('email',e.target.value)}/></Field>
        <Field label="Пароль" hint="Не короче 10 символов"><Input type="password" value={f.pass} placeholder="••••••••••" onChange={e=>set('pass',e.target.value)}/></Field>
        <label className="check"><input type="checkbox" checked={f.consent} onChange={e=>set('consent',e.target.checked)}/><span>Согласен на обработку персональных данных в соответствии с 152-ФЗ. Контакты станут видны компании только после того, как я приму приглашение.</span></label>
        <div className="row-12"><Button disabled={!f.consent||!f.email} onClick={next}>Создать аккаунт</Button><Button variant="secondary" onClick={next}>Войти через ФСП ID</Button></div>
        <div className="hint">Уже есть аккаунт? <a href="#login" style={{color:'var(--accent-text)'}}>Войти</a></div>
      </div>
    </Panel>
  </div>;
}

function ObCode({f,set,next}){
  React.useEffect(()=>{const t=setTimeout(()=>set('code','482913'),700);return()=>clearTimeout(t)},[]);
  return <div className="stack-24">
    <ArtHead art="email"><SectionTitle level={1} eyebrow="{•} подтверждение">Проверьте почту</SectionTitle></ArtHead>
    <p className="sub">Отправили код на <b style={{color:'var(--fg-1)'}}>{f.email}</b>. Код действует 15 минут.</p>
    <Panel><div className="stack-16">
      <div className="code-cells">{[0,1,2,3,4,5].map(i=><span key={i} className={f.code[i]?'on':''}>{f.code[i]||''}</span>)}</div>
      <div className="row-12"><Button disabled={f.code.length<6} onClick={next}>Подтвердить</Button><Button variant="ghost" size="sm">Отправить ещё раз</Button></div>
    </div></Panel>
  </div>;
}

function ObFsp({hasFsp,f,set,next}){
  const [linking,setLinking]=React.useState(false);
  const link=()=>{setLinking(true);setTimeout(()=>{set('fsp',hasFsp?'linked':'empty');setLinking(false)},900)};
  const me=D.CANDIDATES.find(c=>c.id==='me');
  return <div className="stack-24">
    <ArtHead art="fsp"><SectionTitle level={1} eyebrow="{•} необязательно">Привяжите ФСП ID</SectionTitle></ArtHead>
    <p className="sub">Результаты соревнований Федерации подтверждают навыки и поднимают вас выше в категории. Без истории ФСП вы ранжируетесь по тесту и заданиям — это не штраф.</p>
    <Panel>
      {f.fsp===null&&<div className="stack-16">
        <div className="row-12"><Button onClick={link} disabled={linking}>{linking?'Подключаемся…':'Войти через ФСП ID'}</Button><Button variant="ghost" onClick={()=>{set('fsp','skipped');next()}}>У меня нет ФСП ID</Button></div>
        <div className="hint">Мы получим только: дисциплины, мероприятия, место и год. Отвязать можно в настройках.</div>
      </div>}
      {f.fsp==='linked'&&<div className="stack-16">
        <div className="row-12"><Tag discipline="security">ФСП ID привязан</Tag><span className="hint">ID 0047-2219</span></div>
        <FspBadge fsp={me.fsp}/>
        <div><Button onClick={next} iconRight="→">Дальше</Button></div>
      </div>}
      {f.fsp==='empty'&&<div className="stack-16">
        <div className="row-12"><Tag discipline="security">ФСП ID привязан</Tag></div>
        <div style={{fontSize:14}}>Участий в соревнованиях пока нет. Когда появятся — профиль обновится автоматически.</div>
        <div><Button onClick={next} iconRight="→">Дальше</Button></div>
      </div>}
    </Panel>
  </div>;
}

function ObSurvey({f,set,tog,next}){
  const [parsing,setParsing]=React.useState(false);
  const pdf=()=>{setParsing(true);setTimeout(()=>{set('stack',['Python','Go','PostgreSQL','Kafka','Docker']);set('exp','3');setParsing(false)},1000)};
  return <div className="stack-24">
    <ArtHead art="survey"><SectionTitle level={1} eyebrow="{•} опрос · 1 из 2">Специализация и стек</SectionTitle></ArtHead>
    <Panel action={<Button variant="secondary" size="sm" onClick={pdf}>{parsing?'Распознаём…':'Заполнить из PDF-резюме'}</Button>} title="Опрос">
      <div className="stack-24">
        <Field label="Специализация"><div className="chips">{D.SPECS.map(s=><Chip key={s.id} on={f.spec===s.id} onClick={()=>{set('spec',s.id);set('stack',[])}}>{s.label}</Chip>)}</div></Field>
        <Field label="Стек — отметьте, с чем работали в продакшене"><div className="chips">{D.STACKS[f.spec].map(s=><Chip key={s} on={f.stack.includes(s)} onClick={()=>tog('stack',s)}>{s}</Chip>)}</div></Field>
        <div className="grid-2">
          <Field label="Коммерческий опыт, лет"><Input value={f.exp} onChange={e=>set('exp',e.target.value)}/></Field>
          <Field label="Формат работы"><Select value="Удалённо" onChange={()=>{}} options={['Удалённо','Гибрид','Офис']}/></Field>
        </div>
        <Field label="Отрасли, которые интересны"><div className="chips">{INDUSTRIES.map(s=><Chip key={s} on={f.ind.includes(s)} onClick={()=>tog('ind',s)}>{s}</Chip>)}</div></Field>
      </div>
    </Panel>
    <div><Button disabled={!f.stack.length} onClick={next} iconRight="→">Выбрать грейд</Button></div>
  </div>;
}

function ObGrade({f,set,next}){
  return <div className="stack-24">
    <ArtHead art="grade"><SectionTitle level={1} eyebrow="{•} опрос · 2 из 2">На какой грейд претендуете?</SectionTitle></ArtHead>
    <p className="sub">Тест проверит заявленный уровень. Если не пройдёте — можно сразу сдать тест на уровень ниже. Грейд меняется не чаще раза в 3 месяца.</p>
    <div className="grade-grid">{D.GRADES.map(g=><button key={g.id} className={'grade-card'+(f.grade===g.id?' on':'')} onClick={()=>set('grade',g.id)}>
      <span className="cap">{D.specLabel(f.spec)}</span><span className="grade-n">{g.label}</span><span className="hint">{g.hint}</span></button>)}</div>
    <Panel title="Что будет на тесте">
      <div className="grid-3">
        <div className="stack-8"><Glyph color="var(--accent-text)">{'</>'}</Glyph><b>Лайвкодинг на время</b><span className="hint">Одна задача, 40 минут. Условие собрано из реальных вакансий вашей категории, данные — уникальные для вас.</span></div>
        <div className="stack-8"><Glyph color="var(--accent-text)">{'{•}'}</Glyph><b>Оценка ИИ</b><span className="hint">Сразу после отправки: корректность, память, граничные случаи, качество кода.</span></div>
        <div className="stack-8"><Glyph color="var(--fsp-red)">{'>|<'}</Glyph><b>Проверка эксперта</b><span className="hint">Инженер компании-партнёра подтверждает или корректирует оценку ИИ.</span></div>
      </div>
    </Panel>
    <div><Button onClick={next} iconRight="→">Начать тест на {D.gradeLabel(f.grade)}</Button></div>
  </div>;
}

const SKELETON=`WINDOW = 600  # секунд

def dedupe(stream):
    # ваше решение
    ...
`;
function ObTest({f,next}){
  const T=D.TASK;
  const [code,setCode]=React.useState(SKELETON);
  const [left,setLeft]=React.useState(T.minutes*60-7*60-12);
  const [phase,setPhase]=React.useState('code');
  React.useEffect(()=>{const t=setInterval(()=>setLeft(l=>Math.max(0,l-1)),1000);return()=>clearInterval(t)},[]);
  const submit=()=>{setPhase('eval');setTimeout(next,1800)};
  const mm=String(Math.floor(left/60)).padStart(2,'0'),ss=String(left%60).padStart(2,'0');
  const lines=code.split('\n').length;
  return <div className="test">
    <div className="test-bar">
      <div className="row-12"><ATag>{D.specLabel(f.spec)} · {D.gradeLabel(f.grade)}</ATag><span className="hint">Вариант #A7-3F1 · {T.from}</span></div>
      <div className="timer"><span className="cap">Осталось</span><span className="timer-n">{mm}:{ss}</span></div>
    </div>
    <div className="test-grid">
      <Panel title={T.title} eyebrow="Задача 1 из 1">
        <div className="stack-16">
          <p style={{margin:0,fontSize:14,lineHeight:1.6,textWrap:'pretty'}}>{T.text}</p>
          <div><div className="cap" style={{marginBottom:8}}>Что проверяется</div><ul className="ul">{T.checks.map(c=><li key={c}>{c}</li>)}</ul></div>
          <div className="code-sm">{`>>> list(dedupe([e1, e2, e1, e3]))\n[e1, e2, e3]`}</div>
          <div className="hint">Можно пользоваться документацией. Вставка большого фрагмента кода и уход со вкладки отмечаются в отчёте для эксперта.</div>
        </div>
      </Panel>
      <section className="panel editor">
        <div className="panel-h"><div className="row-12"><span className="tab on">solution.py</span><span className="tab">tests.py</span></div></div>
        <div className="ed">
          <div className="ed-ln">{Array.from({length:Math.max(lines,18)},(_,i)=><div key={i}>{i+1}</div>)}</div>
          <textarea spellCheck="false" value={code} onChange={e=>setCode(e.target.value)}></textarea>
        </div>
        <div className="ed-f">
          <span className="hint">{phase==='eval'?'ИИ проверяет решение: 18 тестов, анализ сложности…':'Python 3.12 · автосохранение'}</span>
          <div className="row-12"><Button variant="secondary" size="sm">Запустить тесты</Button><Button size="sm" onClick={submit} disabled={phase==='eval'}>{phase==='eval'?'Проверяем…':'Отправить решение'}</Button></div>
        </div>
      </section>
    </div>
  </div>;
}

function ObResult({f,onDone}){
  const total=Math.round(D.AI_EVAL.reduce((a,e)=>a+e.v,0)/D.AI_EVAL.length);
  return <div className="stack-24">
    <ArtHead art="result"><SectionTitle level={1} eyebrow="{•} результат">Категория присвоена</SectionTitle></ArtHead>
    <div className="grid-2" style={{alignItems:'stretch'}}>
      <Panel><div className="stack-16">
        <span className="cap">Ваша категория</span>
        <div className="big-cat">{D.specLabel(f.spec)}<br/><span style={{color:'var(--accent-text)'}}>{D.gradeLabel(f.grade)}</span></div>
        <div className="row-12"><Tag tone="neutral">ИИ-оценка</Tag><span className="hint">Эксперт подтвердит до 09.10</span></div>
      </div></Panel>
      <Panel><div className="stack-16">
        <span className="cap">Оценка ИИ</span>
        <StatBlock value={total} label="из 100 · порог Middle — 70" size="sm"/>
      </div></Panel>
    </div>
    <Panel title="Разбор решения">
      <div className="stack-16">{D.AI_EVAL.map(e=><div key={e.k} className="eval-row">
        <div style={{fontSize:14,fontWeight:700}}>{e.k}</div><Bar value={e.v} color={e.v<70?'var(--warning)':'var(--accent)'}/><div className="num">{e.v}</div>
        <div className="hint" style={{gridColumn:'1 / -1'}}>{e.note}</div></div>)}</div>
    </Panel>
    <p className="sub">Профиль уже виден работодателям в категории с пометкой «ИИ-оценка». После проверки эксперта она сменится на «Подтверждено». Следующая смена грейда — с 07.01.2027.</p>
    <div><Button onClick={onDone} iconRight="→">Перейти в кабинет</Button></div>
  </div>;
}
Object.assign(window,{Onboarding});
