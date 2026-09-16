# Configuración de ejercicios y eventos

No hay plantillas predefinidas ni un evento precargado. Crear evento inicia con estaciones, categorías, tarifas, descuentos, nombre, sede, fechas y precio vacíos.

## 1. Catálogo de pruebas

Define nombre, capacidad, tipo de resultado, unidad y dirección (mayor/menor). Parámetros opcionales:

- Duración del esfuerzo en segundos, distancia por recorrido en metros y número de recorridos.
- Carga sin prescripción, fija en kg o porcentaje del peso corporal; barra, incrementos y redondeo.
- Decimales y límites válidos de la marca, equipo y protocolo técnico.
- Referencias base/élite opcionales para quien elija evaluación lineal en su evento.

Ejemplos de modelado (no se cargan automáticamente): burpees → repeticiones durante 60 segundos; shuttle → tiempo para 10 recorridos de 10 m; sentadilla → repeticiones con carga de 75% del peso corporal; salto → distancia/altura en cm. El tipo, nombre y parámetros no están acoplados.

## 2. Crear evento

1. Nombre, sede, fecha y hora, cierre de inscripción, precio general MXN y cupo. El cupo puede quedar vacío en borrador; se exige para publicar.
2. Agregar estaciones desde catálogo o definirlas para esa edición. Se admiten de 1 a 32, ordenables, con parámetros propios. Los máximos deben sumar 100 puntos. Repartir por igual es una acción explícita, no un formato automático de ocho pruebas.
3. Categorías por sexo/peso; mínimo incluido y máximo excluido. Máximo vacío = sin límite. Se rechazan solapamientos; un peso fuera de rangos exige resolver las reglas antes de recepción.
4. Edad mínima/máxima al día del evento, apertura de inscripción, recepción, fin del evento, orden de estaciones, reglamento, beneficios y contacto. Horarios en America/Mexico_City; las vigencias se almacenan con zona horaria.
5. Tarifas por periodo, sin solapamientos. Fuera de esos periodos rige el precio general. Cada vigencia incluye inicio y excluye fin.
6. Códigos porcentuales o de importe fijo, fechas y límite de usos. Un código por inscripción, aplicado sobre tarifa vigente. El total no baja de cero. Reservas activas cuentan en el límite y conservan cotización, descuento e importe.

El botón Verificar/Calcular importe consulta el servidor. Confirmar inscripción vuelve a validar precio, código, cupo y edad. El precio no se acepta desde el navegador como autoridad. Los descuentos se controlan dentro de la misma transacción que la reserva. El pago online debe habilitarse expresamente y requiere configuración Stripe.

## 3. Recepción y captura

La fecha de nacimiento es opcional para crear una cuenta y obligatoria para eventos con restricción de edad. Administradores y coaches no tienen este campo deportivo en su alta. Cada inscripción conserva fecha de nacimiento y precio aplicados. Recepción valida horario, peso/categoría y lote.

El coach ve protocolo, duración, recorridos y referencia de carga por estación; captura marca, carga usada si aplica y puntuación si la evaluación es por juez. Valida enteros para repeticiones, decimales y mínimos/máximos. Se conserva una marca final por estación; corregir exige motivo y revisión concurrente. La carga usada se registra y la referencia se muestra; cualquier tolerancia o penalización deportiva requiere el criterio del organizador.

El administrador puede descalificar con motivo. Se conserva el historial y se excluye de posiciones; rectificar una descalificación deja recepción pendiente. Los resultados cerrados no se modifican.

## Compatibilidad y límites expresos

Las ediciones anteriores conservan su cálculo original; las nuevas guardan puntos por estación y suman el total. El radar y la comparación de puntos se normalizan a 0–100 y las marcas originales permanecen disponibles. El catálogo no modifica copias guardadas en eventos.

Capacidades disponibles: Fuerza, Resistencia, Velocidad, Potencia. Una métrica principal por estación, unidades libres, moneda MXN, un descuento por inscripción. No hay agregación de múltiples intentos ni penalizaciones automáticas sin reglas acordadas. La puntuación relativa y los desempates están implementados; consultar PREGUNTAS_PUNTUACION.md para fórmulas y operación.

## Identidad visual

Se conservan composición, tipografía y navegación. Paleta: negro/carbón, blanco y amarillo #F2ED00. Los colores de error mantienen su función de aviso.


## Alta guiada y cuentas del equipo

El catálogo inicia vacío. El formulario agrupa la información en: qué mide el coach, condiciones de ejecución, carga, límites de captura y referencias opcionales. La puntuación se configura en el evento; las referencias no son necesarias para evaluación relativa. Las secciones opcionales pueden desplegarse según el ejercicio.

Administradores y coaches acceden a Mi cuenta, sin dorsal, peso, trayectoria ni inscripción deportiva. Las participaciones históricas de una cuenta que cambió de rol se conservan, pero no se muestran en su cuenta administrativa.


## Flujo simplificado

Eventos: 1) datos básicos; 2) pruebas; 3) categorías y opciones. Se puede guardar un borrador antes de añadir estaciones. Las pruebas nuevas reparten 100 puntos por igual automáticamente; desmarca esa opción para definir pesos propios. Editar una edición existente conserva su reparto. Las condiciones y evaluación de cada estación están en Personalizar prueba.

Catálogo: nombre, capacidad y tipo de resultado. Elegir el tipo propone unidad y dirección; las unidades de una prueba guardada se conservan al abrirla. El apartado Agregar condiciones u opciones avanzadas permite modificar esas propuestas y configurar carga, duración, recorridos y límites. No se crean ejercicios ni eventos predefinidos.
