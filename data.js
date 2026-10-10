window.FSPDATA = (function(){
const SPECS=[
 {id:'backend',label:'Backend'},{id:'frontend',label:'Frontend'},{id:'mobile',label:'Mobile'},
 {id:'data',label:'Data / ML'},{id:'devops',label:'DevOps'},{id:'qa',label:'QA'},{id:'security',label:'Инф. безопасность'}];
const GRADES=[
 {id:'intern',label:'Стажёр',hint:'Учебные проекты, без коммерческого опыта'},
 {id:'junior',label:'Junior',hint:'Опыт до 1–1,5 лет, задачи под присмотром'},
 {id:'middle',label:'Middle',hint:'Самостоятельно ведёт задачи от постановки до релиза'},
 {id:'senior',label:'Senior',hint:'Проектирует системы, отвечает за архитектуру'}];
const STACKS={
 backend:['Python','Go','Java','Kotlin','C#','PostgreSQL','Kafka','Redis','Docker','gRPC','FastAPI','Spring'],
 frontend:['TypeScript','React','Vue','Next.js','CSS','Webpack','Redux','Vite'],
 mobile:['Kotlin','Swift','Flutter','React Native','Jetpack Compose'],
 data:['Python','PyTorch','SQL','Spark','Airflow','pandas','ClickHouse'],
 devops:['Kubernetes','Terraform','Docker','Ansible','Prometheus','GitLab CI','Linux'],
 qa:['Python','Pytest','Selenium','Playwright','Postman','Java'],
 security:['Python','Burp Suite','Wireshark','SIEM','Linux','C']};
const DISC={product:'Продуктовое программирование',algo:'Алгоритмическое программирование',security:'Программирование систем ИБ',robotics:'Программирование робототехники',uas:'Программирование БАС'};
const C=(o)=>o;
const CANDIDATES=[
 C({id:'k2041',name:'Мария Л.',spec:'backend',grade:'middle',exp:3.5,stack:['Python','FastAPI','PostgreSQL','Kafka','Docker'],test:91,expert:true,fsp:[{disc:'product',event:'Чемпионат России 2025',place:'Финалист'},{disc:'algo',event:'Кубок России 2024',place:'Призёр, 3 место'}],fresh:2,format:'Удалённо',city:'Казань',want:'240–280 тыс.',tasks:14}),
 C({id:'k1187',name:'Игорь С.',spec:'backend',grade:'middle',exp:4,stack:['Go','PostgreSQL','Kafka','gRPC','Redis'],test:88,expert:true,fsp:[{disc:'algo',event:'Чемпионат России 2024',place:'Участник финала'}],fresh:5,format:'Гибрид',city:'Москва',want:'260–300 тыс.',tasks:9}),
 C({id:'k3302',name:'Дарья П.',spec:'backend',grade:'middle',exp:2.5,stack:['Python','Django','PostgreSQL','Redis','Docker'],test:84,expert:true,fsp:[],fresh:1,format:'Удалённо',city:'Новосибирск',want:'210–250 тыс.',tasks:11}),
 C({id:'me',name:'Алексей К.',spec:'backend',grade:'middle',exp:3,stack:['Python','Go','PostgreSQL','Kafka','Docker'],test:86,expert:true,fsp:[{disc:'product',event:'Кубок России 2025',place:'Полуфиналист'},{disc:'algo',event:'Региональный этап, Татарстан 2024',place:'Победитель'}],fresh:3,format:'Удалённо',city:'Казань',want:'230–270 тыс.',tasks:7}),
 C({id:'k0954',name:'Тимур А.',spec:'backend',grade:'middle',exp:5,stack:['Java','Spring','PostgreSQL','Kafka'],test:79,expert:false,fsp:[],fresh:12,format:'Офис',city:'Екатеринбург',want:'250–290 тыс.',tasks:3}),
 C({id:'k4410',name:'Ксения В.',spec:'backend',grade:'middle',exp:2,stack:['Python','FastAPI','MongoDB','Docker'],test:74,expert:true,fsp:[{disc:'security',event:'Кубок России 2024',place:'Участник'}],fresh:20,format:'Удалённо',city:'Самара',want:'200–230 тыс.',tasks:4}),
 C({id:'k2290',name:'Роман Е.',spec:'backend',grade:'senior',exp:7,stack:['Python','Go','PostgreSQL','Kafka','Kubernetes'],test:90,expert:true,fsp:[{disc:'algo',event:'Чемпионат России 2023',place:'Победитель'}],fresh:6,format:'Удалённо',city:'Санкт-Петербург',want:'380–450 тыс.',tasks:10}),
 C({id:'k5021',name:'Олег Н.',spec:'backend',grade:'junior',exp:1,stack:['Python','FastAPI','PostgreSQL'],test:82,expert:true,fsp:[{disc:'product',event:'Первенство России 2025',place:'Призёр, 2 место'}],fresh:2,format:'Гибрид',city:'Томск',want:'120–150 тыс.',tasks:12}),
 C({id:'k5133',name:'Анна Г.',spec:'backend',grade:'junior',exp:0.8,stack:['Go','PostgreSQL','Docker'],test:77,expert:false,fsp:[],fresh:4,format:'Удалённо',city:'Пермь',want:'110–140 тыс.',tasks:5}),
 C({id:'k6012',name:'Никита Б.',spec:'frontend',grade:'middle',exp:3,stack:['TypeScript','React','Next.js','Redux'],test:87,expert:true,fsp:[{disc:'product',event:'Кубок России 2025',place:'Финалист'}],fresh:3,format:'Удалённо',city:'Москва',want:'230–270 тыс.',tasks:8}),
 C({id:'k6120',name:'Елена Ш.',spec:'frontend',grade:'junior',exp:1,stack:['TypeScript','Vue','CSS'],test:80,expert:true,fsp:[],fresh:7,format:'Офис',city:'Уфа',want:'110–140 тыс.',tasks:6}),
 C({id:'k7004',name:'Артём Ж.',spec:'data',grade:'middle',exp:3,stack:['Python','PyTorch','SQL','Airflow'],test:85,expert:true,fsp:[{disc:'algo',event:'Чемпионат России 2025',place:'Призёр, 2 место'}],fresh:4,format:'Гибрид',city:'Москва',want:'260–310 тыс.',tasks:9}),
 C({id:'k7781',name:'Софья Р.',spec:'devops',grade:'middle',exp:4,stack:['Kubernetes','Terraform','GitLab CI','Prometheus'],test:83,expert:true,fsp:[],fresh:9,format:'Удалённо',city:'Иркутск',want:'250–290 тыс.',tasks:5}),
 C({id:'k8015',name:'Глеб Ф.',spec:'security',grade:'junior',exp:1,stack:['Python','Burp Suite','Linux'],test:81,expert:true,fsp:[{disc:'security',event:'Чемпионат России 2025',place:'Финалист'}],fresh:2,format:'Удалённо',city:'Владивосток',want:'130–160 тыс.',tasks:10}),
 C({id:'k8820',name:'Вера М.',spec:'qa',grade:'middle',exp:3,stack:['Python','Pytest','Playwright','Postman'],test:78,expert:false,fsp:[],fresh:15,format:'Удалённо',city:'Воронеж',want:'180–220 тыс.',tasks:2}),
];
const COMPANY={name:'Северный код',field:'Финтех · платёжная инфраструктура',size:'180 сотрудников',site:'severcode.ru',contact:'hr@severcode.ru',about:'Разрабатываем процессинг и антифрод для региональных банков. Команда платформы — 14 инженеров, Python и Go, событийная архитектура на Kafka.'};
const NEED={title:'Backend-разработчик в команду платформы',spec:'backend',grade:'middle',stack:['Python','PostgreSQL','Kafka','Docker'],salaryFrom:220000,salaryTo:280000,format:'Удалённо',team:'Сервис платёжных событий: приём, дедупликация и маршрутизация ~3 тыс. событий/с.'};
const VACANCIES=[
 {id:'v1',company:'Северный код',title:'Backend-разработчик (Python)',spec:'backend',grade:'middle',stack:['Python','PostgreSQL','Kafka'],from:220000,to:280000,format:'Удалённо',city:'Москва',posted:'3 дня назад',own:true,responses:4},
 {id:'v2',company:'Северный код',title:'Go-разработчик, антифрод',spec:'backend',grade:'senior',stack:['Go','ClickHouse','Kafka'],from:350000,to:420000,format:'Гибрид',city:'Москва',posted:'неделю назад',own:true,responses:2},
 {id:'v3',company:'Лаборатория Т',title:'Python-разработчик, сервис аналитики',spec:'backend',grade:'middle',stack:['Python','FastAPI','PostgreSQL'],from:200000,to:250000,format:'Удалённо',city:'Казань',posted:'сегодня'},
 {id:'v4',company:'Ростехсеть',title:'Backend-инженер (Go)',spec:'backend',grade:'middle',stack:['Go','gRPC','Redis'],from:240000,to:290000,format:'Офис',city:'Санкт-Петербург',posted:'2 дня назад'},
 {id:'v5',company:'Медиаплатформа «Кадр»',title:'Backend-разработчик, рекомендации',spec:'backend',grade:'middle',stack:['Python','Kafka','Redis'],from:230000,to:270000,format:'Удалённо',city:'Москва',posted:'5 дней назад'},
];
const INVITES=[
 {id:'i1',cand:'k2041',company:'Северный код',title:'Backend-разработчик в команду платформы',from:240000,to:280000,status:'accepted',date:'02.10.2026',contact:'Telegram @severcode_hr',msg:'Мария, ваше решение задачи про дедупликацию событий — ровно то, чем занимается команда.'},
 {id:'i2',cand:'k1187',company:'Северный код',title:'Backend-разработчик в команду платформы',from:250000,to:290000,status:'viewed',date:'04.10.2026',contact:'hr@severcode.ru',msg:''},
 {id:'i3',cand:'k3302',company:'Северный код',title:'Backend-разработчик в команду платформы',from:220000,to:260000,status:'sent',date:'06.10.2026',contact:'hr@severcode.ru',msg:''},
 {id:'i4',cand:'k0954',company:'Северный код',title:'Go-разработчик, антифрод',from:300000,to:340000,status:'declined',date:'28.09.2026',contact:'hr@severcode.ru',msg:''},
 {id:'i5',cand:'me',company:'Лаборатория Т',title:'Python-разработчик, сервис аналитики',from:210000,to:250000,status:'viewed',date:'05.10.2026',contact:'Telegram @labt_team',msg:'Алексей, смотрим кандидатов с опытом Kafka и PostgreSQL. Ваш результат теста — в верхней части категории.'},
];
const RESPONSES=[
 {id:'r1',vac:'v4',status:'viewed',date:'01.10.2026'},
];
const VAC_RESPONSES=[
 {id:'vr1',vac:'v1',cand:'k5021',date:'06.10.2026',status:'new'},
 {id:'vr2',vac:'v1',cand:'k4410',date:'05.10.2026',status:'viewed'},
 {id:'vr3',vac:'v1',cand:'k0954',date:'03.10.2026',status:'viewed'},
 {id:'vr4',vac:'v1',cand:'k5133',date:'02.10.2026',status:'declined'},
];
const TASK={
 title:'Дедупликация платёжных событий',
 from:'Сформирована по 3 вакансиям категории Backend · Middle',
 minutes:40,
 text:'Сервис получает поток событий {id, account, amount, ts}. Из-за повторных доставок одно событие может прийти несколько раз с интервалом до 10 минут. Реализуйте функцию dedupe(stream), которая отдаёт каждое событие ровно один раз и не держит в памяти больше, чем нужно для окна в 10 минут.',
 checks:['Корректность на повторных доставках','Ограничение памяти окном','События не по порядку (ts)','Сложность и читаемость'],
 code:`from collections import OrderedDict

WINDOW = 600  # секунд

def dedupe(stream):
    seen = OrderedDict()          # id -> ts
    for ev in stream:
        # выкидываем всё, что старше окна
        while seen:
            oldest_id, oldest_ts = next(iter(seen.items()))
            if ev["ts"] - oldest_ts <= WINDOW:
                break
            seen.popitem(last=False)
        if ev["id"] in seen:
            continue
        seen[ev["id"]] = ev["ts"]
        yield ev
`};
const AI_EVAL=[
 {k:'Корректность',v:92,note:'Все 18 тестов на повторные доставки пройдены'},
 {k:'Ограничение памяти',v:88,note:'Окно очищается при каждом событии; пиковая память ∝ событиям за 10 мин'},
 {k:'Порядок событий',v:61,note:'Событие с ts меньше, чем у самого старого в окне, может пройти дважды'},
 {k:'Качество кода',v:85,note:'Читаемо, комментарии по делу; нет типизации'},
];
const DAILY=[
 {id:'d1',company:'Северный код',title:'Идемпотентный webhook',kind:'Предложить подход',mins:15,due:'до 10.10',text:'Партнёр шлёт webhook об оплате, иногда дважды и в произвольном порядке. Опишите, как обработать его ровно один раз. Код не обязателен.',status:'open'},
 {id:'d2',company:'Лаборатория Т',title:'Медленный запрос к заказам',kind:'Решить',mins:20,due:'до 12.10',text:'SELECT по таблице orders (40 млн строк) с фильтром по статусу и дате выполняется 9 с. Предложите индекс и перепишите запрос.',status:'open'},
 {id:'d3',company:'Ростехсеть',title:'Rate limiter на Go',kind:'Решить',mins:25,due:'выполнено 28.09',text:'',status:'done',score:84},
];
const fmt=(n)=>n.toLocaleString('ru-RU').replace(/,/g,' ');
const rub=(a,b)=>`${fmt(a)} – ${fmt(b)} ₽`;
const specLabel=(id)=>(SPECS.find(s=>s.id===id)||{}).label||id;
const gradeLabel=(id)=>(GRADES.find(g=>g.id===id)||{}).label||id;
const catLabel=(c)=>`${specLabel(c.spec)} · ${gradeLabel(c.grade)}`;
// ранжирование: тест 45% · стек 25% · ФСП 15% · свежесть 10% · экспертная проверка 5%
function score(c,need,opts={}){
 const fspOn=opts.fsp!==false;
 const ov=need.stack.filter(s=>c.stack.includes(s));
 const stack=need.stack.length?ov.length/need.stack.length:1;
 const fspPts=fspOn&&c.fsp&&c.fsp.length?Math.min(1,c.fsp.reduce((a,f)=>a+(/Победитель|Призёр/.test(f.place)?0.6:/Финалист|финала/.test(f.place)?0.45:0.25),0)):0;
 const fresh=c.fresh<=3?1:c.fresh<=7?0.8:c.fresh<=14?0.5:0.2;
 const parts={test:c.test/100*45,stack:stack*25,fsp:fspPts*15,fresh:fresh*10,expert:c.expert?5:0};
 const total=Math.round(Object.values(parts).reduce((a,b)=>a+b,0));
 const reasons=[];
 reasons.push(`Тест на ${gradeLabel(c.grade)}: ${c.test}/100${c.expert?', подтверждён экспертом':', ждёт проверки эксперта'}`);
 reasons.push(ov.length?`Совпадение стека ${ov.length}/${need.stack.length}: ${ov.join(', ')}`:'Нет совпадений по стеку');
 if(fspOn&&c.fsp&&c.fsp.length) reasons.push(`ФСП: ${c.fsp[0].place.toLowerCase()} · ${c.fsp[0].event}`);
 else reasons.push('Нет истории ФСП — оценка по тесту и заданиям');
 reasons.push(c.fresh<=7?`Решал задание ${c.fresh} дн. назад`:`Последнее задание ${c.fresh} дн. назад`);
 return {total,parts,reasons,overlap:ov};
}
return {SPECS,GRADES,STACKS,DISC,CANDIDATES,COMPANY,NEED,VACANCIES,INVITES,RESPONSES,VAC_RESPONSES,TASK,AI_EVAL,DAILY,fmt,rub,specLabel,gradeLabel,catLabel,score};
})();
