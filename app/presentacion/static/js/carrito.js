/* Pre-pedido: cajón lateral y llamadas a /api/carrito. Expone window.Carrito para la carta. */
(() => {
  const cajon = document.getElementById('cajon-carrito');
  if (!cajon) return;
  const velo = document.getElementById('velo-carrito');
  const boton = document.getElementById('abrir-carrito');
  const lista = document.getElementById('carrito-lineas');
  const vacio = document.getElementById('carrito-vacio');
  const total = document.getElementById('carrito-total');
  const insignia = document.getElementById('insignia-carrito');
  const csrf = document.querySelector('meta[name="csrf-token"]').content;

  const cop = (n) => '$' + Math.round(n).toString().replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  let estado = JSON.parse(document.getElementById('carrito-inicial').textContent);

  function pintar() {
    lista.replaceChildren();
    for (const l of estado.lineas) {
      const li = document.createElement('li');
      li.className = 'cajon-linea';
      const nombre = document.createElement('span');
      nombre.className = 'cajon-nombre';
      nombre.textContent = l.nombre;
      const precio = document.createElement('span');
      precio.className = 'cajon-precio';
      precio.textContent = cop(l.subtotal_cop);
      const control = document.createElement('div');
      control.className = 'cajon-cant';
      const menos = botonCant('−', `Quitar una unidad de ${l.nombre}`, () => cambiar(l.producto_id, l.cantidad - 1));
      const n = document.createElement('span');
      n.textContent = l.cantidad;
      n.setAttribute('aria-label', `${l.cantidad} unidades`);
      const mas = botonCant('+', `Agregar una unidad de ${l.nombre}`, () => cambiar(l.producto_id, l.cantidad + 1));
      control.append(menos, n, mas);
      li.append(nombre, precio, control);
      lista.appendChild(li);
    }
    vacio.hidden = estado.lineas.length > 0;
    total.textContent = cop(estado.total_cop);
    insignia.textContent = estado.cantidad;
    document.getElementById('vaciar-carrito').disabled = !estado.lineas.length;
    const reservar = document.getElementById('carrito-reservar');
    reservar.href = estado.restaurante_id ? `/reservar?restaurante_id=${estado.restaurante_id}` : '/reservar';
    document.dispatchEvent(new CustomEvent('carrito:cambio', { detail: estado }));
  }

  function botonCant(texto, etiqueta, accion) {
    const b = document.createElement('button');
    b.type = 'button'; b.className = 'cant-btn'; b.textContent = texto;
    b.setAttribute('aria-label', etiqueta);
    b.addEventListener('click', accion);
    return b;
  }

  async function llamar(ruta, cuerpo) {
    const resp = await fetch(ruta, {
      method: 'POST', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf, Accept: 'application/json' },
      body: JSON.stringify(cuerpo || {}),
    });
    const datos = await resp.json().catch(() => ({ error: 'Respuesta inesperada del servidor.' }));
    if (!resp.ok) throw new Error(datos.error || 'No se pudo actualizar el pre-pedido.');
    estado = datos;
    pintar();
    return datos;
  }

  const cambiar = (id, cantidad) => llamar('/api/carrito/cambiar', { producto_id: id, cantidad }).catch(avisar);
  const avisar = (e) => (window.mostrarToast ? window.mostrarToast(e.message, 'error') : alert(e.message));

  function abrir() {
    cajon.classList.add('abierto'); velo.hidden = false;
    cajon.setAttribute('aria-hidden', 'false'); boton.setAttribute('aria-expanded', 'true');
    cajon.focus();
  }
  function cerrar() {
    cajon.classList.remove('abierto'); velo.hidden = true;
    cajon.setAttribute('aria-hidden', 'true'); boton.setAttribute('aria-expanded', 'false');
    boton.focus();
  }
  boton.addEventListener('click', () => (cajon.classList.contains('abierto') ? cerrar() : abrir()));
  velo.addEventListener('click', cerrar);
  document.getElementById('cerrar-carrito').addEventListener('click', cerrar);
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && cajon.classList.contains('abierto')) cerrar(); });
  document.getElementById('vaciar-carrito').addEventListener('click', () => llamar('/api/carrito/vaciar').catch(avisar));

  window.Carrito = {
    agregar: (producto_id, cantidad) => llamar('/api/carrito/agregar', { producto_id, cantidad }),
    abrir,
    estado: () => estado,
  };
  pintar();
})();
