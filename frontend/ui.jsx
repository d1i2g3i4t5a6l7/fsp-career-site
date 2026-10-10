const DS = window.DesignSystem_2ade33;
const { Button, Tag, SectionTitle, StatBlock, Timeline } = DS;
const D = window.FSPDATA;

function Panel({title,eyebrow,action,children,pad=24,style,bodyStyle}){
  return <section className="panel" style={style}>
    {(title||action)&&<div className="panel-h"><div>{eyebrow&&<div className="eyebrow">{eyebrow}</div>}{title&&<div className="panel-t">{title}</div>}</div>{action}</div>}
    <div style={{padding:pad,...bodyStyle}}>{children}</div></section>;
}
function Field({label,hint,children,style}){
  return <label className="field" style={style}><span className="cap">{label}</span>{children}{hint&&<span className="hint">{hint}</span>}</label>;
}
function Input(p){return <input className="inp" {...p}/>;}
function Textarea(p){return <textarea className="inp" rows={4} {...p}></textarea>;}
function Select({options,value,onChange,style}){
  return <select className="inp" value={value} onChange={e=>onChange(e.target.value)} style={style}>{options.map(o=><option key={o.id||o} value={o.id||o}>{o.label||o}</option>)}</select>;
}
function Chip({on,onClick,children,small}){
  return <button type="button" className={'chip'+(on?' on':'')+(small?' sm':'')} onClick={onClick}>{children}</button>;
}
function Toggle({on,onChange,label,hint}){
  return <div className="toggle-row" onClick={()=>onChange(!on)}>
    <div style={{minWidth:0}}><div style={{fontSize:14}}>{label}</div>{hint&&<div className="hint">{hint}</div>}</div>
    <span className={'tgl'+(on?' on':'')}><span></span></span></div>;
}
function Bar({value,max=100,color='var(--accent)',h=6}){
  return <div style={{height:h,background:'var(--bg-surface-2)',width:'100%'}}><div style={{height:'100%',width:Math.max(0,Math.min(100,value/max*100))+'%',background:color,transition:'width var(--dur-base) var(--ease)'}}></div></div>;
}
const STATUS={sent:['Отправлено','neutral'],viewed:['Просмотрено','accent'],accepted:['Принято','green'],declined:['Отклонено','red'],new:['Новый','accent'],open:['Открыто','accent'],done:['Выполнено','green'],review:['На проверке','neutral']};
function ATag({children}){return <Tag tone="accent" style={{color:'var(--accent-text)'}}>{children}</Tag>;}
function Status({s}){
  const [l,t]=STATUS[s]||[s,'neutral'];
  if(t==='green') return <Tag discipline="security">{l}</Tag>;
  if(t==='red') return <Tag discipline="red">{l}</Tag>;
  return t==='accent'?<ATag>{l}</ATag>:<Tag tone={t}>{l}</Tag>;
}
function Modal({title,onClose,children,width=640,footer}){
  React.useEffect(()=>{const f=e=>e.key==='Escape'&&onClose();window.addEventListener('keydown',f);return()=>window.removeEventListener('keydown',f)},[]);
  return <div className="overlay" onMouseDown={e=>{if(e.target===e.currentTarget)onClose()}}>
    <div className="modal" style={{width}}>
      <div className="panel-h"><div className="panel-t">{title}</div><button className="x" onClick={onClose} aria-label="Закрыть">×</button></div>
      <div className="modal-b">{children}</div>
      {footer&&<div className="modal-f">{footer}</div>}</div></div>;
}
function Drawer({onClose,children,width=560}){
  React.useEffect(()=>{const f=e=>e.key==='Escape'&&onClose();window.addEventListener('keydown',f);return()=>window.removeEventListener('keydown',f)},[]);
  return <div className="overlay right" onMouseDown={e=>{if(e.target===e.currentTarget)onClose()}}><div className="drawer" style={{width}}>{children}</div></div>;
}
function Kv({k,v}){return <div className="kv"><span className="cap">{k}</span><span>{v}</span></div>;}
function Glyph({children,color='var(--accent)'}){return <span className="glyph" style={{color}}>{children}</span>;}
function FspBadge({fsp,compact}){
  if(!fsp||!fsp.length) return <span className="nofsp">нет истории ФСП</span>;
  const best=fsp[0];
  if(compact) return <span className="fspb"><img src="assets/fsp-mark-dark.png" alt=""/>{best.place}</span>;
  return <div style={{display:'flex',flexDirection:'column',gap:8}}>{fsp.map((f,i)=><div key={i} className="fsprow">
    <img src="assets/fsp-mark-dark.png" alt=""/><div><div style={{fontSize:14,fontWeight:700}}>{f.place}</div><div className="hint">{f.event} · {D.DISC[f.disc]}</div></div></div>)}</div>;
}
function Toast({text}){return text?<div className="toast">{text}</div>:null;}
function PageHead({eyebrow,title,action,sub}){
  return <div className="page-head"><SectionTitle level={2} eyebrow={eyebrow} action={action}>{title}</SectionTitle>{sub&&<p className="sub">{sub}</p>}</div>;
}
function Empty({art='search',title,text,action}){
  return <div className="empty"><PixelArt name={art} px={4} style={{marginBottom:6}}/><div style={{fontWeight:700}}>{title}</div>{text&&<div className="hint" style={{maxWidth:420}}>{text}</div>}{action}</div>;
}

function Shell({role,setRole,nav,page,setPage,user,onHome,children}){
  return <div className="app">
    <aside className="side">
      <button className="brand brand-btn" onClick={onHome} aria-label="На главную"><img src="assets/fsp-mark-dark.png" alt="ФСП"/><div><div className="brand-1">ФСП</div><div className="brand-2">КАРЬЕРА</div></div></button>
      <div className="role-sw">{[['candidate','Кандидат'],['employer','Работодатель']].map(([id,l])=><button key={id} className={role===id?'on':''} onClick={()=>setRole(id)}>{l}</button>)}</div>
      <nav className="nav">{nav.map(n=>n.sep?<div key={n.sep} className="nav-sep">{n.sep}</div>:
        <button key={n.id} className={'nav-i'+(page===n.id?' on':'')} onClick={()=>setPage(n.id)}>
          <span className="nav-g">{n.g}</span><span style={{flex:1}}>{n.label}</span>{n.badge?<span className="badge">{n.badge}</span>:null}</button>)}</nav>
      <div className="me"><div className="ava">{user.initials}</div><div style={{minWidth:0}}><div style={{fontSize:13,fontWeight:700,whiteSpace:'nowrap',overflow:'hidden',textOverflow:'ellipsis'}}>{user.name}</div><div className="hint">{user.sub}</div></div></div>
    </aside>
    <main className="main">{children}</main>
  </div>;
}

Object.assign(window,{ATag,Panel,Field,Input,Textarea,Select,Chip,Toggle,Bar,Status,Modal,Drawer,Kv,Glyph,FspBadge,Toast,PageHead,Empty,Shell,Button,Tag,SectionTitle,StatBlock,Timeline,D});
