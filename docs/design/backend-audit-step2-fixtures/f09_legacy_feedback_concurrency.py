"""F-09 fixture: dos ciclos concurrentes load -> update -> save sobre un
Parquet de feedback LEGACY temporal (nunca datos reales), usando exactamente
human_feedback.registry.{load_feedback_log,save_feedback_log} y
human_feedback.schema.update_feedback -- el mismo patron que
backend/app/routers/feedback.py (confirm_feedback/reject_feedback). Sincroniza
con multiprocessing.Barrier justo despues de la lectura, para forzar que
ambos procesos actualicen sobre la MISMA version leida antes de escribir
(el peor caso de una carrera real).
"""
import sys, os, tempfile
sys.path.insert(0, r"C:\Repo\AAI_Hydric_Stress_audit_step2\src")
import multiprocessing as mp
import pandas as pd

from human_feedback.registry import load_feedback_log, save_feedback_log
from human_feedback.schema import init_feedback_log, update_feedback

N_ROWS = 10


def build_initial_log():
    dates = pd.date_range("2024-01-01", periods=N_ROWS, freq="D")
    alerts = pd.Series([True] * N_ROWS)
    return init_feedback_log(pd.Series(dates), alerts)


def worker(data_dir, name, barrier, idx, fecha_a_modificar, estado, result_path):
    log = load_feedback_log(name, data_dir=data_dir)
    barrier.wait()  # both processes now hold their own in-memory copy of the SAME version
    updated = update_feedback(log, fecha=fecha_a_modificar, estado_validacion=estado)
    save_feedback_log(name, updated, data_dir=data_dir)
    with open(result_path, "w") as f:
        f.write("done")


if __name__ == "__main__":
    tmpdir = tempfile.mkdtemp(prefix="f09_legacy_fb_")
    data_dir = __import__("pathlib").Path(tmpdir)
    name = "feedback__test_sensor"

    initial = build_initial_log()
    save_feedback_log(name, initial, data_dir=data_dir)
    fechas = list(initial["fecha"])

    barrier = mp.Barrier(2)
    r0 = os.path.join(tmpdir, "r0.done")
    r1 = os.path.join(tmpdir, "r1.done")
    p0 = mp.Process(
        target=worker, args=(data_dir, name, barrier, 0, fechas[0], "confirmada", r0)
    )
    p1 = mp.Process(
        target=worker, args=(data_dir, name, barrier, 1, fechas[1], "rechazada", r1)
    )
    p0.start()
    p1.start()
    p0.join()
    p1.join()

    print("exitcodes:", p0.exitcode, p1.exitcode)
    print("worker0_finished:", os.path.exists(r0))
    print("worker1_finished:", os.path.exists(r1))

    final = load_feedback_log(name, data_dir=data_dir)
    row0 = final.loc[final["fecha"] == fechas[0]].iloc[0]
    row1 = final.loc[final["fecha"] == fechas[1]].iloc[0]
    print("row0 (worker0 tried 'confirmada'):", "estado_validacion=", row0["estado_validacion"])
    print("row1 (worker1 tried 'rechazada'):", "estado_validacion=", row1["estado_validacion"])

    both_applied = row0["estado_validacion"] == "confirmada" and row1["estado_validacion"] == "rechazada"
    print("RESULT:", "BOTH_UPDATES_SURVIVED" if both_applied else "LOST_UPDATE_DETECTED (uno de los dos cambios desaparecio)")
    print("data_dir=", tmpdir)
