# AGENTS.md — Contexto autoritativo del proyecto

Este archivo se carga automáticamente en cada sesión. **Léelo antes de tocar cualquier archivo.**

## Qué es este proyecto

`Metalnova` (nombre técnico: **MetalNova Smart Factory BI**) es un prototipo académico de Business Intelligence que analiza el rendimiento de una fábrica de componentes automotrices mediante datos sintéticos de 180 días más una simulación de eventos cercanos al tiempo real. Stack: PostgreSQL en Docker + scripts Python + Power BI Desktop en Windows.

## Jerarquía de autoridad (orden de precedencia)

Cuando dos documentos se contradigan, **manda el de mayor rango**:

1. `specs/CONSTITUTION.md` — fuente de verdad normativa. Contiene reglas de trabajo, modelo de datos, definiciones de KPI y la tabla de **Supersesiones**.
2. `specs/00N-*/spec.md` — requisitos y criterios de aceptación del incremento activo.
3. `specs/00N-*/plan.md` y `tasks.md` — diseño y desglose de tareas del incremento.
4. `docs/*.md` — documentación operativa derivada (arquitectura, diccionario, pruebas, decisiones).
5. `docs/reference/*` — **insumos históricos NO normativos** (`caso_practico.txt`, `MetalNova_Documento_Maestro_Agentes.md`). Se conservan solo como trazabilidad académica. No son fuente de requisitos vigentes.

## Reglas no negociables

- Todo dato es **sintético** y se etiqueta como tal. Nunca presentar datos generados como telemetría real.
- No inventar métricas, credenciales ni resultados.
- No afirmar que una prueba pasó sin haber ejecutado y observado su salida. Registrar evidencia en `specs/00N-*/verification.md`.
- No ejecutar `docker compose down -v` (borra el volumen con la base de datos).
- No commitear `.env` ni secretos. Los logs no deben contener contraseñas.
- No instalar paquetes globales ni cambiar configuración del sistema sin autorización.
- No avanzar de incremento si falla una prueba esencial. Registrar el bloqueo.

## Cómo se trabaja aquí (SDD)

Cada incremento vive en `specs/00N-<nombre>/` con cuatro artefactos:

| Archivo | Contenido |
|---|---|
| `spec.md` | Contexto, requisitos `FR-xxx`, criterios de aceptación `AC-xxx`, fuera de alcance |
| `plan.md` | Diseño técnico, decisiones y estructura de archivos |
| `tasks.md` | Tareas `T-xxx` con estado (`pendiente` / `en curso` / `hecha` / `bloqueada`) |
| `verification.md` | Evidencia real: comando, salida observada, fecha, veredicto |

Estados del proyecto y orden de dependencia: ver `specs/README.md`.

## Entorno

- Windows 11, 8 GB de RAM (verificado ~7,9 GB), 12 CPUs.
- Python 3.13 local; las dependencias del pipeline viven en el contenedor `python/`.
- Docker Desktop operativo (motor WSL2 con ~3,7 GB asignados).
- Power BI Desktop (Microsoft Store) para la capa de visualización. No ejecuta en Docker.
