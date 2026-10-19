# Registro de decisiones — MetalNova Smart Factory BI

Formato: decisión, alternativas consideradas, motivo, consecuencias y estado.

---

## D-001 · Arquitectura SDD con specs versionadas

- **Decisión:** organizar el trabajo en `specs/00N-*/` con `spec.md`, `plan.md`, `tasks.md` y
  `verification.md`, y mantener `specs/CONSTITUTION.md` como fuente de verdad.
- **Alternativas:** trabajar solo con el Documento Maestro; usar el doc maestro como spec viva.
- **Motivo:** evitar confusión entre sesiones y garantizar trazabilidad requisito→evidencia.
- **Consecuencias:** los documentos originales pasan a `docs/reference/` como insumos no normativos.
- **Estado:** aceptada.

## D-002 · Conservar los insumos originales sin editar ni eliminar

- **Decisión:** mover `caso_practico.txt` y `MetalNova_Documento_Maestro_Agentes.md` a
  `docs/reference/` intactos.
- **Alternativas:** editarlos a v1.1; eliminarlos tras extraer su contenido.
- **Motivo:** preservar trazabilidad académica; evitar dos fuentes de verdad en conflicto.
- **Consecuencias:** las divergencias se listan en la sección Supersesiones de la Constitución.
- **Estado:** aceptada.

## D-003 · PostgreSQL 16.4-alpine en Docker con puerto en loopback

- **Decisión:** imagen `postgres:16.4-alpine`, publicación `127.0.0.1:5432`, volumen nombrado.
- **Alternativas:** `latest`; exponer a la red; instalar PostgreSQL nativo.
- **Motivo:** reproducibilidad, superficie de exposición mínima y ajuste a 8 GB.
- **Consecuencias:** Power BI Desktop se conecta a `127.0.0.1:5432`.
- **Estado:** aceptada.

## D-004 · Enmiendas G1–G6

- **Decisión:** aplicar las enmiendas G1 a G6 (jerarquías línea/familia, alerta con temperatura,
  FPY obligatorio con retrabajo, energía por unidad buena, reglas IoT completas, umbral de microparada).
- **Motivo:** cerrar brechas entre el Documento Maestro y el enunciado del caso.
- **Consecuencias:** la Constitución prevalece sobre el Documento Maestro donde difieran.
- **Estado:** aceptada.

## D-005 · Modo de conexión Power BI (DirectQuery vs Import)

- **Decisión:** pendiente de prueba en el incremento 006.
- **Criterios:** ver Constitución §9.
- **Estado:** pendiente.
