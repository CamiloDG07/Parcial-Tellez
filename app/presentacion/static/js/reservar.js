/* Formulario de reserva: disponibilidad en vivo, plano de mesas y validación en cliente. */
(() => {
  const form = document.getElementById('form-reserva');
  if (!form) return;

  const $ = (id) => document.getElementById(id);
  const campoFecha = $('fecha'), campoPersonas = $('personas');
  const campoHora = $('campo-hora'), campoMesa = $('campo-mesa'), auto = $('auto-mesa');
  const chips = $('chips-hora'), plano = $('plano'), estado = $('estado-disp');
  const restauranteId = form.dataset.restaurante;
  let datos = null;                        // última respuesta de /api/disponibilidad
  let peticion = 0;                        // evita que una respuesta lenta pise a una más nueva

  const pasos = [...form.querySelectorAll('.paso')];
  let pasoActual = 0;
  const error = (id, texto) => { $(id).textContent = texto || ''; };
  const horaDe = (franja) => franja.hora;

  async function cargar() {
    const personas = parseInt(campoPersonas.value, 10);
    error('err-fecha'); error('err-personas');
    if (!campoFecha.value) { error('err-fecha', 'Elige una fecha.'); return; }
    if (campoFecha.value < form.dataset.hoy) { error('err-fecha', 'La fecha no puede ser pasada.'); return; }
    if (!(personas >= 1 && personas <= 30)) { error('err-personas', 'Indica entre 1 y 30 personas.'); return; }

    const mia = ++peticion;
    estado.textContent = 'Cargando disponibilidad…';
    esqueletos();
    chips.setAttribute('aria-busy', 'true');
    try {
      const url = `/api/disponibilidad?restaurante_id=${encodeURIComponent(restauranteId)}` +
                  `&fecha=${encodeURIComponent(campoFecha.value)}&personas=${personas}`;
      const resp = await fetch(url, { headers: { Accept: 'application/json' }, credentials: 'same-origin' });
      const cuerpo = await resp.json();
      if (mia !== peticion) return;
      if (!resp.ok) throw new Error(cuerpo.error || 'No se pudo consultar la disponibilidad.');
      datos = cuerpo;
    } catch (e) {
      if (mia !== peticion) return;
      datos = null;
      estado.textContent = e.message;
      chips.replaceChildren(); plano.replaceChildren();
      return;
    } finally {
      if (mia === peticion) chips.removeAttribute('aria-busy');
    }
    pintarHoras();
    pintarPlano();
    progreso();
  }

  function esqueletos() {
    // Marcadores de carga (skeletons) mientras llega la respuesta.
    chips.replaceChildren(...Array.from({ length: 8 }, () => Object.assign(document.createElement('span'), { className: 'chip chip-esqueleto' })));
    const fila = Object.assign(document.createElement('div'), { className: 'zona-mesas' });
    fila.append(...Array.from({ length: 6 }, () => Object.assign(document.createElement('span'), { className: 'mesa mesa-esqueleto' })));
    plano.replaceChildren(fila);
  }

  function pintarHoras() {
    chips.replaceChildren();
    if (!datos.abierto) {
      estado.textContent = 'El restaurante está cerrado ese día. Prueba otra fecha.';
      campoHora.value = '';
      return;
    }
    const disponibles = datos.franjas.filter((f) => f.mesas_libres.length > 0).length;
    estado.textContent = disponibles
      ? `${disponibles} franjas con mesa libre para ${datos.personas} persona(s).`
      : 'No hay mesas libres ese día para ese número de personas.';
    // Si la hora elegida ya no tiene mesas libres, se descarta.
    const actual = datos.franjas.find((f) => horaDe(f) === campoHora.value);
    if (!actual || !actual.mesas_libres.length) campoHora.value = '';
    for (const f of datos.franjas) {
      const b = document.createElement('button');
      b.type = 'button';
      b.className = 'chip';
      b.textContent = f.hora;
      b.setAttribute('role', 'radio');
      const libre = f.mesas_libres.length > 0;
      b.disabled = !libre;
      b.setAttribute('aria-checked', String(campoHora.value === f.hora));
      if (campoHora.value === f.hora) b.classList.add('activo');
      b.title = libre ? `${f.mesas_libres.length} mesa(s) libre(s)` : 'Sin mesas libres';
      b.addEventListener('click', () => { campoHora.value = f.hora; error('err-hora'); pintarHoras(); pintarPlano(); progreso(); });
      chips.appendChild(b);
    }
  }

  function pintarPlano() {
    plano.replaceChildren();
    if (!datos) return;
    const franja = datos.franjas.find((f) => f.hora === campoHora.value);
    const libres = new Set(franja ? franja.mesas_libres : []);
    if (campoMesa.value && (!franja || !libres.has(parseInt(campoMesa.value, 10)))) campoMesa.value = '';

    // El salón se dibuja por zonas (columna `ubicacion` de la mesa); la forma depende de la capacidad.
    const zonas = new Map();
    for (const m of datos.mesas) {
      const nombre = (m.ubicacion || '').trim() || 'Salón';
      if (!zonas.has(nombre)) zonas.set(nombre, []);
      zonas.get(nombre).push(m);
    }
    for (const [nombre, mesas] of zonas) {
      const zona = document.createElement('div');
      zona.className = 'zona';
      zona.setAttribute('role', 'group');
      zona.setAttribute('aria-label', `Zona ${nombre}`);
      const titulo = document.createElement('p');
      titulo.className = 'zona-titulo';
      const disp = mesas.filter((m) => m.activa && m.capacidad >= datos.personas && libres.has(m.id)).length;
      titulo.textContent = nombre;
      if (franja) {
        const nota = document.createElement('small');
        nota.textContent = disp === 1 ? '1 libre' : `${disp} libres`;
        titulo.appendChild(nota);
      }
      const fila = document.createElement('div');
      fila.className = 'zona-mesas';
      for (const m of mesas) fila.appendChild(botonMesa(m, franja, libres));
      zona.append(titulo, fila);
      plano.appendChild(zona);
    }
  }

  function botonMesa(m, franja, libres) {
    const b = document.createElement('button');
    b.type = 'button';
    let clase, etiqueta, activa = false;
    if (!m.activa) { clase = 'nula'; etiqueta = 'inactiva'; }
    else if (m.capacidad < datos.personas) { clase = 'nula'; etiqueta = 'capacidad insuficiente'; }
    else if (!franja) { clase = 'libre'; etiqueta = 'elige una hora'; }
    else if (libres.has(m.id)) { clase = 'libre'; etiqueta = 'libre'; activa = true; }
    else { clase = 'ocupada'; etiqueta = 'ocupada'; }
    if (String(m.id) === campoMesa.value) clase = 'sel';
    const forma = m.capacidad <= 2 ? 'redonda' : m.capacidad <= 4 ? 'cuadrada' : 'larga';
    b.className = `mesa mesa-${clase} forma-${forma}`;
    b.style.setProperty('--cap', m.capacidad);
    const sillas = (n) => {
      const fila = document.createElement('span');
      fila.className = 'sillas';
      fila.setAttribute('aria-hidden', 'true');
      for (let i = 0; i < n; i++) fila.appendChild(document.createElement('i'));
      return fila;
    };
    const total = Math.min(m.capacidad, 12);
    const tablero = document.createElement('span');
    tablero.className = 'tablero';
    tablero.innerHTML = '<strong></strong><span></span>';
    tablero.firstChild.textContent = m.numero;
    tablero.lastChild.textContent = m.capacidad + ' pax';
    b.append(sillas(Math.ceil(total / 2)), tablero, sillas(Math.floor(total / 2)));
    b.setAttribute('aria-label', `Mesa ${m.numero}, ${m.capacidad} personas, ${m.ubicacion || 'sin ubicación'}: ${etiqueta}`);
    b.setAttribute('aria-pressed', String(clase === 'sel'));
    b.disabled = !activa || auto.checked;
    b.addEventListener('click', () => {
      campoMesa.value = String(m.id); auto.checked = false; error('err-mesa');
      pintarPlano(); progreso();
    });
    return b;
  }

  function progreso() {
    const pct = Math.round(((pasoActual + 1) / pasos.length) * 100);   // barra POWER = avance del asistente
    $('power-relleno').style.width = pct + '%';
    $('power-pct').textContent = pct + '%';
    $('power').setAttribute('aria-valuenow', String(pct));
  }

  auto.addEventListener('change', () => {
    if (auto.checked) campoMesa.value = '';
    pintarPlano(); progreso();
  });
  let temporizador;
  const recargar = () => { clearTimeout(temporizador); temporizador = setTimeout(cargar, 200); };
  campoFecha.addEventListener('change', recargar);
  campoPersonas.addEventListener('input', recargar);

  // Validación en cliente (el servidor vuelve a validar todo).
  form.addEventListener('submit', (ev) => {
    let ok = true;
    for (const id of ['err-fecha', 'err-personas', 'err-hora', 'err-mesa']) error(id);
    if (!campoFecha.value || campoFecha.value < form.dataset.hoy) { error('err-fecha', 'Elige una fecha futura.'); ok = false; }
    const p = parseInt(campoPersonas.value, 10);
    if (!(p >= 1 && p <= 30)) { error('err-personas', 'Indica entre 1 y 30 personas.'); ok = false; }
    if (!campoHora.value) { error('err-hora', 'Elige una hora disponible.'); ok = false; }
    if (!auto.checked && !campoMesa.value) { error('err-mesa', 'Elige una mesa o activa la asignación automática.'); ok = false; }
    if (!ok) {
      ev.preventDefault();
      const primero = form.querySelector('.error-campo:not(:empty)');
      if (primero) {
        irAPaso(pasos.indexOf(primero.closest('.paso')));
        primero.scrollIntoView({ block: 'center' });
      }
    }
  });


  // ---- Asistente por pasos con transición (si no hay JavaScript, se ve el formulario completo) ----
  const indicador = $('pasos');
  const nav = document.createElement('div');
  nav.className = 'paso-nav';
  nav.innerHTML = '<button type="button" class="btn btn-fantasma" id="paso-ant">← ANTERIOR</button>' +
                  '<button type="button" class="btn btn-dorado" id="paso-sig">SIGUIENTE →</button>';
  form.classList.add('con-pasos');
  form.appendChild(nav);
  for (const p of pasos) {
    const li = document.createElement('li');
    li.textContent = p.dataset.titulo;
    indicador.appendChild(li);
  }
  indicador.hidden = false;

  function valido(i) {
    for (const id of ['err-fecha', 'err-personas', 'err-hora', 'err-mesa']) error(id);
    const p = parseInt(campoPersonas.value, 10);
    if (i === 0) {
      let ok = true;
      if (!campoFecha.value || campoFecha.value < form.dataset.hoy) { error('err-fecha', 'Elige una fecha futura.'); ok = false; }
      if (!(p >= 1 && p <= 30)) { error('err-personas', 'Indica entre 1 y 30 personas.'); ok = false; }
      return ok;
    }
    if (i === 1 && !campoHora.value) { error('err-hora', 'Elige una hora disponible.'); return false; }
    if (i === 2 && !auto.checked && !campoMesa.value) { error('err-mesa', 'Elige una mesa o activa la asignación automática.'); return false; }
    return true;
  }

  function irAPaso(nuevo) {
    const dir = nuevo >= pasoActual ? 1 : -1;
    pasos.forEach((p, i) => { p.hidden = i !== nuevo; });
    const entrante = pasos[nuevo];
    if (!window.reducirMovimiento && entrante.animate && nuevo !== pasoActual) {
      entrante.animate([{ opacity: 0, transform: `translateX(${28 * dir}px)` }, { opacity: 1, transform: 'none' }],
                       { duration: 320, easing: 'ease-out' });
    }
    pasoActual = nuevo;
    [...indicador.children].forEach((li, i) => {
      li.classList.toggle('hecho', i < nuevo);
      if (i === nuevo) li.setAttribute('aria-current', 'step'); else li.removeAttribute('aria-current');
    });
    $('paso-ant').hidden = nuevo === 0;
    $('paso-sig').hidden = nuevo === pasos.length - 1;
    progreso();
  }
  $('paso-sig').addEventListener('click', () => { if (valido(pasoActual)) irAPaso(pasoActual + 1); });
  $('paso-ant').addEventListener('click', () => irAPaso(pasoActual - 1));
  irAPaso(0);

  // Total a pagar: el servidor lo calcula (cadena de decoradores); aquí solo se envía si se incluye la propina.
  const propina = $('propina');
  if (propina) {
    const cop = (n) => (n < 0 ? '-' : '') + '$' + Math.abs(Math.round(n)).toString().replace(/\B(?=(\d{3})+(?!\d))/g, '.');
    propina.addEventListener('change', async () => {
      try {
        const r = await fetch(`/api/cobro?propina=${propina.checked}`, { credentials: 'same-origin', headers: { Accept: 'application/json' } });
        if (!r.ok) throw new Error('No se pudo recalcular el total.');
        const d = await r.json();
        const ul = $('cobro-lineas');
        ul.replaceChildren(...d.lineas.map((l) => {
          const li = document.createElement('li');
          li.append(l.etiqueta + ' ', Object.assign(document.createElement('span'), { textContent: cop(l.monto_cop) }));
          return li;
        }));
        const total = document.createElement('li');
        total.className = 'total';
        total.append('TOTAL A PAGAR ', Object.assign(document.createElement('span'), { id: 'cobro-total', textContent: cop(d.total_cop) }));
        ul.appendChild(total);
      } catch (e) { if (window.mostrarToast) window.mostrarToast(e.message, 'error'); }
    });
  }

  campoHora.value = form.dataset.horaInicial || '';
  campoMesa.value = form.dataset.mesaInicial || '';
  cargar();
})();
