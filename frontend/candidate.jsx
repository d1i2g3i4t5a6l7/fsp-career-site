function useMe(hasFsp){
  const base=D.CANDIDATES.find(c=>c.id==='me');
  return {...base,fsp:hasFsp?base.fsp:[]};
}
function rankInCat(me){
  const pool=D.CANDIDATES.filter(c=>c.spec===me.spec&&c.grade===me.grade).map(c=>c.id==='me'?me:c);
  const sorted=pool.map(c=>({c,s:D.score(c,{stack:[]}).total})).sort((a,b)=>b.s-a.s);
  return {pos:sorted.findIndex(x=>x.c.id==='me')+1,of:38};
}

function CandHome({me,invites,go}){
  const r=rankInCat(me);const myInv=invites.filter(i=>i.cand==='me');
  const pct=Math.round(r.pos/r.of*100);
  return <div className="page">
    <PageHead eyebrow="// мой профиль" title="Профиль и категория"/>
    <div className="hero-cat">
      <div className="stack-16">
        <span className="cap">Категория, которую видят работодатели</span>
        <div className="big-cat">{D.specLabel(me.spec)} <span style={{color:'var(--accent-text)'}}>{D.gradeLabel(me.grade)}</span></div>
        <div className="row-12" style={{flexWrap:'wrap'}}><Tag discipline="security">Подтверждено экспертом</Tag><Tag>Тест {me.test}/100</Tag><Tag>Обновлён {me.fresh} дн. назад</Tag></div>
      </div>
      <div className="hero-stats">
        <div><span className="cap">Место в категории</span><div className="pix">{r.pos}<small>/{r.of}</small></div><span className="hint">топ {pct}%</span></div>
        <div><span className="cap">Приглашений</span><div className="pix">{myInv.length}</div><span className="hint">{myInv.filter(i=>i.status==='sent').length} новых</span></div>
      </div>
    </div>
    <div className="grid-2">
      <Panel title="Достижения ФСП" action={<Button variant="ghost" size="sm" onClick={()=>go('settings')}>ФСП ID →</Button>}>
        {me.fsp.length?<FspBadge fsp={me.fsp}/>:<div className="stack-12"><div style={{fontSize:14}}>Истории ФСП нет. Вы ранжируетесь по тесту и регулярным заданиям.</div><div className="hint">Участие в соревнованиях ФСП добавит до 15 баллов к рейтингу в категории.</div></div>}
      </Panel>
      <Panel title="Почему вы на этом месте">
        {(()=>{const s=D.score(me,{stack:[]});return <div className="stack-12">
          {[['Тест',s.parts.test,45],['ФСП',s.parts.fsp,15],['Свежесть заданий',s.parts.fresh,10],['Экспертная проверка',s.parts.expert,5]].map(([k,v,m])=><div key={k} className="eval-row"><span style={{fontSize:13}}>{k}</span><Bar value={v} max={m}/><span className="num">{Math.round(v)}/{m}</span></div>)}
          <div className="hint">Ещё 25 баллов — совпадение стека с потребностью конкретной компании.</div></div>})()}
      </Panel>
    </div>
    <Panel title="Последние приглашения" action={<Button variant="ghost" size="sm" onClick={()=>go('invites')}>Все →</Button>} pad={0}>
      {myInv.length?myInv.slice(0,3).map(i=><div key={i.id} className="list-row" onClick={()=>go('invites')}>
        <div style={{minWidth:0}}><div style={{fontWeight:700,fontSize:14}}>{i.title}</div><div className="hint">{i.company} · {i.date}</div></div>
        <div className="salary-sm">{D.rub(i.from,i.to)}</div><Status s={i.status}/></div>):<div style={{padding:24}}><Empty art="mail" title="Пока приглашений нет" text="Компании просматривают вашу категорию. Решайте регулярные задания — это поднимает профиль в выдаче."/></div>}
    </Panel>
  </div>;
}

function CandInvites({invites,setInvites,toast}){
  const mine=invites.filter(i=>i.cand==='me');
  const [sel,setSel]=React.useState(mine[0]&&mine[0].id);
  const cur=mine.find(i=>i.id===sel)||mine[0];
  React.useEffect(()=>{if(cur&&cur.status==='sent')setInvites(v=>v.map(i=>i.id===cur.id?{...i,status:'viewed'}:i))},[cur&&cur.id]);
  const [decl,setDecl]=React.useState(false);const [reason,setReason]=React.useState('');
  React.useEffect(()=>{setDecl(false);setReason('')},[cur&&cur.id]);
  const act=(st)=>{setInvites(v=>v.map(i=>i.id===cur.id?{...i,status:st,...(st==='declined'?{reason:reason.trim()}:{})}:i));toast(st==='accepted'?'Приглашение принято — компания видит ваши контакты':'Приглашение отклонено')};
  if(!mine.length) return <div className="page"><PageHead eyebrow="// входящие" title="Приглашения"/><Empty art="mail" title="Пока приглашений нет" text="Компании видят вашу категорию и сами выходят на связь с предложением и зарплатой."/></div>;
  return <div className="page">
    <PageHead eyebrow="// входящие" title="Приглашения" sub="Компания пишет первой и сразу называет зарплату. Ваши контакты откроются, только если вы примете приглашение."/>
    <div className="split">
      <div className="panel" style={{alignSelf:'start'}}>{mine.map(i=><div key={i.id} className={'list-row col'+(cur.id===i.id?' sel':'')} onClick={()=>setSel(i.id)}>
        <div className="row-12" style={{justifyContent:'space-between',width:'100%'}}><span style={{fontWeight:700,fontSize:14}}>{i.company}</span><Status s={i.status}/></div>
        <div style={{fontSize:13}}>{i.title}</div><div className="salary-sm">{D.rub(i.from,i.to)}</div></div>)}</div>
      <Panel eyebrow={cur.company+' · '+cur.date} title={cur.title}>
        <div className="stack-24">
          <div><span className="cap">Зарплата, на руки до НДФЛ</span><div className="salary">{D.rub(cur.from,cur.to)}</div></div>
          {cur.msg&&<blockquote className="quote">{cur.msg}</blockquote>}
          <div className="grid-2"><Kv k="Формат" v="Удалённо"/><Kv k="Связь" v={cur.status==='accepted'?cur.contact:'откроется после принятия'}/></div>
          {(cur.status==='sent'||cur.status==='viewed')&&!decl&&<div className="row-12"><Button onClick={()=>act('accepted')}>Принять</Button><Button variant="secondary" onClick={()=>setDecl(true)}>Отклонить</Button></div>}
          {(cur.status==='sent'||cur.status==='viewed')&&decl&&<div className="stack-12"><Field label="Причина отказа" hint="Компания увидит её вместе со статусом"><Textarea rows={3} value={reason} onChange={e=>setReason(e.target.value)} placeholder="Например: вилка ниже ожиданий, не интересен домен"/></Field><div className="row-12"><Button variant="red" disabled={!reason.trim()} onClick={()=>act('declined')}>Отклонить</Button><Button variant="ghost" onClick={()=>setDecl(false)}>Отмена</Button></div></div>}
          {cur.status==='accepted'&&<div className="note ok">Вы приняли приглашение. Компания получила ваши контакты: почту и телефон из профиля.</div>}
          {cur.status==='declined'&&<div className="note">{cur.reason?'Вы отклонили приглашение. Компания видит причину: «'+cur.reason+'».':'Вы отклонили приглашение.'}</div>}
        </div>
      </Panel>
    </div>
  </div>;
}

function CandTasks({toast}){
  const [tasks,setTasks]=React.useState(D.DAILY);
  const [open,setOpen]=React.useState(null);const [ans,setAns]=React.useState('');
  const t=tasks.find(x=>x.id===open);
  const send=()=>{setTasks(v=>v.map(x=>x.id===open?{...x,status:'review'}:x));setOpen(null);setAns('');toast('Ответ отправлен — профиль обновлён')};
  return <div className="page">
    <PageHead eyebrow="// регулярные задания" title="Задания от компаний" sub="Короткие задачи из реальной работы компаний. Решение или описание подхода держит профиль свежим: компании видят дату последнего задания."/>
    <div className="cards-3">{tasks.map(x=><div key={x.id} className="tcard">
      <div className="row-12" style={{justifyContent:'space-between'}}><span className="cap">{x.company}</span>{x.status!=='open'&&<Status s={x.status}/>}</div>
      <div style={{fontWeight:700,fontSize:16}}>{x.title}</div>
      <div className="row-12"><ATag>{x.kind}</ATag><span className="hint">~{x.mins} мин · {x.due}</span></div>
      {x.status==='done'?<div className="hint">Оценка: {x.score}/100</div>:x.status==='open'?<Button size="sm" onClick={()=>setOpen(x.id)}>Открыть</Button>:<div className="hint">Компания посмотрит ответ</div>}
    </div>)}</div>
    {t&&<Modal title={t.title} onClose={()=>setOpen(null)} footer={<><Button variant="ghost" onClick={()=>setOpen(null)}>Позже</Button><Button onClick={send} disabled={!ans.trim()}>Отправить</Button></>}>
      <div className="stack-16"><div className="row-12"><span className="cap">{t.company}</span><ATag>{t.kind}</ATag></div>
        <p style={{margin:0,fontSize:14,lineHeight:1.6}}>{t.text}</p>
        <Field label={t.kind==='Решить'?'Решение':'Подход к решению'}><Textarea rows={8} value={ans} onChange={e=>setAns(e.target.value)} placeholder="Ключ идемпотентности по event_id + уникальный индекс…"/></Field></div>
    </Modal>}
  </div>;
}

function CandVacancies({responses,setResponses,toast}){
  const [tab,setTab]=React.useState('all');
  const has=id=>responses.find(r=>r.vac===id);
  const apply=v=>{setResponses(r=>[{id:'r'+Date.now(),vac:v.id,status:'sent',date:'07.10.2026'},...r]);toast('Отклик отправлен в «'+v.company+'»')};
  return <div className="page">
    <PageHead eyebrow="// вакансии" title="Вакансии" sub="Если хотите проявить инициативу сами. Отклик открывает компании ваш профиль и контакты."/>
    <div className="tabs">{[['all','Все вакансии'],['mine','Мои отклики · '+responses.length]].map(([id,l])=><button key={id} className={tab===id?'on':''} onClick={()=>setTab(id)}>{l}</button>)}</div>
    {tab==='all'?<div className="panel">{D.VACANCIES.map(v=><div key={v.id} className="vac-row">
      <div style={{minWidth:0}}><div style={{fontWeight:700}}>{v.title}</div><div className="hint">{v.company} · {v.city} · {v.format} · {v.posted}</div>
        <div className="chips" style={{marginTop:8}}>{v.stack.map(s=><Tag key={s}>{s}</Tag>)}</div></div>
      <div className="salary-sm">{D.rub(v.from,v.to)}</div>
      <div>{has(v.id)?<Status s={has(v.id).status}/>:<Button size="sm" variant="secondary" onClick={()=>apply(v)}>Откликнуться</Button>}</div></div>)}</div>
    :<div className="panel">{responses.length?responses.map(r=>{const v=D.VACANCIES.find(x=>x.id===r.vac);return <div key={r.id} className="vac-row">
      <div><div style={{fontWeight:700}}>{v.title}</div><div className="hint">{v.company} · отклик {r.date}</div></div><div className="salary-sm">{D.rub(v.from,v.to)}</div><Status s={r.status}/></div>}):<div style={{padding:24}}><Empty title="Откликов нет"/></div>}</div>}
  </div>;
}

const GRADE_IDS=['intern','junior','middle','senior'];
function CandGrade({me}){
  const [modal,setModal]=React.useState(null);
  const [vibe,setVibe]=React.useState(null);
  // Грейд, доступные тесты и история — с бэкенда; пока их нет, показываем демо-профиль
  const [st,setSt]=React.useState(null);const [hist,setHist]=React.useState([]);
  const cat=D.specLabel(me.spec);
  React.useEffect(()=>{if(vibe)return;WS.grade(cat).then(setSt).catch(()=>setSt(null));WS.history().then(setHist).catch(()=>setHist([]))},[vibe]);
  if(vibe&&vibe.run) return <VibeTest category={cat} level={vibe.run} onExit={()=>setVibe(null)} onSubmit={id=>setVibe({attempt:id})}/>;
  if(vibe) return <VibeResult attemptId={vibe.attempt} onExit={()=>setVibe(null)}/>;
  const grade=st&&st.grade||me.grade;const gi=GRADE_IDS.indexOf(grade);
  const up=GRADE_IDS[gi+1],down=gi>0?GRADE_IDS[gi-1]:null;
  const why=l=>{const t=st&&st.tests.find(x=>x.level===l);return t&&!t.available?t.reason+(t.available_from?' (с '+fmtDate(t.available_from)+')':''):''};
  const active=hist.find(a=>a.status==='active');
  const story=[...hist].reverse().map(a=>({date:fmtDate(a.started_at),text:'Тест на '+D.gradeLabel(a.level)+' «'+a.task_title+'» — '+(a.status==='active'?'идёт':a.final?'ИИ '+a.ai_score+'/100'+(a.final.score!==a.ai_score?', после проверки эксперта '+a.final.score+'/100':'')+', '+(a.annulled?'аннулирован':a.final.passed?'пройден':'не пройден'):a.grading_status==='failed'?'проверка не удалась':'проверяется')+(a.tab_leaves?' · уходов со вкладки: '+a.tab_leaves:'')}));
  return <div className="page">
    <PageHead eyebrow="// грейд" title="Грейд и тесты"/>
    <div className="grid-2">
      <Panel title="Текущий статус"><div className="stack-16">
        <div className="big-cat" style={{fontSize:36}}>{D.specLabel(me.spec)} · <span style={{color:'var(--accent-text)'}}>{D.gradeLabel(grade)}</span></div>
        <Kv k="Отрасли" v="Финтех"/><Kv k="Тест" v={st&&st.grade?st.score+'/100 · подтверждён '+fmtDate(st.confirmed_at):me.test+'/100 · подтверждён экспертом 09.07.2026'}/>
      </div></Panel>
      <Panel title="Смена грейда"><div className="stack-16">
        <div className="row-12">{st&&st.frozen_until?<Tag discipline="red">Тесты заморожены до {fmtDate(st.frozen_until)}</Tag>:st&&!st.change_available?<Tag>Доступно с {fmtDate(st.next_change_at)}</Tag>:<Tag discipline="security">Доступно сейчас</Tag>}<span className="hint">раз в 3 месяца</span></div>
        <div className="vibe-promo"><div className="row-12"><span className="beta">Тестовый режим</span><b style={{fontSize:14}}>Вайбкодинг с ИИ</b></div><span className="hint">Тест на повышение проходит вместе с ИИ-ассистентом: оцениваем, как вы ставите ему задачу и проверяете его код.</span></div>
        {active?<div><Button onClick={()=>setVibe({run:active.level})}>Вернуться к тесту на {D.gradeLabel(active.level)}</Button></div>
        :<div className="row-12" style={{flexWrap:'wrap'}}>{up&&<Button onClick={()=>setModal('up')} disabled={!!why(up)}>Тест на {D.gradeLabel(up)}</Button>}{down&&<Button variant="secondary" onClick={()=>setModal('down')} disabled={!!why(down)}>Тест на {D.gradeLabel(down)}</Button>}</div>}
        {!active&&(why(up)||why(down))&&<div className="hint">{up&&down&&why(up)===why(down)?why(up):[up&&why(up)&&D.gradeLabel(up)+': '+why(up),down&&why(down)&&D.gradeLabel(down)+': '+why(down)].filter(Boolean).join(' · ')}</div>}
      </div></Panel>
    </div>
    <Panel title="История опроса и тестов">
      <Timeline items={[
        {date:'02.07.2026',text:'Опрос: Backend · Python, Go, PostgreSQL, Kafka, Docker · опыт 3 года'},
        {date:'02.07.2026',text:'Тест на Middle «Дедупликация платёжных событий» — ИИ 82/100'},
        {date:'09.07.2026',text:'Эксперт «Северный код» скорректировал оценку: 86/100 (граничные случаи по ts учтены частично)'},
        {date:'09.07.2026',text:'Присвоена категория Backend · Middle'},...story]}/>
    </Panel>
    {modal==='up'&&<Modal title={'Тест на '+D.gradeLabel(up)+' · вайбкодинг'} onClose={()=>setModal(null)} footer={<><Button variant="ghost" onClick={()=>setModal(null)}>Отмена</Button><Button onClick={()=>{setModal(null);setVibe({run:up})}}>Начать, 30 минут</Button></>}>
      <div className="stack-16"><div className="row-12"><span className="beta">Тестовый режим</span></div>
      <p style={{margin:0,fontSize:14,lineHeight:1.6}}>Одна задача уровня {D.gradeLabel(up)}, 30 минут. Рядом с редактором — ИИ-ассистент: просите код, спорьте с ним, правьте вручную. Ассистент может ошибаться, и заметить это — часть проверки.</p>
      <ul className="ul"><li>Все запросы к ассистенту и принятые правки попадают в отчёт</li><li>Итог выносит ИИ по критериям задачи, эксперт может его скорректировать</li><li>Уход со вкладки запрещён: он отмечается в результате, попытку могут аннулировать</li><li>При успехе грейд меняется, следующая смена — через 3 месяца</li></ul></div>
    </Modal>}
    {modal==='down'&&<Modal title={'Тест на '+D.gradeLabel(down)} onClose={()=>setModal(null)} footer={<><Button variant="ghost" onClick={()=>setModal(null)}>Отмена</Button><Button variant="red" onClick={()=>{setModal(null);setVibe({run:down})}}>Понимаю, начать</Button></>}>
      <p style={{margin:0,fontSize:14,lineHeight:1.6}}>Если пройдёте тест, категория сменится на {D.specLabel(me.spec)} · {D.gradeLabel(down)}, и следующая смена будет доступна через 3 месяца. Текущий грейд принудительно не понижается — тест вы проходите по своему решению.</p>
    </Modal>}
  </div>;
}

function CandResume({me,toast}){
  const [pdf,setPdf]=React.useState(false);
  return <div className="page">
    <PageHead eyebrow="// резюме" title="Резюме" action={<div className="row-12"><Button variant="secondary" size="sm" onClick={()=>toast('Распознано: ФИО, контакты, стек, опыт, роли')}>Загрузить PDF</Button><Button size="sm" onClick={()=>setPdf(true)}>Сформировать PDF-профиль</Button></div>} sub="Резюме дополняет профиль. Выдача для работодателей строится по категории и тесту, а не по тексту резюме."/>
    <Panel><div className="stack-24">
      <div className="grid-2"><Field label="ФИО"><Input defaultValue="Корнеев Алексей Игоревич"/></Field><Field label="Город"><Input defaultValue="Казань"/></Field>
        <Field label="Почта"><Input defaultValue="a.korneev@mail.ru"/></Field><Field label="Телефон"><Input defaultValue="+7 917 000-12-34"/></Field></div>
      <Field label="Стек"><div className="chips">{me.stack.map(s=><Tag key={s}>{s}</Tag>)}</div></Field>
      <div className="grid-2"><Field label="Роли в команде"><Input defaultValue="Разработчик, ревьюер, дежурный on-call"/></Field><Field label="Стаж"><Input defaultValue="3 года"/></Field></div>
      <Field label="Опыт"><Textarea rows={5} defaultValue={'2023–н.в. · Платёжный сервис, backend-разработчик\nСервис выплат на Go и Python, миграция с RabbitMQ на Kafka, p99 с 800 до 120 мс.'}/></Field>
      <Field label="Софт-скиллы"><div className="chips">{['Менторство','Публичные выступления','Документирование','Работа с бизнесом'].map((s,i)=><Chip key={s} on={i<3} small>{s}</Chip>)}</div></Field>
    </div></Panel>
    {pdf&&<Modal title="PDF-профиль" width={560} onClose={()=>setPdf(false)} footer={<Button onClick={()=>{setPdf(false);toast('profile_korneev.pdf скачан')}}>Скачать PDF</Button>}>
      <div className="pdf">
        <div className="row-12" style={{justifyContent:'space-between'}}><b>КОРНЕЕВ АЛЕКСЕЙ</b><img src="assets/fsp-mark-dark.png" alt="" style={{height:28,filter:'invert(1) hue-rotate(180deg)'}}/></div>
        <div style={{fontSize:12}}>Backend · Middle · тест 86/100, подтверждено экспертом</div>
        <hr/><div style={{fontSize:11}}>Python · Go · PostgreSQL · Kafka · Docker</div>
        {me.fsp.length?<div style={{fontSize:11}}>ФСП: {me.fsp.map(f=>f.place+', '+f.event).join('; ')}</div>:null}
        <div style={{fontSize:11}}>2023–н.в. · Платёжный сервис, backend-разработчик</div>
        <div className="pdf-ph"></div><div className="pdf-ph" style={{width:'70%'}}></div>
      </div>
    </Modal>}
  </div>;
}

function CandSettings({hasFsp,setHasFsp}){
  const [p,setP]=React.useState({name:false,city:true,fsp:true,tasks:true,photo:false,open:true});
  const s=(k)=>v=>setP(o=>({...o,[k]:v}));
  return <div className="page">
    <PageHead eyebrow="// настройки" title="Настройки"/>
    <div className="grid-2" style={{alignItems:'start'}}>
      <Panel title="Что видит работодатель до принятия приглашения" pad={0}>
        <Toggle on={p.open} onChange={s('open')} label="Профиль виден в банке кандидатов" hint="Выключите, если сейчас не ищете работу"/>
        <Toggle on={p.name} onChange={s('name')} label="Полное имя" hint="Иначе — «Алексей К.»"/>
        <Toggle on={p.city} onChange={s('city')} label="Город"/>
        <Toggle on={p.fsp} onChange={s('fsp')} label="Достижения ФСП"/>
        <Toggle on={p.tasks} onChange={s('tasks')} label="Решения регулярных заданий"/>
        <div style={{padding:'16px 20px'}} className="hint">Почта и телефон не видны никогда — до момента, пока вы не примете приглашение или не откликнитесь.</div>
      </Panel>
      <div className="stack-24">
        <Panel title="ФСП ID"><div className="stack-16">
          {hasFsp?<><div className="row-12"><Tag discipline="security">Привязан</Tag><span className="hint">ID 0047-2219 · синхр. 06.10.2026</span></div><Button variant="secondary" size="sm" onClick={()=>setHasFsp(false)}>Отвязать</Button></>
          :<><div style={{fontSize:14}}>Не привязан. Достижения ФСП поднимают профиль внутри категории.</div><div><Button size="sm" onClick={()=>setHasFsp(true)}>Привязать ФСП ID</Button></div></>}
        </div></Panel>
        <Panel title="Согласия"><div className="stack-12">
          <label className="check"><input type="checkbox" defaultChecked/><span>Обработка персональных данных (152-ФЗ) · 02.07.2026</span></label>
          <label className="check"><input type="checkbox" defaultChecked/><span>Публикация обезличенного профиля в банке кандидатов</span></label>
          <label className="check"><input type="checkbox" defaultChecked/><span>Получение регулярных заданий от компаний</span></label>
          <div><Button variant="ghost" size="sm">Удалить аккаунт и данные</Button></div>
        </div></Panel>
      </div>
    </div>
  </div>;
}
Object.assign(window,{CandHome,CandInvites,CandTasks,CandVacancies,CandGrade,CandResume,CandSettings,useMe});
