"""F-08 fixture v2 (revision): mismas condiciones que v1, pero con:
- verificacion explicita de exit code de cada proceso hijo (ninguna excepcion
  silenciada);
- stdout/stderr de cada worker redirigido a un archivo propio, revisado
  despues del join;
- conteo de bytes esperados vs bytes reales en disco, para distinguir
  "perdida de bytes" (sobrescritura/puntero de archivo no resincronizado)
  de "solo interleaving" (todos los bytes presentes pero mezclados);
- registro de plataforma, ejecutable de Python, filesystem del directorio
  temporal.
Todo sobre datos 100% sinteticos, en un directorio temporal aislado. Usa
ReplayFeedbackStore.append real (no una reimplementacion).
"""
import sys, os, json, tempfile, platform, traceback
sys.path.insert(0, r"C:\Repo\AAI_Hydric_Stress_audit_step2\src")
import multiprocessing as mp
from datetime import datetime, timezone

from historical_replay.feedback import ReplayFeedbackStore, ReplayFeedbackRecord

N_WRITERS = 8
N_PER_WRITER = 200


def worker(path, barrier, idx, stdout_path):
    with open(stdout_path, "w", encoding="utf-8") as log:
        try:
            store = ReplayFeedbackStore(os.path.dirname(path), package_id=os.path.basename(path)[:-6])
            barrier.wait()
            bytes_written = 0
            for i in range(N_PER_WRITER):
                rec = ReplayFeedbackRecord(
                    timestamp_origen="2024-01-01",
                    experiment_id="exp",
                    run_id=f"writer{idx}",
                    estado_validacion="confirmada",
                    etiqueta_corregida=1,
                    observacion=f"writer={idx} seq={i} " + ("X" * 50),
                    registered_at=datetime.now(timezone.utc).isoformat(),
                    simulated_at="2024-01-05",
                )
                # Replicate exactly what append() serializes, to compute the
                # expected byte count independently of the method under test.
                from dataclasses import asdict
                line = json.dumps(asdict(rec), ensure_ascii=False) + "\n"
                bytes_written += len(line.encode("utf-8"))
                store.append(rec)
            log.write(f"OK bytes_written={bytes_written}\n")
        except Exception:
            log.write("EXCEPTION\n")
            log.write(traceback.format_exc())
            raise


if __name__ == "__main__":
    tmpdir = tempfile.mkdtemp(prefix="f08_replay_fb_v2_")
    path = os.path.join(tmpdir, "pkg-test.jsonl")
    stdout_paths = [os.path.join(tmpdir, f"worker{i}.log") for i in range(N_WRITERS)]
    barrier = mp.Barrier(N_WRITERS)
    procs = [
        mp.Process(target=worker, args=(path, barrier, i, stdout_paths[i]))
        for i in range(N_WRITERS)
    ]
    for p in procs:
        p.start()
    for p in procs:
        p.join()

    print("=== entorno ===")
    print("platform:", platform.platform())
    print("python:", sys.version)
    print("executable:", sys.executable)
    print("tmpdir:", tmpdir)
    try:
        import ctypes
        # Windows filesystem type of the drive containing tmpdir.
        drive = os.path.splitdrive(tmpdir)[0] + "\\"
        fs_name_buf = ctypes.create_unicode_buffer(261)
        ctypes.windll.kernel32.GetVolumeInformationW(
            ctypes.c_wchar_p(drive), None, 0, None, None, None, fs_name_buf, 261
        )
        print("filesystem:", fs_name_buf.value, "(drive", drive, ")")
    except Exception as e:
        print("filesystem: no determinado (", e, ")")

    print("=== exit codes ===")
    all_ok = True
    for i, p in enumerate(procs):
        print(f"worker{i} exitcode={p.exitcode}")
        if p.exitcode != 0:
            all_ok = False
    print("all_exitcodes_zero:", all_ok)

    print("=== worker logs (excepciones si las hubo) ===")
    total_expected_bytes = 0
    any_exception = False
    for i, sp in enumerate(stdout_paths):
        with open(sp, encoding="utf-8") as f:
            content = f.read()
        if "EXCEPTION" in content:
            any_exception = True
            print(f"--- worker{i} RAISED ---")
            print(content)
        else:
            # parse "OK bytes_written=NNNN"
            for line in content.splitlines():
                if line.startswith("OK bytes_written="):
                    total_expected_bytes += int(line.split("=")[1])
    print("any_worker_exception:", any_exception)
    print("total_expected_bytes(from workers' own accounting)=", total_expected_bytes)

    actual_size = os.path.getsize(path)
    print("actual_file_size_bytes=", actual_size)
    print("byte_delta(expected-actual)=", total_expected_bytes - actual_size)

    with open(path, "rb") as f:
        raw = f.read()
    lines = [l for l in raw.split(b"\n") if l.strip()]

    expected_lines = N_WRITERS * N_PER_WRITER
    print(f"expected_lines={expected_lines} actual_lines={len(lines)}")

    bad = 0
    seen = set()
    for l in lines:
        try:
            payload = json.loads(l.decode("utf-8"))
            key = (payload["run_id"], payload["observacion"])
            if key in seen:
                print("DUPLICATE:", key)
            seen.add(key)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            bad += 1
            print("UNPARSEABLE LINE:", repr(l)[:160], e)
    print(f"unparseable_lines={bad}")
    print(f"unique_records={len(seen)}")
    print(
        "RESULT:",
        "PASS_NO_CORRUPTION" if bad == 0 and len(lines) == expected_lines else "CORRUPTION_OR_LOSS_DETECTED",
    )
    print("path=", path)
