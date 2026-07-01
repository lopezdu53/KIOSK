# -*- coding: utf-8 -*-
from odoo import api, fields, models


class WorkstationPresenceEvent(models.Model):
    """Evento de auditoría enviado por la cámara/IA de un puesto de trabajo.

    El timing 'oficial' de cada operación lo sigue dando Odoo (botones
    Iniciar/Pausar/Terminar sobre ``mrp.workorder``). Este modelo guarda lo que
    el botón no captura: presencia/ausencia física, zona y tiempo estático.
    No se almacena video, solo el evento.
    """

    _name = 'workstation.presence.event'
    _description = 'Evento de presencia de puesto de trabajo'
    _order = 'timestamp desc, id desc'
    _rec_name = 'display_name'

    EVENT_TYPES = [
        ('presence', 'Presencia'),
        ('absence', 'Ausencia'),
        ('zone', 'Cambio de zona'),
        ('static', 'Tiempo estático'),
        ('heartbeat', 'Latido (heartbeat)'),
    ]

    event_type = fields.Selection(
        EVENT_TYPES, string='Tipo de evento', required=True, index=True,
    )
    timestamp = fields.Datetime(
        string='Marca de tiempo', required=True, index=True,
        default=fields.Datetime.now,
        help="Momento del evento en UTC (lo reporta el RPi5).",
    )
    workcenter_id = fields.Many2one(
        'mrp.workcenter', string='Centro de trabajo',
        required=True, index=True, ondelete='cascade',
    )
    workorder_id = fields.Many2one(
        'mrp.workorder', string='Orden de trabajo',
        index=True, ondelete='set null',
        help="Orden de trabajo activa en el momento del evento, si aplica.",
    )
    production_id = fields.Many2one(
        related='workorder_id.production_id',
        string='Orden de producción', store=True,
    )
    product_id = fields.Many2one(
        related='workorder_id.product_id',
        string='Producto', store=True,
    )
    workorder_state = fields.Selection(
        related='workorder_id.state', string='Estado OT', store=True,
    )
    zone = fields.Char(
        string='Zona', help="Etiqueta de zona detectada por la IA (opcional).",
    )
    duration_seconds = fields.Float(
        string='Duración (s)',
        help="Duración del estado reportado (p.ej. segundos de ausencia o de "
             "inmovilidad). 0 para eventos instantáneos.",
    )
    is_anomalous = fields.Boolean(
        string='Anómalo', compute='_compute_is_anomalous', store=True,
        help="True si es un tiempo estático/ausencia que supera el umbral "
             "configurado en el centro de trabajo.",
    )
    confidence = fields.Float(
        string='Confianza IA',
        help="Confianza de la inferencia (0.0 - 1.0), si el modelo la aporta.",
    )
    source_device = fields.Char(
        string='Dispositivo origen',
        help="Identificador del RPi5/cámara que reportó el evento.",
    )
    note = fields.Text(string='Nota')

    @api.depends('event_type', 'duration_seconds',
                 'workcenter_id.ws_static_threshold')
    def _compute_is_anomalous(self):
        for event in self:
            threshold = event.workcenter_id.ws_static_threshold or 0
            event.is_anomalous = bool(
                event.event_type in ('static', 'absence')
                and threshold
                and event.duration_seconds >= threshold
            )

    @api.depends('event_type', 'workcenter_id.name', 'timestamp')
    def _compute_display_name(self):
        type_labels = dict(self.EVENT_TYPES)
        for event in self:
            wc = event.workcenter_id.name or '?'
            label = type_labels.get(event.event_type, event.event_type or '?')
            ts = event.timestamp or ''
            event.display_name = f'[{wc}] {label} @ {ts}'
