# Visión y alcance

Optimus Race es una plataforma independiente de Gymforce, abierta al público. La cuenta del participante persiste entre ediciones; cada evento conserva sus reglas, pesaje, marcas y resultados. Sustituye fórmulas frágiles de una hoja por validaciones explícitas y trazabilidad.

El producto cubre preparación del evento, inscripción en línea o recepción, pagos, captura, clasificación, pantalla pública e historial del atleta. La experiencia visual prioriza teléfonos para atletas/coaches y lectura a distancia para TV.

## Roles

| Rol | Funciones |
| --- | --- |
| Administrador | Configuración visual, publicación, efectivo, recepción, prueba/lote, correcciones y cierre |
| Coach | Lista estable por dorsal, captura individual, faltantes/ausentes/retirados y correcciones con motivo |
| Atleta | Cuenta, inscripción, foto, radar, comparación y evolución por edición |
| Audiencia | TV pública con acumulado, completitud, categoría y posiciones |

## Principios

- Ocho pruebas: 12.5% cada una. Dos por capacidad: fuerza, resistencia, velocidad y potencia, 25% cada capacidad.
- Una marca por atleta/prueba, sin gestión de intentos. Puntos definitivos al guardar; no hay aprobación posterior.
- Faltante, ausente y retirado se conservan como valores nulos. No se redistribuye su peso.
- Peso del evento y categoría deportiva separados del lote operativo. Referencia de fuerza de 75% y carga usada explícita.
- Un evento publicado conserva reglas, precio, fechas y cupo. Duplicar permite cambios en otra edición.
- Una corrección exige motivo y versión vigente. El administrador puede corregir peso o una marca de otra prueba mientras el evento está vivo. Cierre conserva instantánea sin reapertura.
- Los pagos se confirman por evidencia del proveedor; volver de Checkout no confirma por sí mismo.
- Comparar marcas originales evita confundir cambios de benchmark con mejora deportiva.

## Experiencia implementada

Portada con campaña editorial, filtros de eventos y cupos; acceso y recuperación; ficha de evento; perfil con foto y radar, comparación superpuesta, línea temporal por ejercicio/unidad y modo marca/puntos; lista de marcas e historial desplegable. Coach con búsqueda, filtro de pendientes, entradas numéricas grandes, previsualización de puntaje y estado de conexión. Administrador con pestañas, registro en modal, búsqueda de cuenta por correo y editor visual de reglas. TV actualiza cada 5 segundos y rota páginas cada 10; escala para Full HD.

## Decisiones explícitas

Empates comparten posición (1,1,3); dorsal solo desempata la presentación. Atletas sin categoría o sin pruebas no tienen posición. Faltantes no impiden cerrar, pero reservas de pago pendientes sí. El coach puede operar todos los eventos; no hay asignación por evento. Benchmarks se comparten entre categorías de una edición. No se avanza prueba/lote automáticamente.

La instalación no contiene datos demo. Las referencias iniciales son configurables y no constituyen estándares deportivos oficiales. El organizador debe definir benchmarks, rangos de peso, desempate si lo requiere, carga/redondeo, sede, fechas y precio antes de publicar su competencia.

## Fuera del alcance construido

Operación offline, múltiples intentos, integración Gymforce, reembolsos, facturación fiscal, cupones, descuentos, pagos parciales, cancelación de inscripción confirmada, exportación de tarjetas, multi-organización y reapertura de eventos. Sí se permite cancelar una **reserva pendiente de Checkout** después de confirmación de Stripe.
