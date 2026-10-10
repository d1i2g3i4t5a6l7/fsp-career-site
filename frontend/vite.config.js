// JSX собирается так же, как раньше его собирал Babel в браузере: в React.createElement
// из общего React (public/vendor), который index.html подключает отдельным файлом.
// Один React на всё: им же пользуются компоненты дизайн-системы из public/ds.
// Куда пересылать запросы к бэкенду при разработке; другой адрес — WORKSPACE_URL=http://… npm run dev
const WORKSPACE = {
  target: process.env.WORKSPACE_URL || 'http://localhost:8010',
  rewrite: (p) => p.replace(/^\/api\/workspace/, ''),
};

export default {
  // Пути относительные, как во всём сайте: открывается и из подпапки сервера
  base: './',
  // Запросы сайта к бэкенду (api/workspace/…) при разработке пересылаются на workspace, в docker compose — nginx
  server: { proxy: { '/api/workspace': WORKSPACE } },
  preview: { proxy: { '/api/workspace': WORKSPACE } },
  esbuild: {
    jsx: 'transform',
    jsxFactory: 'React.createElement',
    jsxFragment: 'React.Fragment',
  },
};
