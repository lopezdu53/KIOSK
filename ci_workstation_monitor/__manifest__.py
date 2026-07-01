# -*- coding: utf-8 -*-
{
    'name': 'CI Steel - Workstation Monitor',
    'version': '19.0.1.0.0',
    'summary': 'Auditoría de presencia física por puesto de trabajo (cámara/IA) '
               'cruzada con el timing real de MRP',
    'description': """
CI Steel - Monitoreo de Puestos de Trabajo
==========================================

Complemento de auditoría para las órdenes de trabajo de Manufacturing (MRP).

- Registra eventos de presencia/ausencia/zona/tiempo estático enviados por los
  RPi5 con cámara + IA a través de un controlador HTTP propio (API key por
  estación), sin depender del IoT Box.
- Vincula cada evento a ``mrp.workcenter`` y (opcionalmente) a la
  ``mrp.workorder`` activa, para cruzar tiempo planeado vs. real (botones Odoo)
  vs. presencia física detectada por cámara.
- No almacena video: solo eventos (Ley 1581 - Habeas Data, Colombia).

Endpoint: ``POST /workstation/event`` (type='json').
""",
    'category': 'Manufacturing',
    'author': 'CI Steel SAS',
    'website': 'https://envasadoras.co',
    'license': 'LGPL-3',
    'depends': ['mrp'],
    'data': [
        'security/ir.model.access.csv',
        'views/mrp_workcenter_views.xml',
        'views/workstation_presence_event_views.xml',
        'views/menu_views.xml',
    ],
    'application': True,
    'installable': True,
}
