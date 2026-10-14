/* Efectos de interfaz (JavaScript vanilla, sin librerías). Todo se omite con prefers-reduced-motion. */
(() => {
  const reducir = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  window.reducirMovimiento = reducir;

  // ---- Aparición al hacer scroll (IntersectionObserver + clases CSS) ----
  if (!reducir && 'IntersectionObserver' in window) {
    const observador = new IntersectionObserver((entradas) => {
      for (const e of entradas) {
        if (e.isIntersecting) {
          e.target.classList.add('visible');
          observador.unobserve(e.target);
          // terminada la aparición, el retraso escalonado no debe afectar a las transiciones de hover
          setTimeout(() => e.target.style.setProperty('--retraso', '0ms'), 900);
        }
      }
    }, { threshold: 0.08, rootMargin: '0px 0px -30px 0px' });
    document.querySelectorAll('.tarjeta, .plato, .panel, .kpi, .banner, .carta-seccion > h2, .tabla tbody tr, .grafico')
      .forEach((el, i) => {
        el.classList.add('revela');
        el.style.setProperty('--retraso', `${Math.min(i % 8, 7) * 45}ms`);
        observador.observe(el);
      });
  }

  // ---- Contadores animados en los KPIs ----
  const formato = (n, tipo, sufijo) => {
    const t = tipo === 'cop' ? '$' + Math.round(n).toString().replace(/\B(?=(\d{3})+(?!\d))/g, '.') : String(Math.round(n));
    return t + (sufijo || '');
  };
  document.querySelectorAll('[data-contar]').forEach((el) => {
    const meta = parseFloat(el.dataset.contar);
    if (reducir || !(meta > 0)) return;
    const inicio = performance.now(), duracion = 900;
    const paso = (ahora) => {
      const t = Math.min(1, (ahora - inicio) / duracion);
      el.textContent = formato(meta * (1 - Math.pow(1 - t, 3)), el.dataset.formato, el.dataset.sufijo);
      if (t < 1) requestAnimationFrame(paso);
    };
    requestAnimationFrame(paso);
  });

  // ---- Modal de confirmación (reemplaza a window.confirm; <dialog> con transición) ----
  let dialogo;
  function crearDialogo() {
    dialogo = document.createElement('dialog');
    dialogo.className = 'modal';
    dialogo.setAttribute('aria-labelledby', 'modal-titulo');
    dialogo.innerHTML = '<form method="dialog"><h2 class="subtitulo" id="modal-titulo">CONFIRMAR</h2><p id="modal-texto"></p>' +
      '<div class="acciones"><button class="btn btn-fantasma" value="no">VOLVER</button>' +
      '<button class="btn btn-rojo" value="si" autofocus>CONFIRMAR</button></div></form>';
    document.body.appendChild(dialogo);
  }
  document.addEventListener('click', (ev) => {
    const b = ev.target.closest('[data-confirmar]');
    if (!b || !b.form) return;
    ev.preventDefault();
    ev.stopImmediatePropagation();
    if (!dialogo) crearDialogo();
    dialogo.querySelector('#modal-texto').textContent = b.dataset.confirmar;
    dialogo.onclose = () => { if (dialogo.returnValue === 'si') { b.form.requestSubmit(b); } dialogo.returnValue = ''; };
    dialogo.showModal();
  }, true);

  // ---- "Vuela al carrito" (Web Animations API) ----
  window.volarAlCarrito = (origen) => {
    const destino = document.getElementById('abrir-carrito');
    if (reducir || !origen || !destino || !origen.animate) return;
    const a = origen.getBoundingClientRect(), b = destino.getBoundingClientRect();
    const volador = origen.cloneNode(true);
    Object.assign(volador.style, { position: 'fixed', left: a.left + 'px', top: a.top + 'px', width: a.width + 'px',
      height: a.height + 'px', zIndex: 95, pointerEvents: 'none', borderRadius: '10px', objectFit: 'cover', margin: 0 });
    document.body.appendChild(volador);
    const dx = b.left + b.width / 2 - (a.left + a.width / 2), dy = b.top + b.height / 2 - (a.top + a.height / 2);
    const anim = volador.animate([
      { transform: 'translate(0,0) scale(1)', opacity: 1 },
      { transform: `translate(${dx * 0.6}px, ${dy * 0.6 - 60}px) scale(.45)`, opacity: .9, offset: .6 },
      { transform: `translate(${dx}px, ${dy}px) scale(.08)`, opacity: .2 },
    ], { duration: 650, easing: 'cubic-bezier(.4,.1,.3,1)' });
    anim.onfinish = () => volador.remove();
  };

  // ---- Insignia del carrito que rebota cuando cambia la cantidad ----
  let previo = null;
  document.addEventListener('carrito:cambio', (ev) => {
    const n = ev.detail.cantidad;
    const insignia = document.getElementById('insignia-carrito');
    if (!reducir && insignia && previo !== null && n !== previo && insignia.animate) {
      insignia.animate([{ transform: 'scale(1)' }, { transform: 'scale(1.6)' }, { transform: 'scale(.9)' }, { transform: 'scale(1)' }],
        { duration: 420, easing: 'ease-out' });
    }
    previo = n;
  });
})();
