"""Pruebas del enforcement de solo lectura para los roles lectores.

Cubren el caso positivo (lectura permitida), los casos negativos (escritura
en el repositorio y en ``$HOME`` rechazada, sin red) y la ausencia de efectos
laterales fuera del sandbox. Si ``bwrap`` no esta disponible, las pruebas se
saltan explicitamente: un entorno sin la herramienta NO debe interpretarse
como enforcement acreditado (AUD-READ03 / LNX-03 / CRIT-SUB-01).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SANDBOX = REPO_ROOT / "scripts" / "readonly_role_sandbox.sh"
VERIFIER = REPO_ROOT / "scripts" / "verify_readonly_sandbox.sh"

_BWRAP = shutil.which("bwrap")


@unittest.skipIf(_BWRAP is None, "bwrap ausente: enforcement no acreditable en este entorno")
class ReadOnlyRoleSandboxTest(unittest.TestCase):
    def _run_in_sandbox(self, script: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [str(SANDBOX), "/bin/bash", "-c", script],
            capture_output=True,
            text=True,
            timeout=120,
        )

    def test_wrapper_and_verifier_are_executable(self):
        self.assertTrue(SANDBOX.is_file(), f"falta {SANDBOX}")
        self.assertTrue(VERIFIER.is_file(), f"falta {VERIFIER}")
        self.assertTrue(os.access(SANDBOX, os.X_OK), "readonly_role_sandbox.sh no es ejecutable")
        self.assertTrue(os.access(VERIFIER, os.X_OK), "verify_readonly_sandbox.sh no es ejecutable")

    def test_read_of_repository_is_allowed(self):
        result = self._run_in_sandbox('head -c 12 "$REPO/AGENTS.md"')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("# AGENTS.md", result.stdout)

    def test_write_into_repository_is_refused_with_erofs(self):
        probe = REPO_ROOT / ".test-readonly-probe-repo"
        result = self._run_in_sandbox(f'echo x > "{probe}"')
        self.assertNotEqual(result.returncode, 0, "la escritura en el repositorio no fue rechazada")
        self.assertIn("Read-only file system", result.stderr)
        self.assertFalse(probe.exists(), "la sonda sobrevivio fuera del sandbox")

    def test_write_into_real_home_is_refused(self):
        probe = Path.home() / ".test-readonly-probe-home"
        result = self._run_in_sandbox(f'echo x > "{probe}"')
        self.assertNotEqual(result.returncode, 0, "la escritura en $HOME no fue rechazada")
        self.assertFalse(probe.exists(), "la sonda sobrevivio fuera del sandbox")

    def test_ephemeral_tmp_is_writable_and_not_shared(self):
        marker = "/tmp/test-readonly-probe-tmp"
        result = self._run_in_sandbox(f"echo x > {marker} && cat {marker}")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "x")
        self.assertFalse(Path(marker).exists(), "el /tmp del sandbox no fue efimero")

    def test_dev_writes_are_ephemeral_and_do_not_escape(self):
        """`/dev` dentro del sandbox es tmpfs escribible; lo escrito alli no
        sobrevive fuera. Se comprueba en vez de afirmarse: la cabecera del
        envoltorio afirmaba antes que TODA escritura fuera de /tmp fallaba,
        lo cual era falso para /dev y /dev/shm (hallazgo N-01 del critico)."""
        marker = "/dev/test-readonly-probe-dev"
        result = self._run_in_sandbox(f"echo x > {marker} && cat {marker}")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "x")
        self.assertFalse(Path(marker).exists(), "la escritura en /dev escapo del sandbox")

    def test_network_is_unavailable(self):
        result = self._run_in_sandbox("getent hosts pypi.org")
        self.assertNotEqual(result.returncode, 0, "el sandbox tuvo resolucion DNS")

    def test_wsl_windows_interop_is_closed(self):
        """Hallazgo A-01 de la auditoria independiente: un binario PE de
        Windows invocado desde dentro del sandbox corre en el host Windows,
        fuera de los namespaces de Linux, con red y escritura completas. El
        auditor lo demostro obteniendo HTTP 200 con `curl.exe` y creando un
        archivo en la raiz del repositorio. Se comprueba que la via esta
        cerrada: /mnt vacio y binarios de Windows inalcanzables."""
        result = self._run_in_sandbox(
            "ls -A /mnt 2>/dev/null | wc -l; "
            "ls /mnt/c/Windows/System32/cmd.exe >/dev/null 2>&1; "
            'echo "cmd_exit=$?"'
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = result.stdout.split()
        self.assertEqual(lines[0], "0", "/mnt no esta vacio dentro del sandbox")
        self.assertIn("cmd_exit=", result.stdout)
        self.assertNotIn(
            "cmd_exit=0", result.stdout, "binarios de Windows alcanzables: A-01 sigue abierto"
        )

    def test_wsl_interop_sockets_are_unreachable(self):
        """Hallazgo NF-01 de la re-auditoria: cerrar la ejecucion de binarios
        PE no cerraba los endpoints de interoperabilidad. Los sockets
        `/run/WSL/*_interop` viven en el bind de solo lectura de `/` y los
        AF_UNIX por ruta atraviesan los namespaces de red, de modo que
        `--unshare-net` no los alcanza. Se comprueba que `/run` esta vacio."""
        result = self._run_in_sandbox(
            "ls -A /run 2>/dev/null | wc -l; ls -A /run/WSL 2>/dev/null | wc -l"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        counts = result.stdout.split()
        self.assertEqual(counts[0], "0", "/run no esta vacio: NF-01 sigue abierto")
        self.assertEqual(counts[1], "0", "sockets de interop visibles: NF-01 sigue abierto")

    def test_verifier_reports_pass_with_all_conditions_true(self):
        result = subprocess.run([str(VERIFIER)], capture_output=True, text=True, timeout=180)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["verdict"], "PASS")
        self.assertTrue(payload["checks"]["dev_probe_absent_after"])
        self.assertTrue(payload["checks"]["wsl_windows_binaries_unreachable"])
        self.assertTrue(payload["checks"]["mnt_is_empty"])
        self.assertTrue(payload["checks"]["wsl_interop_sockets_unreachable"])
        for name, value in payload["checks"].items():
            if isinstance(value, bool):
                self.assertTrue(value, f"comprobacion fallida: {name}")

    def test_wrapper_without_arguments_fails_explicitly(self):
        result = subprocess.run([str(SANDBOX)], capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 2)
        self.assertIn("uso:", result.stderr)


if __name__ == "__main__":
    unittest.main()
