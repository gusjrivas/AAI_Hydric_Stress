# Recuperación de los faltantes obligatorios del paquete

> **Actualización (2026-11-08).** Los dos faltantes de esta guía se resolvieron con el respaldo `backup_AAI_Hydric_strees-20261108T152637Z-1-001.zip` (ver `verification-report.md`): las salidas A/B/C y la evidencia H se recuperaron de él y verificaron contra sus manifiestos históricos. La operación privilegiada de la sección 1 **no se ejecutó**; queda documentada solo como alternativa para comparar byte a byte los originales protegidos de WSL con el respaldo.

El paquete está en estado **PARCIAL** mientras falten las evidencias de esta guía. Ninguna operación aquí reentrena, repite A/B/C/H ni evalúa el holdout 2024-2025; solo copia y verifica bytes ya existentes.

## 1. Salidas crudas de A, A_sensitivity_7_28cm, B y C (75 archivos ilegibles)

**Situación comprobada.** En WSL Ubuntu, `/home/gus/scientific-closure-runtime/evidence/{A,A_sensitivity_7_28cm,C}` y 14 de los 15 archivos de `B` pertenecen a `root:root` con modo `0600`; el usuario `gus` no puede leerlos. Los directorios se pueden listar. Se generaron así porque la ejecución corrió como `root` dentro del contenedor.

**Operación preparada** (`scripts/recover_closure_evidence.sh`, probada con un árbol de ejemplo): lista los archivos de las cuatro carpetas, calcula SHA-256 del origen, los copia a una carpeta **nueva**, vuelve a calcular el hash del origen y exige que ambos coincidan, ajusta propietario y permisos **solo de la copia**, y verifica la copia contra el hash del origen y la cantidad de archivos. Se detiene si el destino existe o está dentro del origen. No modifica permisos, propietario, contenido ni nombres de los originales.

**Comando exacto que requiere autorización** (privilegios de administrador, solo para poder leer el origen). En una terminal de Ubuntu (WSL):

```bash
sudo env SRC=/home/gus/scientific-closure-runtime/evidence \
         DST=/home/gus/closure-evidence-readable-20261108 \
         OWNER=gus \
  bash /mnt/c/Repo/AAI_wt_pkg/scripts/recover_closure_evidence.sh
```

Resultado esperado: `OK: 76 archivos copiados y verificados en …` (los 75 ilegibles más `B/stage_b_custody.json`, que ya es legible) y los archivos `SHA256SUMS.source-before`, `SHA256SUMS.source-after` y `verify.log` en el destino. Comprobación posterior sin privilegios:

```bash
cd /home/gus/closure-evidence-readable-20261108 && sha256sum -c SHA256SUMS.source-before | grep -vc ': OK$'   # debe imprimir 0
```

Una vez integrado el PR, el script está en `scripts/recover_closure_evidence.sh` del repositorio; la ruta `/mnt/c/Repo/AAI_wt_pkg/…` corresponde al worktree usado en esta tarea.

**Siguiente paso tras la copia.** Agregar a `docs/delivery/artifact-selection.json` un grupo obligatorio con `required_files` explícito para esos archivos (la herramienta no acepta un grupo obligatorio sin requisitos mínimos), reconstruir el paquete y repetir `verify`/`restore`. Hasta entonces las cifras de A/B/C no se pueden recalcular desde cero.

## 2. Evidencia del complemento H

**Respaldo esperado** (según `openspec/changes/sc-08-aux-hitl/human-package-freeze.json` y la auditoría de `sc-06`):

- Ruta: `/mnt/scientific-backup/AAI_Hydric_Stress/hitl-complement-2026-09-21/` (campaña `hitl-complement-2026-09-21`).
- Dispositivo: el **disco USB 1**, serie `8986451183503575922` (el mismo del respaldo de `closure-campaign-2026-09-21`; el checkpoint lo distingue del NVMe que respalda el `ext4.vhdx` de WSL).
- Integridad esperada: `manifest/SHA256SUMS` con **100 archivos** (auditoría de `sc-06`: «100/100 OK, 0 FAILED»), más `evidence/governance/hitl-complement-2026-09-21/sc-08-aux-hitl/findings-resolution.json` citado en los informes de revisión.

**Estado observado el 2026-11-08.** `/mnt/scientific-backup` existe en Ubuntu como directorio vacío y **no es un punto de montaje** (`findmnt` sin resultado, sin entrada en `/etc/fstab`); `Get-Disk` en Windows muestra solo el NVMe (disco 0). Un directorio vacío no demuestra que el respaldo no exista: lo que falta es el **dispositivo conectado y montado**. Tampoco se encontró H en el árbol de trabajo de WSL (`evidence/governance` solo contiene `closure-campaign-2026-09-21`).

**Qué hay que facilitar:** conectar el disco USB 1 (serie `8986451183503575922`) y montarlo en Ubuntu en `/mnt/scientific-backup` (o indicar otra ubicación donde se encuentre el directorio `hitl-complement-2026-09-21`). Comprobación, solo lectura:

```bash
findmnt /mnt/scientific-backup
cd /mnt/scientific-backup/AAI_Hydric_Stress/hitl-complement-2026-09-21 && sha256sum -c manifest/SHA256SUMS | grep -vc ': OK$'   # debe imprimir 0
```

Con el respaldo visible se agrega un grupo `evidencia-H` (y, si se desea, el respaldo `closure-campaign-2026-09-21` para contrastar la copia de trabajo) a la selección y se reconstruye el paquete.
