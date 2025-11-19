// Simple password strength checker
(function(){
  const pw = document.getElementById('password');
  if(!pw) return;
  const bar = document.getElementById('pwBar');
  const feedback = document.getElementById('pwFeedback');
  const checklist = {
    len: document.getElementById('pw_len'),
    upper: document.getElementById('pw_upper'),
    lower: document.getElementById('pw_lower'),
    digit: document.getElementById('pw_digit'),
    special: document.getElementById('pw_special')
  };

  function scorePassword(s){
    let score = 0;
    if(!s) return score;
    if(s.length >= 8) score += 20;
    if(s.length >= 12) score += 10;
    if(/[a-z]/.test(s)) score += 15;
    if(/[A-Z]/.test(s)) score += 15;
    if(/[0-9]/.test(s)) score += 20;
    if(/[^A-Za-z0-9]/.test(s)) score += 20;
    return Math.min(score,100);
  }

  function updateUI(){
    const v = pw.value || '';
    const sc = scorePassword(v);
    bar.style.width = sc + '%';
    // color
    if(sc < 40) { bar.className = 'progress-bar bg-danger'; feedback.textContent = 'Weak'; }
    else if(sc < 70) { bar.className = 'progress-bar bg-warning'; feedback.textContent = 'Moderate'; }
    else { bar.className = 'progress-bar bg-success'; feedback.textContent = 'Strong'; }

    // checklist
    checklist.len.style.opacity = (v.length >= 8) ? '0.6' : '1';
    checklist.upper.style.opacity = (/[A-Z]/.test(v)) ? '0.6' : '1';
    checklist.lower.style.opacity = (/[a-z]/.test(v)) ? '0.6' : '1';
    checklist.digit.style.opacity = (/[0-9]/.test(v)) ? '0.6' : '1';
    checklist.special.style.opacity = (/[^A-Za-z0-9]/.test(v)) ? '0.6' : '1';
  }

  pw.addEventListener('input', updateUI);
  // init
  updateUI();
})();
