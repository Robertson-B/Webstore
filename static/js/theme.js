(function(){
  const THEME_KEY = 'theme'; // 'light'|'dark'|'system'
  const body = document.body;
  const meta = document.querySelector('meta[name="theme-color"]');

  function applyTheme(theme){
    if(theme === 'system'){
      body.classList.remove('dark');
      document.documentElement.classList.remove('user-theme');
      // set meta to match system
      const isDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
      if(meta) meta.setAttribute('content', isDark ? '#0f1720' : '#00a87e');
      updateToggleIcon('system');
      return;
    }
    document.documentElement.classList.add('user-theme');
    if(theme === 'dark'){
      body.classList.add('dark');
      if(meta) meta.setAttribute('content', '#0f1720');
      updateToggleIcon('dark');
    } else {
      body.classList.remove('dark');
      if(meta) meta.setAttribute('content', '#00a87e');
      updateToggleIcon('light');
    }
  }

  function updateToggleIcon(state){
    const btn = document.getElementById('theme-toggle');
    if(!btn) return;
    if(state === 'dark') btn.textContent = '🌙';
    else if(state === 'light') btn.textContent = '☀️';
    else btn.textContent = '🌗';
  }

  function setCookieTheme(theme){
    try{
      // Set a cookie for 1 year
      document.cookie = `theme=${theme};max-age=${60*60*24*365};path=/;samesite=Lax`;
      // also notify server to set cookie with proper attributes (credentials same-origin required)
      fetch('/set-theme', {method: 'POST', credentials: 'same-origin', headers: {'Content-Type':'application/json'}, body: JSON.stringify({theme})}).catch(()=>{});
    }catch(e){}
  }

  // initialize
  const cookieMatch = document.cookie.match(/(?:^|; )theme=([^;]+)/);
  const cookieTheme = cookieMatch ? decodeURIComponent(cookieMatch[1]) : null;
  const stored = localStorage.getItem(THEME_KEY);
  const initial = stored || cookieTheme || 'system';
  applyTheme(initial);

  // if system changes and user chose system, update
  window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {
    if((localStorage.getItem(THEME_KEY) || cookieTheme || 'system') === 'system') applyTheme('system');
  });

  // expose toggler
  window.toggleTheme = function(){
    const current = localStorage.getItem(THEME_KEY) || cookieTheme || 'system';
    let next;
    if(current === 'system' || current === 'light') next = 'dark';
    else next = 'light';
    localStorage.setItem(THEME_KEY, next);
    setCookieTheme(next);
    applyTheme(next);
  };

  // expose setter
  window.setTheme = function(t){
    if(!['light','dark','system'].includes(t)) return;
    localStorage.setItem(THEME_KEY, t);
    setCookieTheme(t);
    applyTheme(t);
  };
})();
