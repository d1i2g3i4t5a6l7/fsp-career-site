/* @ds-bundle: {"format":4,"namespace":"DesignSystem_2ade33","components":[{"name":"DisciplineCard","sourcePath":"components/content/DisciplineCard.jsx"},{"name":"EventCard","sourcePath":"components/content/EventCard.jsx"},{"name":"MediaCard","sourcePath":"components/content/MediaCard.jsx"},{"name":"NewsCard","sourcePath":"components/content/NewsCard.jsx"},{"name":"RegionCard","sourcePath":"components/content/RegionCard.jsx"},{"name":"StatBlock","sourcePath":"components/content/StatBlock.jsx"},{"name":"Timeline","sourcePath":"components/content/Timeline.jsx"},{"name":"Button","sourcePath":"components/core/Button.jsx"},{"name":"LangSwitch","sourcePath":"components/core/LangSwitch.jsx"},{"name":"SectionTitle","sourcePath":"components/core/SectionTitle.jsx"},{"name":"Tag","sourcePath":"components/core/Tag.jsx"},{"name":"Accordion","sourcePath":"components/feedback/Accordion.jsx"},{"name":"CookieBanner","sourcePath":"components/feedback/CookieBanner.jsx"},{"name":"Footer","sourcePath":"components/navigation/Footer.jsx"},{"name":"Header","sourcePath":"components/navigation/Header.jsx"}],"sourceHashes":{"components/content/DisciplineCard.jsx":"9df19ce37f2c","components/content/EventCard.jsx":"7344f40e0ff6","components/content/MediaCard.jsx":"458a9f76a54f","components/content/NewsCard.jsx":"fdd8cc723f5e","components/content/RegionCard.jsx":"7dbe0effb123","components/content/StatBlock.jsx":"91d39ea8228f","components/content/Timeline.jsx":"9bd6fc4cd121","components/core/Button.jsx":"9cab02921ea3","components/core/LangSwitch.jsx":"fc1f2a3e7e58","components/core/SectionTitle.jsx":"1f967dfad1e9","components/core/Tag.jsx":"b7e44ad036c4","components/feedback/Accordion.jsx":"dcb884aa26a6","components/feedback/CookieBanner.jsx":"e705d8b1c9e2","components/navigation/Footer.jsx":"d72db223e5c2","components/navigation/Header.jsx":"83ad17abd9e7","ui_kits/website/Calendar.jsx":"93df4aaf8e80","ui_kits/website/Home.jsx":"3c1d96048d5f","ui_kits/website/News.jsx":"ccc89828bd92","ui_kits/website/Regions.jsx":"c66e82679c53","ui_kits/website/data.js":"de388a96d278"},"inlinedExternals":[],"unexposedExports":[]} */

(() => {

const __ds_ns = (window.DesignSystem_2ade33 = window.DesignSystem_2ade33 || {});

const __ds_scope = {};

(__ds_ns.__errors = __ds_ns.__errors || []);

// components/content/DisciplineCard.jsx
try { (() => {
const COL = {
  product: 'var(--disc-product)',
  algo: 'var(--disc-algo)',
  uas: 'var(--disc-uas)',
  robotics: 'var(--disc-robotics)',
  security: 'var(--disc-security)'
};
const GLYPH = {
  product: '</>',
  algo: '{ }',
  uas: '>|<',
  robotics: '[•]',
  security: '//'
};
function DisciplineCard({
  discipline = 'algo',
  title,
  description,
  glyph
}) {
  const c = COL[discipline];
  return /*#__PURE__*/React.createElement("div", {
    style: {
      border: '1px solid var(--border-1)',
      borderTop: '4px solid ' + c,
      padding: '24px',
      display: 'flex',
      flexDirection: 'column',
      gap: '16px',
      background: 'var(--bg-page)',
      height: '100%',
      boxSizing: 'border-box'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: '32px',
      fontWeight: 700,
      color: c,
      lineHeight: 1
    }
  }, glyph || GLYPH[discipline]), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: '17px',
      fontWeight: 700,
      lineHeight: 1.3
    }
  }, title), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: '13px',
      color: 'var(--fg-2)',
      lineHeight: 1.55
    }
  }, description));
}
Object.assign(__ds_scope, { DisciplineCard });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/content/DisciplineCard.jsx", error: String((e && e.message) || e) }); }

// components/content/MediaCard.jsx
try { (() => {
function MediaCard({
  source,
  date,
  title,
  href = '#'
}) {
  const [h, setH] = React.useState(false);
  return /*#__PURE__*/React.createElement("a", {
    href: href,
    target: "_blank",
    rel: "noreferrer",
    onMouseEnter: () => setH(true),
    onMouseLeave: () => setH(false),
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: '14px',
      padding: '20px 0',
      borderTop: '1px solid var(--border-1)',
      color: 'var(--fg-1)'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      justifyContent: 'space-between',
      gap: '12px',
      fontSize: '12px'
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      color: 'var(--fsp-blue)',
      fontWeight: 700,
      textTransform: 'uppercase'
    }
  }, source), /*#__PURE__*/React.createElement("span", {
    style: {
      color: 'var(--fg-2)'
    }
  }, date)), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: '15px',
      fontWeight: 500,
      lineHeight: 1.4,
      color: h ? 'var(--accent-hover)' : 'var(--fg-1)'
    }
  }, title, " \u2197"));
}
Object.assign(__ds_scope, { MediaCard });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/content/MediaCard.jsx", error: String((e && e.message) || e) }); }

// components/content/NewsCard.jsx
try { (() => {
function NewsCard({
  image,
  title,
  date,
  href = '#',
  onClick,
  size = 'md'
}) {
  const [h, setH] = React.useState(false);
  return /*#__PURE__*/React.createElement("a", {
    lang: "ru",
    href: href,
    onClick: onClick,
    onMouseEnter: () => setH(true),
    onMouseLeave: () => setH(false),
    style: {
      display: 'flex',
      flexDirection: 'column',
      background: 'var(--bg-surface)',
      border: '1px solid ' + (h ? 'var(--fsp-blue)' : 'var(--border-1)'),
      color: 'var(--fg-1)',
      transition: 'border-color var(--dur-fast) var(--ease)',
      height: '100%'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      aspectRatio: size === 'lg' ? '16/9' : '4/3',
      overflow: 'hidden',
      background: 'var(--bg-surface-2)'
    }
  }, image && /*#__PURE__*/React.createElement("img", {
    src: image,
    alt: "",
    style: {
      width: '100%',
      height: '100%',
      objectFit: 'cover',
      display: 'block',
      transform: h ? 'scale(1.03)' : 'none',
      transition: 'transform var(--dur-base) var(--ease)'
    }
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      padding: '20px',
      display: 'flex',
      flexDirection: 'column',
      gap: '16px',
      flex: 1
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: size === 'lg' ? '20px' : '16px',
      fontWeight: 700,
      lineHeight: 1.35,
      textWrap: 'pretty',
      overflowWrap: 'anywhere',
      hyphens: 'auto',
      color: h ? 'var(--fsp-white)' : 'var(--fg-1)'
    }
  }, title), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 'auto',
      fontSize: '13px',
      color: 'var(--fg-2)'
    }
  }, date)));
}
Object.assign(__ds_scope, { NewsCard });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/content/NewsCard.jsx", error: String((e && e.message) || e) }); }

// components/content/RegionCard.jsx
try { (() => {
function RegionCard({
  name,
  label = 'Федерация',
  linkText = 'Контакты представительств',
  href = '#',
  onClick
}) {
  const [h, setH] = React.useState(false);
  return /*#__PURE__*/React.createElement("a", {
    href: href,
    onClick: onClick,
    onMouseEnter: () => setH(true),
    onMouseLeave: () => setH(false),
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: '10px',
      padding: '20px',
      border: '1px solid var(--border-1)',
      background: h ? 'var(--fsp-blue)' : 'var(--bg-surface)',
      color: 'var(--fg-1)',
      transition: 'background var(--dur-fast) var(--ease)'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: '12px',
      color: h ? '#fff' : 'var(--fg-2)'
    }
  }, label), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: '16px',
      fontWeight: 700,
      lineHeight: 1.3
    }
  }, name), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: '13px',
      marginTop: 'auto',
      color: h ? '#fff' : 'var(--fsp-blue)',
      fontWeight: 500
    }
  }, linkText, " \u2192"));
}
Object.assign(__ds_scope, { RegionCard });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/content/RegionCard.jsx", error: String((e && e.message) || e) }); }

// components/content/StatBlock.jsx
try { (() => {
function StatBlock({
  value,
  label,
  color = 'var(--fsp-blue)',
  size = 'lg'
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: '8px'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-pixel)',
      fontSize: size === 'lg' ? '120px' : '64px',
      lineHeight: 0.9,
      color
    }
  }, value), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: '14px',
      color: 'var(--fg-2)',
      maxWidth: '280px',
      lineHeight: 1.45
    }
  }, label));
}
Object.assign(__ds_scope, { StatBlock });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/content/StatBlock.jsx", error: String((e && e.message) || e) }); }

// components/content/Timeline.jsx
try { (() => {
function Timeline({
  items = []
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      flexDirection: 'column'
    }
  }, items.map((it, i) => /*#__PURE__*/React.createElement("div", {
    key: i,
    style: {
      display: 'grid',
      gridTemplateColumns: '200px minmax(0,1fr)',
      gap: '24px',
      padding: '18px 0',
      borderTop: '1px solid var(--border-1)'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: '15px',
      fontWeight: 700,
      color: i === items.length - 1 ? 'var(--fsp-red)' : 'var(--fsp-blue)'
    }
  }, it.date), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: '14px',
      color: 'var(--fg-1)',
      lineHeight: 1.5
    }
  }, it.text))));
}
Object.assign(__ds_scope, { Timeline });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/content/Timeline.jsx", error: String((e && e.message) || e) }); }

// components/core/Button.jsx
try { (() => {
function Button({
  variant = 'primary',
  size = 'md',
  disabled = false,
  iconRight,
  children,
  onClick,
  href,
  fullWidth = false,
  style
}) {
  const [h, setH] = React.useState(false);
  const [p, setP] = React.useState(false);
  const pad = {
    sm: '8px 14px',
    md: '12px 22px',
    lg: '16px 30px'
  }[size];
  const fs = {
    sm: '12px',
    md: '14px',
    lg: '16px'
  }[size];
  const V = {
    primary: {
      bg: p ? 'var(--accent-press)' : h ? 'var(--accent-hover)' : 'var(--accent)',
      fg: '#fff',
      bd: 'transparent'
    },
    secondary: {
      bg: h ? 'var(--fsp-white)' : 'transparent',
      fg: h ? 'var(--fsp-black)' : 'var(--fg-1)',
      bd: 'var(--fsp-white)'
    },
    red: {
      bg: h ? 'var(--fsp-red-hover)' : 'var(--fsp-red)',
      fg: '#fff',
      bd: 'transparent'
    },
    ghost: {
      bg: h ? 'var(--bg-surface)' : 'transparent',
      fg: 'var(--fg-1)',
      bd: 'transparent'
    }
  }[variant];
  const s = {
    display: fullWidth ? 'flex' : 'inline-flex',
    width: fullWidth ? '100%' : undefined,
    alignItems: 'center',
    justifyContent: 'center',
    gap: '10px',
    padding: pad,
    fontFamily: 'var(--font-mono)',
    fontSize: fs,
    fontWeight: 700,
    letterSpacing: '0.06em',
    textTransform: 'uppercase',
    background: V.bg,
    color: V.fg,
    border: '1px solid ' + V.bd,
    borderRadius: 0,
    cursor: disabled ? 'not-allowed' : 'pointer',
    opacity: disabled ? 0.4 : 1,
    transition: 'background var(--dur-fast) var(--ease),color var(--dur-fast) var(--ease)',
    textDecoration: 'none',
    boxSizing: 'border-box',
    ...style
  };
  const Tag = href ? 'a' : 'button';
  return /*#__PURE__*/React.createElement(Tag, {
    href: href,
    onClick: disabled ? undefined : onClick,
    disabled: Tag === 'button' ? disabled : undefined,
    style: s,
    onMouseEnter: () => setH(true),
    onMouseLeave: () => {
      setH(false);
      setP(false);
    },
    onMouseDown: () => setP(true),
    onMouseUp: () => setP(false)
  }, children, iconRight && /*#__PURE__*/React.createElement("span", {
    "aria-hidden": "true"
  }, iconRight));
}
Object.assign(__ds_scope, { Button });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Button.jsx", error: String((e && e.message) || e) }); }

// components/core/LangSwitch.jsx
try { (() => {
function LangSwitch({
  value = 'ru',
  onChange,
  options = ['ru', 'en']
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'inline-flex',
      border: '1px solid var(--border-1)'
    }
  }, options.map(o => {
    const a = o === value;
    return /*#__PURE__*/React.createElement("button", {
      key: o,
      onClick: () => onChange && onChange(o),
      style: {
        padding: '6px 10px',
        background: a ? 'var(--fsp-white)' : 'transparent',
        color: a ? 'var(--fsp-black)' : 'var(--fg-2)',
        border: 0,
        fontFamily: 'var(--font-mono)',
        fontSize: '12px',
        fontWeight: 700,
        textTransform: 'uppercase',
        cursor: 'pointer'
      }
    }, o);
  }));
}
Object.assign(__ds_scope, { LangSwitch });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/LangSwitch.jsx", error: String((e && e.message) || e) }); }

// components/core/SectionTitle.jsx
try { (() => {
function SectionTitle({
  children,
  eyebrow,
  action,
  level = 2,
  style
}) {
  const fs = {
    1: 'var(--fs-h1)',
    2: 'var(--fs-h2)',
    3: 'var(--fs-h3)'
  }[level];
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'flex-end',
      justifyContent: 'space-between',
      gap: '24px',
      flexWrap: 'wrap',
      ...style
    }
  }, /*#__PURE__*/React.createElement("div", null, eyebrow && /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-mono)',
      fontSize: '14px',
      color: 'var(--fsp-blue)',
      fontWeight: 700,
      marginBottom: '8px'
    }
  }, eyebrow), /*#__PURE__*/React.createElement("div", {
    role: "heading",
    "aria-level": level,
    style: {
      fontFamily: 'var(--font-display)',
      fontSize: fs,
      fontWeight: 500,
      lineHeight: 1.1,
      letterSpacing: 'var(--ls-caps)',
      textTransform: 'uppercase',
      color: 'var(--fg-1)'
    }
  }, children)), action);
}
Object.assign(__ds_scope, { SectionTitle });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/SectionTitle.jsx", error: String((e && e.message) || e) }); }

// components/core/Tag.jsx
try { (() => {
const DISC = {
  product: 'var(--disc-product)',
  algo: 'var(--disc-algo)',
  uas: 'var(--disc-uas)',
  robotics: 'var(--disc-robotics)',
  security: 'var(--disc-security)',
  red: 'var(--fsp-red)'
};
function Tag({
  tone = 'neutral',
  discipline,
  children,
  style
}) {
  const c = discipline ? DISC[discipline] : tone === 'accent' ? 'var(--accent)' : tone === 'online' ? 'var(--disc-uas)' : tone === 'offline' ? 'var(--fsp-red)' : 'var(--fg-2)';
  return /*#__PURE__*/React.createElement("span", {
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: '6px',
      padding: '4px 10px',
      border: '1px solid ' + c,
      color: tone === 'neutral' && !discipline ? 'var(--fg-1)' : c,
      fontFamily: 'var(--font-mono)',
      fontSize: '12px',
      fontWeight: 500,
      lineHeight: 1.3,
      whiteSpace: 'nowrap',
      ...style
    }
  }, /*#__PURE__*/React.createElement("span", {
    "aria-hidden": "true",
    style: {
      width: 6,
      height: 6,
      background: c,
      display: 'inline-block'
    }
  }), children);
}
Object.assign(__ds_scope, { Tag });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Tag.jsx", error: String((e && e.message) || e) }); }

// components/content/EventCard.jsx
try { (() => {
function EventCard({
  day,
  month,
  title,
  format = 'Онлайн',
  location,
  discipline,
  href = '#',
  onClick
}) {
  const [h, setH] = React.useState(false);
  return /*#__PURE__*/React.createElement("a", {
    href: href,
    onClick: onClick,
    onMouseEnter: () => setH(true),
    onMouseLeave: () => setH(false),
    style: {
      display: 'grid',
      gridTemplateColumns: '96px minmax(0,1fr)',
      border: '1px solid ' + (h ? 'var(--fsp-blue)' : 'var(--border-1)'),
      background: h ? 'var(--bg-surface)' : 'transparent',
      color: 'var(--fg-1)',
      transition: 'all var(--dur-fast) var(--ease)'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      borderRight: '1px solid var(--border-1)',
      padding: '16px 0',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-pixel)',
      fontSize: '40px',
      lineHeight: 1,
      color: 'var(--fsp-blue)'
    }
  }, day), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: '12px',
      color: 'var(--fg-2)',
      marginTop: '6px'
    }
  }, month)), /*#__PURE__*/React.createElement("div", {
    style: {
      padding: '16px 20px',
      display: 'flex',
      flexDirection: 'column',
      gap: '12px'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: '15px',
      fontWeight: 700,
      lineHeight: 1.35,
      textWrap: 'pretty'
    }
  }, title), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: '8px',
      flexWrap: 'wrap',
      alignItems: 'center'
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.Tag, {
    tone: format === 'Оффлайн' ? 'offline' : 'online'
  }, format), discipline && /*#__PURE__*/React.createElement(__ds_scope.Tag, {
    discipline: discipline.key
  }, discipline.label), location && /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: '12px',
      color: 'var(--fg-2)'
    }
  }, location))));
}
Object.assign(__ds_scope, { EventCard });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/content/EventCard.jsx", error: String((e && e.message) || e) }); }

// components/feedback/Accordion.jsx
try { (() => {
function Accordion({
  items = [],
  defaultOpen = -1
}) {
  const [open, setOpen] = React.useState(defaultOpen);
  return /*#__PURE__*/React.createElement("div", {
    style: {
      borderBottom: '1px solid var(--border-1)'
    }
  }, items.map((it, i) => {
    const o = open === i;
    return /*#__PURE__*/React.createElement("div", {
      key: i,
      style: {
        borderTop: '1px solid var(--border-1)'
      }
    }, /*#__PURE__*/React.createElement("button", {
      onClick: () => setOpen(o ? -1 : i),
      style: {
        width: '100%',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        gap: '24px',
        padding: '22px 0',
        background: 'none',
        border: 0,
        color: 'var(--fg-1)',
        fontFamily: 'var(--font-mono)',
        fontSize: '16px',
        fontWeight: 700,
        textAlign: 'left',
        cursor: 'pointer'
      }
    }, /*#__PURE__*/React.createElement("span", null, it.q), /*#__PURE__*/React.createElement("span", {
      "aria-hidden": "true",
      style: {
        color: o ? 'var(--fsp-red)' : 'var(--fsp-blue)',
        fontSize: '22px',
        flexShrink: 0
      }
    }, o ? '−' : '+')), o && /*#__PURE__*/React.createElement("div", {
      style: {
        padding: '0 48px 22px 0',
        fontSize: '14px',
        lineHeight: 1.6,
        color: 'var(--fg-2)'
      }
    }, it.a));
  }));
}
Object.assign(__ds_scope, { Accordion });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/feedback/Accordion.jsx", error: String((e && e.message) || e) }); }

// components/feedback/CookieBanner.jsx
try { (() => {
function CookieBanner({
  onAccept,
  text = 'Используем cookies для улучшения работы сайта. Оставаясь с нами, вы соглашаетесь на использование файлов куки.',
  style
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: '20px',
      padding: '16px 20px',
      background: 'var(--bg-surface)',
      border: '1px solid var(--border-1)',
      maxWidth: '560px',
      boxShadow: 'var(--shadow-pop)',
      ...style
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: '13px',
      lineHeight: 1.5,
      color: 'var(--fg-1)'
    }
  }, text), /*#__PURE__*/React.createElement(__ds_scope.Button, {
    size: "sm",
    onClick: onAccept
  }, "\u041E\u041A"));
}
Object.assign(__ds_scope, { CookieBanner });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/feedback/CookieBanner.jsx", error: String((e && e.message) || e) }); }

// components/navigation/Footer.jsx
try { (() => {
function Footer({
  logoSrc,
  patternSrc,
  columns = [],
  copyright = 'Федерация спортивного программирования России ©2025'
}) {
  return /*#__PURE__*/React.createElement("footer", {
    style: {
      background: 'var(--bg-page)',
      borderTop: '1px solid var(--border-1)'
    }
  }, patternSrc && /*#__PURE__*/React.createElement("img", {
    src: patternSrc,
    alt: "",
    style: {
      display: 'block',
      width: '100%',
      maxWidth: 'var(--container)',
      margin: '0 auto',
      padding: '32px var(--gutter) 0',
      boxSizing: 'border-box'
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      maxWidth: 'var(--container)',
      margin: '0 auto',
      padding: '48px var(--gutter)',
      display: 'grid',
      gridTemplateColumns: 'minmax(0,1.3fr) repeat(' + Math.max(columns.length, 1) + ',minmax(0,1fr))',
      gap: '32px'
    }
  }, /*#__PURE__*/React.createElement("div", null, logoSrc ? /*#__PURE__*/React.createElement("img", {
    src: logoSrc,
    alt: "\u0424\u0421\u041F",
    style: {
      height: '44px'
    }
  }) : /*#__PURE__*/React.createElement("b", null, "\u0424\u0421\u041F")), columns.map(c => /*#__PURE__*/React.createElement("div", {
    key: c.title
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: '14px',
      fontWeight: 700,
      textTransform: 'uppercase',
      letterSpacing: 'var(--ls-caps)',
      marginBottom: '14px'
    }
  }, c.title), c.lines.map((l, i) => /*#__PURE__*/React.createElement("div", {
    key: i,
    style: {
      fontSize: '13px',
      color: 'var(--fg-2)',
      lineHeight: 1.7
    }
  }, l))))), /*#__PURE__*/React.createElement("div", {
    style: {
      borderTop: '1px solid var(--border-1)'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      maxWidth: 'var(--container)',
      margin: '0 auto',
      padding: '16px var(--gutter)',
      display: 'flex',
      justifyContent: 'space-between',
      gap: '16px',
      flexWrap: 'wrap',
      fontSize: '12px',
      color: 'var(--fg-muted)'
    }
  }, /*#__PURE__*/React.createElement("span", null, copyright), /*#__PURE__*/React.createElement("span", {
    style: {
      display: 'flex',
      gap: '24px'
    }
  }, /*#__PURE__*/React.createElement("a", {
    href: "#",
    style: {
      color: 'var(--fg-2)'
    }
  }, "\u041F\u043E\u043B\u0438\u0442\u0438\u043A\u0430 \u043A\u043E\u043D\u0444\u0438\u0434\u0435\u043D\u0446\u0438\u0430\u043B\u044C\u043D\u043E\u0441\u0442\u0438"), /*#__PURE__*/React.createElement("a", {
    href: "#",
    style: {
      color: 'var(--fg-2)'
    }
  }, "\u0423\u0441\u043B\u043E\u0432\u0438\u044F \u0441\u043E\u0433\u043B\u0430\u0448\u0435\u043D\u0438\u044F")))));
}
Object.assign(__ds_scope, { Footer });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/navigation/Footer.jsx", error: String((e && e.message) || e) }); }

// components/navigation/Header.jsx
try { (() => {
function NavItem({
  item,
  active,
  onNavigate
}) {
  const [open, setOpen] = React.useState(false);
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'relative'
    },
    onMouseEnter: () => setOpen(true),
    onMouseLeave: () => setOpen(false)
  }, /*#__PURE__*/React.createElement("a", {
    href: item.href || '#',
    onClick: e => {
      if (onNavigate) {
        e.preventDefault();
        onNavigate(item.id || item.label);
      }
    },
    style: {
      display: 'flex',
      alignItems: 'center',
      height: '80px',
      boxSizing: 'border-box',
      whiteSpace: 'nowrap',
      fontSize: 'clamp(12px,1.1vw,14px)',
      fontWeight: 500,
      color: active || open ? 'var(--fg-1)' : 'var(--fg-2)',
      borderBottom: '2px solid ' + (active ? 'var(--fsp-blue)' : 'transparent')
    }
  }, item.label), item.children && open && /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      top: '100%',
      left: '-16px',
      minWidth: '260px',
      background: 'var(--bg-surface)',
      border: '1px solid var(--border-1)',
      padding: '8px 0',
      zIndex: 20,
      boxShadow: 'var(--shadow-pop)'
    }
  }, item.children.map(c => /*#__PURE__*/React.createElement("a", {
    key: c.label,
    href: c.href || '#',
    onClick: e => {
      if (onNavigate) {
        e.preventDefault();
        onNavigate(c.id || c.label);
      }
    },
    style: {
      display: 'block',
      padding: '10px 16px',
      fontSize: '13px',
      color: 'var(--fg-1)'
    }
  }, c.label))));
}
function useNarrow(bp) {
  const get = () => typeof window !== 'undefined' && window.innerWidth < bp;
  const [n, setN] = React.useState(get);
  React.useEffect(() => {
    const f = () => setN(get());
    window.addEventListener('resize', f);
    return () => window.removeEventListener('resize', f);
  }, []);
  return n;
}
function Header({
  logoSrc,
  compactLogoSrc,
  nav = [],
  active,
  lang = 'ru',
  onLang,
  onNavigate,
  onLogin,
  onRegister,
  breakpoint = 1200
}) {
  const narrow = useNarrow(breakpoint);
  const [menu, setMenu] = React.useState(false);
  if (narrow) {
    const nv = id => {
      setMenu(false);
      onNavigate && onNavigate(id);
    };
    return /*#__PURE__*/React.createElement("header", {
      style: {
        background: 'var(--bg-page)',
        borderBottom: '1px solid var(--border-1)',
        position: 'sticky',
        top: 0,
        zIndex: 10
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        padding: '0 var(--gutter)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '16px',
        height: '64px'
      }
    }, /*#__PURE__*/React.createElement("a", {
      href: "#",
      onClick: e => {
        e.preventDefault();
        nv('home');
      },
      style: {
        display: 'flex'
      }
    }, compactLogoSrc || logoSrc ? /*#__PURE__*/React.createElement("img", {
      src: compactLogoSrc || logoSrc,
      alt: "\u0424\u0421\u041F",
      style: {
        height: '32px'
      }
    }) : /*#__PURE__*/React.createElement("b", null, "\u0424\u0421\u041F")), /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        alignItems: 'center',
        gap: '12px'
      }
    }, /*#__PURE__*/React.createElement(__ds_scope.LangSwitch, {
      value: lang,
      onChange: onLang
    }), /*#__PURE__*/React.createElement("button", {
      "aria-label": "\u041C\u0435\u043D\u044E",
      onClick: () => setMenu(!menu),
      style: {
        width: '44px',
        height: '44px',
        border: '1px solid var(--border-1)',
        background: menu ? 'var(--fsp-blue)' : 'transparent',
        color: 'var(--fg-1)',
        fontFamily: 'var(--font-mono)',
        fontSize: '18px',
        fontWeight: 700,
        cursor: 'pointer'
      }
    }, menu ? '×' : '≡'))), menu && /*#__PURE__*/React.createElement("div", {
      style: {
        borderTop: '1px solid var(--border-1)',
        padding: '8px var(--gutter) 20px',
        background: 'var(--bg-page)',
        maxHeight: 'calc(100vh - 64px)',
        overflowY: 'auto'
      }
    }, nav.map(i => /*#__PURE__*/React.createElement("div", {
      key: i.label,
      style: {
        borderBottom: '1px solid var(--border-1)',
        padding: '12px 0'
      }
    }, /*#__PURE__*/React.createElement("a", {
      href: "#",
      onClick: e => {
        e.preventDefault();
        nv(i.id || i.label);
      },
      style: {
        display: 'block',
        fontSize: '16px',
        fontWeight: 700,
        color: active === (i.id || i.label) ? 'var(--fsp-blue)' : 'var(--fg-1)'
      }
    }, i.label), i.children && /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        flexWrap: 'wrap',
        gap: '6px 16px',
        marginTop: '8px'
      }
    }, i.children.map(c => /*#__PURE__*/React.createElement("a", {
      key: c.label,
      href: "#",
      onClick: e => {
        e.preventDefault();
        nv(c.id || c.label);
      },
      style: {
        fontSize: '13px',
        color: 'var(--fg-2)'
      }
    }, c.label))))), /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        gap: '12px',
        marginTop: '16px'
      }
    }, /*#__PURE__*/React.createElement(__ds_scope.Button, {
      variant: "secondary",
      size: "sm",
      fullWidth: true,
      onClick: onLogin
    }, "\u0412\u043E\u0439\u0442\u0438"), /*#__PURE__*/React.createElement(__ds_scope.Button, {
      size: "sm",
      fullWidth: true,
      onClick: onRegister
    }, "\u0420\u0435\u0433\u0438\u0441\u0442\u0440\u0430\u0446\u0438\u044F"))));
  }
  return /*#__PURE__*/React.createElement("header", {
    style: {
      background: 'var(--bg-page)',
      borderBottom: '1px solid var(--border-1)',
      position: 'sticky',
      top: 0,
      zIndex: 10
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      maxWidth: 'var(--container)',
      margin: '0 auto',
      padding: '0 var(--gutter)',
      display: 'flex',
      alignItems: 'center',
      gap: 'clamp(16px,2vw,32px)',
      height: '80px'
    }
  }, /*#__PURE__*/React.createElement("a", {
    href: "#",
    onClick: e => {
      if (onNavigate) {
        e.preventDefault();
        onNavigate('home');
      }
    },
    style: {
      display: 'flex',
      alignItems: 'center',
      flexShrink: 0
    }
  }, logoSrc ? /*#__PURE__*/React.createElement("img", {
    src: logoSrc,
    alt: "\u0424\u0421\u041F",
    style: {
      height: '36px'
    }
  }) : /*#__PURE__*/React.createElement("b", {
    style: {
      fontSize: '22px'
    }
  }, "\u0424\u0421\u041F")), /*#__PURE__*/React.createElement("nav", {
    style: {
      display: 'flex',
      gap: 'clamp(12px,1.6vw,24px)',
      flex: 1,
      minWidth: 0,
      flexWrap: 'nowrap'
    }
  }, nav.map(i => /*#__PURE__*/React.createElement(NavItem, {
    key: i.label,
    item: i,
    active: active === (i.id || i.label),
    onNavigate: onNavigate
  }))), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: '12px',
      flexShrink: 0
    }
  }, /*#__PURE__*/React.createElement(__ds_scope.LangSwitch, {
    value: lang,
    onChange: onLang
  }), /*#__PURE__*/React.createElement(__ds_scope.Button, {
    variant: "ghost",
    size: "sm",
    onClick: onLogin
  }, "\u0412\u043E\u0439\u0442\u0438"), /*#__PURE__*/React.createElement(__ds_scope.Button, {
    variant: "primary",
    size: "sm",
    onClick: onRegister
  }, "\u0420\u0435\u0433\u0438\u0441\u0442\u0440\u0430\u0446\u0438\u044F"))));
}
Object.assign(__ds_scope, { Header });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/navigation/Header.jsx", error: String((e && e.message) || e) }); }

// ui_kits/website/Calendar.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const {
  EventCard: CEventCard,
  SectionTitle: CSectionTitle,
  Tag: CTag
} = window.DesignSystem_2ade33;
function Calendar() {
  const D = window.FSP_DATA;
  const [tab, setTab] = React.useState('Анонс');
  const [f, setF] = React.useState('Все');
  const DL = {
    product: 'Продуктовое',
    robotics: 'Робототехника'
  };
  const list = D.events.filter(e => f === 'Все' || e.format === f);
  return /*#__PURE__*/React.createElement("main", {
    style: {
      maxWidth: 'var(--container)',
      margin: '0 auto',
      padding: '48px var(--gutter) 80px',
      boxSizing: 'border-box'
    }
  }, /*#__PURE__*/React.createElement(CSectionTitle, {
    level: 1
  }, "\u041A\u0430\u043B\u0435\u043D\u0434\u0430\u0440\u044C"), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      margin: '32px 0 24px',
      gap: 16,
      flexWrap: 'wrap',
      borderBottom: '1px solid var(--border-1)'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 24
    }
  }, ['Анонс', 'Архив событий'].map(t => /*#__PURE__*/React.createElement("button", {
    key: t,
    onClick: () => setTab(t),
    style: {
      background: 'none',
      border: 0,
      borderBottom: '2px solid ' + (tab === t ? 'var(--fsp-blue)' : 'transparent'),
      color: tab === t ? 'var(--fg-1)' : 'var(--fg-2)',
      padding: '12px 0',
      fontFamily: 'var(--font-mono)',
      fontSize: 15,
      fontWeight: 700,
      cursor: 'pointer'
    }
  }, t))), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 8,
      paddingBottom: 8
    }
  }, ['Все', 'Онлайн', 'Оффлайн'].map(x => /*#__PURE__*/React.createElement("button", {
    key: x,
    onClick: () => setF(x),
    style: {
      padding: '6px 12px',
      border: '1px solid ' + (f === x ? 'var(--fsp-white)' : 'var(--border-1)'),
      background: f === x ? 'var(--fsp-white)' : 'transparent',
      color: f === x ? 'var(--fsp-black)' : 'var(--fg-2)',
      fontFamily: 'var(--font-mono)',
      fontSize: 12,
      fontWeight: 700,
      cursor: 'pointer'
    }
  }, x)))), tab === 'Анонс' ? /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'grid',
      gridTemplateColumns: '1fr 1fr',
      gap: 12
    }
  }, list.map((e, i) => /*#__PURE__*/React.createElement(CEventCard, _extends({
    key: i
  }, e, {
    discipline: e.d ? {
      key: e.d,
      label: DL[e.d]
    } : null
  })))) : /*#__PURE__*/React.createElement("div", {
    style: {
      border: '1px dashed var(--border-1)',
      padding: 48,
      textAlign: 'center',
      color: 'var(--fg-2)'
    }
  }, "\u0410\u0440\u0445\u0438\u0432 \u0441\u043E\u0431\u044B\u0442\u0438\u0439 \u2014 \u0441\u043E\u0434\u0435\u0440\u0436\u0438\u043C\u043E\u0435 \u043D\u0435 \u0432\u043E\u0441\u043F\u0440\u043E\u0438\u0437\u0432\u043E\u0434\u0438\u0442\u0441\u044F \u0432 UI kit."));
}
window.Calendar = Calendar;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/website/Calendar.jsx", error: String((e && e.message) || e) }); }

// ui_kits/website/Home.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const {
  NewsCard,
  EventCard,
  DisciplineCard,
  RegionCard,
  MediaCard,
  StatBlock,
  Timeline,
  SectionTitle,
  Button,
  Accordion
} = window.DesignSystem_2ade33;
const HW = {
  maxWidth: 'var(--container)',
  margin: '0 auto',
  padding: '0 var(--gutter)',
  boxSizing: 'border-box'
};
function Home({
  go
}) {
  const D = window.FSP_DATA;
  return /*#__PURE__*/React.createElement("main", null, /*#__PURE__*/React.createElement("section", {
    style: {
      ...HW,
      padding: '40px var(--gutter) 64px',
      display: 'flex',
      flexWrap: 'wrap',
      gap: 24,
      alignItems: 'flex-start'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fill,minmax(220px,1fr))',
      gap: 16,
      flex: '2 1 560px',
      minWidth: 0
    }
  }, D.news.map((n, i) => /*#__PURE__*/React.createElement(NewsCard, {
    key: i,
    image: n.img,
    title: n.title,
    date: n.date,
    onClick: e => {
      e.preventDefault();
      go('article', i);
    }
  }))), /*#__PURE__*/React.createElement("aside", {
    style: {
      flex: '1 1 300px',
      minWidth: 0
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 20,
      fontWeight: 700,
      textTransform: 'uppercase',
      letterSpacing: 'var(--ls-caps)',
      marginBottom: 16
    }
  }, "\u0421\u043E\u0431\u044B\u0442\u0438\u044F"), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: 10
    }
  }, D.events.slice(0, 5).map((e, i) => /*#__PURE__*/React.createElement(EventCard, _extends({
    key: i
  }, e, {
    discipline: null,
    onClick: ev => {
      ev.preventDefault();
      go('calendar');
    }
  })))), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 16
    }
  }, /*#__PURE__*/React.createElement(Button, {
    variant: "secondary",
    fullWidth: true,
    iconRight: "\u2192",
    onClick: () => go('calendar')
  }, "\u041A\u0430\u043B\u0435\u043D\u0434\u0430\u0440\u044C")))), /*#__PURE__*/React.createElement("section", {
    id: "about",
    style: {
      borderTop: '1px solid var(--border-1)'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      ...HW,
      padding: '72px var(--gutter)'
    }
  }, /*#__PURE__*/React.createElement(SectionTitle, {
    level: 1
  }, "\u0424\u0435\u0434\u0435\u0440\u0430\u0446\u0438\u044F \u0441\u043F\u043E\u0440\u0442\u0438\u0432\u043D\u043E\u0433\u043E \u043F\u0440\u043E\u0433\u0440\u0430\u043C\u043C\u0438\u0440\u043E\u0432\u0430\u043D\u0438\u044F"), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'grid',
      gridTemplateColumns: '1fr 1fr',
      gap: 48,
      marginTop: 40
    }
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 18,
      fontWeight: 700,
      marginBottom: 12
    }
  }, "\u0421\u043F\u043E\u0440\u0442\u0438\u0432\u043D\u043E\u0435 \u043F\u0440\u043E\u0433\u0440\u0430\u043C\u043C\u0438\u0440\u043E\u0432\u0430\u043D\u0438\u0435"), /*#__PURE__*/React.createElement("p", {
    style: {
      margin: 0,
      color: 'var(--fg-2)',
      fontSize: 15
    }
  }, "\u0420\u0430\u0437\u043D\u043E\u0432\u0438\u0434\u043D\u043E\u0441\u0442\u044C \u0438\u043D\u0442\u0435\u043B\u043B\u0435\u043A\u0442\u0443\u0430\u043B\u044C\u043D\u043E\u0433\u043E \u0441\u043F\u043E\u0440\u0442\u0430. \u0421\u043E\u0440\u0435\u0432\u043D\u043E\u0432\u0430\u043D\u0438\u044F \u0432\u043A\u043B\u044E\u0447\u0430\u044E\u0442 \u0440\u0435\u0448\u0435\u043D\u0438\u0435 \u043D\u0430\u0431\u043E\u0440\u0430 \u0437\u0430\u0434\u0430\u0447 \u0438\u043B\u0438 \u043E\u0434\u043D\u043E\u0439 \u0437\u0430\u0434\u0430\u0447\u0438: \u043D\u0430\u043F\u0438\u0441\u0430\u043D\u0438\u0435 \u043F\u0440\u043E\u0433\u0440\u0430\u043C\u043C\u044B \u043D\u0430 \u043E\u0434\u043D\u043E\u043C \u0438\u0437 \u044F\u0437\u044B\u043A\u043E\u0432 \u043F\u0440\u043E\u0433\u0440\u0430\u043C\u043C\u0438\u0440\u043E\u0432\u0430\u043D\u0438\u044F \u0432 \u0440\u0435\u0436\u0438\u043C\u0435 \u043E\u0433\u0440\u0430\u043D\u0438\u0447\u0435\u043D\u043D\u043E\u0433\u043E \u0432\u0440\u0435\u043C\u0435\u043D\u0438, \u0432 \u0441\u043E\u043E\u0442\u0432\u0435\u0442\u0441\u0442\u0432\u0443\u044E\u0449\u0435\u043C \u0441\u0435\u0433\u043C\u0435\u043D\u0442\u0435 IT-\u043E\u0442\u0440\u0430\u0441\u043B\u0438.")), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 18,
      fontWeight: 700,
      marginBottom: 12
    }
  }, "\u0424\u0435\u0434\u0435\u0440\u0430\u0446\u0438\u044F \u0441\u043F\u043E\u0440\u0442\u0438\u0432\u043D\u043E\u0433\u043E \u043F\u0440\u043E\u0433\u0440\u0430\u043C\u043C\u0438\u0440\u043E\u0432\u0430\u043D\u0438\u044F"), /*#__PURE__*/React.createElement("p", {
    style: {
      margin: 0,
      color: 'var(--fg-2)',
      fontSize: 15
    }
  }, "\u042D\u0442\u043E \u043E\u0431\u0449\u0435\u0441\u0442\u0432\u0435\u043D\u043D\u0430\u044F \u0441\u043F\u043E\u0440\u0442\u0438\u0432\u043D\u0430\u044F \u043E\u0440\u0433\u0430\u043D\u0438\u0437\u0430\u0446\u0438\u044F, \u043A\u043E\u0442\u043E\u0440\u0430\u044F \u0440\u0430\u0437\u0432\u0438\u0432\u0430\u0435\u0442 \u0438 \u043F\u043E\u043F\u0443\u043B\u044F\u0440\u0438\u0437\u0438\u0440\u0443\u0435\u0442 \u0441\u043F\u043E\u0440\u0442\u0438\u0432\u043D\u043E\u0435 \u043F\u0440\u043E\u0433\u0440\u0430\u043C\u043C\u0438\u0440\u043E\u0432\u0430\u043D\u0438\u0435 \u0432 \u0420\u043E\u0441\u0441\u0438\u0438, \u043F\u0440\u043E\u0432\u043E\u0434\u0438\u0442 \u0441\u043E\u0440\u0435\u0432\u043D\u043E\u0432\u0430\u043D\u0438\u044F \u043D\u0430\u0446\u0438\u043E\u043D\u0430\u043B\u044C\u043D\u043E\u0433\u043E \u0443\u0440\u043E\u0432\u043D\u044F. \u041C\u044B \u0442\u0430\u043A\u0436\u0435 \u0437\u0430\u043D\u0438\u043C\u0430\u0435\u043C\u0441\u044F \u0444\u043E\u0440\u043C\u0438\u0440\u043E\u0432\u0430\u043D\u0438\u0435\u043C \u043D\u0430\u0446\u0438\u043E\u043D\u0430\u043B\u044C\u043D\u044B\u0445 \u0441\u0431\u043E\u0440\u043D\u044B\u0445, \u043E\u0431\u0443\u0447\u0435\u043D\u0438\u0435\u043C \u0438 \u0430\u0442\u0442\u0435\u0441\u0442\u0430\u0446\u0438\u0435\u0439 \u0441\u043F\u043E\u0440\u0442\u0438\u0432\u043D\u044B\u0445 \u0441\u0443\u0434\u0435\u0439, \u0430\u043A\u043A\u0440\u0435\u0434\u0438\u0442\u0430\u0446\u0438\u0435\u0439 \u043F\u043B\u043E\u0449\u0430\u0434\u043E\u043A, \u043F\u043E\u0434\u0433\u043E\u0442\u043E\u0432\u043A\u043E\u0439 \u043C\u0435\u0442\u043E\u0434\u0438\u0447\u0435\u0441\u043A\u0438\u0445 \u043C\u0430\u0442\u0435\u0440\u0438\u0430\u043B\u043E\u0432, \u043E\u0431\u0440\u0430\u0437\u043E\u0432\u0430\u0442\u0435\u043B\u044C\u043D\u044B\u043C\u0438 \u043F\u0440\u043E\u0435\u043A\u0442\u0430\u043C\u0438, \u0440\u0430\u0437\u0432\u0438\u0442\u0438\u0435\u043C \u043A\u043B\u0443\u0431\u043E\u0432 \u0438 \u0441\u0435\u043A\u0446\u0438\u0439."))), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 48
    }
  }, /*#__PURE__*/React.createElement(Timeline, {
    items: D.timeline
  })))), /*#__PURE__*/React.createElement("section", {
    style: {
      background: 'var(--fsp-digital)'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      ...HW,
      padding: '72px var(--gutter)'
    }
  }, /*#__PURE__*/React.createElement(SectionTitle, null, "\u0414\u0438\u0441\u0446\u0438\u043F\u043B\u0438\u043D\u044B \u0441\u043F\u043E\u0440\u0442\u0438\u0432\u043D\u043E\u0433\u043E \u043F\u0440\u043E\u0433\u0440\u0430\u043C\u043C\u0438\u0440\u043E\u0432\u0430\u043D\u0438\u044F"), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'grid',
      gridTemplateColumns: 'repeat(5,minmax(0,1fr))',
      gap: 16,
      marginTop: 40
    }
  }, D.disciplines.map(d => /*#__PURE__*/React.createElement(DisciplineCard, {
    key: d.k,
    discipline: d.k,
    title: d.t,
    description: d.d
  }))))), /*#__PURE__*/React.createElement("section", null, /*#__PURE__*/React.createElement("div", {
    style: {
      ...HW,
      padding: '72px var(--gutter)'
    }
  }, /*#__PURE__*/React.createElement(SectionTitle, {
    action: /*#__PURE__*/React.createElement(Button, {
      variant: "ghost",
      iconRight: "\u2192",
      onClick: () => go('regions')
    }, "\u0412\u0441\u0435 \u0440\u0435\u0433\u0438\u043E\u043D\u044B")
  }, "\u0413\u0435\u043E\u0433\u0440\u0430\u0444\u0438\u044F \u0424\u0421\u041F"), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'grid',
      gridTemplateColumns: '320px minmax(0,1fr)',
      gap: 40,
      marginTop: 40,
      alignItems: 'start'
    }
  }, /*#__PURE__*/React.createElement(StatBlock, {
    value: "89",
    label: "\u0434\u0435\u0439\u0441\u0442\u0432\u0443\u044E\u0449\u0438\u0445 \u0440\u0435\u0433\u0438\u043E\u043D\u0430\u043B\u044C\u043D\u044B\u0445 \u043F\u0440\u0435\u0434\u0441\u0442\u0430\u0432\u0438\u0442\u0435\u043B\u044C\u0441\u0442\u0432 \u0424\u0421\u041F \u0432 \u0420\u043E\u0441\u0441\u0438\u0438"
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'grid',
      gridTemplateColumns: 'repeat(3,minmax(0,1fr))',
      gap: 12
    }
  }, D.regions.slice(0, 6).map(r => /*#__PURE__*/React.createElement(RegionCard, {
    key: r,
    name: r,
    onClick: e => {
      e.preventDefault();
      go('regions');
    }
  })))))), /*#__PURE__*/React.createElement("section", {
    style: {
      borderTop: '1px solid var(--border-1)'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      ...HW,
      padding: '72px var(--gutter)'
    }
  }, /*#__PURE__*/React.createElement(SectionTitle, null, "\u0424\u0421\u041F \u0432 \u0421\u041C\u0418"), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'grid',
      gridTemplateColumns: 'repeat(4,minmax(0,1fr))',
      gap: 24,
      marginTop: 32
    }
  }, D.media.map((m, i) => /*#__PURE__*/React.createElement(MediaCard, {
    key: i,
    source: m.s,
    date: m.d,
    title: m.t
  }))))), /*#__PURE__*/React.createElement("section", {
    style: {
      borderTop: '1px solid var(--border-1)'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      ...HW,
      padding: '56px var(--gutter)'
    }
  }, /*#__PURE__*/React.createElement(SectionTitle, {
    level: 3
  }, "\u041F\u0430\u0440\u0442\u043D\u0435\u0440\u044B"), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 16,
      marginTop: 24,
      flexWrap: 'wrap'
    }
  }, D.partners.map((p, i) => /*#__PURE__*/React.createElement("div", {
    key: i,
    style: {
      flex: '1 1 160px',
      height: 96,
      background: 'var(--fsp-white)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: 16,
      boxSizing: 'border-box'
    }
  }, /*#__PURE__*/React.createElement("img", {
    src: p,
    alt: "",
    style: {
      maxWidth: '100%',
      maxHeight: '100%'
    }
  })))))), /*#__PURE__*/React.createElement("section", {
    style: {
      borderTop: '1px solid var(--border-1)'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      ...HW,
      padding: '72px var(--gutter)',
      display: 'grid',
      gridTemplateColumns: '1fr 2fr',
      gap: 48
    }
  }, /*#__PURE__*/React.createElement(SectionTitle, null, "FAQ"), /*#__PURE__*/React.createElement(Accordion, {
    items: D.faq,
    defaultOpen: 0
  }))));
}
window.Home = Home;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/website/Home.jsx", error: String((e && e.message) || e) }); }

// ui_kits/website/News.jsx
try { (() => {
const {
  NewsCard: NNewsCard,
  SectionTitle: NSectionTitle,
  Button: NButton
} = window.DesignSystem_2ade33;
function News({
  go
}) {
  const D = window.FSP_DATA;
  return /*#__PURE__*/React.createElement("main", {
    style: {
      maxWidth: 'var(--container)',
      margin: '0 auto',
      padding: '48px var(--gutter) 80px',
      boxSizing: 'border-box'
    }
  }, /*#__PURE__*/React.createElement(NSectionTitle, {
    level: 1
  }, "\u041D\u043E\u0432\u043E\u0441\u0442\u0438"), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'grid',
      gridTemplateColumns: 'repeat(3,minmax(0,1fr))',
      gap: 20,
      marginTop: 32
    }
  }, D.news.map((n, i) => /*#__PURE__*/React.createElement(NNewsCard, {
    key: i,
    size: "lg",
    image: n.img,
    title: n.title,
    date: n.date,
    onClick: e => {
      e.preventDefault();
      go('article', i);
    }
  }))));
}
function Article({
  go,
  idx = 0
}) {
  const n = window.FSP_DATA.news[idx];
  return /*#__PURE__*/React.createElement("main", {
    style: {
      maxWidth: 880,
      margin: '0 auto',
      padding: '40px var(--gutter) 80px',
      boxSizing: 'border-box'
    }
  }, /*#__PURE__*/React.createElement(NButton, {
    variant: "ghost",
    size: "sm",
    onClick: () => go('news')
  }, "\u2190 \u041D\u043E\u0432\u043E\u0441\u0442\u0438"), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 13,
      color: 'var(--fg-2)',
      margin: '24px 0 12px'
    }
  }, n.date), /*#__PURE__*/React.createElement("h1", {
    style: {
      margin: 0,
      fontSize: 32,
      lineHeight: 1.2,
      fontWeight: 700,
      textWrap: 'pretty'
    }
  }, n.title), /*#__PURE__*/React.createElement("img", {
    src: n.img,
    alt: "",
    style: {
      width: '100%',
      aspectRatio: '16/9',
      objectFit: 'cover',
      display: 'block',
      margin: '32px 0'
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      border: '1px dashed var(--border-1)',
      padding: 24,
      color: 'var(--fg-2)',
      fontSize: 14
    }
  }, "\u0422\u0435\u043A\u0441\u0442 \u0441\u0442\u0430\u0442\u044C\u0438 \u043D\u0435 \u0432\u043E\u0441\u043F\u0440\u043E\u0438\u0437\u0432\u043E\u0434\u0438\u0442\u0441\u044F \u2014 \u043E\u0442\u043A\u0440\u043E\u0439\u0442\u0435 \u043E\u0440\u0438\u0433\u0438\u043D\u0430\u043B \u043D\u0430 fsp-russia.ru."));
}
window.News = News;
window.Article = Article;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/website/News.jsx", error: String((e && e.message) || e) }); }

// ui_kits/website/Regions.jsx
try { (() => {
const {
  RegionCard: RRegionCard,
  SectionTitle: RSectionTitle,
  StatBlock: RStatBlock
} = window.DesignSystem_2ade33;
function Regions() {
  const D = window.FSP_DATA;
  const [q, setQ] = React.useState('');
  const list = D.regions.filter(r => r.toLowerCase().includes(q.toLowerCase()));
  return /*#__PURE__*/React.createElement("main", {
    style: {
      maxWidth: 'var(--container)',
      margin: '0 auto',
      padding: '48px var(--gutter) 80px',
      boxSizing: 'border-box'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'flex-end',
      gap: 24,
      flexWrap: 'wrap'
    }
  }, /*#__PURE__*/React.createElement(RSectionTitle, {
    level: 1
  }, "\u041A\u043E\u043D\u0442\u0430\u043A\u0442\u044B \u043F\u0440\u0435\u0434\u0441\u0442\u0430\u0432\u0438\u0442\u0435\u043B\u0435\u0439"), /*#__PURE__*/React.createElement(RStatBlock, {
    value: "89",
    size: "md",
    label: "\u0440\u0435\u0433\u0438\u043E\u043D\u0430\u043B\u044C\u043D\u044B\u0445 \u043F\u0440\u0435\u0434\u0441\u0442\u0430\u0432\u0438\u0442\u0435\u043B\u044C\u0441\u0442\u0432"
  })), /*#__PURE__*/React.createElement("input", {
    value: q,
    onChange: e => setQ(e.target.value),
    placeholder: "\u041F\u043E\u0438\u0441\u043A \u0440\u0435\u0433\u0438\u043E\u043D\u0430",
    style: {
      width: '100%',
      boxSizing: 'border-box',
      margin: '32px 0 24px',
      padding: '14px 16px',
      background: 'var(--bg-surface)',
      border: '1px solid var(--border-1)',
      borderRadius: 'var(--radius-sm)',
      color: 'var(--fg-1)',
      fontFamily: 'var(--font-mono)',
      fontSize: 15,
      outline: 'none'
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'grid',
      gridTemplateColumns: 'repeat(4,minmax(0,1fr))',
      gap: 12
    }
  }, list.map(r => /*#__PURE__*/React.createElement(RRegionCard, {
    key: r,
    name: r
  }))));
}
window.Regions = Regions;
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/website/Regions.jsx", error: String((e && e.message) || e) }); }

// ui_kits/website/data.js
try { (() => {
window.FSP_DATA = {
  nav: [{
    label: 'О нас',
    id: 'about',
    children: [{
      label: 'О Федерации',
      id: 'about'
    }, {
      label: 'Руководство'
    }, {
      label: 'Как стать членом федерации'
    }, {
      label: 'Документы'
    }, {
      label: 'Сборная России'
    }, {
      label: 'Международное сотрудничество'
    }]
  }, {
    label: 'Регионы',
    id: 'regions',
    children: [{
      label: 'Контакты представителей',
      id: 'regions'
    }]
  }, {
    label: 'Календарь',
    id: 'calendar',
    children: [{
      label: 'Анонс',
      id: 'calendar'
    }, {
      label: 'Архив событий',
      id: 'calendar'
    }]
  }, {
    label: 'Статистика'
  }, {
    label: 'Антидопинг'
  }, {
    label: 'Пресс-служба',
    id: 'news',
    children: [{
      label: 'ФСП в СМИ'
    }, {
      label: 'Новости',
      id: 'news'
    }, {
      label: 'Фото и видео'
    }, {
      label: 'Брендбук'
    }, {
      label: 'Логотипы'
    }]
  }, {
    label: 'Контакты'
  }],
  news: [{
    img: 'https://fsp-russia.ru/upload/iblock/e91/c5yf7wqs6jm80qn2mx16xzz2er431okz.jpg',
    title: 'Кубок Федерации спортивного программирования — регистрация открыта',
    date: '09 сентября 2026'
  }, {
    img: 'https://fsp-russia.ru/upload/iblock/947/4a911ebhidxw5avnwpbk5cpn31brfsr5.jpg',
    title: 'Завершился первый Кубок Дальнего Востока по спортивному программированию',
    date: '09 сентября 2026'
  }, {
    img: 'https://fsp-russia.ru/upload/iblock/c89/jkygobl18vwb61h1d3chws1q496hlwj4.jpg',
    title: 'Стартует регистрация на Чемпионат и Первенство России по продуктовому программированию',
    date: '09 сентября 2026'
  }, {
    img: 'https://fsp-russia.ru/upload/iblock/c0b/ylo9rfvcf3i35cjj4hw34v5antui6o25.jpg',
    title: 'Федерация спортивного программирования представила технологические разработки на заседании комиссии Госсовета',
    date: '29 июля 2026'
  }, {
    img: 'https://fsp-russia.ru/upload/iblock/cbd/2a2uxpb6hb142279zz1jikkrj4d5k3h9.jpg',
    title: 'СТАРТ НА «БИРЮСЕ»: НАУКА, ТЕХНОЛОГИИ И СПОРТИВНОЕ ПРОГРАММИРОВАНИЕ ОБЪЕДИНИЛИ УЧАСТНИКОВ ВСЕРОССИЙСКОГО ФОРУМА',
    date: '02 июля 2026'
  }, {
    img: 'https://fsp-russia.ru/upload/iblock/238/8lt85oam5m1jiygvwvcrquub3h8rym8w.jpg',
    title: 'Финал Кубка России по спортивному программированию в дисциплине «Программирование робототехники» успешно завершился в Санкт-Петербурге',
    date: '02 июля 2026'
  }],
  events: [{
    day: '25',
    month: 'июня',
    title: 'Кубок России финальный этап',
    format: 'Оффлайн',
    location: 'г. Санкт-Петербург',
    d: 'robotics'
  }, {
    day: '11',
    month: 'сентября',
    title: 'Международные спортивные соревнования',
    format: 'Оффлайн',
    location: 'Свердловская область'
  }, {
    day: '11',
    month: 'сентября',
    title: 'Всероссийский фестиваль по спортивному программированию, приуроченный ко Дню программиста',
    format: 'Оффлайн',
    location: 'по всей России'
  }, {
    day: '17',
    month: 'сентября',
    title: 'Всероссийское физкультурное мероприятие "Кубок Федерации спортивного программирования России" (отборочный этап среди округов)',
    format: 'Онлайн',
    location: 'по месту нахождения участников'
  }, {
    day: '03',
    month: 'октября',
    title: 'Чемпионат и Первенство ФО',
    format: 'Онлайн',
    location: 'по месту нахождения участников',
    d: 'product'
  }, {
    day: '06',
    month: 'октября',
    title: 'Чемпионат и Первенство ФО',
    format: 'Онлайн',
    location: 'по месту нахождения участников',
    d: 'product'
  }],
  timeline: [{
    date: '19 октября 2021',
    text: 'Дата основания Федерации спортивного программирования'
  }, {
    date: '12 апреля 2022',
    text: 'Спортивное программирование было официально признано видом спорта'
  }, {
    date: '16 июня 2022',
    text: 'На площадке ПМЭФ Минспорта и Минцифры подписали меморандум о сотрудничестве в целях развития и популяризации нового вида спорта «спортивное программирование»'
  }, {
    date: '17 февраля 2023',
    text: 'ФСП получила статус Общероссийской спортивной федерации'
  }, {
    date: '2 августа 2023',
    text: 'Федерация включена в реестр социально ориентированных некоммерческих организаций (СОНКО)'
  }],
  disciplines: [{
    k: 'product',
    t: 'Продуктовое программирование (хакатон)',
    d: 'Создание программных продуктов (приложений, сайтов, сервисов), отвечающих заданным требованиям и выполняющих определенные прикладные задачи'
  }, {
    k: 'algo',
    t: 'Программирование алгоритмическое',
    d: 'Решение группы задач путем написания наиболее оптимальных программных алгоритмов в условиях ограниченного времени'
  }, {
    k: 'security',
    t: 'Программирование систем информационной безопасности',
    d: 'Комплекс соревнований в области кибербезопасности, включающий в себя поиск и устранение системных уязвимостей, отработку кибератак и защиты от них'
  }, {
    k: 'robotics',
    t: 'Программирование робототехники',
    d: 'Написание кода и поведенческих алгоритмов для автономных роботов, соревнующихся по определенным правилам'
  }, {
    k: 'uas',
    t: 'Программирование БАС',
    d: 'Написание кода для автономного полета дрона или роя дронов, а также выполнения им поставленных задач в условиях соревновательного полигона'
  }],
  regions: ['Донецкая Народная Республика', 'Республика Дагестан', 'Республика Башкортостан', 'Курганская область', 'Республика Алтай', 'Республика Саха-Якутия', 'Республика Карелия', 'Белгородская область', 'Свердловская область', 'Республика Татарстан', 'Челябинская область', 'Новосибирская область', 'Приморский край', 'Краснодарский край', 'Пермский край', 'Самарская область', 'г. Санкт Петербург', 'г. Москва'],
  media: [{
    s: 'Советский спорт',
    d: '30 июля 2026',
    t: 'В Кисловодске завершились первые сборы сборной России по спортивному программированию'
  }, {
    s: 'РБ спорт',
    d: '24 июня 2026',
    t: 'Федерация спортивного программирования присоединилась к «РуКоду»'
  }, {
    s: 'Советский спорт',
    d: '19 июня 2026',
    t: 'Финал Кубка по спортивному программированию в дисциплине «Программирование робототехники» пройдёт в Санкт-Петербурге'
  }, {
    s: 'Панорама Саратова',
    d: '23 сентября 2025',
    t: 'Сильнейшие программисты со всей страны приехали в Саратов'
  }],
  partners: ['https://fsp-russia.ru/upload/iblock/ef0/cay74w9j5w3g4oe53h3gf7k5zq302y1t.svg', 'https://fsp-russia.ru/upload/iblock/65d/du8h7f1741ozvzuuuqpxb4rqgzcoq8tz.svg', 'https://fsp-russia.ru/upload/iblock/94c/3oegw92xnmb6dmzu7n4fgcaa6135898p.svg', 'https://fsp-russia.ru/upload/iblock/685/9c5ch31th9foux01zvjjxaea268ec2ie.png', 'https://fsp-russia.ru/upload/iblock/ca0/jdohy3dj59ar7sq0kz10sqp765icasdu.svg'],
  faq: [{
    q: 'Как получить разряд по спортивному программированию?',
    a: 'Разряды по спортивному программированию выдаются по результатам участия в официальных соревнованиях. Критерии присвоения разрядов опубликованы на сайте Министерства спорта РФ в разделе «Виды спорта, развиваемые на общероссийском уровне» и доступны для ознакомления всем желающим.'
  }, {
    q: 'Где находится отделение ФСП в моем регионе?',
    a: 'Федерация спортивного программирования имеет представительства в 89 регионах. С адресами и контактами представителей ФСП в вашем городе можно ознакомиться в разделе «Регионы».'
  }]
};
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/website/data.js", error: String((e && e.message) || e) }); }

__ds_ns.DisciplineCard = __ds_scope.DisciplineCard;

__ds_ns.EventCard = __ds_scope.EventCard;

__ds_ns.MediaCard = __ds_scope.MediaCard;

__ds_ns.NewsCard = __ds_scope.NewsCard;

__ds_ns.RegionCard = __ds_scope.RegionCard;

__ds_ns.StatBlock = __ds_scope.StatBlock;

__ds_ns.Timeline = __ds_scope.Timeline;

__ds_ns.Button = __ds_scope.Button;

__ds_ns.LangSwitch = __ds_scope.LangSwitch;

__ds_ns.SectionTitle = __ds_scope.SectionTitle;

__ds_ns.Tag = __ds_scope.Tag;

__ds_ns.Accordion = __ds_scope.Accordion;

__ds_ns.CookieBanner = __ds_scope.CookieBanner;

__ds_ns.Footer = __ds_scope.Footer;

__ds_ns.Header = __ds_scope.Header;

})();
