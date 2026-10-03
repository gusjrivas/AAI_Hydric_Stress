# Prueba con un productor de hortalizas

Guion para la primera sesión con una persona productora, antes de cualquier uso real. El objetivo no es validar los
modelos sino ver **dónde se traba una persona sin conocimientos de informática** al preguntarse «¿va a haber falta de
agua?». No acredita validación agronómica ni preparación productiva.

## Antes de empezar (quien facilita)

1. Dejar la demo de cero: `./scripts/demo_reset.ps1 -Action Reset -StartFrontend` (ver la guía de arranque).
2. Abrir http://127.0.0.1:15199/ **sin ruta** (debe abrir en «Mi cultivo»).
3. Explicar solo esto: «Es una herramienta en evaluación que ayuda a revisar la situación; no dice cuánto ni cuándo
   regar». No explicar la pantalla ni los botones: observar.
4. **Aclarar que los puntos «Pergamino» y «Melchor Romero» son demostraciones con datos históricos.** Por eso la pantalla
   avisa «Este pronóstico no es actual». Es un comportamiento esperado: con datos viejos la herramienta no debe decir
   «hoy». Hoy no hay en el backend de demostración un punto con mediciones al día, así que la experiencia de «pronóstico
   actual» no se puede probar con esta configuración.

## Las 5 tareas (una por vez, sin ayuda)

| # | Tarea (se la dice en voz alta) | Qué se observa | Se considera logrado si… |
|---|---|---|---|
| 1 | «Mirá la pantalla y decime si va a haber falta de agua.» | Dónde mira primero; si lee el titular; si nota el aviso de datos viejos | Dice con sus palabras que el pronóstico **no es actual** (o, con datos al día, qué se espera) y que igual hay que mirar el cultivo |
| 2 | «Elegí tu lote» (el punto de demostración) | Si entiende «lote» / «punto de medición» | Elige el punto sin preguntar qué es |
| 3 | «¿Para qué días dice algo? ¿Hay algún día sin información?» | Si entiende la tira de tres días | Distingue «sin alerta» de «sin pronóstico» y no los confunde con «está todo bien» |
| 4 | «Contanos si lo que dice coincide con lo que ves en el cultivo.» (en un día con fecha ya pasada) | Si encuentra el detalle de cada día y el botón de opinión | Encuentra «Detalle de cada día y tu opinión» y entiende que guardar su opinión no cambia los pronósticos automáticamente |
| 5 | «¿Qué datos usa para decir esto?» | Si encuentra de dónde salen los datos | Lee «Con mediciones hasta…» y el origen (datos externos), sin pedir traducción |

## Hoja de observación (por tarea)

- Tiempo hasta lograrlo o abandonar (segundos).
- Dónde dudó o hizo clic equivocado.
- Palabras que no entendió (anotarlas textuales).
- Qué dijo que entendió, con sus palabras (para comparar con lo que la herramienta quiso decir).
- ¿Interpretó «sin alerta» como «está todo bien»? (hallazgo grave si es que sí).
- ¿Interpretó algún número como porcentaje de riesgo? (hallazgo grave si es que sí).

## Qué hacer con los resultados

Cada palabra que no entendió y cada tarea no lograda es un cambio de texto o de pantalla a priorizar. Los hallazgos graves
(confundir «sin alerta» con seguridad, o leer un puntaje como porcentaje) se corrigen antes de cualquier otra mejora.
