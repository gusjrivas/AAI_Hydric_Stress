# Change: Menú de presentación de tres entradas

- HU6/HU7 (presentación) · `alerting-ui` · CRISP-DM Deployment. Sin impacto científico, de API ni de permisos.
- Problema: la navegación principal ofrece seis entradas al mismo nivel (Seguimiento histórico, Mi cultivo, Laboratorio, Evidencia, Arquitectura y Herramientas técnicas) y la aplicación abre en «Mi cultivo». Para quien ve la aplicación por primera vez no queda claro qué hace cada pantalla ni en qué orden se relacionan con el trabajo.
- Cambio (solo presentación): la navegación principal pasa a tres entradas en el orden de la defensa, **Arquitectura** (cómo está construido), **Caso de demostración** (cómo se usa) y **Resultados** (qué se obtuvo), más un menú **Más** que conserva «Mi cultivo» y «Herramientas técnicas».
- «Caso de demostración» reúne Pergamino, Melchor Romero y el Laboratorio de sensores mediante un selector de caso. Cada caso muestra una línea que indica si usa datos reales o sintéticos y qué ofrece. El selector reemplaza a la navegación «Localidad» que existía dentro de cada sitio.
- La aplicación abre en `#arquitectura` cuando no hay ruta.
- No se elimina ni se renombra ninguna ruta ni ancla (`#productor`, `#resumen`, `#calidad`, `#evidencia`, etc.); los enlaces previos mantienen su destino.
- Este cambio sustituye, para la navegación principal, el agrupamiento en seis secciones del requisito «Navegación centrada en la decisión y resumen fiel».
- Non-goals: cambiar el contenido de las pantallas existentes, los datos, los modelos o los experimentos. Rollback: revertir el PR.
