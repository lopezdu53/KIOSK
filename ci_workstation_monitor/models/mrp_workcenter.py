# -*- coding: utf-8 -*-
import secrets

from odoo import api, fields, models


class MrpWorkcenter(models.Model):
    """Extiende el centro de trabajo con la configuración del puesto:
    la API key con la que se autentica su RPi5 y el umbral de tiempo
    estático que se considera anómalo para ese proceso."""

    _inherit = 'mrp.workcenter'

    ws_api_key = fields.Char(
        string='API Key del puesto',
        copy=False,
        index=True,
        help="Clave con la que el RPi5 de esta estación se autentica ante el "
             "endpoint POST /workstation/event. Cada estación debería tener su "
             "propia clave para poder identificar el origen de cada evento.",
    )
    ws_static_threshold = fields.Integer(
        string='Umbral tiempo estático (s)',
        default=300,
        help="Segundos de inmovilidad/ausencia a partir de los cuales la IA "
             "considera el tiempo como anómalo para este proceso. Ajustable por "
             "tipo de centro de trabajo.",
    )
    ws_presence_event_ids = fields.One2many(
        'workstation.presence.event', 'workcenter_id',
        string='Eventos de presencia',
    )
    ws_presence_event_count = fields.Integer(
        string='# Eventos de presencia',
        compute='_compute_ws_presence_event_count',
    )

    @api.depends('ws_presence_event_ids')
    def _compute_ws_presence_event_count(self):
        data = self.env['workstation.presence.event']._read_group(
            [('workcenter_id', 'in', self.ids)],
            groupby=['workcenter_id'],
            aggregates=['__count'],
        )
        mapped = {wc.id: count for wc, count in data}
        for workcenter in self:
            workcenter.ws_presence_event_count = mapped.get(workcenter.id, 0)

    def action_ws_generate_api_key(self):
        """Genera (o regenera) una API key aleatoria para el puesto."""
        for workcenter in self:
            workcenter.ws_api_key = secrets.token_urlsafe(32)
        return True

    def action_ws_view_presence_events(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Eventos de presencia',
            'res_model': 'workstation.presence.event',
            'view_mode': 'list,form',
            'domain': [('workcenter_id', '=', self.id)],
            'context': {'default_workcenter_id': self.id},
        }
