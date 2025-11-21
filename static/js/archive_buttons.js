document.addEventListener('DOMContentLoaded', function() {
  document.querySelectorAll('form.archive-form').forEach(function(form) {
    form.addEventListener('submit', function(e) {
      e.preventDefault();
      var confirmText = form.dataset.confirm || 'Archive this item?';
      if (!window.confirm(confirmText)) return;
      fetch(form.action, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'X-Requested-With': 'XMLHttpRequest'
        }
      }).then(function(resp) {
        // Try to parse JSON body when present to show a helpful message
        resp.text().then(function(txt) {
          var parsed = null;
          try { parsed = txt ? JSON.parse(txt) : null; } catch (e) { parsed = null; }
          var contentType = resp.headers.get('content-type') || '';
          // If server returned HTML (likely a redirect to login), detect and surface a helpful message
          if (resp.ok && contentType.indexOf('text/html') !== -1) {
            var low = txt ? txt.toLowerCase() : '';
            if (resp.url && resp.url.indexOf('/login') !== -1 || low.indexOf('name="username"') !== -1 || low.indexOf('name="password"') !== -1 || low.indexOf('login') !== -1) {
              alert('Session expired or not authorized. Please log in and try again.');
              window.location = '/login?next=' + encodeURIComponent(window.location.pathname);
              return;
            }
          }
          if (resp.ok) {
            var msg = (parsed && parsed.message) ? parsed.message : 'Product archived.';
            alert(msg);
            window.location.reload();
            return;
          }
          if (resp.status === 403 || resp.status === 401) {
            alert('Not authorized. Please log in with an account that has permission.');
            window.location.reload();
            return;
          }
          var body = parsed ? JSON.stringify(parsed) : txt;
          // If fetch returned a non-OK response, fall back to a normal form POST submit
          // This helps when fetch is blocked, cookies are Secure, or fetch is redirected.
          if (confirm('Archiving via AJAX failed (status ' + resp.status + '). Try a full form submit instead?')) {
            // create and submit a hidden form to replicate a regular POST
            var f = document.createElement('form');
            f.method = 'POST';
            f.action = form.action;
            f.style.display = 'none';
            // copy any inputs from the original (csrf tokens if present)
            Array.from(form.querySelectorAll('input[name], textarea[name], select[name]')).forEach(function(inp){
              try{
                var el = document.createElement(inp.tagName.toLowerCase());
                el.name = inp.name;
                el.value = inp.value;
                f.appendChild(el);
              }catch(e){}
            });
            document.body.appendChild(f);
            f.submit();
            return;
          }
          alert('Archive failed: ' + resp.status + '\n' + body);
        });
      }).catch(function(err) {
        // On network error, offer to fall back to a full form submit
        if (confirm('Network error while archiving. Try a full form submit instead?')) {
          var f2 = document.createElement('form');
          f2.method = 'POST';
          f2.action = form.action;
          f2.style.display = 'none';
          Array.from(form.querySelectorAll('input[name], textarea[name], select[name]')).forEach(function(inp){
            try{
              var el = document.createElement(inp.tagName.toLowerCase());
              el.name = inp.name;
              el.value = inp.value;
              f2.appendChild(el);
            }catch(e){}
          });
          document.body.appendChild(f2);
          f2.submit();
          return;
        }
        alert('Network error while archiving: ' + err);
      });
    });
  });
});
