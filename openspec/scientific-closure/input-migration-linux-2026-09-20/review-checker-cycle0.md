# Respuesta exacta del evidence_checker — snapshot inicial

Fuente: `/root/migration_checker`, FINAL_ANSWER.

Revisión mecánica del snapshot `39f3d55ee0f161fed91e60374bb6aeca241257130fd932a26885fdcaa6c74226` sobre `e669bf8`:

- Perfil efectivo informado: `evidence_checker`, modelo nominal `gpt-5.6-luna`, esfuerzo `low`, sandbox nominal `read-only`; mi entorno efectivo no es introspectable/acreditable como read-only.
- Los 11 artefactos declarados en `implementation-snapshot.json` coinciden byte a byte con sus SHA-256 declarados. El snapshot mismo coincide con el hash solicitado.
- Se verificaron los 6 archivos trasladados en origen, `scientific-closure-inputs` y `scientific-closure-backup`: tamaños y SHA-256 coinciden, y las comparaciones byte a byte reportadas son consistentes. No se parsearon CSV.
- Fixture de recuperación `pip-freeze.txt`: SHA-256 `d0f0b912…a387667`, comparación exitosa. La copia primaria, backup y rehearsal están en el mismo dispositivo `2128` (`/dev/sdf`); LNX-06 queda sólo parcialmente satisfecho.
- Las definiciones LNX-01..06 y AUD-READ01..08 del `blocker-definitions.json` corresponden a las fuentes citadas. LNX-01/LNX-02/LNX-04/LNX-05 permanecen bloqueados; LNX-06 parcialmente satisfecho.
- La procedencia está correctamente separada por estados. NASA POWER conserva `BLOCKING_UNKNOWN` para licencia y versión histórica; no se infirió adquisición desde mtime.
- ADR-0011 permanece bloqueado: `origin/main` registrado como `9fcbfd9f4dd4860a07f7e99d5b16d849ac81c4af`; el ejecutable `214735e…` no es ancestro y el protocolo difiere.
- La imagen aprobada no es accesible; el runtime registra correctamente la exportación exacta requerida. Docker Linux, Ruff y Black no están disponibles. `command -v` resuelve ejecutables Windows (`/mnt/c/...`), por lo que no debe interpretarse como disponibilidad Linux.
- Hallazgo material: `validation.json` declara `git diff --check` PASS sobre una ruta aún no versionada (`??`); `git diff --check` no inspecciona archivos no rastreados, por lo que ese PASS no prueba el contenido del snapshot.
- Hallazgo material: varios `checked_at_utc` parecen horas redondeadas/no observadas (`mount-check` 03:20, runtime 03:21, validation 03:25, snapshot 03:27). No deben presentarse como timestamps exactos de ejecución sin respaldo. El stderr del probe está normalizado con `PID`; no es una transcripción literal. `recovery-rehearsal` 03:20:48 tampoco acredita por sí solo la hora de ejecución.
- Limitación adicional: la evidencia de búsqueda no conserva stdout completo de `rg --files`/términos documentales; sólo permite auditar la conclusión resumida, no reproducir exactamente esa salida.

Conclusión mecánica: los hashes, tamaños, transferencias y fixture son consistentes; el snapshot actual no es auditable como PASS por los claims de timestamps/probe y por el falso alcance del `git diff --check`.
