"""Experimento de aislamiento de mecanismo para F-08 (no reemplaza el hallazgo
principal, que ya usa ReplayFeedbackStore.append real). Compara, bajo el mismo
patron de concurrencia (barrier, 8 procesos x 200 escrituras), dos formas de
escribir la MISMA linea JSONL:

  (A) Python io de alto nivel en modo texto "a" (lo que hace
      ReplayFeedbackStore.append hoy: open()/write()/close() por registro).
  (B) os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND) + os.write()
      (bytes, un solo syscall write por registro, sin buffering de io.TextIOWrapper),
      cerrando el fd inmediatamente despues (mismo patron abrir/escribir/cerrar
      por registro que (A), para aislar UNICAMENTE la diferencia de API de
      apertura/escritura, no el patron de vida del handle).

Si (B) no pierde datos y (A) si, es evidencia de que el mecanismo pasa por la
capa de io con buffering de Python (modo texto) y no por semantica O_APPEND del
SO en si. Si ambas pierden datos por igual, el mecanismo esta en otro lado
(ej. no todos los procesos ven una posicion de EOF actualizada al abrir,
independientemente de la API usada).
"""
import sys, os, json, tempfile
import multiprocessing as mp

N_WRITERS = 8
N_PER_WRITER = 200


def worker_textio(path, barrier, idx):
    barrier.wait()
    for i in range(N_PER_WRITER):
        line = json.dumps({"writer": idx, "seq": i, "pad": "X" * 50}) + "\n"
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(line)


def worker_oslevel(path, barrier, idx):
    barrier.wait()
    for i in range(N_PER_WRITER):
        line = (json.dumps({"writer": idx, "seq": i, "pad": "X" * 50}) + "\n").encode("utf-8")
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND)
        try:
            os.write(fd, line)
        finally:
            os.close(fd)


def run(kind, worker_fn):
    tmpdir = tempfile.mkdtemp(prefix=f"f08_mech_{kind}_")
    path = os.path.join(tmpdir, "out.jsonl")
    # touch file so O_CREAT races don't matter
    open(path, "a").close()
    barrier = mp.Barrier(N_WRITERS)
    procs = [mp.Process(target=worker_fn, args=(path, barrier, i)) for i in range(N_WRITERS)]
    for p in procs:
        p.start()
    for p in procs:
        p.join()
    codes = [p.exitcode for p in procs]
    with open(path, "rb") as f:
        raw = f.read()
    lines = [l for l in raw.split(b"\n") if l.strip()]
    bad = 0
    for l in lines:
        try:
            json.loads(l.decode("utf-8"))
        except Exception:
            bad += 1
    expected = N_WRITERS * N_PER_WRITER
    print(
        f"[{kind}] exitcodes_all_zero={all(c == 0 for c in codes)} "
        f"expected_lines={expected} actual_lines={len(lines)} "
        f"missing={expected - len(lines)} unparseable={bad} path={path}"
    )


if __name__ == "__main__":
    run("textio_a_mode", worker_textio)
    run("oslevel_o_append", worker_oslevel)
