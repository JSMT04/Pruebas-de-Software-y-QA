# Informe de Pruebas de Software, QA y Análisis de Calidad

**Asignatura:** Taller Práctico de Pruebas de Software y Garantía de Calidad  
**Proyecto:** Pipeline ETL con Análisis de Calidad ISO/IEC 25010  
**Repositorio:** https://github.com/JSMT04/Pruebas-de-Software-y-QA  
**Fecha:** Noviembre 2026

---

## 1. Introducción y Objetivos

### Enfoque Shift-Left y Pirámide de Pruebas

El paradigma **Shift-Left** propone anticipar la detección de defectos hacia las fases más tempranas del ciclo de desarrollo, antes de que alcancen entornos de producción. Aplicado a pipelines ETL, esto significa validar cada función de transformación de datos de forma unitaria, antes de ensamblar el flujo completo.

La **pirámide de pruebas** adoptada en este proyecto se estructura en tres niveles:

```
            ┌─────────────────┐
            │  Integración     │  test_integracion.py → SQLite, pipeline completo
            ├─────────────────┤
            │  Unitarias       │  test_transform.py → normalizar_email, calcular_total
            ├─────────────────┤
            │  Análisis SAST   │  SonarQube → reportes.py (antes y después)
            └─────────────────┘
```

La base de la pirámide (pruebas unitarias) es la más amplia: rápidas, aisladas y sin dependencias externas. Las pruebas de integración confirman que los componentes funcionan correctamente en conjunto. El análisis SAST con SonarQube complementa ambas capas detectando vulnerabilidades estructurales que las pruebas funcionales no pueden encontrar.

### Relación con ISO/IEC 25010

La norma ISO/IEC 25010 define el modelo de calidad de producto software. Este taller aborda cuatro de sus características principales:

| Característica | Dimensión | Implementación en el proyecto |
|---|---|---|
| **Adecuación funcional** | Corrección | `normalizar_email` y `calcular_total` validadas con 36 casos de prueba |
| **Fiabilidad** | Tolerancia a fallos | Pipeline omite emails inválidos sin abortar la ejecución |
| **Seguridad** | Confidencialidad, integridad | Corrección de SQL Injection, credenciales en env vars, eliminación de `eval()` |
| **Mantenibilidad** | Analizabilidad | Docstrings, módulos SRP, corrección de code smells detectados por SonarQube |

---

## 2. Cobertura y Pruebas Unitarias / Integración

### Suite de Pruebas con pytest

La suite de pruebas se organiza en dos archivos que totalizan **36 casos de prueba**:

| Archivo | Función cubierta | Técnica | Casos |
|---|---|---|---|
| `test_transform.py` | `normalizar_email` — válidos | `@pytest.mark.parametrize` | 4 |
| `test_transform.py` | `normalizar_email` — inválidos | `pytest.raises` + parametrize | 6 |
| `test_transform.py` | `calcular_total` — válidos | `@pytest.mark.parametrize` | 5 |
| `test_transform.py` | `calcular_total` — inválidos | `pytest.raises` + parametrize | 4 |
| `test_integracion.py` | Pipeline — inserción básica | Fixture `con` + `tmp_path` | 2 |
| `test_integracion.py` | Pipeline — **IDEMPOTENCIA** | Doble ejecución + COUNT(*) | 1 |
| `test_integracion.py` | Pipeline — emails inválidos | Fixture CSV mixto | 1 |
| `test_integracion.py` | `buscar_cliente` — SQL Injection | Vector `' OR '1'='1` | 2 |
| `test_integracion.py` | `evaluar_expresion` | Válidas + prohibidas | 6 |
| `test_integracion.py` | `procesar_datos` | Clave existente + errores | 3 |
| `test_integracion.py` | `obtener_password` | `monkeypatch` env var | 2 |

### Prueba de Idempotencia

La prueba `test_pipeline_idempotencia` verifica el comportamiento de re-ejecución:

```python
# Primera ejecución: inserta 3 registros
resultado_1 = ejecutar_pipeline(csv_valido, con)
filas_tras_primera = con.execute("SELECT COUNT(*) FROM clientes").fetchone()[0]

# Segunda ejecución: REPLACE los mismos registros (no duplica)
resultado_2 = ejecutar_pipeline(csv_valido, con)
filas_tras_segunda = con.execute("SELECT COUNT(*) FROM clientes").fetchone()[0]

assert filas_tras_primera == filas_tras_segunda == 3  # ← Idempotencia garantizada
```

La idempotencia se garantiza estructuralmente mediante `INSERT OR REPLACE` sobre la columna `email` declarada como `PRIMARY KEY`. SQLite reemplaza el registro existente en lugar de insertar uno nuevo, asegurando que múltiples ejecuciones sobre el mismo CSV producen siempre el mismo estado final.

---

#### Evidencia 1: Ejecución de la Suite de Pruebas con pytest
![Ejecución de pruebas unitarias e integración con pytest](img/Captura%20de%20pantalla%201.png)
*Figura 1: 36 pruebas unitarias y de integración superadas exitosamente (100% PASSED).*

---

#### Evidencia 2: Reporte de Cobertura de Código
![Reporte de cobertura con pytest-cov](img/Captura%20de%20pantalla%202.png)
*Figura 2: Cobertura de código del 100% alcanzada en todo el paquete etl/.*

---

## 3. Análisis SAST con SonarQube (Antes y Después)

### Hallazgos en `etl/reportes.py` (versión vulnerable)

| # | Tipo SonarQube | CWE | Descripción | Severidad |
|---|---|---|---|---|
| 1 | **Vulnerability** | CWE-798 | `DB_PASSWORD = "admin123"` — credencial hardcodeada directamente en el código fuente | 🔴 Critical |
| 2 | **Vulnerability** | CWE-89 | `f"SELECT * FROM clientes WHERE email = '{email}'"` — f-string en consulta SQL permite inyección | 🔴 Critical |
| 3 | **Security Hotspot** | CWE-95 | `eval(expresion)` — ejecución arbitraria de código Python sin sanitización | 🟠 High |
| 4 | **Code Smell** | CWE-390 | `except: pass` — captura genérica oculta errores sin ningún manejo ni logging | 🟡 Major |

### Correcciones Aplicadas

**Fallo 1 — Credencial hardcodeada (CWE-798):**  
Reemplazada por `os.getenv("DB_PASSWORD")`. Si la variable no está configurada, se lanza `EnvironmentError` explícito. Esto separa la configuración sensible del código fuente y permite su gestión segura mediante variables de entorno o vaults.

**Fallo 2 — SQL Injection (CWE-89):**  
La f-string se reemplazó por una consulta parametrizada: `"SELECT * FROM clientes WHERE email = ?"` con el valor pasado como tupla `(email,)`. SQLite escapa automáticamente el parámetro, neutralizando cualquier vector de inyección. La prueba `test_buscar_cliente_resiste_sql_injection` valida que el vector `' OR '1'='1` retorna lista vacía.

**Fallo 3 — `eval()` arbitrario (CWE-95):**  
Reemplazado por `ast.parse()` con inspección de nodos. Se define una lista blanca `NODOS_PROHIBIDOS` que incluye `ast.Call`, `ast.Import`, `ast.Attribute`, entre otros. Solo expresiones con literales y operadores aritméticos básicos son permitidas.

**Fallo 4 — `except: pass` (CWE-390):**  
Reemplazado por `except (KeyError, TypeError) as exc:` con re-raise mediante `raise ValueError(...) from exc`. Esto hace el error visible, loggeable y trazable.

---

#### Evidencia 3: Análisis SAST en SonarQube - Estado Vulnerable (ANTES)

A continuación se presentan las vistas detalladas del Dashboard de SonarQube con la versión vulnerable de `etl/reportes.py`:

![SonarQube Dashboard - Estado Inicial con Vulnerabilidades](img/Captura%20de%20pantalla%203.0.png)
*Figura 3.1: Vista general del proyecto en SonarQube mostrando el Quality Gate y métricas iniciales.*

![SonarQube Detalle de Problemas y Reglas](img/Captura%20de%20pantalla%203.1.png)
*Figura 3.2: Desglose de issues identificados, severidad y clasificación de vulnerabilidades.*

![SonarQube Inspección en Código Fuente](img/Captura%20de%20pantalla%203.2.png)
*Figura 3.3: Detección estática en el código de etl/reportes.py (SQL Injection, hardcoded password y eval).*

---

#### Evidencia 4: Análisis SAST en SonarQube - Estado Corregido (DESPUÉS)

![SonarQube Dashboard - Quality Gate PASSED](img/Captura%20de%20pantalla%204.png)
*Figura 4: Dashboard de SonarQube tras la refactorización integral, mostrando Quality Gate APROBADO (PASSED), 0 vulnerabilidades y cobertura de pruebas.*

---

## 4. Conclusiones y Reflexión

### Impacto del Shift-Left: Detección Temprana vs. Producción

El costo de corregir un defecto escala exponencialmente con la fase en que se detecta. Estudios del NIST y el modelo de Barry Boehm estiman que un defecto encontrado en producción puede costar **hasta 100 veces más** que el mismo defecto detectado durante la codificación.

En este proyecto se evidencian dos vectores de riesgo concretos:

1. **SQL Injection en `buscar_cliente`:** Si este código hubiera llegado a producción, un atacante podría haber extraído todos los registros de clientes con una petición trivial (`' OR '1'='1`). El costo de un breach de datos incluye sanciones regulatorias (GDPR), pérdida de confianza y remediación de infraestructura.

2. **Credencial hardcodeada:** Una contraseña en el código fuente queda expuesta en el historial de Git para siempre, incluso si se elimina en un commit posterior. Herramientas como `git log --all -p` o GitHub's secret scanning la detectan automáticamente.

### Valor de las Pruebas Automatizadas en Pipelines ETL

La prueba de idempotencia es especialmente crítica en contextos ETL, donde los pipelines suelen re-ejecutarse por fallos de red, reinicios de schedulers o reprocesamiento de datos históricos. Un pipeline no idempotente puede duplicar registros silenciosamente, corrompiendo métricas de negocio sin generar errores visibles.

La cobertura del 100% alcanzada, combinada con el análisis SAST de SonarQube, proporciona una red de seguridad que permite refactorizar con confianza, incorporar nuevas fuentes de datos y escalar el pipeline sin regresiones.

### Lecciones Clave

- **Las pruebas unitarias parametrizadas** (`@pytest.mark.parametrize`) reducen la duplicación de código de test y facilitan la extensión de casos límite.
- **El análisis SAST no reemplaza las pruebas** — son complementarios: SonarQube detecta patrones estructuralmente peligrosos; las pruebas verifican el comportamiento observable.
- **La seguridad es una propiedad de diseño**, no un parche posterior. Las consultas parametrizadas y las variables de entorno deben ser el estándar desde el primer commit.
