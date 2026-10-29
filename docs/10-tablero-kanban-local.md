# Backlog y Kanban

## Tablero del repositorio

[Abrir Sistema de Préstamos EPCC — Implementación básica](https://github.com/users/carlosGCMP/projects/2)

El tablero privado usa el campo `Estado` con cinco columnas: **Backlog**, **Por hacer**, **En progreso**, **Revisión** y **Hecho**. Los issues de trabajo inmediato (#6, #8, #10 y #14–#16) usan el milestone [Implementación básica](https://github.com/carlosGCMP/Sistema_Prestamos_EPCC/milestone/3); las tareas históricas o diferidas conservan sus milestones previos.

| Columna | Issues | Enfoque |
| --- | --- | --- |
| Revisión | [#1](https://github.com/carlosGCMP/Sistema_Prestamos_EPCC/issues/1)–[#5](https://github.com/carlosGCMP/Sistema_Prestamos_EPCC/issues/5), [#8](https://github.com/carlosGCMP/Sistema_Prestamos_EPCC/issues/8), [#10](https://github.com/carlosGCMP/Sistema_Prestamos_EPCC/issues/10), [#13](https://github.com/carlosGCMP/Sistema_Prestamos_EPCC/issues/13), [#14](https://github.com/carlosGCMP/Sistema_Prestamos_EPCC/issues/14) | Alcance y API básica; consultar el PR correspondiente para ramas en revisión. |
| En progreso | [#17](https://github.com/carlosGCMP/Sistema_Prestamos_EPCC/issues/17) | Frontend web básico en la rama `feat/frontend-basico`. |
| Por hacer | [#6](https://github.com/carlosGCMP/Sistema_Prestamos_EPCC/issues/6), [#15](https://github.com/carlosGCMP/Sistema_Prestamos_EPCC/issues/15) | Automatización CI y pruebas focalizadas. |
| Backlog | [#7](https://github.com/carlosGCMP/Sistema_Prestamos_EPCC/issues/7), [#9](https://github.com/carlosGCMP/Sistema_Prestamos_EPCC/issues/9), [#16](https://github.com/carlosGCMP/Sistema_Prestamos_EPCC/issues/16) | Políticas y préstamos diferidos; estrategia de migración segura del esquema heredado. |
## Convención para nuevas tareas

- Título: verbo + resultado, por ejemplo, “Validar conflictos de intervalos en reservas”.
- Descripción: contexto breve, alcance explícito y criterios de aceptación observables.
- Issue por cambio coherente; asociarlo al milestone y al tablero.
- `En progreso` indica trabajo activo; `Revisión` indica implementación disponible para revisión local/PR; `Hecho` se usa cuando se integra y verifica, no solo cuando el código existe en un equipo.
- Capacidades fuera del corte permanecen en `Backlog`, sin mezclarse con el hito básico.
- La interfaz inicial se desarrolla desde la rama `feat/frontend-basico` y se registra en el issue [#17](https://github.com/carlosGCMP/Sistema_Prestamos_EPCC/issues/17).
