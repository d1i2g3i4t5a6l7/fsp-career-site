// Связь сайта с бэкендом (workspace): тест на грейд, ИИ-ассистент, тесты задачи, проверка, грейд.
// Сайт обращается к нему по своему же адресу api/workspace/… — запрос пересылает nginx, при разработке — Vite.
const WS_BASE='api/workspace';
const CAND_KEY='fspk_cand';
// Номер кандидата в бэкенде — свой у каждого браузера; «Сбросить мои данные» на главной заводит нового
function candId(){try{let id=localStorage.getItem(CAND_KEY);if(!id){id='me-'+Math.random().toString(36).slice(2,10);localStorage.setItem(CAND_KEY,id)}return id}catch(e){return 'me'}}
async function wsApi(path,opt={}){
  const has=opt.body!==undefined;let r;
  try{r=await fetch(WS_BASE+path,{method:opt.method||'GET',headers:has?{'Content-Type':'application/json'}:undefined,body:has?JSON.stringify(opt.body):undefined})}
  catch(e){throw new Error('Нет связи с сервером. Проверьте подключение и попробуйте ещё раз.')}
  const data=await r.json().catch(()=>({}));
  if(!r.ok){
    // Показываем только понятные человеку ответы: правила тестов, «ассистент недоступен»; остальное — общими словами
    const text=typeof data.detail==='string'&&(r.status===409||r.status===400||r.status===502)?data.detail
      :r.status>=500?'Сервер временно недоступен, попробуйте ещё раз.':r.status===404?'Не найдено — обновите страницу.':'Не удалось выполнить действие, попробуйте ещё раз.';
    const e=new Error(text);e.status=r.status;throw e}
  return data;
}
const cand=()=>'/candidates/'+encodeURIComponent(candId());
const WS={
  start:(category,level)=>wsApi('/attempts',{method:'POST',body:{candidate_id:candId(),category,level}}),
  attempt:id=>wsApi('/attempts/'+id),
  save:(id,path,content)=>wsApi('/attempts/'+id+'/files',{method:'PUT',body:{path,content}}),
  ask:(id,text)=>wsApi('/attempts/'+id+'/assistant',{method:'POST',body:{text}}),
  edit:(id,editId,ok)=>wsApi('/attempts/'+id+'/edits/'+editId+'/'+(ok?'accept':'reject'),{method:'POST',body:{}}),
  tests:id=>wsApi('/attempts/'+id+'/tests',{method:'POST'}),
  submit:id=>wsApi('/attempts/'+id+'/submit',{method:'POST'}),
  focus:(id,left)=>wsApi('/attempts/'+id+'/focus',{method:'POST',body:{left}}),
  result:id=>wsApi('/attempts/'+id+'/result'),
  grade:category=>wsApi(cand()+'/grade?category='+encodeURIComponent(category)),
  history:()=>wsApi(cand()+'/attempts'),
  // «Проверка оценок» у работодателя: очередь сданных тестов и решение человека по попытке
  reviews:()=>wsApi('/reviews'),
  review:(id,body)=>wsApi('/attempts/'+id+'/review',{method:'POST',body}),
};
// Тест на грейд идёт один за раз: начатый продолжаем, иначе начинаем новый
async function startOrResume(category,level){
  const active=(await WS.history()).find(a=>a.status==='active');
  return active?WS.attempt(active.attempt_id):WS.start(category,level);
}
// Результат теста: опрашиваем, пока ИИ проверяет решение
function useAttemptResult(id){
  const [res,setRes]=React.useState(null);const [err,setErr]=React.useState('');
  React.useEffect(()=>{if(!id)return;let stop=false,t;
    const tick=async()=>{try{const r=await WS.result(id);if(stop)return;setRes(r);setErr('');if(!['done','failed'].includes(r.status))t=setTimeout(tick,2000)}catch(e){if(!stop){setErr(e.message);t=setTimeout(tick,4000)}}};
    tick();return()=>{stop=true;clearTimeout(t)}},[id]);
  return [res,err];
}
const fmtDate=iso=>iso?new Date(iso).toLocaleDateString('ru-RU'):'';
Object.assign(window,{WS,candId,startOrResume,useAttemptResult,fmtDate});
