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

  // Рейтинг: ваша синяя полоса поднимается с 3-го места на 1-е, загорается стрелка.
  const others=[['g',13],['g',10]];
  const board=(pos,len,arrow)=>{
    const rows=others.slice();rows.splice(pos,0,['p',len]);
    const a=pxBlank(18,9).map(r=>[...r]);
    rows.forEach(([c,L],i)=>{const y=1+i*3;const you=c==='p';
      for(let x=0;x<L&&x<18;x++){a[y][x]=you?'b':c;a[y+1][x]=you?'b':c}
      if(you&&arrow){[[16,y],[15,y+1],[16,y+1],[17,y+1]].forEach(([x,yy])=>{if(a[yy])a[yy][x]='G'})}
    });
    return a.map(r=>r.join(''));
  };
  PX_ANIM.climb={fps:4,frames:[board(2,6),board(2,8),board(2,10),board(1,10),board(1,12),board(0,12),board(0,14,1),board(0,14,0),board(0,14,1),board(0,14,0),board(0,14,1),board(0,14,1)]};

  // Приглашение: собеседник печатает, затем приходит пузырь с ₽ и мигает уведомление.
  const RUB=['.pppp.','.p...p','.p...p','pppppp','.p....','pppp..','.p....'];
  const bubble=(mode,dot)=>{
    const a=pxBlank(18,15).map(r=>[...r]);
    const box=(x0,y0,x1,y1)=>{for(let y=y0;y<=y1;y++)for(let x=x0;x<=x1;x++)a[y][x]=(y===y0||y===y1||x===x0||x===x1)?'w':'.'};
    if(mode<3){box(3,6,11,10);[[5,8],[7,8],[9,8]].forEach(([x,y],i)=>{a[y][x]=i===mode?'w':'g'});a[11][4]=a[12][4]='w';a[11][5]='w'}
    else{box(3,1,14,11);RUB.forEach((r,dy)=>[...r].forEach((c,dx)=>{if(c==='p')a[3+dy][6+dx]='b'}));
      a[12][4]=a[13][4]='w';a[12][5]='w';
      if(dot){a[0][14]=a[0][15]=a[1][14]=a[1][15]='r'}}
    return a.map(r=>r.join(''));
  };
  PX_ANIM.offer={fps:5,frames:[bubble(0),bubble(1),bubble(2),bubble(0),bubble(1),bubble(2),bubble(3,1),bubble(3,1),bubble(3,0),bubble(3,1),bubble(3,0),bubble(3,1),bubble(3,1),bubble(3,1)]};

  // «Пишете код»: программист за ноутбуком печатает, кусочки кода всплывают вверх.
  const coder=(k)=>{
    const W=20,H=18,a=pxBlank(W,H).map(r=>[...r]);
    const put=(x,y,c)=>{if(a[y]&&x>=0&&x<W)a[y][x]=c};
    const rect=(x0,y0,x1,y1,c)=>{for(let y=y0;y<=y1;y++)for(let x=x0;x<=x1;x++)put(x,y,c)};
    rect(8,6,11,9,'w');put(9,8,'k');put(10,8,'k');rect(8,6,11,6,'g');     // голова, волосы, глаза
    rect(6,10,13,13,'b');                                                  // худи
    rect(4,11,15,15,'l');rect(9,13,10,13,'r');                             // крышка ноутбука с меткой
    rect(2,16,17,16,'g');                                                  // основание
    const up=k%2;put(5,15-up,'w');put(14,14+up,'w');                       // руки печатают по очереди
    // всплывающие кусочки кода: [x, цвет, длина, фаза]
    [[3,'p',3,0],[8,'G',2,2],[13,'b',3,4],[16,'p',2,1]].forEach(([x,c,len,ph])=>{
      const t=(k+ph)%6;const y=5-t;if(y<0)return;
      for(let i=0;i<len;i++)put(x+i,y,t>=4?'g':c);
    });
    return a.map(r=>r.join(''));
  };
  PX_ANIM.coder={fps:5,frames:Array.from({length:12},(_,k)=>coder(k))};

  // «Работодатели пишут вам»: из офиса вылетает письмо, летит по дуге и приземляется с уведомлением.
  const ENV=['wwwwwww','wbwwwbw','wwbwbww','wwwbwww','wwwwwww'];
  const PATH=[[2,9],[6,6],[10,4],[14,5],[16,8],[16,11],[16,11],[16,11],[16,11],[16,11]];
  const hire=(k)=>{
    const W=24,H=18,a=pxBlank(W,H).map(r=>[...r]);
    const put=(x,y,c)=>{if(a[y]&&x>=0&&x<W)a[y][x]=c};
    for(let y=3;y<=17;y++)for(let x=0;x<=8;x++)put(x,y,(x===0||x===8||y===3)?'g':'k');   // здание
    put(4,1,'r');put(4,2,'g');                                                             // антенна
    for(let r=0;r<5;r++)[2,5].forEach((x,c)=>{const lit=(r*2+c+k)%4===0;put(x,5+r*2,lit?'y':'B');put(x+1,5+r*2,lit?'y':'B')}); // окна, по очереди загораются
    for(let x=3;x<=5;x++)for(let y=15;y<=17;y++)put(x,y,'l');                              // дверь
    const step=k%PATH.length;const [ex,ey]=PATH[step];
    ENV.forEach((row,dy)=>[...row].forEach((c,dx)=>put(ex+dx,ey+dy,c)));
    if(step>=5&&step%2===1){put(ex+6,ey-1,'r');put(ex+7,ey-1,'r');put(ex+6,ey,'r');put(ex+7,ey,'r')} // уведомление
    if(step>=6)[[ex+2,ey+6],[ex+3,ey+6],[ex+4,ey+6]].forEach(([x,y])=>put(x,y,'G'));        // «принято»
    return a.map(r=>r.join(''));
  };
  PX_ANIM.hire={fps:5,frames:Array.from({length:PATH.length},(_,k)=>hire(k))};

  // Найм: рукопожатие кандидата (синий рукав ФСП) и компании (серый рукав), с искрами.
  const shake=(off,dy,spark)=>{
    const W=22,H=13,a=pxBlank(W,H).map(r=>[...r]);
    const put=(x,y,c)=>{if(a[y]&&x>=0&&x<W)a[y][x]=c};
    const rect=(x0,y0,x1,y1,c)=>{for(let y=y0;y<=y1;y++)for(let x=x0;x<=x1;x++)put(x,y,c)};
    const y0=6+dy;
    rect(0,y0,3,y0+3,'b');rect(4,y0,4,y0+3,'p');            // рукав кандидата и манжета
    rect(18,y0,21,y0+3,'l');rect(17,y0,17,y0+3,'g');         // рукав компании и манжета
    rect(5,y0,7+off,y0+3,'w');put(6+off,y0-1,'w');           // рука кандидата и большой палец
    rect(14-off,y0,16,y0+3,'w');put(15-off,y0+4,'w');        // рука компании
    if(off===3){put(11,y0+1,'l');put(11,y0+2,'l');put(10,y0+3,'l')} // пальцы в замке
    if(spark)[[10,0],[9,1],[11,1],[10,2],[4,2],[17,1]].forEach(([x,y])=>put(x,y,'y'));
    return a.map(r=>r.join(''));
  };
  PX_ANIM.shake={fps:5,frames:[shake(0,0),shake(1,0),shake(2,0),shake(3,0),shake(3,-1),shake(3,1),shake(3,-1),shake(3,1),shake(3,0,1),shake(3,0,1),shake(3,0),shake(3,0,1),shake(3,0),shake(0,0)]};

  // Работа в IT: монитор — код набирается, полоса тестов заполняется и становится зелёной галочкой;
  // рядом кружка, над ней пар.
  const LINES=[[2,'p',5],[3,'b',8],[4,'w',4],[5,'b',7],[6,'p',3]];
  const desk=(k)=>{
    const W=26,H=18,a=pxBlank(W,H).map(r=>[...r]);
    const put=(x,y,c)=>{if(a[y]&&x>=0&&x<W)a[y][x]=c};
    const rect=(x0,y0,x1,y1,c)=>{for(let y=y0;y<=y1;y++)for(let x=x0;x<=x1;x++)put(x,y,c)};
    rect(0,0,19,12,'g');rect(1,1,18,11,'k');                 // монитор
    rect(8,13,11,14,'g');rect(5,15,14,15,'l');               // подставка
    const typed=Math.min(k,LINES.reduce((s,l)=>s+l[2],0));let left=typed;
    LINES.forEach(([y,c,len])=>{const n=Math.min(len,left);for(let i=0;i<n;i++)put(3+i+(c==='b'?2:0),y,c);left-=n});
    const prog=Math.max(0,k-27);                              // полоса тестов
    if(k>27&&k<34)for(let i=0;i<Math.min(14,prog*2+2);i++)put(3+i,9,'b');
    if(k>=34){for(let i=0;i<14;i++)put(3+i,9,'G');[[14,6],[15,7],[16,6],[17,5]].forEach(([x,y])=>put(x,y,'G'))}
    rect(21,11,24,15,'w');put(25,12,'w');put(25,13,'w');rect(22,12,23,12,'B');  // кружка
    const st=k%3;[[22,9-st],[23,8-st]].forEach(([x,y])=>{if(y>=6)put(x,y,'g')}); // пар
    return a.map(r=>r.join(''));
  };
  PX_ANIM.desk={fps:7,frames:Array.from({length:44},(_,k)=>desk(k))};
})();
