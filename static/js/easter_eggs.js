// Minimal Easter eggs: Konami code + typing "bitrealm"
(function(){
  'use strict';

  function launchConfetti(count) {
    count = count || 50;
    const colors = ['#ff6b6b','#ffd93d','#6bcB77','#4d96ff','#9b59b6'];
    const container = document.createElement('div');
    container.style.position = 'fixed'; container.style.left = '0'; container.style.top = '0';
    container.style.width = '100%'; container.style.height = '0'; container.style.pointerEvents = 'none';
    container.style.overflow = 'visible'; container.className = 'easter-confetti-container';
    document.body.appendChild(container);
    for (let i=0;i<count;i++) {
      const el = document.createElement('div');
      const s = Math.floor(Math.random()*12)+6;
      el.style.width = s+'px'; el.style.height = s+'px'; el.style.background = colors[Math.floor(Math.random()*colors.length)];
      el.style.position = 'absolute'; el.style.left = (Math.random()*100)+'%'; el.style.top = '-10px';
      el.style.opacity = '1'; el.style.borderRadius = (Math.random()>0.5? '2px':'50%');
      el.style.transition = 'transform 2s linear, opacity 2s linear';
      container.appendChild(el);
      (function(el){
        requestAnimationFrame(()=>{
          const endX = (Math.random()*60)-30; const endY = 110 + Math.random()*60; const rot = (Math.random()*720)-360;
          el.style.transform = `translate(${endX}vw, ${endY}vh) rotate(${rot}deg)`; el.style.opacity = '0';
        });
        setTimeout(()=>{ if (el.parentNode) el.parentNode.removeChild(el); }, 2200);
      })(el);
    }
    setTimeout(()=>{ if (container.parentNode) container.parentNode.removeChild(container); }, 2500);
  }

  function showModal(title, message) {
    try {
      const modalEl = document.getElementById('easterModal');
      if (!modalEl) { alert(title + '\n' + (message||'')); return; }
      modalEl.querySelector('.modal-title').textContent = title || 'Surprise!';
      const body = modalEl.querySelector('.easter-message'); if (body) body.innerHTML = message || '';
      const bsModal = new bootstrap.Modal(modalEl); bsModal.show();
    } catch (err) { console.warn('modal error', err); }
  }

  function unlock(key, title, message) {
    try { const unlocked = JSON.parse(localStorage.getItem('easter.unlocked')||'[]'); if (!unlocked.includes(key)) { unlocked.push(key); localStorage.setItem('easter.unlocked', JSON.stringify(unlocked)); } } catch(e){}
    launchConfetti(60); showModal(title, message);
    try{ if (typeof window.__easter_renderAchievements === 'function') window.__easter_renderAchievements(); }catch(e){}
  }

  // Konami code
  (function(){
    const code = [38,38,40,40,37,39,37,39,66,65]; let pos=0;
    window.addEventListener('keydown', function(e){
      if (e.keyCode === code[pos]) { pos++; if (pos === code.length) { pos=0; unlock('konami','Konami','<p>You know the Konami code.</p>'); } }
      else { pos = 0; }
    });
  })();

  // Typing egg: 'bitrealm' (case-insensitive), allow rolling buffer
  (function(){
    const target = 'bitrealm'; let buf = '';
    window.addEventListener('keydown', function(e){
      const k = (e.key || '').toLowerCase(); if (!k || k.length !== 1) return;
      buf += k; if (buf.length > target.length) buf = buf.slice(-target.length);
      if (buf === target) { buf = ''; unlock('bitrealm','Dev Egg','<p>You know  "bitrealm" — a true gaming connoisseur!</p>'); }
    });
  })();

  // Typing egg: 'tumblr' -> toggle retro theme (persisted in localStorage)
  (function(){
    const target = 'tumblr'; let buf = '';
    function applyRetro(enable){
      try{
        if (enable) {
          if (!document.getElementById('retro-css')){
            const l = document.createElement('link'); l.rel='stylesheet'; l.id='retro-css'; l.href = '/static/css/retro.css'; document.head.appendChild(l);
          }
          document.body.classList.add('retro-theme');
          localStorage.setItem('easter.retro','1');
        } else {
          const l = document.getElementById('retro-css'); if (l && l.parentNode) l.parentNode.removeChild(l);
          document.body.classList.remove('retro-theme');
          localStorage.removeItem('easter.retro');
        }
      }catch(e){console.warn(e)}
    }
    // restore preference on load
    try{ if (localStorage.getItem('easter.retro') === '1') applyRetro(true); }catch(e){}
    window.addEventListener('keydown', function(e){
      const k = (e.key || '').toLowerCase(); if (!k || k.length !== 1) return;
      buf += k; if (buf.length > target.length) buf = buf.slice(-target.length);
      if (buf === target) {
        buf = '';
        // determine current enabled state (prefer localStorage, fallback to body class)
        let cur = false;
        try { cur = (localStorage.getItem('easter.retro') === '1'); } catch (err) { cur = document.body.classList.contains('retro-theme'); }
        const enabled = !cur;
        applyRetro(enabled);
        unlock('retro', 'Retro Theme', enabled ? '<p>Retro theme enabled.</p>' : '<p>Retro theme disabled.</p>');
      }
    });
  })();

  // Typing egg: 'ping pong' -> open a Pong mini-game inside the modal
  (function(){
    const target = 'pingpong'; let buf = '';
    let gameInterval = null;
    let gameState = null;
    let modalEl = null;
    let originalModalBody = null;
    let footerBtn = null;
    let footerClickHandler = null;
    let closeBtn = null;
    let closeClickHandler = null;

    function keyDown(e){ if (!gameState) return; if (e.key === 'w') gameState.up = true; if (e.key === 's') gameState.down = true; if (e.key === 'ArrowUp') gameState.rightUp = true; if (e.key === 'ArrowDown') gameState.rightDown = true; }
    function keyUp(e){ if (!gameState) return; if (e.key === 'w') gameState.up = false; if (e.key === 's') gameState.down = false; if (e.key === 'ArrowUp') gameState.rightUp = false; if (e.key === 'ArrowDown') gameState.rightDown = false; }

    function stopGame(){
      try{ if (gameInterval) { clearInterval(gameInterval); gameInterval = null; } }catch(e){}
      gameState = null;
      try{ window.removeEventListener('keydown', keyDown); window.removeEventListener('keyup', keyUp); }catch(e){}
      try{ const c = document.getElementById('easter-pong-canvas'); if (c && c.parentNode) c.parentNode.removeChild(c); }catch(e){}
      // restore modal body
      try{ if (modalEl && originalModalBody !== null) { const mb = modalEl.querySelector('#easterModalBody'); if (mb) mb.innerHTML = originalModalBody; } }catch(e){}
      // restore footer and close button behavior
      try{ if (footerBtn && footerClickHandler) { footerBtn.removeEventListener('click', footerClickHandler); footerClickHandler = null; } }catch(e){}
      try{ if (closeBtn && closeClickHandler) { closeBtn.removeEventListener('click', closeClickHandler); closeClickHandler = null; } }catch(e){}
      originalModalBody = null; footerBtn = null; closeBtn = null; modalEl = null;
      // defensive cleanup: remove any lingering modal backdrop and restore body state
      try{
        document.body.classList.remove('modal-open');
        document.body.style.overflow = '';
        const bds = document.querySelectorAll('.modal-backdrop');
        bds.forEach(b=>{ if (b && b.parentNode) b.parentNode.removeChild(b); });
      }catch(e){}
    }

    function startPong(){
      stopGame();
      modalEl = document.getElementById('easterModal');
      const modalBody = document.getElementById('easterModalBody');
      if (!modalBody) { alert('Pong!'); return; }
      // save original body so we can restore it later
      originalModalBody = modalBody.innerHTML;
      modalBody.innerHTML = '';
      const canvas = document.createElement('canvas'); canvas.id = 'easter-pong-canvas'; canvas.width = 640; canvas.height = 360; canvas.style.width='100%'; canvas.style.maxWidth='640px'; canvas.style.display='block'; canvas.style.margin='0 auto'; modalBody.appendChild(canvas);
      const ctx = canvas.getContext('2d');
      const H = canvas.height, W = canvas.width;
      gameState = {
        ball: {x: W/2, y: H/2, vx: 4*(Math.random()>0.5?1:-1), vy: 2*(Math.random()>0.5?1:-1), r: 6},
        left: {y: H/2 - 30, h:60}, right: {y: H/2 - 30, h:60},
        leftScore:0, rightScore:0,
        up:false, down:false
      };

      // wire controls
      window.addEventListener('keydown', keyDown);
      window.addEventListener('keyup', keyUp);

      // change modal primary button and header close button to navigate home while game is active
      try{
        footerBtn = modalEl.querySelector('.modal-footer .btn-primary');
        if (footerBtn){
          footerClickHandler = function(ev){ ev.preventDefault(); window.location.href = '/'; };
          footerBtn.addEventListener('click', footerClickHandler);
        }
        closeBtn = modalEl.querySelector('.modal-header .btn-close');
        if (closeBtn){
          closeClickHandler = function(ev){ ev.preventDefault(); window.location.href = '/'; };
          closeBtn.addEventListener('click', closeClickHandler);
        }
      }catch(e){}

      function draw(){
        if (!gameState) return;
        const s = gameState;
        if (s.up) s.left.y -= 5; if (s.down) s.left.y += 5;
        if (!s.rightUp && !s.rightDown) {
          const center = s.right.y + s.right.h/2; if (s.ball.y < center - 6) s.right.y -= 3; else if (s.ball.y > center + 6) s.right.y += 3;
        } else {
          if (s.rightUp) s.right.y -= 5; if (s.rightDown) s.right.y += 5;
        }
        s.left.y = Math.max(0, Math.min(H - s.left.h, s.left.y));
        s.right.y = Math.max(0, Math.min(H - s.right.h, s.right.y));
        s.ball.x += s.ball.vx; s.ball.y += s.ball.vy;
        if (s.ball.y - s.ball.r <= 0 || s.ball.y + s.ball.r >= H) s.ball.vy *= -1;
        if (s.ball.x - s.ball.r <= 20){ if (s.ball.y >= s.left.y && s.ball.y <= s.left.y + s.left.h){ s.ball.vx = Math.abs(s.ball.vx); s.ball.vx *= 1.05; s.ball.vy += (Math.random()-0.5)*2; } }
        if (s.ball.x + s.ball.r >= W - 20){ if (s.ball.y >= s.right.y && s.ball.y <= s.right.y + s.right.h){ s.ball.vx = -Math.abs(s.ball.vx); s.ball.vx *= 1.05; s.ball.vy += (Math.random()-0.5)*2; } }
        if (s.ball.x < 0){ s.rightScore++; resetBall(s, 1); }
        if (s.ball.x > W){ s.leftScore++; resetBall(s, -1); }

        ctx.fillStyle = '#0b0b0b'; ctx.fillRect(0,0,W,H);
        ctx.fillStyle = '#cccccc'; for(let y=0;y<H;y+=20) ctx.fillRect(W/2-2, y, 4, 12);
        ctx.fillStyle = '#ffffff'; ctx.fillRect(10, s.left.y, 8, s.left.h); ctx.fillRect(W-18, s.right.y, 8, s.right.h);
        ctx.beginPath(); ctx.arc(s.ball.x, s.ball.y, s.ball.r, 0, Math.PI*2); ctx.fill();
        ctx.fillStyle='#ffffff'; ctx.font='24px monospace'; ctx.fillText(s.leftScore, W/2 - 60, 30); ctx.fillText(s.rightScore, W/2 + 40, 30);
      }

      function resetBall(s, dir){ s.ball.x = W/2; s.ball.y = H/2; s.ball.vx = 4 * dir; s.ball.vy = 2 * (Math.random()>0.5?1:-1); }

      gameInterval = setInterval(draw, 1000/60);

      // ensure we cleanup when modal is hidden
      try{
        modalEl.addEventListener('hidden.bs.modal', function onHidden(){ stopGame(); modalEl.removeEventListener('hidden.bs.modal', onHidden); });
      }catch(e){}
    }

    window.addEventListener('keydown', function(e){
      // build buffer ignoring spaces; detect pingpong as contiguous letters
      const k = (e.key || '').toLowerCase(); if (!k || k.length !== 1) return;
      if (k === ' ') return; buf += k; if (buf.length > target.length) buf = buf.slice(-target.length);
      if (buf === target) { buf = ''; unlock('pong','Ping Pong', '<p>Ready to play Pong — use W/S to move, or Arrow keys for two-player.</p>');
        try{ const modal = document.getElementById('easterModal'); const bsModal = new bootstrap.Modal(modal); bsModal.show(); setTimeout(startPong, 200); }catch(e){ startPong(); }
      }
    });
  })();

  // === New additions: coupon, Snake, Invaders, and achievements rendering ===
  (function(){
    // render achievements into the Fong page if present
    function renderAchievements(){
      try{
        const el = document.getElementById('easter-achievements'); if (!el) return;
        let unlocked = JSON.parse(localStorage.getItem('easter.unlocked')||'[]');
        // remove any unwanted or legacy keys we no longer support (e.g. 'secret.local')
        try{
          if (Array.isArray(unlocked) && unlocked.length > 0) {
            const filtered = unlocked.filter(k => k !== 'secret.local');
            if (filtered.length !== unlocked.length) {
              unlocked = filtered;
              try{ localStorage.setItem('easter.unlocked', JSON.stringify(unlocked)); }catch(e){}
            }
          }
        }catch(e){/* ignore */}
        const map = {
          'konami':'Konami code discovered',
          'bitrealm':'BitRealm dev egg',
          'retro':'Retro theme toggled',
          'pong':'Played Pong',
          'coupon':'Got Secret Coupon',
          'snake_played':'Played Snake',
          'snake_win':'Won Snake (length 10+)',
          'mines_played':'Played Minesweeper',
          'hundred_shopper':'Purchased 100 Products'
        };
        el.innerHTML = '';
        if (!unlocked || unlocked.length === 0){ el.innerHTML = '<li class="list-group-item">No achievements unlocked yet.</li>'; return; }
        unlocked.forEach(k => {
          const text = map[k] || k;
          const li = document.createElement('li'); li.className = 'list-group-item'; li.textContent = text; el.appendChild(li);
        });
      }catch(e){console.warn(e)}
    }

    // expose to global so other parts can call it after unlocking
    window.__easter_renderAchievements = renderAchievements;

    // call at load
    try{ renderAchievements(); }catch(e){}

    // Secret coupon: type 'easter10' to get code EASTER10
    (function(){
      const target = 'easter10'; let buf='';
      window.addEventListener('keydown', function(e){
        const k = (e.key || '').toLowerCase(); if (!k || k.length!==1) return;
        buf += k; if (buf.length > target.length) buf = buf.slice(-target.length);
        if (buf === target){ buf=''; try{ localStorage.setItem('coupon.code','EASTER10'); }catch(e){}
          unlock('coupon','Secret Coupon','<p>Use code <strong>EASTER10</strong> at checkout for a special discount!</p>'); try{ renderAchievements(); }catch(e){}
        }
      });
    })();

    // Snake mini-game
    (function(){
      const target = 'snake'; let buf='';
      function startSnake(){
        unlock('snake_played','Snake','<p>Snake started. Use Arrow keys to move. Grow to length 10 to win.</p>'); try{ renderAchievements(); }catch(e){}
        const modal = document.getElementById('easterModal'); const modalBody = document.getElementById('easterModalBody'); if (!modalBody) { alert('Snake!'); return; }
        const orig = modalBody.innerHTML; modalBody.innerHTML='';
        const canvas = document.createElement('canvas'); canvas.id='easter-snake-canvas'; canvas.width=480; canvas.height=360; canvas.style.width='100%'; modalBody.appendChild(canvas);
        const ctx = canvas.getContext('2d');
        let grid = 20; let cols = Math.floor(canvas.width/grid), rows = Math.floor(canvas.height/grid);
        let snake = [{x:Math.floor(cols/2), y:Math.floor(rows/2)}]; let dir = {x:1,y:0}; let food = {x: Math.floor(Math.random()*cols), y: Math.floor(Math.random()*rows)}; let alive=true; let interval=null;
        function draw(){ if (!alive) return; ctx.fillStyle='#000'; ctx.fillRect(0,0,canvas.width,canvas.height); ctx.fillStyle='#0f0'; snake.forEach(s=>ctx.fillRect(s.x*grid,s.y*grid,grid-2,grid-2)); ctx.fillStyle='#f00'; ctx.fillRect(food.x*grid, food.y*grid, grid-2, grid-2); }
        function step(){ if (!alive) return; const head = {x: snake[0].x + dir.x, y: snake[0].y + dir.y}; if (head.x<0||head.x>=cols||head.y<0||head.y>=rows) { alive=false; stop(); return; } for(let i=0;i<snake.length;i++){ if (snake[i].x===head.x && snake[i].y===head.y){ alive=false; stop(); return; } } snake.unshift(head); if (head.x===food.x && head.y===food.y){ food = {x: Math.floor(Math.random()*cols), y: Math.floor(Math.random()*rows)}; if (snake.length >= 10){ unlock('snake_win','Snake Master','<p>You grew to length 10 — Snake Master!</p>'); try{ renderAchievements(); }catch(e){} } } else { snake.pop(); } draw(); }
        function stop(){ clearInterval(interval); interval=null; window.removeEventListener('keydown', kd); setTimeout(()=>{ try{ const mb = document.getElementById('easterModalBody'); if (mb) mb.innerHTML = orig; }catch(e){} }, 300); }
        // defensive cleanup in case Bootstrap backdrop wasn't removed
        try{ document.body.classList.remove('modal-open'); document.body.style.overflow=''; const bds=document.querySelectorAll('.modal-backdrop'); bds.forEach(b=>{ if (b && b.parentNode) b.parentNode.removeChild(b); }); }catch(e){}
        function kd(e){ if (e.key==='ArrowUp'){ if (dir.y!==1) dir={x:0,y:-1}; } if (e.key==='ArrowDown'){ if (dir.y!==-1) dir={x:0,y:1}; } if (e.key==='ArrowLeft'){ if (dir.x!==1) dir={x:-1,y:0}; } if (e.key==='ArrowRight'){ if (dir.x!==-1) dir={x:1,y:0}; } }
        window.addEventListener('keydown', kd);
        interval = setInterval(step, 120);
        // cleanup when modal is hidden
        try{ modal.addEventListener('hidden.bs.modal', function onHidden(){ stop(); modal.removeEventListener('hidden.bs.modal', onHidden); }); }catch(e){}
      }
      window.addEventListener('keydown', function(e){ const k=(e.key||'').toLowerCase(); if (!k||k.length!==1) return; buf += k; if (buf.length>target.length) buf=buf.slice(-target.length); if (buf===target){ buf=''; try{ const modal = document.getElementById('easterModal'); const bs = new bootstrap.Modal(modal); bs.show(); setTimeout(startSnake, 200); }catch(e){ startSnake(); } } });
    })();

    // Minesweeper mini-game
    (function(){
      const target = 'minesweeper'; let buf='';
      function startMines(){
        unlock('mines_played','Minesweeper','<p>Minesweeper started. Click tiles to reveal, Shift+Click to flag. Clear all non-mine tiles to win.</p>'); try{ renderAchievements(); }catch(e){}
        const modal = document.getElementById('easterModal'); const modalBody = document.getElementById('easterModalBody'); if (!modalBody) { alert('Minesweeper'); return; }
        const orig = modalBody.innerHTML; modalBody.innerHTML='';
        const canvas = document.createElement('canvas'); canvas.id='easter-mines-canvas'; canvas.width=480; canvas.height=360; canvas.style.width='100%'; modalBody.appendChild(canvas);
        const ctx = canvas.getContext('2d');
        const cols = 12, rows = 9; const cell = Math.floor(Math.min(canvas.width/cols, canvas.height/rows));
        const M = Math.floor(cols*rows*0.15) || 10; // number of mines
        let board = []; for(let y=0;y<rows;y++){ board[y]=[]; for(let x=0;x<cols;x++){ board[y][x]={mine:false, adj:0, revealed:false, flagged:false}; }}
        // place mines
        let placed=0; while(placed<M){ const rx=Math.floor(Math.random()*cols), ry=Math.floor(Math.random()*rows); if (!board[ry][rx].mine){ board[ry][rx].mine=true; placed++; }}
        // compute adjacency
        function inBounds(x,y){return x>=0&&y>=0&&x<cols&&y<rows}
        for(let y=0;y<rows;y++){ for(let x=0;x<cols;x++){ if (board[y][x].mine) continue; let cnt=0; for(let dy=-1;dy<=1;dy++) for(let dx=-1;dx<=1;dx++){ if (dx===0&&dy===0) continue; const nx=x+dx, ny=y+dy; if (inBounds(nx,ny)&&board[ny][nx].mine) cnt++; } board[y][x].adj=cnt; }}

        function draw(){ ctx.fillStyle='#222'; ctx.fillRect(0,0,canvas.width,canvas.height); ctx.strokeStyle='#444'; ctx.lineWidth=1; ctx.font=(cell-4)+'px monospace'; for(let y=0;y<rows;y++){ for(let x=0;x<cols;x++){ const b=board[y][x]; const px=x*cell, py=y*cell; ctx.fillStyle=b.revealed? '#ddd':'#666'; ctx.fillRect(px,py,cell-1,cell-1); ctx.strokeRect(px,py,cell-1,cell-1); if (b.revealed){ if (b.mine){ ctx.fillStyle='#f00'; ctx.fillRect(px+4,py+4,cell-8,cell-8); } else if (b.adj>0){ ctx.fillStyle='#000'; ctx.fillText(String(b.adj), px+6, py+cell-6); } } else if (b.flagged){ ctx.fillStyle='#ff0'; ctx.fillText('F', px+6, py+cell-6); } }} }

        function reveal(x,y){ if (!inBounds(x,y)) return; const b = board[y][x]; if (b.revealed||b.flagged) return; b.revealed=true; if (b.mine){ // game over
            draw(); setTimeout(()=>{ try{ showModal('Minesweeper Boom','<p>You hit a mine — try again!</p>'); }catch(e){} }, 200); cleanup(); return; }
          if (b.adj===0){ for(let dy=-1;dy<=1;dy++) for(let dx=-1;dx<=1;dx++){ if (dx===0&&dy===0) continue; reveal(x+dx,y+dy); }}
        }

        function checkWin(){ let unrevealed=0; for(let y=0;y<rows;y++) for(let x=0;x<cols;x++){ if (!board[y][x].revealed && !board[y][x].mine) unrevealed++; } if (unrevealed===0){ try{ showModal('Minesweeper Champion','<p>You cleared the field — nice work!</p>'); }catch(e){}; cleanup(); } }

        function canvasCoord(ev){ const rect=canvas.getBoundingClientRect(); const cx=Math.floor((ev.clientX-rect.left)/cell), cy=Math.floor((ev.clientY-rect.top)/cell); return {x:cx,y:cy}; }

        function onClick(ev){ ev.preventDefault(); const c = canvasCoord(ev); if (!inBounds(c.x,c.y)) return; if (ev.shiftKey || ev.button===2){ board[c.y][c.x].flagged = !board[c.y][c.x].flagged; draw(); } else { reveal(c.x,c.y); draw(); checkWin(); } }

        function onContext(ev){ ev.preventDefault(); return false; }

        canvas.addEventListener('click', onClick);
        canvas.addEventListener('contextmenu', onContext);

        function cleanup(){ try{ canvas.removeEventListener('click', onClick); canvas.removeEventListener('contextmenu', onContext); }catch(e){}
          setTimeout(()=>{ try{ const mb=document.getElementById('easterModalBody'); if (mb) mb.innerHTML=orig; }catch(e){}; // defensive modal cleanup
            try{ document.body.classList.remove('modal-open'); document.body.style.overflow=''; const bds=document.querySelectorAll('.modal-backdrop'); bds.forEach(b=>{ if (b && b.parentNode) b.parentNode.removeChild(b); }); }catch(e){} }, 300);
        }

        // ensure cleanup when modal is hidden
        try{ modal.addEventListener('hidden.bs.modal', function onHidden(){ cleanup(); modal.removeEventListener('hidden.bs.modal', onHidden); }); }catch(e){}

        draw();
      }
      window.addEventListener('keydown', function(e){ const k=(e.key||'').toLowerCase(); if (!k||k.length!==1) return; buf+=k; if (buf.length>target.length) buf=buf.slice(-target.length); if (buf===target){ buf=''; try{ const modal=document.getElementById('easterModal'); const bs=new bootstrap.Modal(modal); bs.show(); setTimeout(startMines,200); }catch(e){ startMines(); } } });
    })();

  })();

})();
