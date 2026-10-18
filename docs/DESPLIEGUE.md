# Despliegue de MIDNIGHT DINER

La app es FastAPI + Jinja2 + SQLite. SQLite necesita un sistema de archivos que permita escribir, así que la plataforma recomendada es **Render** (servicio web de larga duración). **Vercel no sirve para esta app tal como está**: sus funciones son serverless con sistema de archivos de solo lectura (solo `/tmp`, efímero y distinto por invocación), por lo que las reservas se perderían entre peticiones. Solo valdría la pena en Vercel si se cambiara SQLite por una base externa (Postgres), lo cual rompe la capa de datos que ya está entregada.

## Render (plan gratuito, para demostración)

Archivos incluidos en el repositorio: `render.yaml` (Blueprint), `Procfile` y `requirements-prod.txt` (solo dependencias de ejecución).

1. Subir el repositorio a GitHub (rama que se va a desplegar).
2. En <https://dashboard.render.com> → **New → Blueprint** → elegir el repositorio. Render lee `render.yaml` y crea el servicio `midnight-diner`.
   - Sin Blueprint: **New → Web Service**, Build Command `pip install -r requirements-prod.txt`, Start Command el `uvicorn …` de `Procfile` (sin `web:`), y las variables de abajo.
3. Variables de entorno:

| Variable | Valor | Para qué |
|----------|-------|----------|
| `SECRET_KEY` | cadena aleatoria larga (el Blueprint la genera) | firma de la cookie de sesión |
| `HTTPS_ONLY` | `1` | cookie `Secure` + cabecera HSTS (Render sirve por HTTPS) |
| `AUTOSEMBRAR` | `1` | al iniciar, si la BD está vacía, siembra los datos demo (no borra nada existente) |
| `RESERVAS_DB` | `/tmp/reservas.db` | ruta de la BD SQLite |
| `PYTHON_VERSION` | `3.13.5` (o la versión con la que se probó) | versión de Python |

4. El comando de arranque es solo `uvicorn app.main:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips='*'`. Con `AUTOSEMBRAR=1` la app siembra sola, al iniciar, restaurantes, cartas por restaurante, usuarios demo e historial si la BD está vacía. `--proxy-headers` es necesario para que el limitador de login vea la IP real del cliente y no la del proxy de Render.
5. Probar: abrir la URL `https://<servicio>.onrender.com`, iniciar sesión con `cliente@demo.com` / `Cliente123!` y hacer una reserva completa; entrar como `admin@demo.com` / `Admin123!`.

### Limitaciones del plan gratuito (decirlas en la sustentación)

- **Disco efímero**: cada reinicio o redeploy borra la BD y se vuelve a sembrar. Las reservas y las fotos subidas por el administrador no persisten. Es aceptable para una demostración; si se necesita persistencia, usar un plan de pago con *Persistent Disk* montado en, por ejemplo, `/var/data` y `RESERVAS_DB=/var/data/reservas.db`.
- **Arranque en frío**: el servicio se duerme tras ~15 min sin tráfico y la primera petición tarda del orden de un minuto. Abrir la URL un par de minutos antes de la sustentación o de grabar el video.
- **Una sola instancia**: el limitador de intentos de login y el carrito son por proceso/sesión; no escalar a varias instancias sin moverlos a un almacén compartido.
- **Credenciales demo públicas**: cualquiera con la URL puede entrar con ellas. No usar datos reales. Si la URL va a circular, cambiar las contraseñas del seed o no publicar el enlace.

## Probado / no probado

**Probado el 18-oct-2026 en Windows 11 con Python 3.14.3 (local, no en Render):**
- Entorno virtual nuevo con solo `requirements-prod.txt` (22 paquetes): arranque con el comando exacto de `Procfile` y `AUTOSEMBRAR=1`, `HTTPS_ONLY=1`. La base se sembró sola; `/login` respondió 200 con cookie `httponly; samesite=lax; secure` y cabecera `strict-transport-security`; las cartas de los 5 restaurantes respondieron 200.
- En PowerShell, con `$env:AUTOSEMBRAR="1"; $env:HTTPS_ONLY="0"` y `uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'` la app arranca y responde 200.
- Entorno virtual nuevo con `requirements.txt`, `seed --reset`, `uvicorn` y una reserva completa por HTTP; E2E de Playwright sin fallos.

**No probado:**
- El despliegue real en Render: no hay sesión de Render CLI ni clave de API en este equipo y no se crearon credenciales. URL pública: **no probada**. Tampoco se probó la cabecera HSTS desde una URL pública `https://`.
- `PYTHON_VERSION=3.13.5` (la que fija `render.yaml`) no se ejecutó localmente: la prueba local fue con 3.14.3. Se dejó 3.13.5 porque no se verificó que Render soporte 3.14; si el build falla por la versión, probar con otra versión soportada.

**Pasos exactos para desplegar (Blueprint, 3 clics):**
1. Entrar a <https://dashboard.render.com> con la cuenta propia y elegir **New → Blueprint**.
2. Conectar el repositorio `CamiloDG07/Parcial-Tellez` y elegir la rama `fase-6-entrega` (ya está subida a GitHub); Render lee `render.yaml`.
3. **Apply**: esperar el build (`pip install -r requirements-prod.txt`) y abrir `https://midnight-diner.onrender.com` (o la URL que asigne Render). Probar `cliente@demo.com` / `Cliente123!`, una reserva completa y `admin@demo.com` / `Admin123!`. Anotar aquí la URL y la fecha si se prueba.
