/* Comportamiento común: reloj del monitor, menú móvil, confirmaciones y avisos que se cierran. */
(() => {
  const reloj = document.getElementById('reloj');
  if (reloj) {
    const pintar = () => {
      const d = new Date();
      let h = d.getHours() % 12 || 12;
      const m = String(d.getMinutes()).padStart(2, '0');
      reloj.textContent = `${String(h).padStart(2, '0')}:${m} ${d.getHours() < 12 ? 'AM' : 'PM'}`;
    };
    pintar();
    setInterval(pintar, 30000);
  }

  const btn = document.getElementById('menu-btn');
  const menu = document.getElementById('menu');
  if (btn && menu) {
    btn.addEventListener('click', () => {
      const abierto = menu.classList.toggle('abierto');
      btn.setAttribute('aria-expanded', String(abierto));
    });
  }

  // Los botones con data-confirmar piden confirmación antes de enviar su formulario.
  document.addEventListener('click', (ev) => {
    const b = ev.target.closest('[data-confirmar]');
    if (b && !window.confirm(b.dataset.confirmar)) ev.preventDefault();
  });

  // Botones «imprimir» (sin atributos onclick, para poder usar una CSP estricta).
  document.addEventListener('click', (ev) => { if (ev.target.closest('[data-imprimir]')) window.print(); });

  // Toasts de éxito/error (región aria-live), reutilizables desde otros scripts.
  let contenedor;
  window.mostrarToast = (texto, tipo = 'ok') => {
    if (!contenedor) {
      contenedor = document.createElement('div');
      contenedor.className = 'toasts';
      contenedor.setAttribute('role', 'status');
      contenedor.setAttribute('aria-live', 'polite');
      document.body.appendChild(contenedor);
    }
    const t = document.createElement('div');
    t.className = 'toast' + (tipo === 'error' ? ' toast-error' : '');
    t.textContent = texto;
    contenedor.appendChild(t);
    setTimeout(() => t.remove(), 4000);
  };
})();
