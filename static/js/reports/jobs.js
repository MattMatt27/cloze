// Report-v2 job helpers: enqueue + poll. Shared by the viewer and the hub.

export async function enqueueReport(scope, scopeId, templateId = null) {
  const res = await fetch('/api/v2/reports/jobs', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scope, scope_id: scopeId, template_id: templateId }),
  });
  if (!res.ok) throw new Error(`enqueue failed (${res.status})`);
  return res.json();
}

// Polls until the job leaves queued/running. onProgress(job) fires each poll.
export async function pollJob(jobId, onProgress, intervalMs = 2000) {
  for (;;) {
    const res = await fetch(`/api/v2/reports/jobs/${jobId}`);
    if (!res.ok) throw new Error(`poll failed (${res.status})`);
    const job = await res.json();
    if (onProgress) onProgress(job);
    if (job.status !== 'queued' && job.status !== 'running') return job;
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }
}

export function progressLabel(job) {
  if (job.status === 'queued') return 'Queued…';
  if (job.status === 'running') {
    return job.progress_total > 0
      ? `Analyzing ${job.progress_current}/${job.progress_total} conversations…`
      : 'Generating…';
  }
  return job.status;
}
