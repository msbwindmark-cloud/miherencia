# Guia de Importacion de Datos - SmartHeritage

## 1. Importar Lecturas de Sensores (CSV)

**Boton:** "Importar CSV" en la ficha de cada edificio

### Formato del CSV

```csv
valor,fecha
23.5,2026-07-21 10:30:00
24.1,2026-07-21 11:00:00
22.8,2026-07-21 12:00:00
25.0,2026-07-21 13:00:00
```

| Columna  | Tipo   | Obligatorio | Formato               | Ejemplo            |
|----------|--------|-------------|-----------------------|--------------------|
| valor    | float  | SI          | Numero con decimales  | 23.5, -5.2, 100    |
| fecha    | string | NO          | YYYY-MM-DD HH:MM:SS  | 2026-07-21 10:30:00|

- Si no pones fecha, se usa la fecha y hora actual
- El separador es **coma** (,)
- La primera linea (cabecera) se ignora automaticamente
- Codificacion: **UTF-8**

### Ejemplo completo para sensor de temperatura

```csv
valor,fecha
23.5,2026-07-01 08:00:00
24.2,2026-07-01 09:00:00
25.1,2026-07-01 10:00:00
26.8,2026-07-01 11:00:00
27.3,2026-07-01 12:00:00
28.0,2026-07-01 13:00:00
27.5,2026-07-01 14:00:00
26.2,2026-07-01 15:00:00
25.0,2026-07-01 16:00:00
24.1,2026-07-01 17:00:00
23.3,2026-07-01 18:00:00
22.8,2026-07-01 19:00:00
```

### Ejemplo para sensor de humedad

```csv
valor,fecha
65.2,2026-07-01 08:00:00
63.8,2026-07-01 09:00:00
62.1,2026-07-01 10:00:00
60.5,2026-07-01 11:00:00
58.9,2026-07-01 12:00:00
57.3,2026-07-01 13:00:00
58.1,2026-07-01 14:00:00
60.0,2026-07-01 15:00:00
62.5,2026-07-01 16:00:00
64.8,2026-07-01 17:00:00
```

### Ejemplo para sensor de vibracion

```csv
valor,fecha
0.02,2026-07-01 08:00:00
0.03,2026-07-01 09:00:00
0.01,2026-07-01 10:00:00
0.05,2026-07-01 11:00:00
0.02,2026-07-01 12:00:00
0.01,2026-07-01 13:00:00
0.03,2026-07-01 14:00:00
```

---

## 2. Exportar Datos

### Exportar Excel (.xlsx)
**Boton:** "Exportar Excel" en la ficha del edificio
- Descarga un archivo Excel con todas las lecturas del edificio
- Incluye columnas: Sensor, Valor, Unidad, Fecha, Es Alerta

### Exportar CSV
**Boton:** "Exportar CSV" en la ficha del edificio
- Descarga un CSV con las mismas lecturas
- Formato: sensor,valor,unidad,fecha,es_alerta

---

## 3. Formatos para Otros Modulos

### Documentos (subir archivos)
**Ubicacion:** Ficha edificio > Documentos
- **Planos:** PDF, DWG, JPG/PNG de planos arquitectonicos
- **Permisos:** PDF de licencias, declaraciones de Utilidad Publica
- **Informes tecnicos:** PDF con analisis estructural, fotos
- **Fotografias:** JPG/PNG de antes/despues, estado actual

### Timeline Historico
**Ubicacion:** Ficha edificio > Timeline Historico
| Campo       | Tipo   | Ejemplo                    |
|-------------|--------|----------------------------|
| titulo      | texto  | "Restauracion fachada"     |
| descripcion | texto  | "Se restauro la fachada.." |
| fecha       | fecha  | 2020-03-15                 |
| categoria   | texto  | restauracion               |

Categorias validas: restauracion, construccion, dano, evento_historico, proteccion, modificacion

### Herramientas
**Ubicacion:** Menu > Herramientas
| Campo          | Tipo    | Ejemplo              |
|----------------|---------|----------------------|
| nombre         | texto   | "Nivel laser"        |
| categoria      | texto   | "Medida"             |
| numero_serie   | texto   | "NL-2024-001"        |
| estado         |选择     | "disponible"         |
| costo          | decimal | 150.00               |

### Formulario de Inspeccion
**Ubicacion:** Ficha edificio > Inspecciones > Nueva
- Checklist con 8 items predefinidos (fachada, cubierta, electrica, etc.)
- Se puede anadir firma digital dibujando en el canvas
- Estados: aprobado, rechazado, pendiente, con_observaciones

---

## 4. Consejos

1. **Codificacion UTF-8:** Siempre guarda los CSV en UTF-8 para que no haya problemas con tildes
2. **Fechas:** Usa siempre el formato `YYYY-MM-DD HH:MM:SS`
3. **Decimales:** Usa punto (.) como separador decimal, no coma
4. **Sensores:** Primero crea los sensores en el edificio antes de importar datos
5. **Volumen:** Puedes importar cientos de registros de golpe, el sistema los procesa uno a uno
