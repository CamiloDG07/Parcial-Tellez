-- Esquema relacional (SQLite). Las claves foráneas se activan en cada conexión (PRAGMA foreign_keys = ON).

CREATE TABLE IF NOT EXISTS usuario (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre        TEXT NOT NULL,
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    rol           TEXT NOT NULL CHECK (rol IN ('cliente', 'administrador'))
);

CREATE TABLE IF NOT EXISTS restaurante (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre      TEXT NOT NULL,
    direccion   TEXT NOT NULL,
    ciudad      TEXT NOT NULL,
    tipo_cocina TEXT NOT NULL,
    descripcion TEXT NOT NULL DEFAULT '',
    admin_id    INTEGER NOT NULL REFERENCES usuario(id)
);

CREATE TABLE IF NOT EXISTS mesa (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    restaurante_id INTEGER NOT NULL REFERENCES restaurante(id) ON DELETE CASCADE,
    numero         INTEGER NOT NULL CHECK (numero > 0),
    capacidad      INTEGER NOT NULL CHECK (capacidad > 0),
    ubicacion      TEXT NOT NULL DEFAULT '',
    activa         INTEGER NOT NULL DEFAULT 1 CHECK (activa IN (0, 1)),
    UNIQUE (restaurante_id, numero)
);

CREATE TABLE IF NOT EXISTS horario (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    restaurante_id INTEGER NOT NULL REFERENCES restaurante(id) ON DELETE CASCADE,
    dia_semana     INTEGER NOT NULL CHECK (dia_semana BETWEEN 0 AND 6),
    hora_apertura  TEXT NOT NULL,
    hora_cierre    TEXT NOT NULL CHECK (hora_cierre > hora_apertura),
    UNIQUE (restaurante_id, dia_semana)
);

CREATE TABLE IF NOT EXISTS reserva (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id     INTEGER NOT NULL REFERENCES usuario(id),
    restaurante_id INTEGER NOT NULL REFERENCES restaurante(id),
    mesa_id        INTEGER NOT NULL REFERENCES mesa(id),
    fecha          TEXT NOT NULL,
    hora           TEXT NOT NULL,
    num_personas   INTEGER NOT NULL CHECK (num_personas > 0),
    estado         TEXT NOT NULL DEFAULT 'PENDIENTE' CHECK (estado IN ('PENDIENTE', 'CONFIRMADA', 'CANCELADA')),
    notas          TEXT NOT NULL DEFAULT '',
    creado_en      TEXT NOT NULL,
    -- Instantánea del cobro al crear la reserva (COP enteros): un cambio posterior de tasas en config.py
    -- no altera lo que se le cobró a cada cliente. La propina es voluntaria y no se guarda.
    subtotal_cop    INTEGER NOT NULL DEFAULT 0 CHECK (subtotal_cop >= 0),
    descuento_pct   INTEGER NOT NULL DEFAULT 0 CHECK (descuento_pct BETWEEN 0 AND 100),
    descuento_cop   INTEGER NOT NULL DEFAULT 0 CHECK (descuento_cop >= 0),
    impuesto_pct    INTEGER NOT NULL DEFAULT 0 CHECK (impuesto_pct BETWEEN 0 AND 100),
    impuesto_cop    INTEGER NOT NULL DEFAULT 0 CHECK (impuesto_cop >= 0),
    total_pagar_cop INTEGER NOT NULL DEFAULT 0 CHECK (total_pagar_cop = subtotal_cop - descuento_cop + impuesto_cop)
);

CREATE INDEX IF NOT EXISTS idx_reserva_mesa_fecha ON reserva (mesa_id, fecha);
CREATE INDEX IF NOT EXISTS idx_reserva_usuario ON reserva (usuario_id);
CREATE INDEX IF NOT EXISTS idx_reserva_restaurante_fecha ON reserva (restaurante_id, fecha);

-- ===================== Fase 2: carta y pre-pedido (dinero en COP enteros, sin centavos) =====================
CREATE TABLE IF NOT EXISTS categoria (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    restaurante_id INTEGER NOT NULL REFERENCES restaurante(id) ON DELETE CASCADE,
    nombre         TEXT NOT NULL,
    orden          INTEGER NOT NULL DEFAULT 0,
    UNIQUE (restaurante_id, nombre)
);

CREATE TABLE IF NOT EXISTS producto (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    restaurante_id INTEGER NOT NULL REFERENCES restaurante(id) ON DELETE CASCADE,
    categoria_id   INTEGER NOT NULL REFERENCES categoria(id),
    nombre         TEXT NOT NULL,
    descripcion    TEXT NOT NULL DEFAULT '',
    precio_cop     INTEGER NOT NULL CHECK (precio_cop >= 0),
    imagen         TEXT NOT NULL DEFAULT '',
    disponible     INTEGER NOT NULL DEFAULT 1 CHECK (disponible IN (0, 1))
);

CREATE TABLE IF NOT EXISTS reserva_item (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    reserva_id          INTEGER NOT NULL REFERENCES reserva(id) ON DELETE CASCADE,
    producto_id         INTEGER NOT NULL REFERENCES producto(id),
    cantidad            INTEGER NOT NULL CHECK (cantidad > 0),
    precio_unitario_cop INTEGER NOT NULL CHECK (precio_unitario_cop >= 0)
);

CREATE INDEX IF NOT EXISTS idx_producto_restaurante ON producto (restaurante_id, categoria_id);
CREATE INDEX IF NOT EXISTS idx_item_reserva ON reserva_item (reserva_id);
