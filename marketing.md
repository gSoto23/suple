# Documentación del Módulo de Marketing y Envíos Masivos

El módulo de Marketing permite al CRM interactuar con la API Oficial de WhatsApp Cloud de Meta para sincronizar plantillas aprobadas, crear campañas y realizar envíos masivos dinámicos a múltiples clientes de la base de datos de Sales-AI.

---

## 1. Configuraciones Iniciales Obligatorias

Para que el módulo funcione correctamente y pueda comunicarse con Meta, debes tener configuradas las siguientes variables de entorno en tu archivo `.env` en la raíz del proyecto.

```env
# Token de acceso temporal o permanente de Meta for Developers
WHATSAPP_ACCESS_TOKEN="EAAxxxx..."

# El ID del número de teléfono desde el cual se enviarán los mensajes (En Meta > WhatsApp > Inicio)
WHATSAPP_PHONE_NUMBER_ID="123456789012345"

# [NUEVO] El ID de tu Cuenta de WhatsApp Business. 
# Requerido EXCLUSIVAMENTE para sincronizar (descargar) las plantillas.
WHATSAPP_BUSINESS_ACCOUNT_ID="109876543210987"

# Prefijo de código de país por defecto (Costa Rica)
COUNTRY_PHONE_CODE="506"
```

> **Nota sobre el Business Account ID (WABA ID)**: Este identificador suele encontrarse en el panel de Facebook Business Manager bajo *Cuentas de WhatsApp* o en el panel de *Meta for Developers* (Configuración de la API > Identificador de la cuenta de WhatsApp Business).

---

## 2. Flujo de Trabajo y Operación UI

El funcionamiento del módulo consta de los siguientes flujos para los administradores del CRM:

### A. Sincronización de Plantillas
1. Navega a la sección **Marketing** en el menú lateral.
2. En la tabla inferior de "Plantillas de Meta", haz clic en **[Sincronizar de Meta]**.
3. El sistema llamará a tu Meta Business Manager y descargará todas las plantillas (junto con su configuración de variables (`{{1}}`), idioma, estado, etc). Estas reemplazarán o complementarán el listado local de plantillas aprobadas.

### B. Creación de Campaña
1. Haz clic en **[Nueva Campaña]** e ingresa un nombre interno (ej. *Promo Verano 2026*).
2. Selecciona qué **Plantilla de Meta** deseas utilizar en el menú desplegable.
3. **Mapeo de Variables**: Si la plantilla seleccionada tiene parámetros dinámicos (ej: `Estimado {{1}}, tu pedido...`), la UI lo detectará. Aparecerá un formulario permitiendo elegir con qué dato de la base de datos rellenar esa variable (Ej: `{{1}}` -> "Nombre Completo" ó "Teléfono").
4. Haz clic en guardar para crear la campaña.

### C. Selección de Destinatarios y Ejecución
1. En la lista de campañas, haz clic en **[Gestionar]** sobre la campaña recién creada.
2. En el panel modal, utiliza el menú de **Añadir Destinatarios** para seleccionar y agregar a los clientes (guardados previamente en la BD de Clientes) a los cuales quieres enviar la notificación masiva.
3. Una vez añadidos todos los destinatarios, haz clic en el botón verde **[Iniciar Envío Masivo]**.
4. El sistema hará el despacho progresivo. Puedes visualizar en la misma tabla si el mensaje fue marcado como "Sent" (Enviado) o "Failed" (Fallido) y la descripción del error.

---

## 3. Detalles Técnicos

### Base de Datos
- `marketing_templates`: Almacena el ID, idioma, componentes JSON (estructura de Meta) y estado.
- `campaigns`: Almacena el nombre, la plantilla referenciada `template_id` y el campo json `variables_mapping` donde se guarda el cruce de variable-cliente (ej. `{"body_1": "full_name"}`).
- `campaign_recipients`: Funciona como tabla pivote entre la Campaña y los Clientes (`customers`), llevando el tracking de `status` individual (sent, failed, pending).

### Endpoints Principales (`/api/v1/marketing`)
- `POST /templates/sync`: Ejecuta la invocación a Graph API usando `get_templates()`.
- `POST /campaigns`: Guarda la configuración inicial y el `variables_mapping`.
- `POST /campaigns/{id}/execute`: Itera los `recipients` pendientes. Extrae los atributos del modelo Customer (usando reflection de Python `getattr()`) y construye el Request Body con el que se invoca remotamente a `whatsapp_client.send_template_message()`.

### Consideraciones sobre WhatsApp API
- Este módulo asume que las plantillas oficiales ya fueron validadas y pre-aprobadas en la plataforma de Facebook. Modificar el texto de los componentes o intentar inyectar plantillas alteradas causará errores de API (HTTP 400 - Validation Failed).
- Las plantillas rechazadas temporalmente en Meta no funcionarán hasta que recuperen su Quality Score (Estado `APPROVED`).
