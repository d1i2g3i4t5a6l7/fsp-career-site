// Пиксельные анимации для главной: секундомер, рост в рейтинге, приглашение с зарплатой.
// Те же палитра и сетка, что в pixel.jsx; кадры добавляются в PX_ANIM.
(()=>{
  // Секундомер: кольцо прогресса заполняется, стрелка идёт по кругу.
  const W=17,H=18,cx=8,cy=10,R=6.6;
  const clock=k=>{
    const a=pxBlank(W,H).map(r=>[...r]);
    const put=(x,y,c)=>{if(a[y]&&x>=0&&x<W)a[y][x]=c};
    for(let y=0;y<H;y++)for(let x=0;x<W;x++){
      const dx=x-cx,dy=y-cy,d=Math.hypot(dx,dy);
      if(d<R-0.9)put(x,y,'B');
      else if(d<R+0.6){let ang=Math.atan2(dx,-dy);if(ang<0)ang+=Math.PI*2;put(x,y,ang<=k/8*Math.PI*2+0.01&&k>0?'b':'g')}
    }
    [[7,0],[8,0],[9,0],[8,1],[8,2]].forEach(([x,y])=>put(x,y,'l'));
    put(14,4,'r');put(15,3,'r');
    [[cx,cy-5],[cx+5,cy],[cx,cy+5],[cx-5,cy]].forEach(([x,y])=>put(x,y,'l'));
    const ang=k/8*Math.PI*2;
    for(let s=1;s<=4;s++)put(Math.round(cx+Math.sin(ang)*s),Math.round(cy-Math.cos(ang)*s),'r');
    put(cx,cy,'w');
    return a.map(r=>r.join(''));
  };
  PX_ANIM.clock={fps:4,frames:[0,1,2,3,4,5,6,7,8,8,8,8].map(clock)};

  // Рейтинг: таблица из трёх строк с аватарами; ваша синяя строка поднимается с 3-го места на 1-е,
  // загорается стрелка и звезда над лидером.
  const others=[['g',12],['g',9]];
  const board=(pos,len,arrow)=>{
    const rows=others.slice();rows.splice(pos,0,['b',len]);
    const a=pxBlank(22,13).map(r=>[...r]);
    const put=(x,y,c)=>{if(a[y]&&x>=0&&x<22)a[y][x]=c};
    rows.forEach(([c,L],i)=>{const y=3+i*3;const you=c==='b';
      put(0,y,i===0?'y':'l');                                   // место: лидер — жёлтая точка
      [[2,y],[3,y],[2,y+1],[3,y+1]].forEach(([x,yy])=>put(x,yy,you?'p':'g'));   // аватар
      if(you)put(3,y,'w');
      for(let x=5;x<5+L;x++){put(x,y,you?'b':'g');put(x,y+1,you?'B':'k')}  // полоса с тенью
      if(you&&arrow){[[20,y-1],[19,y],[20,y],[21,y],[20,y+1]].forEach(([x,yy])=>put(x,yy,'G'))}
    });
    if(arrow&&pos===0)[[10,0],[9,1],[10,1],[11,1],[10,2]].forEach(([x,y])=>put(x,y,'y')); // звезда
    return a.map(r=>r.join(''));
  };
  PX_ANIM.climb={fps:4,frames:[board(2,6),board(2,8),board(2,10),board(1,10),board(1,12),board(0,12),board(0,14,1),board(0,14,0),board(0,14,1),board(0,14,0),board(0,14,1),board(0,14,1)]};

  // Приглашение: собеседник печатает, затем приходит карточка-сообщение: логотип компании,
  // строка заголовка, крупный ₽ и кнопки «принять» / «отклонить»; мигает уведомление.
  const RUB=['.pppp.','.p...p','.p...p','pppppp','.p....','pppp..','.p....'];
  const bubble=(mode,dot,acc)=>{
    const W2=20,H2=19;
    const a=pxBlank(W2,H2).map(r=>[...r]);
    const put=(x,y,c)=>{if(a[y]&&x>=0&&x<W2)a[y][x]=c};
    const box=(x0,y0,x1,y1)=>{for(let y=y0;y<=y1;y++)for(let x=x0;x<=x1;x++)put(x,y,(y===y0||y===y1||x===x0||x===x1)?'w':'.')};
    if(mode<3){box(2,9,10,13);[[4,11],[6,11],[8,11]].forEach(([x,y],i)=>put(x,y,i===mode?'w':'g'));put(3,14,'w');put(3,15,'w');put(4,14,'w')}
    else{
      box(2,1,17,15);
      [[4,3],[5,3],[4,4],[5,4]].forEach(([x,y])=>put(x,y,'B'));put(5,3,'w');      // логотип компании
      for(let x=7;x<=14;x++)put(x,3,'l');for(let x=7;x<=11;x++)put(x,4,'g');      // название и должность
      RUB.forEach((r,dy)=>[...r].forEach((c,dx)=>{if(c==='p')put(4+dx,6+dy,'b')}));
      for(let x=11;x<=15;x++){put(x,8,'l')}for(let x=11;x<=14;x++){put(x,10,'g')}  // вилка зарплаты
      for(let x=4;x<=9;x++){put(x,13,acc?'G':'b')}for(let x=11;x<=15;x++){put(x,13,'g')} // кнопки
      put(3,16,'w');put(3,17,'w');put(4,16,'w');
      if(dot)[[17,0],[18,0],[17,1],[18,1]].forEach(([x,y])=>put(x,y,'r'));
    }
    return a.map(r=>r.join(''));
  };
  PX_ANIM.offer={fps:5,frames:[bubble(0),bubble(1),bubble(2),bubble(0),bubble(1),bubble(2),bubble(3,1),bubble(3,1),bubble(3,0),bubble(3,1),bubble(3,0),bubble(3,1,1),bubble(3,0,1),bubble(3,1,1),bubble(3,1,1),bubble(3,1,1)]};
})();
