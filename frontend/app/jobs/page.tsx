"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { Explain } from "@/components/explain";
import { Shell } from "@/components/shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getJobs, runJob } from "@/lib/api";

export default function JobsPage() {
  return (
    <Shell>
      <Jobs />
    </Shell>
  );
}

function Jobs() {
  const queryClient = useQueryClient();
  const jobs = useQuery({ queryKey: ["jobs"], queryFn: getJobs, refetchInterval: 15000 });
  const [openId, setOpenId] = useState<string | null>(null);
  const run = useMutation({
    mutationFn: runJob,
    onSuccess: (job) => {
      setOpenId(job.id);
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
      queryClient.invalidateQueries({ queryKey: ["skill"] });
      queryClient.invalidateQueries({ queryKey: ["blended"] });
    },
  });

  return (
    <>
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="font-mono text-xs uppercase tracking-widest text-muted">Operations</p>
          <h1 className="text-2xl font-semibold">Blending jobs</h1>
        </div>
        <Button onClick={() => run.mutate()} disabled={run.isPending}>
          {run.isPending ? "Running blend…" : "Run blending now"}
        </Button>
      </header>

      <Explain title="What a blending cycle does">
        <p>
          A cycle reloads the forecast archive, re-estimates bias and skill on the training window, refits the gating network, writes a new scorecard to the database, and logs domain rainfall plus elevated extreme counts at 24, 48, and 72 hours.
          The scheduler repeats this every few hours. In production the same function is the body of a Celery task fed by the latest GFS, ECMWF, and AI cycles.
        </p>
      </Explain>

      <div className="grid gap-3 md:grid-cols-3">
        <Card>
          <CardHeader><CardTitle>Schedule</CardTitle></CardHeader>
          <CardContent className="text-lg font-semibold">{jobs.data?.schedule ?? "—"}</CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Scheduler</CardTitle></CardHeader>
          <CardContent className="text-lg font-semibold">{jobs.data?.scheduler_enabled ? "Armed" : "Paused"}</CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Recent runs</CardTitle></CardHeader>
          <CardContent className="text-lg font-semibold">{jobs.data?.jobs.length ?? 0}</CardContent>
        </Card>
      </div>

      {run.isError ? <p className="text-sm text-rose-600">{(run.error as Error).message}</p> : null}

      <Card>
        <CardHeader><CardTitle>History</CardTitle></CardHeader>
        <CardContent className="space-y-2">
          {jobs.data?.jobs.map((job) => (
            <div key={job.id} className="rounded-lg border border-line">
              <button className="flex w-full flex-wrap items-center gap-3 px-3 py-3 text-left" onClick={() => setOpenId(openId === job.id ? null : job.id)}>
                <Badge className={job.status === "succeeded" ? "border-emerald-200 bg-emerald-50 text-emerald-800" : "border-rose-200 bg-rose-50 text-rose-800"}>
                  {job.status}
                </Badge>
                <span className="text-sm font-medium">{job.message}</span>
                <span className="ml-auto font-mono text-xs text-muted">{new Date(job.started_at).toLocaleString()}</span>
                <span className="font-mono text-xs uppercase text-muted">{job.trigger}</span>
              </button>
              {openId === job.id ? <pre className="overflow-x-auto border-t border-line bg-slate-50 px-3 py-3 font-mono text-xs leading-relaxed dark:bg-slate-900">{job.log}</pre> : null}
            </div>
          ))}
          {jobs.data && jobs.data.jobs.length === 0 ? <p className="text-sm text-muted">No cycles yet.</p> : null}
        </CardContent>
      </Card>
    </>
  );
}
