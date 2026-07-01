# -*- coding: utf-8 -*-
import logging
from datetime import datetime, timezone

from odoo import fields, http
from odoo.http import request

_logger = logging.getLogger(__name__)

# Alias aceptados desde el dispositivo -> clave almacenada en el modelo.
_EVENT_TYPE_ALIASES = {
    'presence': 'presence',
    'present': 'presence',
    'absence': 'absence',
    'absent': 'absence',
    'zone': 'zone',
    'zone_change': 'zone',
    'static': 'static',
    'idle': 'static',
    'heartbeat': 'heartbeat',
    'ping': 'heartbeat',
}


class WorkstationEventController(http.Controller):
    """Controlador HTTP propio para recibir eventos de los RPi5 con cámara/IA.

    Se usa ``type='http'`` (no jsonrpc) a propósito: los dispositivos hacen un
    POST de JSON plano, sin el envoltorio JSON-RPC. La autenticación es por
    API key de estación (cabecera ``X-API-Key`` o campo ``api_key`` del cuerpo),
    validada contra ``mrp.workcenter.ws_api_key``. Mismo patrón que el sidecar
    de WhatsApp: control total del código, sin IoT Box.

    Contrato:
        POST /workstation/event
        Cabecera: X-API-Key: <clave de la estacion>   (o "api_key" en el body)
        Body JSON:
            {
              "event_type": "absence",        # requerido
              "timestamp": "2026-07-01T14:03:22Z",  # opcional (UTC ISO-8601)
              "duration_seconds": 42.0,        # opcional
              "zone": "mesa_ensamble",         # opcional
              "confidence": 0.91,              # opcional
              "source_device": "rpi5-est-03",  # opcional
              "workorder_id": 128,             # opcional
              "note": "..."                    # opcional
            }
        Respuesta 200: {"status": "ok", "event_id": 42, "is_anomalous": true}
        Errores: 400 (payload inválido), 401 (API key inválida), 500.
    """

    @http.route('/workstation/event', type='http', auth='public',
                methods=['POST'], csrf=False, save_session=False)
    def workstation_event(self, **kwargs):
        # 1) Leer el cuerpo JSON (independiente de kwargs de form-encoded).
        try:
            payload = request.get_json_data()
        except Exception:
            return self._json({'status': 'error',
                               'error': 'invalid_json'}, status=400)
        if not isinstance(payload, dict):
            return self._json({'status': 'error',
                               'error': 'invalid_payload'}, status=400)

        # 2) Autenticación por API key de estación.
        api_key = (request.httprequest.headers.get('X-API-Key')
                   or payload.get('api_key'))
        if not api_key:
            return self._json({'status': 'error',
                               'error': 'missing_api_key'}, status=401)
        workcenter = request.env['mrp.workcenter'].sudo().search(
            [('ws_api_key', '=', api_key)], limit=1)
        if not workcenter:
            return self._json({'status': 'error',
                               'error': 'invalid_api_key'}, status=401)

        # 3) Validar el tipo de evento.
        raw_type = (payload.get('event_type') or '').strip().lower()
        event_type = _EVENT_TYPE_ALIASES.get(raw_type)
        if not event_type:
            return self._json({
                'status': 'error',
                'error': 'invalid_event_type',
                'accepted': sorted(set(_EVENT_TYPE_ALIASES.values())),
            }, status=400)

        # 4) Construir los valores del evento.
        values = {
            'workcenter_id': workcenter.id,
            'event_type': event_type,
            'timestamp': self._parse_timestamp(payload.get('timestamp')),
            'duration_seconds': self._as_float(payload.get('duration_seconds')),
            'confidence': self._as_float(payload.get('confidence')),
            'zone': payload.get('zone') or False,
            'source_device': payload.get('source_device') or False,
            'note': payload.get('note') or False,
        }

        # 5) Vincular la orden de trabajo: la indicada, si pertenece a este
        #    centro; si no se indica, la que esté en progreso en el puesto.
        workorder = self._resolve_workorder(payload.get('workorder_id'),
                                            workcenter)
        if workorder:
            values['workorder_id'] = workorder.id

        # 6) Crear el evento con sudo (el usuario público no tiene permisos).
        try:
            event = request.env['workstation.presence.event'].sudo().create(
                values)
        except Exception:
            _logger.exception('No se pudo registrar el evento de presencia')
            return self._json({'status': 'error',
                               'error': 'internal_error'}, status=500)

        return self._json({
            'status': 'ok',
            'event_id': event.id,
            'workcenter_id': workcenter.id,
            'workorder_id': event.workorder_id.id or None,
            'is_anomalous': event.is_anomalous,
        })

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _resolve_workorder(self, workorder_id, workcenter):
        WorkOrder = request.env['mrp.workorder'].sudo()
        if workorder_id:
            try:
                wo = WorkOrder.browse(int(workorder_id)).exists()
            except (TypeError, ValueError):
                wo = WorkOrder
            if wo and wo.workcenter_id.id == workcenter.id:
                return wo
            return WorkOrder  # id inválido o de otro puesto -> sin vincular
        # Sin id explícito: tomar la OT en progreso de este centro, si hay.
        return WorkOrder.search([
            ('workcenter_id', '=', workcenter.id),
            ('state', '=', 'progress'),
        ], order='date_start desc', limit=1)

    @staticmethod
    def _parse_timestamp(value):
        """Parsea ISO-8601 (UTC) a datetime naive UTC; None -> ahora."""
        if not value:
            return fields.Datetime.now()
        try:
            text = str(value).strip().replace('Z', '+00:00')
            dt = datetime.fromisoformat(text)
            if dt.tzinfo is not None:
                dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
            return dt
        except (ValueError, TypeError):
            return fields.Datetime.now()

    @staticmethod
    def _as_float(value):
        try:
            return float(value) if value is not None else 0.0
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _json(data, status=200):
        return request.make_json_response(data, status=status)
