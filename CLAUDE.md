# Proyecto: Monitoreo de Puestos de Trabajo (Señalización + IA de Productividad) integrado con Odoo

## Contexto del negocio
CI Steel SAS (envasadoras.co / etiquetadoras.co), fabricante de maquinaria de empaque industrial.
Odoo 19 Enterprise ya en producción en `app7.ventabot.cloud`, con módulos custom desarrollados
in-house (ej. conector WhatsApp con sidecar Node.js). El equipo tiene experiencia construyendo
módulos Odoo propios y trabajando con Delta PLC/HMI, así que el desarrollo de este proyecto debe
seguir ese mismo patrón: control total del código, sin depender de soluciones cerradas.

## Objetivo
Por cada puesto de trabajo en planta:
- Mostrar al operario la orden de trabajo del día (señalización).
- Medir automáticamente el tiempo real por proceso/operación.
- Detectar tiempo estático / ausencias no registradas mediante cámara + IA, como auditoría
  del tiempo reportado manualmente.

## Decisiones de arquitectura ya tomadas

### 1. Señalización → se reemplaza Anthias por la vista kiosk nativa de Odoo
No se usará Anthias (screenly/anthias). En su lugar: Chromium en modo kiosco en cada Raspberry Pi 5,
apuntando a la vista tablet/work order de **Odoo Manufacturing (MRP)**, con un usuario dedicado
por estación. Esa vista ya permite Iniciar/Pausar/Terminar operaciones y calcula tiempo real vs.
planeado de forma nativa — no requiere IA para esta parte.

### 2. Comunicación RPi5 ↔ Odoo → API/controlador HTTP custom (no Odoo IoT Box)
Se descartó el IoT Box oficial de Odoo (protocolo cerrado, pensado para hardware certificado
tipo básculas/impresoras). En su lugar: un **controlador HTTP propio dentro de un módulo Odoo
custom** (`http.Controller`, `type='json'`, autenticado con API key), mismo patrón que el sidecar
de WhatsApp ya construido. Endpoint propuesto: `POST /workstation/event`.

### 3. Rol de la cámara/IA → complemento de auditoría, no reemplazo del timing
El timing "oficial" de cada operación lo sigue dando Odoo (botones Iniciar/Pausar/Terminar).
La cámara detecta lo que el botón no captura: ausencias no registradas, operario fuera del
puesto con la orden "iniciada", tiempos estáticos reales.

### 4. Hardware por puesto
- Raspberry Pi 5 (8GB) — corre a la vez el kiosk de Chromium y el proceso de inferencia.
- TV 40" vía HDMI para el kiosk.
- Raspberry Pi AI Kit (Hailo-8L, 13 TOPS) o Raspberry Pi AI Camera (sensor IMX500 con IA
  on-sensor) — para no saturar la CPU del Pi con la inferencia (YOLO11n / pose estimation).
- Cámara CSI compatible (Camera Module 3 si se usa el AI Kit).

### 5. Privacidad / cumplimiento
No se almacena video, solo eventos (presencia/ausencia, zona, timestamp). Pendiente: política de
tratamiento de datos y consentimiento informado a los operarios (Ley 1581 de Habeas Data, Colombia)
antes de poner cámaras en producción.

## Modelo de datos propuesto en Odoo (módulo nuevo, por definir nombre técnico)
- `workstation.presence.event`: evento de presencia/ausencia/zona, con timestamp, estación,
  vinculado a `mrp.workorder` y `mrp.workcenter`.
- Vista/reporte que cruza: tiempo planeado (de la orden) vs. tiempo real (botones Odoo) vs.
  presencia física detectada (cámara).

## Plan por fases
1. **Módulo Odoo**: modelo de datos + controlador HTTP + vista básica de reporte. Se puede
   probar sin hardware (Postman/curl simulando eventos).
2. **Kiosk piloto**: un RPi5 en modo kiosco apuntando a la work order view de Odoo.
3. **Cámara + IA piloto**: agregar cámara/IA a esa misma estación, conectada al endpoint.
4. **Validación**: una semana en un puesto real, ajustar umbrales y lógica.
5. **Réplica**: desplegar a las demás estaciones.

## Estado actual
Estamos en fase de diseño, a punto de arrancar la Fase 1 (módulo Odoo). No hay código escrito
todavía. Próximo paso: definir la estructura del módulo Odoo (nombre técnico, dependencias,
estructura de carpetas) y el modelo `workstation.presence.event`.

## Preguntas abiertas para resolver durante el desarrollo
- Nombre técnico del módulo Odoo custom.
- Umbral de tiempo estático que se considera "anómalo" por tipo de proceso.
- Cómo se autentica cada RPi5 ante el endpoint (API key por estación vs. una sola compartida).
- Framework de inferencia final: YOLO11n-pose vs. detección de zona simple con bounding boxes.
