// Simple ball drop physics demo
(function(){
  const canvas = document.getElementById('gameCanvas');
  const ctx = canvas.getContext('2d');
  let W = canvas.width, H = canvas.height;

  // State
  let ballType = 'soccer';
  let groundType = 'concrete';

  const ball = { x: W/2, y: 60, r: 20, vx:0, vy:0, launched:false };
  const gravity = 0.6;

  // bounce coefficients
  const groundProps = {
    concrete: { restitution: 0.7, color: '#d1d5db' },
    foam: { restitution: 0.12, color: '#e6f7ff' },
    water: { restitution: 0.05, color: '#cfefff', water:true }
  };

  // UI wiring
  document.querySelectorAll('.ball-select').forEach(b=>{
    b.addEventListener('click', ()=>{
      ballType = b.dataset.ball; document.getElementById('cur-ball').textContent = ballType;
    });
  });
  document.querySelectorAll('.ground-select').forEach(g=>{
    g.addEventListener('click', ()=>{
      groundType = g.dataset.ground; document.getElementById('cur-ground').textContent = groundType;
    });
  });
  document.getElementById('start-game').addEventListener('click', reset);

  // Assets from server
  const serverAssets = window.__GAME_ASSETS || {items:[], grounds:[]};
  const selectedGameId = window.__SELECTED_GAME_ID || '';
  // Wire game selector (if present) to reload with query param
  const gameSelect = document.getElementById('game-select');
  if(gameSelect){
    gameSelect.addEventListener('change', ()=>{
      const v = gameSelect.value;
      const base = window.location.pathname;
      const qs = v ? '?game='+encodeURIComponent(v) : '';
      window.location.href = base + qs;
    });
  }

  // bottom-thumb dragging handled by default HTML5 drag; also enable click-to-place fallback
  document.querySelectorAll('.asset-thumb').forEach(el=>{
    el.addEventListener('dragstart', (ev)=>{
      ev.dataTransfer.setData('text/plain', el.dataset.assetUrl);
    });
    el.addEventListener('click', ()=>{
      // click to place at slightly above center
      const url = el.dataset.assetUrl;
      placeAssetAt(url, W/2, H/2 - 40);
    });
  });

  // canvas drop handling
  canvas.addEventListener('dragover', (e)=>{ e.preventDefault(); });
  canvas.addEventListener('drop', (e)=>{
    e.preventDefault(); const r=canvas.getBoundingClientRect(); const url = e.dataTransfer.getData('text/plain'); const x = e.clientX - r.left; const y = e.clientY - r.top; placeAssetAt(url, x, y);
  });

  // placed assets that can be dragged
  let placed = [];

  function placeAssetAt(url,x,y){
    const img = new Image(); img.src = url;
    const obj = { img: img, x:x, y:y, w:60, h:60, dragging:false, offsetX:0, offsetY:0 };
    placed.push(obj);
    // allow dragging on canvas
    img.onload = ()=>{};
  }

  // mouse handlers for dragging placed assets
  let activeObj = null;
  canvas.addEventListener('mousedown', (e)=>{
    const r=canvas.getBoundingClientRect(); const mx=e.clientX-r.left, my=e.clientY-r.top;
    for(let i=placed.length-1;i>=0;i--){ const p=placed[i]; if(mx>=p.x-p.w/2 && mx<=p.x+p.w/2 && my>=p.y-p.h/2 && my<=p.y+p.h/2){ activeObj=p; p.dragging=true; p.offsetX = mx - p.x; p.offsetY = my - p.y; break; }}
  });
  canvas.addEventListener('mousemove', (e)=>{ if(activeObj){ const r=canvas.getBoundingClientRect(); const mx=e.clientX-r.left, my=e.clientY-r.top; activeObj.x = mx - activeObj.offsetX; activeObj.y = my - activeObj.offsetY; }});
  canvas.addEventListener('mouseup', ()=>{ if(activeObj){ activeObj.dragging=false; activeObj=null; }});

  // Drag to set velocity
  let dragging=false, dragStart={x:0,y:0};
  canvas.addEventListener('mousedown', (e)=>{ dragging=true; const r=canvas.getBoundingClientRect(); dragStart={x:e.clientX-r.left,y:e.clientY-r.top}; });
  canvas.addEventListener('mousemove', (e)=>{ if(dragging){ const r=canvas.getBoundingClientRect(); const mx=e.clientX-r.left, my=e.clientY-r.top; draw(); drawArrow(ball.x, ball.y, mx, my); }});
  canvas.addEventListener('mouseup', (e)=>{ if(dragging){ dragging=false; const r=canvas.getBoundingClientRect(); const mx=e.clientX-r.left, my=e.clientY-r.top; launchFromDrag(mx,my); }});
  canvas.addEventListener('mouseleave', ()=>{ dragging=false; });

  function launchFromDrag(mx,my){
    const dx = mx - ball.x; const dy = my - ball.y;
    // use inverse of drag vector as throw direction
    ball.vx = dx * 0.12; ball.vy = dy * 0.12; ball.launched = true;
  }

  function reset(){
    ball.x = W/2; ball.y = 60; ball.vx=0; ball.vy=0; ball.launched=false;
  }

  function drawArrow(x,y,mx,my){
    const dx=mx-x, dy=my-y; ctx.save(); ctx.strokeStyle='rgba(0,0,0,0.6)'; ctx.lineWidth=3; ctx.beginPath(); ctx.moveTo(x,y); ctx.lineTo(mx,my); ctx.stroke(); ctx.restore();
  }

  function drawBall(){
    ctx.save();
    // simple ball visuals by type
    if(ballType==='soccer'){
      ctx.fillStyle='#ffffff'; ctx.beginPath(); ctx.arc(ball.x, ball.y, ball.r,0,Math.PI*2); ctx.fill(); ctx.strokeStyle='#333'; ctx.stroke();
    } else if(ballType==='baseball'){
      ctx.fillStyle='#fff'; ctx.beginPath(); ctx.arc(ball.x, ball.y, ball.r*0.85,0,Math.PI*2); ctx.fill(); ctx.strokeStyle='#d32'; ctx.stroke();
    } else {
      ctx.fillStyle='#f5e0b7'; ctx.beginPath(); ctx.ellipse(ball.x, ball.y, ball.r*1.1, ball.r,0,0,Math.PI*2); ctx.fill(); ctx.strokeStyle='#b36'; ctx.stroke();
    }
    ctx.restore();
  }

  function update(){
    if(ball.launched){
      ball.vy += gravity;
      ball.x += ball.vx; ball.y += ball.vy;

      const groundY = H - 60; // ground line
      if(ball.y + ball.r >= groundY){
        // collision
        const prop = groundProps[groundType] || groundProps.concrete;
        if(prop.water){
          // splash and sink: play simple effect then stop
          createSplash(ball.x, groundY);
          ball.launched = false; ball.vx = 0; ball.vy = 0; ball.y = groundY + ball.r*0.6;
        } else {
          ball.y = groundY - ball.r;
          ball.vy = -ball.vy * prop.restitution;
          // small horizontal damping
          ball.vx *= 0.92;
          // if bounce very small, stop
          if(Math.abs(ball.vy) < 1.2) { ball.vy = 0; ball.vx = 0; ball.launched = false; }
        }
      }
    }
  }

  let splashes = [];
  function createSplash(x,y){ splashes.push({x:x, y:y, t:0}); }
  function drawSplashes(){ splashes.forEach(s=>{
    ctx.save(); const a = 1 - s.t/30; ctx.globalAlpha = a; ctx.fillStyle = '#7fd0ff'; ctx.beginPath(); ctx.ellipse(s.x, s.y, 30 + s.t*1.5, 8 + s.t*0.2,0,0,Math.PI*2); ctx.fill(); ctx.restore(); s.t++;
  }); splashes = splashes.filter(s=>s.t<30);
  }

  function drawGround(){
    const prop = groundProps[groundType] || groundProps.concrete;
    const gy = H - 60;
    // background image for ground if provided via server assets
    const groundAsset = (serverAssets.grounds && serverAssets.grounds.length) ? serverAssets.grounds[0].url : null;
    if(groundAsset){
      const img = new Image(); img.src = groundAsset;
      // draw image anchored at ground line; if not loaded yet, fill with color as fallback
      if(img.complete){
        ctx.drawImage(img, 0, gy, W, H-gy);
      } else {
        img.onload = ()=>{ try{ ctx.drawImage(img, 0, gy, W, H-gy); }catch(e){} };
        ctx.fillStyle = prop.color; ctx.fillRect(0, gy, W, H-gy);
      }
    } else {
      ctx.fillStyle = prop.color; ctx.fillRect(0, gy, W, H-gy);
    }
    // ground line
    ctx.strokeStyle='#999'; ctx.beginPath(); ctx.moveTo(0,gy); ctx.lineTo(W,gy); ctx.stroke();
  }

  function draw(){
    ctx.clearRect(0,0,W,H);
    drawGround();
    drawBall();
    drawSplashes();
  }

  function loop(){ update(); draw(); requestAnimationFrame(loop); }

  // handle resize
  window.addEventListener('resize', ()=>{ const r=canvas.getBoundingClientRect(); W = canvas.width = Math.min(900, Math.floor(r.width)); H = canvas.height = 520; });

  // init
  reset(); loop();
})();
