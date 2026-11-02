# ADR-003: interfaz web básica servida por FastAPI

- Estado: Aceptada
- Fecha: 2026-10-28

## Contexto

El corte básico ya dispone de una API para usuarios, catálogo/inventario y reservas, pero no ofrece una interfaz web de operación. Introducir un framework SPA o una segunda aplicación añadiría dependencias y configuración antes de validar los flujos esenciales.

## Decisión

Crear una interfaz inicial con HTML semántico, CSS y JavaScript nativo en `frontend/`, y servirla desde la misma aplicación FastAPI. El navegador consume la API HTTP del backend; PostgreSQL permanece accesible solo desde el backend.

## Consecuencias

- No se requiere Node.js, bundler ni configuración CORS en desarrollo.
- Se puede reemplazar o ampliar el cliente más adelante sin cambiar las reglas del dominio.
- Las rutas continúan siendo la autoridad de autenticación y autorización; ocultar controles en la UI no constituye un control de acceso.
- El JWT se guarda en `sessionStorage` de esta primera versión; antes de producción se debe revisar el modelo de amenazas y el manejo de sesión del navegador.
- La interfaz es funcional y mínima, no un diseño institucional definitivo.
