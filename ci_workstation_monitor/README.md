# CI Steel — Workstation Monitor (`ci_workstation_monitor`)

Módulo Odoo 19 (Fase 1). Registra eventos de auditoría de presencia física por
puesto de trabajo (cámara + IA en RPi5) y los cruza con el timing real de
Manufacturing (MRP). **No almacena video, solo eventos** (Ley 1581, Habeas Data).

## Qué instala

- **Modelo `workstation.presence.event`** — presencia / ausencia / zona /
  tiempo estático / heartbeat, con timestamp, `workcenter_id`, `workorder_id`
  (opcional), duración, confianza IA, dispositivo origen y bandera `is_anomalous`.
- **Controlador HTTP `POST /workstation/event`** — endpoint propio (sin IoT Box),
  autenticado con **API key por estación**.
- **Extensión de `mrp.workcenter`** — API key del puesto (generable con un botón)
  y umbral de tiempo estático anómalo (segundos), configurable por centro.
- **Vistas + menú** dentro de *Manufacturing → Monitoreo de Puestos*, con filtros
  (anómalos, ausencias, tiempo estático) y agrupaciones.

## Instalación

1. Copiar `ci_workstation_monitor/` a la carpeta de addons.
2. *Apps → Actualizar lista* → instalar **CI Steel - Workstation Monitor**.
   (Depende de `mrp`.)
3. En cada *Centro de trabajo* pulsar **Generar** para crear su API key y ajustar
   el **umbral de tiempo estático**.

## Contrato del endpoint

```
POST /workstation/event
X-API-Key: <clave de la estación>        # o "api_key" dentro del body
Content-Type: application/json

{
  "event_type": "absence",               // requerido: presence|absence|zone|static|heartbeat
  "timestamp": "2026-07-01T14:03:22Z",   // opcional, UTC ISO-8601 (por defecto: ahora)
  "duration_seconds": 42.0,              // opcional
  "zone": "mesa_ensamble",               // opcional
  "confidence": 0.91,                    // opcional (0.0–1.0)
  "source_device": "rpi5-est-03",        // opcional
  "workorder_id": 128,                   // opcional (si no, se toma la OT en progreso del puesto)
  "note": "..."                          // opcional
}
```

Respuesta `200`:
```json
{"status": "ok", "event_id": 42, "workcenter_id": 3, "workorder_id": 128, "is_anomalous": true}
```
Errores: `400` payload/tipo inválido · `401` API key ausente/ inválida · `500` interno.

### Ejemplo `curl` (probar sin hardware — Fase 1)

```bash
curl -sS -X POST https://app7.ventabot.cloud/workstation/event \
  -H "X-API-Key: LA_CLAVE_DE_LA_ESTACION" \
  -H "Content-Type: application/json" \
  -d '{"event_type":"absence","duration_seconds":320,"source_device":"rpi5-est-03"}'
```

## Decisiones tomadas (antes eran preguntas abiertas)

- **Nombre técnico:** `ci_workstation_monitor`.
- **Autenticación:** **API key por estación** (`mrp.workcenter.ws_api_key`), no una
  clave compartida — así se identifica el origen de cada evento. Subsume el caso
  compartido si se decide reutilizar clave.
- **Umbral de tiempo estático:** por centro de trabajo (`ws_static_threshold`,
  default 300 s), ajustable por proceso.
- **Endpoint:** `type='http'` con `csrf=False` (no JSON-RPC) para que los RPi5
  hagan un POST de JSON plano sin el envoltorio JSON-RPC. En Odoo 19 `type='json'`
  está deprecado como alias de `type='jsonrpc'`.

## Pendiente (fases siguientes)

- Framework de inferencia final (YOLO11n-pose vs. bounding boxes de zona) — Fase 3.
- Reporte que cruce tiempo planeado (OT) vs. real (botones Odoo) vs. presencia
  física — se puede montar sobre `is_anomalous` + `duration_seconds` + `workorder_id`.
- Política de tratamiento de datos / consentimiento (Ley 1581) antes de producción.
