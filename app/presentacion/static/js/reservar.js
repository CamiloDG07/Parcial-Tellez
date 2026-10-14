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
    for (const m of datos.mesas) {
      const b = document.createElement('button');
      b.type = 'button';
      b.className = 'mesa';
      b.style.setProperty('--cap', m.capacidad);
      let clase, etiqueta, activa = false;
      if (!m.activa) { clase = 'nula'; etiqueta = 'inactiva'; }
      else if (m.capacidad < datos.personas) { clase = 'nula'; etiqueta = 'capacidad insuficiente'; }
      else if (!franja) { clase = 'libre'; etiqueta = 'elige una hora'; }
      else if (libres.has(m.id)) { clase = 'libre'; etiqueta = 'libre'; activa = true; }
      else { clase = 'ocupada'; etiqueta = 'ocupada'; }
      if (String(m.id) === campoMesa.value) clase = 'sel';
      b.classList.add('mesa-' + clase);
      b.innerHTML = '<strong></strong><span></span>';
      b.firstChild.textContent = m.numero;
      b.lastChild.textContent = m.capacidad + ' pax';
      b.setAttribute('aria-label', `Mesa ${m.numero}, ${m.capacidad} personas, ${m.ubicacion || 'sin ubicación'}: ${etiqueta}`);
      b.setAttribute('aria-pressed', String(clase === 'sel'));
      b.disabled = !activa || auto.checked;
      b.addEventListener('click', () => {
        campoMesa.value = String(m.id); auto.checked = false; error('err-mesa');
        pintarPlano(); progreso();
      });
      plano.appendChild(b);
    }
  }

  function progreso() {
    let pct = 20;                                         // restaurante elegido
    if (campoFecha.value && campoPersonas.value) pct += 20;
    if (campoHora.value) pct += 25;
    if (campoMesa.value || auto.checked) pct += 25;
    if (datos && datos.abierto) pct += 10;
    pct = Math.min(pct, 100);
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
      if (primero) primero.scrollIntoView({ block: 'center' });
    }
  });

  campoHora.value = form.dataset.horaInicial || '';
  campoMesa.value = form.dataset.mesaInicial || '';
  cargar();
})();
