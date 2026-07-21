# AI-Infrastructure-Monitor: Pipeline ETL Modular para Monitoreo de Hardware Enterprise (B2B / IA)

**AI-Infrastructure-Monitor** es una solución avanzada de automatización ETL (Extract, Transform, Load) diseñada como una prueba de concepto industrial para el monitoreo, persistencia histórica y análisis predictivo-financiero de precios en hardware de alto rendimiento orientado a Inteligencia Artificial y Servidores de Misión Crítica (GPUs de grado de estación de trabajo, procesadores AMD EPYC de alta densidad de núcleos, almacenamiento Enterprise PCIe 5.0 y memoria RAM ECC con registro).

> **Nota de Contexto Corporativo:** Este sistema representa un ejercicio de arquitectura de software limpio, enfocado en demostrar competencias clave en ingeniería de datos, resiliencia ante protecciones WAF, consumo optimizado de LLMs de código abierto a través de API e implementaciones de diseño desacoplado. En un ecosistema empresarial real, la adquisición de infraestructura de este calibre se gestiona mediante integraciones API directas (EDI) o contratos consolidados con mayoristas tecnológicos (ej. Arrow, Tech Data, Ingram Micro). Se emplea el web scraping estratégico como una fuente de datos accesible y reactiva para nutrir el pipeline transaccional.

El pipeline orquesta de extremo a extremo la adquisición de datos evadiendo mitigaciones anti-bot, la persistencia indexada en una capa relacional y la inferencia a través de la API de **Groq (usando Llama 3.3 70B)** para ejecutar análisis exclusivamente financieros. Ante ventanas de oportunidad óptimas, el sistema despacha alertas enriquecidas visualmente a canales corporativos mediante webhooks automatizados.

---

## Arquitectura del Sistema (Diseño Modular Basado en Capas)

El diseño del proyecto se rige bajo principios de alta cohesión y bajo acoplamiento, segmentando las responsabilidades de procesamiento de datos en módulos independientes:

* **`scraper.py` (Capa de Extracción Resiliente):** Módulo encargado de la ingesta de datos brutos. Utiliza `cloudscraper` para evadir desafíos WAF mediante emulación avanzada de navegadores y huellas TLS nativas. Implementa una **estrategia de degradación en cascada de 3 niveles** que garantiza que los cambios en la interfaz de usuario (UI) no interrumpan el flujo de datos.
* **`database.py` (Capa de Persistencia Transaccional):** Motor relacional ligero basado en **SQLite**. Abstrae la conexión, inserción segura mediante consultas parametrizadas (prevención de inyección SQL) y la recuperación analítica del precio mínimo histórico de los productos en ventanas móviles de tiempo.
* **`ia_analyst.py` (Capa de Inferencia e Inteligencia B2B):** Integra el SDK oficial de **Groq** para interactuar con el modelo abierto de última generación `llama-3.3-70b-versatile`. Procesa los lotes consolidados de datos del mercado y el histórico de la base de datos bajo un formateo JSON estricto mediante directivas de sistema.
* **`notificador.py` (Capa de Alertas y Desacoplamiento):** Módulo encargado de estructurar y transmitir los payloads hacia la API de Webhooks de Discord. Está diseñado de manera asíncrona/aislada para asegurar que un fallo en los servicios de mensajería externos no comprometa la integridad de la ejecución del pipeline principal.
* **`main.py` (Orquestador Central):** El punto de entrada del sistema. Coordina secuencialmente las fases del pipeline ETL, administrando los tiempos de ejecución mediante técnicas de *jitter* (esperas aleatorias) para mitigar políticas de bloqueo por tasa de ráfaga (*Rate-Limiting*).

---

## Características Técnicas Destacadas

### 1. Extracción Semántica Profunda en 3 Niveles
El motor de scraping no depende estrictamente de selectores visuales volátiles. Se ejecuta bajo un esquema de tolerancia a fallos estructurado:
1.  **Nivel 1 (Semántico - JSON-LD):** Inspecciona bloques `application/ld+json` mediante un algoritmo de búsqueda recursiva case-insensitive, localizando objetos basados en la especificación global *Schema.org/Product*, extrayendo metadatos limpios directamente del motor de datos de la web.
2.  **Nivel 2 (Metadatos - OpenGraph/Twitter):** Si el JSON-LD está ausente o corrupto, el scraper lee las etiquetas de indexación para buscadores (`og:title`, `product:price:amount`, etc.).
3.  **Nivel 3 (Análisis DOM - CSS/Regex Fallback):** Como última línea de defensa, aplica selectores de clases relativas combinados con expresiones regulares globales para capturar expresiones de precios con formato de moneda europeo.

### 2. Base de Datos Optimizada para Lecturas Analíticas
La base de datos local no es un simple almacén plano. Implementa mejoras de indexación avanzadas:
* **Índices Compuestos:** Se genera el índice `idx_spec_fecha` sobre `(categoria_spec, fecha DESC)` para acelerar de forma drástica las consultas agregadas que involucran filtros temporales fijos e históricos por categorías.
* **Mitigación de Vulnerabilidades:** Todas las inserciones y búsquedas utilizan consultas preparadas y parametrizadas con placeholders (`?`), garantizando inmunidad frente a ataques de inyección de código SQL.

### 3. Inferencia de IA Orientada a Negocio y Salida Determinista
El uso de LLMs dentro del flujo está optimizado para evitar alucinaciones técnicas y sobrecostos de tokens:
* **Inferencia Unificada por Lotes:** En lugar de realizar una llamada de API por cada producto escrapeado, se consolida un lote enriquecido en memoria y se envía en un único *payload* hacia la infraestructura ultraveloz de Groq.
* **Modo JSON Estricto:** Se activa el parámetro `response_format={"type": "json_object"}` para obligar al modelo Llama-3.3 a responder exclusivamente con la estructura JSON requerida, permitiendo la deserialización directa en diccionarios de Python sin fallos de parseo.
* **Estrategia de Backoff:** Implementa un bucle de reintentos con retrasos controlados ante saturaciones temporales de cuota en la API o fallos de red.

---

## Instalación y Configuración

### 1. Requisitos Previos
* Python 3.10 o superior instalado en el sistema.
* Una clave de API activa de [Groq Console](https://console.groq.com/).
* Un Webhook configurado en tu servidor de Discord (Opcional, para recibir las alertas).

### 2. Clonación y Aislamiento del Entorno
Clona este repositorio en tu máquina local y configura un entorno virtual para mantener limpias las dependencias:

```bash
git clone [https://github.com/Zerofas/Ai_Component.git](https://github.com/Zerofas/Ai_Component.git)
cd Ai_Component

# Creación del entorno virtual
python3 -m venv venv

# Activación del entorno
# En Linux/macOS:
source venv/bin/activate
# En Windows (CMD):
# venv\\Scripts\\activate.bat
# En Windows (PowerShell):
# .\\venv\\Scripts\\Activate.ps1
