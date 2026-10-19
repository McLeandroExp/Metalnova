# Plan — Incremento 001

## Diseño

```text
compose.yaml            # servicios db + pgadmin + ingestor, volúmenes, healthcheck, red
.env.example            # plantilla sin secretos (PostgreSQL + pgAdmin)
.env                    # local, ignorado por Git
docker/postgres/init/   # reservado para scripts de inicialización (ver regla 13)
docker/pgadmin/servers.json  # servidor pre-registrado en pgAdmin
python/Dockerfile
python/requirements.txt
python/src/check_connection.py
README.md
```

## Decisiones

- **Imagen PostgreSQL:** `postgres:16.4-alpine` (versión fija, huella reducida, adecuada a 8 GB).
- **Puerto:** `5432` publicado en `127.0.0.1` (verificado libre). Se documenta en `.env`.
- **Persistencia:** volumen nombrado `metalinova_pgdata`.
- **Healthcheck:** `pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"`.
- **ingestor:** servicio de perfil separado para carga/simulación; por defecto no queda en bucle,
  se ejecuta con `docker compose run --rm ingestor <comando>`.
- **pgAdmin:** `dpage/pgadmin4:9.18` (versión fija), `PGADMIN_CONFIG_SERVER_MODE=False` y sin
  master password para uso local; volumen nombrado `metalinova_pgadmin`; servidor pre-registrado
  desde `servers.json`. Se accede en `http://127.0.0.1:5050`.
- **initdb:** `docker/postgres/init/` queda reservado; se documenta que solo corre con volumen vacío.
- **Conexión desde Windows (Power BI):** `127.0.0.1:5432`.

## Orden de ejecución

1. Verificar `docker info`.
2. Escribir `.env.example`, `.env`, `compose.yaml`, `Dockerfile`, `requirements.txt`.
3. `docker compose config`.
4. `docker compose up --build -d`.
5. Esperar healthcheck; `docker compose ps`.
6. Ejecutar `check_connection.py`.
7. Prueba de persistencia (crear tabla marca → `down` → `up -d` → verificar).
8. Actualizar `README.md` con salidas reales.

## Riesgos y mitigación

| Riesgo | Mitigación |
|---|---|
| Motor Docker detenido | Verificar `docker info` primero; si falla, pedir al usuario arrancar Docker Desktop |
| Puerto ocupado | Comprobar `netstat`; parametrizar el puerto en `.env` |
| Consumo de memoria | Sin contenedores extra; límites solo si se miden y no causan fallos |
