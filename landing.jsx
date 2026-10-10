// ── Главная: продающий лендинг ──
const WEIGHTS=[
 ['Тест на грейд',45,'var(--fsp-blue)','Лайвкодинг на время, оценка ИИ, подтверждение эксперта'],
 ['Совпадение стека',25,'var(--accent-text)','С потребностью конкретной компании'],
 ['Достижения ФСП',15,'var(--fsp-red)','Финалы и призовые места. Нет истории — не штраф'],
 ['Активность',10,'var(--disc-uas)','Как давно решали регулярное задание'],
 ['Эксперт',5,'var(--disc-security)','Оценку ИИ подтвердил инженер']];
const FLOW=[
 ['</>','Решаете задачу','40 минут лайвкодинга. Условие собрано из реальных вакансий вашей категории.'],
 ['{•}','Получаете категорию','ИИ оценивает сразу, эксперт подтверждает. Например, Backend · Middle, 2 место из 38.'],
 ['→','Компания пишет первой','Приглашение приходит сразу с вилкой зарплаты. Без зарплаты его не отправить.'],
 ['✓','Вы решаете','Контакты открываются только после вашего «принять».']];
const VERSUS=[
 ['Кто делает первый шаг','Вы рассылаете резюме','Компания, с конкретным предложением'],
 ['Зарплата','Узнаёте на третьем собеседовании','Указана в самом приглашении'],
 ['Как оценивают навыки','По строчкам в резюме','Тест на время и проверка эксперта'],
 ['Ваши контакты','Видны всем, кто открыл резюме','Только компании, которую вы приняли'],
 ['Олимпиады и хакатоны','Теряются в разделе «Прочее»','До +15 баллов к рейтингу']];
const TICKER=[
 ['Северный код','Мария Л.','Backend · Middle','240–280 тыс. ₽','принято'],
 ['Лаборатория Т','Алексей К.','Backend · Middle','210–250 тыс. ₽','просмотрено'],
 ['Северный код','Игорь С.','Backend · Middle','250–290 тыс. ₽','просмотрено'],
 ['Ростехсеть','Никита Б.','Frontend · Middle','230–270 тыс. ₽','отправлено'],
 ['Медиаплатформа «Кадр»','Артём Ж.','Data / ML · Middle','260–310 тыс. ₽','принято'],
 ['Северный код','Дарья П.','Backend · Middle','220–260 тыс. ₽','отправлено'],
 ['Лаборатория Т','Глеб Ф.','ИБ · Junior','130–160 тыс. ₽','принято']];
const FAQ=[
 ['У меня нет ФСП ID. Я буду ниже в рейтинге?','Нет штрафа: вы ранжируетесь по тесту, стеку и заданиям. Достижения ФСП только добавляют до 15 баллов сверху.'],
 ['Кто увидит мою почту и телефон?','Только компания, чьё приглашение вы приняли, или та, на вакансию которой вы откликнулись сами. До этого работодатель видит «Алексей К.», категорию и результат теста.'],
 ['Что если тест не получится?','Можно сразу сдать тест на грейд ниже. Повторно сменить грейд можно через 3 месяца.'],
 ['Сколько стоит?','Для кандидатов бесплатно. Для компаний — [ТАРИФ ДЛЯ КОМПАНИЙ].']];

const SCENES=[['clock','Тест на 40 минут'],['climb','Место в рейтинге категории'],['offer','Приглашение с зарплатой']];
// Три пиксельные сцены, как в регистрации; активная подсвечивается по очереди.
function MatchMachine(){
  const reduce=React.useMemo(()=>pxReduced(),[]);
  const [act,setAct]=React.useState(0);
  React.useEffect(()=>{if(reduce)return;const i=setInterval(()=>setAct(a=>(a+1)%SCENES.length),2600);return()=>clearInterval(i)},[reduce]);
  return <ol className="mm3" aria-label="Как это работает: тест, рейтинг, приглашение">
    {SCENES.map(([art,t],i)=><li key={art} className={'mm3-i'+(!reduce&&i===act?' on':'')} aria-label={t}>
      <div className="mm3-art"><PixelArt name={art} px={7}/></div>
    </li>)}
  </ol>;
}

function Landing({go,onReset}){
  return <div className="land">
    <header className="land-h">
      <button className="brand brand-btn" style={{padding:0,border:0}} onClick={()=>go('home')} aria-label="На главную"><img src="assets/fsp-mark-dark.png" alt="ФСП"/><div><div className="brand-1">ФСП</div><div className="brand-2">КАРЬЕРА</div></div></button>
      <nav className="land-nav" aria-label="Разделы">
        <a href="#home" onClick={e=>{e.preventDefault();document.getElementById('how').scrollIntoView({behavior:'smooth'})}}>Как это работает</a>
        <a href="#home" onClick={e=>{e.preventDefault();document.getElementById('companies').scrollIntoView({behavior:'smooth'})}}>Компаниям</a>
        <a href="#home" onClick={e=>{e.preventDefault();document.getElementById('faq').scrollIntoView({behavior:'smooth'})}}>Вопросы</a>
      </nav>
      <div className="row-12">
        <Button variant="ghost" size="sm" onClick={()=>go('login')}>Войти</Button>
        <Button size="sm" onClick={()=>go('signup')}>Регистрация</Button>
      </div>
    </header>
    <main>
      <section className="lp-hero">
        <div className="lp-hero-txt">
          <span className="lp-kicker"><i></i>Федерация спортивного программирования · подбор ИТ-специалистов</span>
          <h1 className="lp-title">Пишете код.<br/><span className="lp-hl">Работодатели пишут вам.</span></h1>
          <p className="land-lead">Один тест на 40 минут вместо сотни откликов. Компании сами приходят с предложением, и зарплата указана сразу.</p>
          <div className="row-12" style={{flexWrap:'wrap'}}>
            <Button size="lg" onClick={()=>go('signup')} iconRight="→">Пройти тест на грейд</Button>
            <Button size="lg" variant="secondary" onClick={()=>go('login-employer')}>Я нанимаю</Button>
          </div>
          <ul className="lp-proof">
            <li><b className="pix">40</b><span>минут на тест</span></li>
            <li><b className="pix">₽</b><span>зарплата в приглашении</span></li>
            <li><b className="pix">0</b><span>контактов без согласия</span></li>
          </ul>
        </div>
        <MatchMachine/>
      </section>

      <div className="lp-ticker" aria-label="Последние приглашения">
        <div className="lp-track">{[...TICKER,...TICKER].map(([co,who,cat,sal,st],i)=><span key={i} className="lp-tick" aria-hidden={i>=TICKER.length?'true':undefined}>
          <b>{co}</b><span className="lp-arrow">→</span>{who}<span className="hint">{cat}</span><span className="salary-sm">{sal}</span><span className={'lp-st '+(st==='принято'?'ok':'')}>{st}</span></span>)}</div>
      </div>

      <section className="land-sec" id="how">
        <SectionTitle level={2} eyebrow="// как это работает">Четыре шага до оффера</SectionTitle>
        <ol className="lp-flow">{FLOW.map(([g,t,d],i)=><li key={t}>
          <div className="lp-flow-top"><span className="land-n">{String(i+1).padStart(2,'0')}</span><span className="lp-glyph">{g}</span></div>
          <b>{t}</b><span className="hint" style={{fontSize:13}}>{d}</span></li>)}</ol>
      </section>

      <section className="land-sec">
        <SectionTitle level={2} eyebrow="// почему это работает">Найм наоборот</SectionTitle>
        <div className="lp-vs" role="table" aria-label="Сравнение: обычный найм и ФСП Карьера">
          <div className="lp-vs-h" role="row"><span role="columnheader"></span><span role="columnheader" className="cap">Обычный найм</span><span role="columnheader" className="cap lp-vs-us">ФСП Карьера</span></div>
          {VERSUS.map(([k,a,b])=><div key={k} className="lp-vs-r" role="row"><span role="rowheader" className="lp-vs-k">{k}</span><span role="cell" className="lp-vs-a">{a}</span><span role="cell" className="lp-vs-b">{b}</span></div>)}
        </div>
      </section>

      <section className="land-sec">
        <SectionTitle level={2} eyebrow="// рейтинг в категории">100 баллов, и каждый объясним</SectionTitle>
        <div className="panel"><div style={{padding:24}} className="stack-24">
          <div className="lp-stack" aria-hidden="true">{WEIGHTS.map(([k,v,c],i)=><div key={k} style={{flexGrow:v,background:c,animationDelay:i*90+'ms'}}><span>{v}</span></div>)}</div>
          <div className="lp-legend">{WEIGHTS.map(([k,v,c,n])=><div key={k}><i style={{background:c}}></i><div><b>{k} · {v}</b><span className="hint">{n}</span></div></div>)}</div>
        </div></div>
      </section>

      <section className="land-sec lp-two" id="companies">
        <div className="lp-aud">
          <div className="row-12" style={{justifyContent:'space-between'}}><span className="eyebrow">кандидатам</span><PixelArt name="laptop" px={3}/></div>
          <h3>Резюме больше не главное</h3>
          <ul className="ul"><li>Категория и место в ней вместо рассылки резюме</li><li>Предложения с зарплатой до начала общения</li><li>Регулярные задания от компаний держат профиль свежим</li><li>Повышение грейда — тест вместе с ИИ-ассистентом</li></ul>
          <div><Button onClick={()=>go('signup')} iconRight="→">Получить категорию</Button></div>
        </div>
        <div className="lp-aud lp-aud-alt">
          <div className="row-12" style={{justifyContent:'space-between'}}><span className="eyebrow">компаниям</span><PixelArt name="search" px={3}/></div>
          <h3>Подборка вместо поиска</h3>
          <ul className="ul"><li>Опишите потребность — подборка пересчитается сразу</li><li>У каждого кандидата две понятные причины, почему он в списке</li><li>Ваши инженеры подтверждают оценки ИИ</li><li>Можно пригласить без опубликованной вакансии</li></ul>
          <div><Button variant="secondary" onClick={()=>go('login-employer')} iconRight="→">Открыть подборку</Button></div>
        </div>
      </section>

      <section className="land-sec" id="faq">
        <SectionTitle level={2} eyebrow="// вопросы">Коротко о важном</SectionTitle>
        <div className="lp-faq">{FAQ.map(([q,a],i)=><details key={q} open={i===0}><summary>{q}</summary><p>{a}</p></details>)}</div>
      </section>

      <section className="lp-final">
        <div className="lp-final-in">
          <PixelArt name="result" px={6}/>
          <div className="stack-16" style={{minWidth:0}}>
            <h2>Следующий оффер начинается с 40 минут кода</h2>
            <div className="row-12" style={{flexWrap:'wrap'}}>
              <Button size="lg" onClick={()=>go('signup')} iconRight="→" style={{background:'var(--fsp-white)',color:'var(--fsp-black)'}}>Начать тест</Button>
              <Button size="lg" variant="secondary" onClick={()=>go('login')}>У меня уже есть аккаунт</Button>
            </div>
          </div>
        </div>
        <div className="strip" aria-hidden="true" style={{margin:0}}></div>
      </section>
    </main>
    <footer className="land-f">
      <span className="hint">ФСП Карьера · Хакатон ФСП, спецтрек, 2026 · вход через ФСП ID (Keycloak, OIDC)</span>
      <Button variant="ghost" size="sm" onClick={onReset}>Сбросить мои данные</Button>
    </footer>
  </div>;
}

const TEST_ACCOUNTS={
 candidate:{email:'a.korneev@mail.ru',pass:'fsp-test-2026',who:'Алексей Корнеев · Backend · Middle',to:'c-home'},
 employer:{email:'i.volkova@severcode.ru',pass:'fsp-test-2026',who:'Ирина Волкова · HR · Северный код',to:'e-shortlist'}};
function Login({go,role:initRole='candidate'}){
  const [role,setRole]=React.useState(initRole);
  const [f,setF]=React.useState(TEST_ACCOUNTS[initRole]);
  const [err,setErr]=React.useState('');const [busy,setBusy]=React.useState(false);
  const pick=r=>{setRole(r);setF(TEST_ACCOUNTS[r]);setErr('')};
  const submit=e=>{e.preventDefault();const a=TEST_ACCOUNTS[role];
    if(f.email.trim().toLowerCase()!==a.email||f.pass!==a.pass){setErr('Неверная почта или пароль. Для теста используйте данные из подсказки ниже.');return}
    setErr('');setBusy(true);setTimeout(()=>go(a.to),500)};
  return <div className="land">
    <header className="land-h">
      <button className="brand brand-btn" style={{padding:0,border:0}} onClick={()=>go('home')} aria-label="На главную"><img src="assets/fsp-mark-dark.png" alt="ФСП"/><div><div className="brand-1">ФСП</div><div className="brand-2">КАРЬЕРА</div></div></button>
      <Button variant="ghost" size="sm" onClick={()=>go('signup')}>Регистрация →</Button>
    </header>
    <main className="login">
      <div className="art-row"><SectionTitle level={1} eyebrow="{•} вход">Войти в кабинет</SectionTitle><PixelArt name="account" px={6}/></div>
      <div className="role-sw" style={{margin:0}} role="group" aria-label="Тип аккаунта">
        <button type="button" className={role==='candidate'?'on':''} aria-pressed={role==='candidate'} onClick={()=>pick('candidate')}>Кандидат</button>
        <button type="button" className={role==='employer'?'on':''} aria-pressed={role==='employer'} onClick={()=>pick('employer')}>Работодатель</button>
      </div>
      <form className="panel" onSubmit={submit} noValidate>
        <div style={{padding:24}} className="stack-16">
          <label className="field" htmlFor="login-email"><span className="cap">Электронная почта</span><input id="login-email" className="inp" type="email" autoComplete="username" value={f.email} onChange={e=>setF({...f,email:e.target.value})}/></label>
          <label className="field" htmlFor="login-pass"><span className="cap">Пароль</span><input id="login-pass" className="inp" type="password" autoComplete="current-password" value={f.pass} onChange={e=>setF({...f,pass:e.target.value})}/></label>
          {err&&<div className="note" role="alert" style={{borderColor:'var(--fsp-red)',color:'var(--fg-1)'}}>{err}</div>}
          <div className="row-12" style={{flexWrap:'wrap'}}>
            <button type="submit" className="btn-submit" disabled={busy}>{busy?'Входим…':'Войти'}</button>
            <Button variant="secondary" onClick={()=>go(TEST_ACCOUNTS[role].to)}>Войти через ФСП ID</Button>
          </div>
        </div>
      </form>
      <div className="note test-acc">
        <div className="cap" style={{color:'var(--warning)'}}>Тестовый аккаунт · уже подставлен</div>
        <div className="kv-grid"><span className="hint">Почта</span><code>{TEST_ACCOUNTS[role].email}</code><span className="hint">Пароль</span><code>{TEST_ACCOUNTS[role].pass}</code><span className="hint">Профиль</span><span>{TEST_ACCOUNTS[role].who}</span></div>
      </div>
      <div className="hint">Нет аккаунта? <a href="#signup" style={{color:'var(--accent-text)'}}>Зарегистрироваться</a> — опрос и тест на грейд займут около часа.</div>
    </main>
  </div>;
}
Object.assign(window,{Landing,Login,TEST_ACCOUNTS});
