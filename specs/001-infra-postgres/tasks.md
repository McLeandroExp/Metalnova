# Tareas — Incremento 001

| ID | Tarea | Requisito | Estado |
|---|---|---|---|
| T-101 | Verificar `docker info` y versión de Compose | AC-102 | hecha |
| T-102 | Crear `.env.example` y `.env` | FR-103 | hecha |
| T-103 | Escribir `compose.yaml` (db, volumen, healthcheck, red) | FR-101,104,105 | hecha |
| T-104 | `python/Dockerfile` + `requirements.txt` | FR-107 | hecha |
| T-105 | `python/src/check_connection.py` | FR-108 | hecha |
| T-106 | Configurar publicación en loopback y documentar puerto | FR-106 | hecha |
| T-107 | Validar `docker compose config` | FR-110, AC-101 | hecha |
| T-108 | `docker compose up --build -d` y estado saludable | AC-102, AC-103 | hecha |
| T-109 | Ejecutar prueba de conexión | AC-104 | hecha |
| T-110 | Prueba de persistencia tras reinicio | AC-105 | hecha |
| T-111 | Verificar exposición solo en loopback | AC-106 | hecha |
| T-112 | Confirmar `.env` fuera de Git | AC-107 | hecha |
| T-113 | Documentar comandos reales en `README.md` | FR-109 | hecha |
| T-114 | Commit `feat: infraestructura postgres en docker` | — | hecha |
| T-115 | Añadir credenciales de pgAdmin a `.env.example` y `.env` | FR-112 | hecha |
| T-116 | Añadir servicio `pgadmin` al Compose (imagen fija, loopback, volumen) | FR-111 | hecha |
| T-117 | Crear `docker/pgadmin/servers.json` con el servidor pre-registrado | FR-113 | hecha |
| T-118 | Levantar pgAdmin y verificar HTTP en `127.0.0.1:5050` | AC-108 | hecha |
| T-119 | Verificar login y visibilidad de la base `metalinova` | AC-109, AC-110 | hecha |
| T-120 | Actualizar documentación y commit `feat: cliente pgadmin` | — | hecha |
