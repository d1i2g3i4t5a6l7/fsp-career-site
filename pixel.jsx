const PX_PAL={b:'var(--fsp-blue)',B:'var(--fsp-digital)',r:'var(--fsp-red)',w:'var(--fsp-white)',g:'var(--fsp-gray-middle)',l:'var(--fsp-gray-light-2)',k:'var(--fsp-black)',y:'var(--disc-robotics)',p:'var(--accent-text)',G:'var(--disc-security)'};
const PX_SPRITES={
bot:`
.......r........
.......r........
....wwwwwwww....
...wbbbbbbbbw...
...wbkkbbkkbw...
...wbkwbbkwbw...
..rwbbbbbbbbwr..
...wbbkkkkbbw...
...wbbbbbbbbw...
....wwwwwwww....
......wwww......
...pbbbbbbbbp...
..pbbbwbbrbbbp..
..wbbbbbbbbbbw..
...bbbbbbbbbb...
...kk......kk...`,
trophy:`
...yyyyyyyyyy...
.wwyyyyyyyyyyww.
.w.yyyyywyyyy.w.
.w.yyyywwyyyy.w.
..wyyyyywyyyyw..
...yyyyywyyyy...
....yyyyyyyy....
.....yyyyyy.....
.......yy.......
.......yy.......
.....yyyyyy.....
....bbbbbbbb....
....bwwrbbbb....
....bbbbbbbb....`,
mail:`
................
.wwwwwwwwwwwwww.
.wbwwwwwwwwwwbw.
.wwbwwwwwwwwbww.
.wwwbwwwwwwbwww.
.wwwwbwrrwbwwww.
.wwwwwbrrbwwwww.
.wwwwwwbbwwwwww.
.wwwwwwwwwwwwww.
.wwwwwwwwwwwwww.
................`,
search:`
....wwwww.......
...w.....w......
..w.pp....w.....
..w.p.....w.....
..w.......w.....
..w.......w.....
...w.....w......
....wwwwwbb.....
..........bb....
...........bb...
............bb..
.............b..`,
laptop:`
..gggggggggggg..
..gkkkkkkkkkkg..
..gkbbkkkkkkkg..
..gkkkppkkkkkg..
..gkkkkkrkkkkg..
..gkkpppppkkkg..
..gkkkkkkkkkkg..
..gggggggggggg..
.llllllllllllll.
llllllllllllllll`};

const pxG=s=>s.trim().split('\n');
const pxRows=(rows,map)=>rows.map((r,i)=>map[i]!=null?map[i]:r);
const pxSet=(rows,pts)=>{const a=rows.map(r=>[...r]);pts.forEach(([x,y,c])=>{if(a[y]&&x>=0&&x<a[y].length)a[y][x]=c});return a.map(r=>r.join(''))};
const pxBlank=(w,h)=>Array.from({length:h},()=>'.'.repeat(w));

const PX_ANIM=(()=>{
  // Аккаунт: робот мигает антенной, моргает, машет рукой
  const B=pxG(PX_SPRITES.bot);
  const off=pxRows(B,{0:'.......w........'});
  const blink=pxRows(B,{4:'...wbbbbbbbbw...',5:'...wbkkbbkkbw...'});
  const arm=pxSet(B,[[13,12,'.'],[13,13,'.'],[12,12,'b']]);
  const w1=pxSet(arm,[[13,11,'p'],[14,10,'p'],[14,9,'w']]);
  const w2=pxSet(arm,[[13,11,'p'],[14,11,'p'],[15,10,'w']]);
  const account={fps:5,frames:[B,B,off,B,blink,B,w1,w2,w1,w2,w1,B,off,B]};

  // Почта: конверт открывается, письмо с кодом выезжает
  const C=pxG(`
................
................
................
................
.wwwwwwwwwwwwww.
.wbwwwwwwwwwwbw.
.wwbwwwwwwwwbww.
.wwwbwwwwwwbwww.
.wwwwbwrrwbwwww.
.wwwwwbrrbwwwww.
.wwwwwwbbwwwwww.
.wwwwwwwwwwwwww.
.wwwwwwwwwwwwww.
................`);
  const O=pxG(`
................
.......gg.......
.....gggggg.....
...gggggggggg...
.gggggggggggggg.
.wggggggggggggw.
.wwggggggggggww.
.wwwggggggggwww.
.wwwwwwrrwwwwww.
.wwwwwwwwwwwwww.
.wwwwwwwwwwwwww.
.wwwwwwwwwwwwww.
.wwwwwwwwwwwwww.
................`);
  const LET=['llllllllll','lpplpplppl','llllllllll','lbbbbbbbbl','llllllllll','llllllllll','llllllllll','llllllllll'];
  const letter=y0=>{const a=O.map(r=>[...r]);LET.forEach((r,dy)=>[...r].forEach((c,dx)=>{const y=y0+dy,x=3+dx;if(a[y]&&'g.'.includes(a[y][x]))a[y][x]=c}));return a.map(r=>r.join(''))};
  const email={fps:6,frames:[C,C,C,C,O,letter(4),letter(2),letter(0),letter(0),letter(0),letter(0),letter(0),letter(2),letter(4),O,C]};

  // ФСП ID: карточка сканируется
  const ID=pxG(`
................
.gggggggggggggg.
.gBBBBBBBBBBBBg.
.gBpppBBwwwwwBg.
.gBpwpBBBBBBBBg.
.gBpppBBwwwBBBg.
.gBBBBBBBBBBBBg.
.gBrBbBwBBBBBBg.
.gBBBBBBBBBBBBg.
.gggggggggggggg.`);
  const scan=r=>ID.map((row,i)=>i===r?row.replace(/B/g,'G'):row);
  const okId=pxSet(ID,[[11,6,'G'],[12,5,'G'],[10,7,'G'],[9,6,'G']]);
  const fsp={fps:9,frames:[ID,ID,2,3,4,5,6,7,8,7,6,5,4,3,2,'ok','ok','ok','ok','ok','ok',ID].map(f=>f==='ok'?okId:typeof f==='number'?scan(f):f)};

  // Опрос: галочки ставятся по очереди
  const S=pxG(`
......gggg......
...gggwwwwggg...
...gwwwwwwwwg...
...gwwwwwwwwg...
...gwgwlllwwg...
...gwwwwwwwwg...
...gwgwllllwg...
...gwwwwwwwwg...
...gwgwllwwwg...
...gwwwwwwwwg...
...gggggggggg...`);
  const chk=n=>S.map((row,i)=>[4,6,8].slice(0,n).includes(i)?row.slice(0,5)+'G'+row.slice(6).replace(/l/g,'b'):row);
  const survey={fps:4,frames:[chk(0),chk(0),chk(1),chk(1),chk(2),chk(2),chk(3),chk(3),chk(3),chk(3),chk(3)]};

  // Грейд: столбики растут, флажок на Middle
  const H=[3,5,8,10],X=[1,5,9,13];
  const bars=(f,flag)=>{let a=pxBlank(16,12);a=pxRows(a,{11:'llllllllllllllll'});const pts=[];
    H.forEach((h,i)=>{const hh=Math.min(h,f);for(let y=0;y<hh;y++)for(let dx=0;dx<3;dx++)pts.push([X[i]+dx,10-y,i===2?'b':'g'])});
    if(flag){pts.push([10,0,'w'],[10,1,'w'],[10,2,'w']);(flag===1?[[11,0],[12,0],[11,1],[12,1]]:[[11,0],[11,1],[12,1],[12,2]]).forEach(([x,y])=>pts.push([x,y,'r']))}
    return pxSet(a,pts)};
  const grade={fps:8,frames:[...Array.from({length:11},(_,f)=>bars(f)),...[1,2,1,2,1,2,1,2,1,2].map(fl=>bars(10,fl))]};

  // Тест: код набирается на ноутбуке
  const LP=pxG(PX_SPRITES.laptop).map((r,i)=>i>=1&&i<=6?'..gkkkkkkkkkkg..':r);
  const LINES=[[1,3,4,'p'],[2,4,6,'b'],[3,4,3,'w'],[4,5,5,'b'],[5,4,4,'r'],[6,3,2,'p']];
  const total=LINES.reduce((a,l)=>a+l[2],0);
  const typed=(n,cur)=>{const pts=[];let left=n,cx=null;
    for(const [y,x0,len,c] of LINES){const k=Math.min(len,left);for(let i=0;i<k;i++)pts.push([x0+i,y,c]);if(left<len&&cx==null)cx=[x0+k,y];left-=k;if(left<=0&&cx==null)cx=[x0+k,y]}
    if(cur&&cx)pts.push([cx[0],cx[1],'w']);return pxSet(LP,pts)};
  const test={fps:10,frames:[...Array.from({length:total+1},(_,n)=>typed(n,n%2===0)),...Array.from({length:10},(_,i)=>typed(total,i%4<2))]};

  // Категория: кубок и искры
  const TR=pxG(PX_SPRITES.trophy).map(r=>'..'+r+'..');
  const base=[...pxBlank(20,3),...TR];
  const spark=(pts,big)=>pxSet(base,pts.flatMap(([x,y])=>big?[[x,y,'w'],[x-1,y,'y'],[x+1,y,'y'],[x,y-1,'y'],[x,y+1,'y']]:[[x,y,'y']]));
  const A=[[2,2],[17,8]],Bp=[[17,1],[1,11]];
  const result={fps:6,frames:[base,spark(A,0),spark(A,1),spark(A,0),base,spark(Bp,0),spark(Bp,1),spark(Bp,0),base,base]};

  return {account,email,fsp,survey,grade,test,result};
})();

const pxReduced=()=>window.matchMedia&&matchMedia('(prefers-reduced-motion: reduce)').matches;
function PxGrid({rows,px,style}){
  const w=Math.max(...rows.map(r=>r.length)),h=rows.length;
  return <svg width={w*px} height={h*px} viewBox={`0 0 ${w} ${h}`} shapeRendering="crispEdges" aria-hidden="true" style={{display:'block',flexShrink:0,...style}}>
    {rows.flatMap((r,y)=>[...r].map((c,x)=>PX_PAL[c]?<rect key={x+'-'+y} x={x} y={y} width="1" height="1" fill={PX_PAL[c]}/>:null))}
  </svg>;
}
function PixelArt({name,px=4,style}){
  const anim=PX_ANIM[name];
  const [i,setI]=React.useState(0);
  React.useEffect(()=>{if(!anim||pxReduced())return;const t=setInterval(()=>setI(n=>(n+1)%anim.frames.length),1000/anim.fps);return()=>clearInterval(t)},[name]);
  const rows=anim?(pxReduced()?anim.frames[anim.frames.length-1]:anim.frames[i]):pxG(PX_SPRITES[name]);
  return <PxGrid rows={rows} px={px} style={style}/>;
}
function ArtHead({art,px=6,children}){return <div style={{display:'flex',alignItems:'flex-end',justifyContent:'space-between',gap:24}}><div style={{minWidth:0}}>{children}</div><PixelArt name={art} px={px}/></div>}
Object.assign(window,{PixelArt,ArtHead});
