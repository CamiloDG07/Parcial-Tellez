/* Carta: pestañas por categoría, búsqueda en vivo y botón "Agregar". */
(() => {
  const carta = document.getElementById('carta');
  if (!carta) return;
  const pestanas = [...document.querySelectorAll('.pestana')];
  const secciones = [...carta.querySelectorAll('.carta-seccion')];
  const buscador = document.getElementById('buscar-plato');
  const sinResultados = document.getElementById('carta-sin-resultados');
  let categoria = 'todas';

  function filtrar() {
    const q = buscador.value.trim().toLowerCase();
    let visibles = 0;
    for (const s of secciones) {
      const deCategoria = categoria === 'todas' || s.dataset.categoria === categoria;
      let enSeccion = 0;
      for (const p of s.querySelectorAll('.plato')) {
        const coincide = deCategoria && (!q || p.dataset.nombre.includes(q));
        p.hidden = !coincide;
        if (coincide) enSeccion++;
      }
      s.hidden = enSeccion === 0;
      visibles += enSeccion;
    }
    sinResultados.hidden = visibles > 0;
  }

  for (const t of pestanas) {
    t.addEventListener('click', () => {
      categoria = t.dataset.categoria;
      for (const o of pestanas) {
        o.classList.toggle('activa', o === t);
        o.setAttribute('aria-selected', String(o === t));
      }
      filtrar();
    });
  }
  buscador.addEventListener('input', filtrar);

  carta.addEventListener('click', async (ev) => {
    const b = ev.target.closest('[data-agregar]');
    if (!b || !window.Carrito) return;
    const plato = b.closest('.plato');
    const cantidad = parseInt(plato.querySelector('.cant').value, 10);
    if (!(cantidad >= 1 && cantidad <= 20)) { avisar('Indica una cantidad entre 1 y 20.', 'error'); return; }
    b.disabled = true;
    try {
      await window.Carrito.agregar(parseInt(b.dataset.agregar, 10), cantidad);
      if (window.volarAlCarrito) window.volarAlCarrito(plato.querySelector('.plato-foto img'));
      avisar(`Agregado: ${plato.querySelector('h3').textContent} × ${cantidad}`, 'ok');
    } catch (e) {
      avisar(e.message, 'error');
    } finally {
      b.disabled = false;
    }
  });

  function avisar(texto, tipo) {
    if (window.mostrarToast) window.mostrarToast(texto, tipo);
  }
})();
