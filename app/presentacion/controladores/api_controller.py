"""API JSON para el frontend (JavaScript vanilla con fetch)."""
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.datos.modelos import Usuario
from app.dependencias import fachada
from app.negocio.excepciones import NoEncontradoError, ReglaNegocioError
from app.presentacion.comun import requiere_usuario

router = APIRouter(prefix="/api")


@router.get("/disponibilidad")
def disponibilidad(restaurante_id: int, fecha: str, personas: int = 2,
                   usuario: Usuario = Depends(requiere_usuario)):
    """Franjas y mesas libres: `GET /api/disponibilidad?restaurante_id=&fecha=&personas=`."""
    try:
        return fachada.buscar_disponibilidad(restaurante_id, fecha, personas)
    except NoEncontradoError as error:
        return JSONResponse({"error": str(error)}, status_code=404)
    except ReglaNegocioError as error:
        return JSONResponse({"error": str(error)}, status_code=400)
