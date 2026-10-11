// Адреса страниц: #home, #signup, #signup-3, #c-invites, #e-shortlist …
const LS='fspk_site_v1';
const C_PAGES=['home','grade','resume','invites','tasks','vacancies','settings'];
const E_PAGES=['need','shortlist','bank','invites','vacancies','review','company'];
function parseRoute(h){
  h=(h||'').replace(/^#/,'');
  let m;
  if(h==='login')return {view:'login',role:'candidate'};
  if(h==='login-employer')return {view:'login',role:'employer'};
  if(h==='signup')return {view:'signup',step:0};
  if((m=h.match(/^signup-([0-6])$/)))return {view:'signup',step:+m[1]};
  if((m=h.match(/^c-([a-z]+)$/))&&C_PAGES.includes(m[1]))return {view:'candidate',page:m[1]};
  if((m=h.match(/^e-([a-z]+)$/))&&E_PAGES.includes(m[1]))return {view:'employer',page:m[1]};
  return {view:'home'};
}
function loadSaved(){try{return JSON.parse(localStorage.getItem(LS))||{}}catch(e){return {}}}
function useRoute(){
  const [r,setR]=React.useState(()=>parseRoute(location.hash));
  React.useEffect(()=>{const f=()=>{setR(parseRoute(location.hash));window.scrollTo(0,0)};window.addEventListener('hashchange',f);return()=>window.removeEventListener('hashchange',f)},[]);
  // Тот же адрес (например, логотип на главной) — страница не меняется, поэтому просто наверх
  const go=to=>{if(('#'+to)!==location.hash)location.hash=to;else{setR(parseRoute(to));window.scrollTo({top:0,behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'})}};
  return [r,go];
}
function App(){
  const saved=React.useMemo(loadSaved,[]);
  const [route,go]=useRoute();
  const [hasFsp,setHasFsp]=React.useState(saved.hasFsp!==undefined?saved.hasFsp:true);
  const [invites,setInvites]=React.useState(saved.invites||D.INVITES);
  const [responses,setResponses]=React.useState(saved.responses||D.RESPONSES);
  const [need,setNeed]=React.useState(saved.need||D.NEED);
  const [stars,setStars]=React.useState(saved.stars||['k2041']);
  const [drawer,setDrawer]=React.useState(null);const [inv,setInv]=React.useState(null);
  const [msg,setMsg]=React.useState('');
  const [reviewN,setReviewN]=React.useState(0);
  const countReview=q=>setReviewN(q.filter(x=>x.needs_review).length);
  React.useEffect(()=>{if(route.view==='employer')WS.reviews().then(countReview).catch(()=>{})},[route.view,route.page]);
  React.useEffect(()=>{try{localStorage.setItem(LS,JSON.stringify({hasFsp,invites,responses,need,stars}))}catch(e){}},[hasFsp,invites,responses,need,stars]);
  React.useEffect(()=>{setDrawer(null);setInv(null)},[route.view,route.page]);
  const toast=m=>{setMsg(m);clearTimeout(window.__tt);window.__tt=setTimeout(()=>setMsg(''),2600)};
  // Грейд и тесты кандидата с бэкенда — для кабинетов; на главной, при входе и регистрации не запрашиваем
  const inCab=route.view==='candidate'||route.view==='employer';
  const [tests,reloadTests]=useMyTests(D.specLabel(D.CANDIDATES.find(c=>c.id==='me').spec),inCab?route.view+route.page:null);
  const me=useMe(hasFsp,tests);
  const fixC=c=>c&&c.id==='me'?me:c;
  const toggleStar=id=>setStars(s=>s.includes(id)?s.filter(x=>x!==id):[...s,id]);
  const today=new Date().toLocaleDateString('ru-RU');
  const send=f=>{const c=inv;setInvites(v=>[{id:'i'+Date.now(),cand:c.id,company:D.COMPANY.name,title:f.title,from:f.from,to:f.to,status:'sent',date:today,contact:f.contact,msg:f.msg},...v]);setInv(null);toast('Приглашение отправлено: '+c.name+(c.id==='me'?' — откройте кабинет кандидата, чтобы увидеть его':''))};
  const reset=()=>{setInvites(D.INVITES);setResponses(D.RESPONSES);setNeed(D.NEED);setStars(['k2041']);setHasFsp(true);try{localStorage.removeItem('fspk_view');localStorage.removeItem('fspk_cand');localStorage.removeItem('fspk_reg')}catch(e){}toast('Данные сброшены')};
  const newInv=invites.filter(i=>i.cand==='me'&&i.status==='sent').length;
  const cNav=[{sep:'Профиль'},{id:'home',g:'{•}',label:'Профиль и категория'},{id:'grade',g:'▲',label:'Грейд и тесты'},{id:'resume',g:'[ ]',label:'Резюме'},{sep:'Работа'},{id:'invites',g:'→',label:'Приглашения',badge:newInv},{id:'tasks',g:'</>',label:'Задания',badge:2},{id:'vacancies',g:'//',label:'Вакансии'},{sep:'Аккаунт'},{id:'settings',g:'⚙',label:'Настройки'}];
  const eNav=[{sep:'Подбор'},{id:'need',g:'{•}',label:'Потребность'},{id:'shortlist',g:'▲',label:'Подборка'},{id:'bank',g:'[ ]',label:'Банк кандидатов'},{id:'invites',g:'→',label:'Приглашения'},{sep:'Найм'},{id:'vacancies',g:'//',label:'Вакансии',badge:1},{id:'review',g:'>|<',label:'Проверка оценок',badge:reviewN},{sep:'Компания'},{id:'company',g:'⚙',label:'Профиль компании'}];
  const goE=p=>go('e-'+p),goC=p=>go('c-'+p);
  const empProps={need,invites,openCand:c=>setDrawer(fixC(c)),openInvite:c=>setInv(fixC(c)),stars,toggleStar,me,toast,go:goE};
  const setRole=r=>go(r==='candidate'?'c-home':'e-shortlist');
  const onEmployerSignup=()=>go('login-employer');
  // Новый аккаунт начинает с чистого листа: без чужих приглашений и откликов; ФСП — по выбору на шаге «ФСП ID»
  const onAccount=()=>{newAccount();setHasFsp(true);setInvites(v=>v.filter(i=>i.cand!=='me'));setResponses([])};
  let content;
  if(route.view==='home') content=<Landing go={go} onReset={reset}/>;
  else if(route.view==='login') content=<Login key={route.role} role={route.role} go={go}/>;
  else if(route.view==='signup') content=<Onboarding step={route.step} setStep={s=>go(s===0?'signup':'signup-'+s)} hasFsp={hasFsp} setHasFsp={setHasFsp} onAccount={onAccount} onHome={()=>go('home')} onEmployer={onEmployerSignup} onDone={()=>{go('c-home');toast('Добро пожаловать в кабинет')}} onExit={()=>go('c-home')}/>;
  else {
    const isC=route.view==='candidate';
    content=<Shell role={route.view} setRole={setRole} nav={isC?cNav:eNav} page={route.page} setPage={isC?goC:goE} onHome={()=>go('home')}
      user={isC?{initials:'АК',name:'Алексей Корнеев',sub:D.specLabel(me.spec)+' · '+(me.grade?D.gradeLabel(me.grade):'без грейда')}:{initials:'ИВ',name:'Ирина Волкова',sub:'HR · Северный код'}}>
      {isC?({home:<CandHome me={me} invites={invites} go={goC} onTests={reloadTests}/>,invites:<CandInvites invites={invites} setInvites={setInvites} toast={toast}/>,tasks:<CandTasks toast={toast}/>,vacancies:<CandVacancies responses={responses} setResponses={setResponses} toast={toast}/>,grade:<CandGrade me={me} onTests={reloadTests}/>,resume:<CandResume me={me} toast={toast}/>,settings:<CandSettings hasFsp={hasFsp} setHasFsp={setHasFsp}/>}[route.page])
      :({need:<EmpNeed need={need} setNeed={setNeed} go={goE} toast={toast}/>,shortlist:<Shortlist {...empProps}/>,bank:<EmpBank {...empProps}/>,invites:<EmpInvites invites={invites} openCand={empProps.openCand}/>,vacancies:<EmpVacancies openCand={empProps.openCand} toast={toast}/>,review:<EmpReview toast={toast} onQueue={countReview}/>,company:<EmpCompany toast={toast}/>}[route.page])}
    </Shell>;
  }
  return <>
    {content}
    {drawer&&<CandDrawer c={drawer} need={need} invites={invites} onClose={()=>setDrawer(null)} onInvite={c=>{setDrawer(null);setInv(c)}}/>}
    {inv&&<InviteModal c={inv} need={need} onClose={()=>setInv(null)} onSend={send}/>}
    <Toast text={msg}/>
  </>;
}
ReactDOM.createRoot(document.getElementById('root')).render(<App/>);
