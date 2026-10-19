# Incremento 001 — Infraestructura PostgreSQL en Docker

Estado: propuesto · Depende de: — · Habilita: 002

## Contexto

Primer incremento. Establece un flujo local mínimo, persistente y comprobable: PostgreSQL en
Docker con volumen nombrado, healthcheck y publicación segura del puerto, más una imagen Python
que demuestre conectividad. Base de todo lo demás.

## Requisitos funcionales

| ID | Requisito |
|---|---|
| FR-101 | `compose.yaml` define los servicios `db` (PostgreSQL) e `ingestor` (Python). |
| FR-102 | La imagen de PostgreSQL usa una versión **fija**, nunca `latest`. |
| FR-103 | Credenciales y parámetros vía variables de entorno; `.env.example` sin secretos y `.env` ignorado por Git. |
| FR-104 | Volumen **nombrado** para el directorio de datos de PostgreSQL. |
| FR-105 | `healthcheck` de PostgreSQL y `depends_on` con condición de servicio saludable. |
| FR-106 | El puerto de PostgreSQL se publica **solo en `127.0.0.1`**, con puerto documentado. |
| FR-107 | `python/Dockerfile` con Python fijado y `requirements.txt` con dependencias mínimas de versión fija. |
| FR-108 | `python/src/check_connection.py` ejecuta `SELECT 1` con consulta parametrizada y sin imprimir secretos. |
| FR-109 | `README.md` con los comandos reales de arranque, parada, logs y reinicio. |
| FR-110 | La configuración se valida con `docker compose config` antes de levantar servicios. |
| FR-111 | Servicio `pgadmin` (`dpage/pgadmin4` con versión fija) como cliente de base de datos, publicado solo en `127.0.0.1`. |
| FR-112 | Credenciales de pgAdmin (`PGADMIN_DEFAULT_EMAIL`, `PGADMIN_DEFAULT_PASSWORD`, `PGADMIN_PORT`) declaradas en `.env.example` y `.env`. |
| FR-113 | Servidor PostgreSQL pre-registrado en pgAdmin mediante `docker/pgadmin/servers.json`. |

## Criterios de aceptación

| ID | Criterio |
|---|---|
| AC-101 | `docker compose config` termina sin errores. |
| AC-102 | `docker compose up --build -d` levanta los servicios. |
| AC-103 | `docker compose ps` muestra `db` en estado `healthy`. |
| AC-104 | `check_connection.py` imprime el resultado de `SELECT 1` y termina con código 0. |
| AC-105 | `docker compose down` seguido de `up -d` **no** pierde datos (prueba con una tabla de marca). |
| AC-106 | El puerto de PostgreSQL escucha solo en loopback (verificado con `netstat`). |
| AC-107 | `.env` no aparece en `git status` ni en el índice de Git. |
| AC-108 | pgAdmin responde por HTTP en `127.0.0.1:5050` y no está expuesto fuera de loopback. |
| AC-109 | El login de pgAdmin funciona con las credenciales de `.env`. |
| AC-110 | pgAdmin muestra el servidor «MetalNova PostgreSQL» pre-registrado y la base `metalinova`. |

## Fuera de alcance

Creación de esquema de negocio (incremento 002) y generación de datos (003). pgAdmin se incluye
como cliente de verificación, no como dependencia funcional del pipeline.

## Riesgos

- **Memoria:** el motor WSL2 dispone de ~3,7 GB. pgAdmin añade ~200–300 MB; vigilar el consumo
  total y no añadir más servicios.
- **Bloqueo conocido:** el motor Docker debe estar en ejecución antes de AC-102.
