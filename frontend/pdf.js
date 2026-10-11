// PDF-профиль кандидата без библиотек: страница A4 рисуется на canvas шрифтами сайта
// и упаковывается в PDF-файл одной картинкой. Текст в файле — изображение, выделить его нельзя.
const A4=[595.28,841.89],PX=3; // размер в пунктах; 3 пикселя на пункт — около 216 точек на дюйм
const INK='#1B1C21',MUTED='#5c5d63',FAINT='#9B9C9E',RULE='#D9DADD',BLUE='#402FFF';

function wrapText(g,text,width){
  const lines=[];
  for(const para of String(text||'').split('\n')){
    let line='';
    for(const word of para.split(/\s+/).filter(Boolean)){
      const next=line?line+' '+word:word;
      if(line&&g.measureText(next).width>width){lines.push(line);line=word}else line=next;
    }
    if(line)lines.push(line);
  }
  return lines;
}

async function drawProfile(p){
  const [W,H]=A4,M=56,c=document.createElement('canvas');
  c.width=Math.round(W*PX);c.height=Math.round(H*PX);
  const g=c.getContext('2d');g.scale(PX,PX);
  g.fillStyle='#fff';g.fillRect(0,0,W,H);
  await Promise.all(['400','500','700'].map(w=>document.fonts.load(w+' 12px "JetBrains Mono"','Аа Zz 0')));
  const logo=new Image();logo.src='assets/fsp-mark-light.png';
  await logo.decode().catch(()=>{});
  const bottom=H-M-28;let y=M;
  const font=(size,weight)=>{g.font=weight+' '+size+'px "JetBrains Mono", monospace'};
  // Абзац с переносом строк; что не помещается на страницу — обрезаем многоточием
  const text=(s,size,{weight=400,color=INK,width=W-2*M,caps=false,after=4}={})=>{
    font(size,weight);g.fillStyle=color;g.letterSpacing=caps?'1.2px':'0px';
    const lines=wrapText(g,caps?String(s).toUpperCase():s,width);
    for(let i=0;i<lines.length;i++){
      const more=i<lines.length-1&&y+2*size*1.45>bottom;
      y+=size*1.45;g.fillText(more?'…':lines[i],M,y);
      if(more){y=bottom;break}
    }
    g.letterSpacing='0px';y+=after;
  };
  const rule=(before,after)=>{y+=before;g.fillStyle=RULE;g.fillRect(M,y,W-2*M,0.75);y+=after};
  const section=(title,body)=>{if(!body||y>=bottom)return;text(title,7.5,{weight:500,color:FAINT,caps:true,after:2});text(body,10);y+=12};

  if(logo.naturalWidth)g.drawImage(logo,W-M-40,M,40,40*logo.naturalHeight/logo.naturalWidth);
  text('// профиль кандидата · ФСП Карьера',8,{color:BLUE,width:W-2*M-56,after:10});
  text(p.name,20,{weight:700,caps:true,width:W-2*M-56,after:6});
  // Категория как на сайте: специализация, грейд — синим
  font(13,700);g.letterSpacing='0.5px';y+=13*1.45;
  const spec=p.spec.toUpperCase()+' · ';g.fillStyle=INK;g.fillText(spec,M,y);
  g.fillStyle=p.grade?BLUE:FAINT;g.fillText((p.grade||'без грейда').toUpperCase(),M+g.measureText(spec).width,y);
  g.letterSpacing='0px';y+=4;
  text(p.status,9.5,{color:MUTED,after:2});
  text(p.contacts.filter(Boolean).join(' · '),9.5,{color:MUTED});
  rule(12,18);
  section('Стек',p.stack.join(' · '));
  section('Опыт'+(p.years?' · '+p.years:''),p.exp);
  section('Роли в команде',p.roles);
  section('Достижения ФСП',p.fsp.map(f=>f.place+' — '+f.event).join('\n'));
  section('Софт-скиллы',p.soft.join(' · '));
  // Подвал: откуда профиль и когда сформирован
  y=H-M-14;rule(0,0);y+=14;
  text('Сформировано на платформе «ФСП Карьера» · '+new Date().toLocaleDateString('ru-RU'),7.5,{color:FAINT,after:0});
  return c;
}

// Картинка страницы → PDF: каталог, страница, изображение, команда «нарисовать на весь лист»
async function canvasToPdf(c,title){
  const {width:w,height:h}=c;let data,filter;
  if(window.CompressionStream){ // без потерь: пиксели RGB, сжатие deflate
    const px=c.getContext('2d').getImageData(0,0,w,h).data,rgb=new Uint8Array(w*h*3);
    for(let i=0,j=0;i<px.length;i+=4){rgb[j++]=px[i];rgb[j++]=px[i+1];rgb[j++]=px[i+2]}
    data=new Uint8Array(await new Response(new Blob([rgb]).stream().pipeThrough(new CompressionStream('deflate'))).arrayBuffer());filter='/FlateDecode';
  }else{
    data=new Uint8Array(await (await new Promise(r=>c.toBlob(r,'image/jpeg',0.92))).arrayBuffer());filter='/DCTDecode';
  }
  const enc=new TextEncoder(),parts=[],offs=[];let len=0;
  const add=x=>{const b=typeof x==='string'?enc.encode(x):x;parts.push(b);len+=b.length};
  const obj=(n,dict,stream)=>{offs[n]=len;add(n+' 0 obj\n'+dict+'\n');if(stream){add('stream\n');add(stream);add('\nendstream\n')}add('endobj\n')};
  const utf16=s=>'<FEFF'+[...s].map(ch=>ch.charCodeAt(0).toString(16).padStart(4,'0')).join('')+'>';
  const [W,H]=A4,draw=enc.encode('q '+W+' 0 0 '+H+' 0 0 cm /Im0 Do Q');
  add('%PDF-1.4\n');
  obj(1,'<< /Type /Catalog /Pages 2 0 R >>');
  obj(2,'<< /Type /Pages /Kids [3 0 R] /Count 1 >>');
  obj(3,'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 '+W+' '+H+'] /Resources << /XObject << /Im0 4 0 R >> >> /Contents 5 0 R >>');
  obj(4,'<< /Type /XObject /Subtype /Image /Width '+w+' /Height '+h+' /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter '+filter+' /Length '+data.length+' >>',data);
  obj(5,'<< /Length '+draw.length+' >>',draw);
  obj(6,'<< /Title '+utf16(title)+' /Creator '+utf16('ФСП Карьера')+' >>');
  const xref=len;
  add('xref\n0 7\n0000000000 65535 f \n'+offs.slice(1).map(o=>String(o).padStart(10,'0')+' 00000 n \n').join(''));
  add('trailer\n<< /Size 7 /Root 1 0 R /Info 6 0 R >>\nstartxref\n'+xref+'\n%%EOF\n');
  return new Blob(parts,{type:'application/pdf'});
}

const TRANSLIT={а:'a',б:'b',в:'v',г:'g',д:'d',е:'e',ё:'e',ж:'zh',з:'z',и:'i',й:'y',к:'k',л:'l',м:'m',н:'n',о:'o',п:'p',р:'r',с:'s',т:'t',у:'u',ф:'f',х:'kh',ц:'ts',ч:'ch',ш:'sh',щ:'shch',ы:'y',э:'e',ю:'yu',я:'ya'};
// Скачать PDF-профиль; возвращает имя файла: profile_korneev.pdf
async function downloadProfilePdf(p){
  const surname=[...(p.name.trim().split(/\s+/)[0]||'').toLowerCase()].map(ch=>TRANSLIT[ch]??ch).join('').replace(/[^a-z0-9]/g,'');
  const file='profile_'+(surname||'candidate')+'.pdf';
  const blob=await canvasToPdf(await drawProfile(p),'Профиль кандидата — '+p.name);
  const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=file;
  document.body.appendChild(a);a.click();a.remove();
  setTimeout(()=>URL.revokeObjectURL(a.href),10000);
  return file;
}
Object.assign(window,{downloadProfilePdf});
