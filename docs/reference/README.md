# Insumos de referencia (NO normativos)

Los archivos de esta carpeta son los **insumos originales del proyecto académico**. Se conservan
intactos como trazabilidad, pero **no son fuente de requisitos vigentes**.

| Archivo | Origen | Rol |
|---|---|---|
| `caso_practico.txt` | Enunciado del caso (profesor) | Requisitos de negocio de origen |
| `MetalNova_Documento_Maestro_Agentes.md` | Especificación de implementación v1.0 | Diseño técnico de partida |

## Por qué están aquí y no en la raíz

Evitar que una sesión futura tome estos documentos como guía de trabajo y contradiga las
decisiones ya fijadas. La fuente de verdad normativa es `specs/CONSTITUTION.md`.

## Precedencia

`specs/CONSTITUTION.md` > `specs/00N-*/spec.md` > `docs/*.md` > `docs/reference/*`

Toda contradicción entre estos documentos y las specs se resuelve en favor de las specs.
Las diferencias concretas respecto al Documento Maestro están enumeradas en la sección
**Supersesiones** de `specs/CONSTITUTION.md`.

> **No editar estos archivos.** Si hace falta una corrección, se refleja como enmienda en
> `specs/CONSTITUTION.md` y se registra la decisión en `docs/DECISIONS.md`.
