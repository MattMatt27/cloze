"""Flask CLI commands for the report-v2 worker.

Production runs ``flask reports-worker`` as its own systemd unit
(``cosmos-worker.service``) — the dedicated worker process from the design doc.
Locally: run it in a second terminal, or skip it entirely with
``REPORTS_WORKER_MODE=eager`` (jobs execute inline on enqueue).

The loop is deliberately thin: all logic lives in
``llm_chat.services.report_jobs.run_once()``, which tests call directly.
"""

import signal
import time

import click


def register_cli(app):
    @app.cli.command("reports-worker")
    @click.option("--tick", default=2.0, show_default=True,
                  help="Idle poll interval in seconds.")
    @click.option("--max-iterations", default=None, type=int,
                  help="Exit after N iterations (used by tests/smoke checks).")
    def reports_worker(tick, max_iterations):
        """Run the report job worker loop."""
        from .services.report_jobs import run_once

        stop = {"requested": False}

        def _request_stop(signum, frame):
            stop["requested"] = True

        signal.signal(signal.SIGTERM, _request_stop)
        signal.signal(signal.SIGINT, _request_stop)

        click.echo(f"reports-worker started (tick={tick}s)")
        iterations = 0
        while not stop["requested"]:
            job = run_once()
            if job is not None:
                click.echo(f"job {job.id} [{job.kind}] -> {job.status}")
            iterations += 1
            if max_iterations is not None and iterations >= max_iterations:
                break
            if job is None and not stop["requested"]:
                time.sleep(tick)
        click.echo("reports-worker stopped")
