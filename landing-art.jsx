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

  // Рейтинг: ваш синий столбец поднимается с 4-го места на 2-е, загорается стрелка.
  const others=[['l',14],['g',12],['g',10]];
  const board=(pos,len,arrow)=>{
    const rows=others.slice();rows.splice(pos,0,['p',len]);
    const a=pxBlank(18,14).map(r=>[...r]);
    rows.forEach(([c,L],i)=>{const y=1+i*3;const you=c==='p';
      a[y][0]=a[y+1][0]=you?'p':'g';
      for(let x=2;x<2+L&&x<18;x++){a[y][x]=you?'b':c;a[y+1][x]=you?'b':c}
      if(you&&arrow){[[16,y],[15,y+1],[16,y+1],[17,y+1]].forEach(([x,yy])=>{if(a[yy])a[yy][x]='G'})}
    });
    return a.map(r=>r.join(''));
  };
  PX_ANIM.climb={fps:4,frames:[board(3,6),board(3,8),board(3,9),board(2,9),board(2,11),board(1,11),board(1,12,1),board(1,12,0),board(1,12,1),board(1,12,0),board(1,12,1),board(1,12,1)]};

  // Приглашение: собеседник печатает, затем приходит пузырь с ₽ и мигает уведомление.
  const RUB=['.pppp.','.p...p','.p...p','pppppp','.p....','pppp..','.p....'];
  const bubble=(mode,dot)=>{
    const a=pxBlank(18,15).map(r=>[...r]);
    const box=(x0,y0,x1,y1)=>{for(let y=y0;y<=y1;y++)for(let x=x0;x<=x1;x++)a[y][x]=(y===y0||y===y1||x===x0||x===x1)?'w':'k'};
    if(mode<3){box(1,6,9,10);[[3,8],[5,8],[7,8]].forEach(([x,y],i)=>{a[y][x]=i===mode?'w':'g'});a[11][2]=a[12][2]='w';a[11][3]='w'}
    else{box(1,1,16,11);RUB.forEach((r,dy)=>[...r].forEach((c,dx)=>{if(c==='p')a[3+dy][3+dx]='b'}));
      for(let x=11;x<=14;x++){a[4][x]='l';a[6][x]=x<14?'l':'k';a[8][x]='G'}
      a[12][2]=a[13][2]='w';a[12][3]='w';
      if(dot){a[0][15]=a[0][16]=a[1][15]=a[1][16]='r'}}
    return a.map(r=>r.join(''));
  };
  PX_ANIM.offer={fps:5,frames:[bubble(0),bubble(1),bubble(2),bubble(0),bubble(1),bubble(2),bubble(3,1),bubble(3,1),bubble(3,0),bubble(3,1),bubble(3,0),bubble(3,1),bubble(3,1),bubble(3,1)]};
})();
