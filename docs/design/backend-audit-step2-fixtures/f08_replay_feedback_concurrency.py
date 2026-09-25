"""F-08 fixture: dos PROCESOS escriben concurrentemente al mismo JSONL de
ReplayFeedbackStore.append, sincronizados con multiprocessing.Barrier para
forzar la escritura simultanea (no solo N repeticiones esperando que falle).
Verifica: cantidad total de lineas, parseabilidad de cada linea (deteccion de
escritura truncada/entrelazada), sin asumir orden. Directorio temporal, datos
sinteticos.
"""
import sys, os, json, tempfile
sys.path.insert(0, r"C:\Repo\AAI_Hydric_Stress_audit_step2\src")
import multiprocessing as mp
from datetime import datetime, timezone

from historical_replay.feedback import ReplayFeedbackStore, ReplayFeedbackRecord

N_WRITERS = 8
N_PER_WRITER = 200


def worker(path, barrier, idx):
    store = ReplayFeedbackStore(os.path.dirname(path), package_id=os.path.basename(path)[:-6])
    barrier.wait()
    for i in range(N_PER_WRITER):
        rec = ReplayFeedbackRecord(
            timestamp_origen=f"2024-01-01",
            experiment_id="exp",
            run_id=f"writer{idx}",
            estado_validacion="confirmada",
            etiqueta_corregida=1,
            observacion=f"writer={idx} seq={i} " + ("X" * 50),
            registered_at=datetime.now(timezone.utc).isoformat(),
            simulated_at="2024-01-05",
        )
        store.append(rec)


if __name__ == "__main__":
    tmpdir = tempfile.mkdtemp(prefix="f08_replay_fb_")
    path = os.path.join(tmpdir, "pkg-test.jsonl")
    barrier = mp.Barrier(N_WRITERS)
    procs = [mp.Process(target=worker, args=(path, barrier, i)) for i in range(N_WRITERS)]
    for p in procs:
        p.start()
    for p in procs:
        p.join()

    with open(path, encoding="utf-8") as f:
        lines = [l for l in f.read().split("\n") if l.strip()]

    expected = N_WRITERS * N_PER_WRITER
    print(f"expected_lines={expected} actual_lines={len(lines)}")

    bad = 0
    seen = set()
    for l in lines:
        try:
            payload = json.loads(l)
            key = (payload["run_id"], payload["observacion"])
            if key in seen:
                print("DUPLICATE:", key)
            seen.add(key)
        except json.JSONDecodeError as e:
            bad += 1
            print("UNPARSEABLE LINE:", repr(l)[:120], e)
    print(f"unparseable_lines={bad}")
    print(f"unique_records={len(seen)}")
    print("RESULT:", "PASS_NO_CORRUPTION" if bad == 0 and len(lines) == expected else "CORRUPTION_OR_LOSS_DETECTED")
    print("path=", path)
