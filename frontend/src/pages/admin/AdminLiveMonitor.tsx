import { useState, useEffect } from "react";
import { 
  Activity, 
  AlertTriangle, 
  AlertCircle, 
  RefreshCw, 
  Search, 
  Server, 
  Cpu, 
  Wifi, 
  ShieldAlert, 
  RotateCcw,
  Layers, 
  Zap, 
  Database, 
  Cloud,
  Smartphone
} from "lucide-react";
import { API_BASE_URL } from "../../config";

interface AlertItem {
  id: string;
  severity: "CRITICAL" | "WARNING" | "INFO";
  title: string;
  metric: string;
  threshold: string;
  description: string;
  action: string;
}

interface IngestionJobSummary {
  job_id: string;
  upload_id: string;
  filename: string;
  folder: string;
  status: string;
  attempts: number;
  file_size_kb: number;
  received_at: string;
  completed_at: string | null;
  last_error: string | null;
  duration_seconds: number | null;
}

interface TraceMilestone {
  step: number;
  name: string;
  title: string;
  status: string;
  timestamp: string | null;
  details: Record<string, any>;
}

interface TraceResult {
  found: boolean;
  query: string;
  current_status: string;
  total_duration_seconds: number | null;
  summary: {
    photo_id: number | null;
    upload_id: string | null;
    job_id: string | null;
    filename: string | null;
    checksum: string | null;
    wedding_slug: string | null;
    cloudinary_url: string | null;
    thumbnail_url: string | null;
    last_error: string | null;
    dead_letter_reason: string | null;
  };
  milestones: TraceMilestone[];
}

export default function AdminLiveMonitor() {
  const [dashboardData, setDashboardData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [retryingDeadLetters, setRetryingDeadLetters] = useState(false);
  const [retryMessage, setRetryMessage] = useState<string | null>(null);

  // Photo Trace state
  const [traceQuery, setTraceQuery] = useState("");
  const [traceLoading, setTraceLoading] = useState(false);
  const [traceResult, setTraceResult] = useState<TraceResult | null>(null);
  const [traceError, setTraceError] = useState<string | null>(null);

  const fetchDashboard = async () => {
    try {
      setRefreshing(true);
      const res = await fetch(`${API_BASE_URL}/observability/dashboard/`);
      if (res.ok) {
        const data = await res.json();
        setDashboardData(data);
      }
    } catch (e) {
      console.error("Failed to fetch observability dashboard", e);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchDashboard();
    const interval = setInterval(fetchDashboard, 10000); // 10s auto-refresh
    return () => clearInterval(interval);
  }, []);

  const handleRetryDeadLetters = async () => {
    try {
      setRetryingDeadLetters(true);
      setRetryMessage(null);
      const res = await fetch(`${API_BASE_URL}/observability/jobs/retry-dead-letters/`, {
        method: "POST"
      });
      const data = await res.json();
      setRetryMessage(data.message || "Dead letters re-queued.");
      fetchDashboard();
    } catch (e) {
      setRetryMessage("Failed to trigger dead-letter retry.");
    } finally {
      setRetryingDeadLetters(false);
    }
  };

  const handleTraceSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!traceQuery.trim()) return;
    try {
      setTraceLoading(true);
      setTraceError(null);
      setTraceResult(null);
      const res = await fetch(`${API_BASE_URL}/observability/trace/?id=${encodeURIComponent(traceQuery.trim())}`);
      const data = await res.json();
      if (res.ok && data.found) {
        setTraceResult(data);
      } else {
        setTraceError(data.message || `No photo found matching "${traceQuery}"`);
      }
    } catch (err: any) {
      setTraceError("Error executing photo trace: " + err.message);
    } finally {
      setTraceLoading(false);
    }
  };

  const m = dashboardData?.metrics || {};
  const alerts: AlertItem[] = dashboardData?.alerts || [];
  const recentJobs: IngestionJobSummary[] = dashboardData?.recent_jobs || [];

  if (loading && !dashboardData) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <RefreshCw className="w-4 h-4 animate-spin text-primary" />
          Connecting to Observability telemetry...
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 pb-12">
      {/* Top Header Bar */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-white p-6 rounded-2xl border border-border shadow-sm">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-serif font-bold text-foreground">Production Observability & Live Monitor</h1>
            <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wider ${
              dashboardData?.service_health === "HEALTHY" ? "bg-green-100 text-green-700 border border-green-200" :
              dashboardData?.service_health === "DEGRADED" ? "bg-yellow-100 text-yellow-800 border border-yellow-200" :
              "bg-red-100 text-red-700 border border-red-200"
            }`}>
              {dashboardData?.service_health || "CHECKING"}
            </span>
          </div>
          <p className="text-xs text-muted-foreground mt-1">
            Real-time pipeline monitoring, telemetry, Cloudinary CDN usage, and photo lifecycle tracking.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={fetchDashboard}
            disabled={refreshing}
            className="flex items-center gap-2 px-3 py-1.5 text-xs font-medium rounded-lg border border-border bg-secondary hover:bg-secondary/80 text-foreground transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? "animate-spin" : ""}`} />
            Refresh
          </button>
          <div className="text-right text-xs text-muted-foreground">
            Uptime: <span className="font-mono font-medium text-foreground">{m.render?.uptime_human || "N/A"}</span>
          </div>
        </div>
      </div>

      {/* Actionable Alerts Banner */}
      {alerts.length > 0 && (
        <div className="space-y-3">
          {alerts.map((alert) => (
            <div 
              key={alert.id}
              className={`p-4 rounded-xl border flex flex-col md:flex-row items-start md:items-center justify-between gap-4 ${
                alert.severity === "CRITICAL"
                  ? "bg-red-50 border-red-200 text-red-950"
                  : "bg-amber-50 border-amber-200 text-amber-950"
              }`}
            >
              <div className="flex items-start gap-3">
                {alert.severity === "CRITICAL" ? (
                  <ShieldAlert className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
                ) : (
                  <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
                )}
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-sm">{alert.title}</span>
                    <span className={`text-[10px] uppercase font-bold px-1.5 py-0.5 rounded ${
                      alert.severity === "CRITICAL" ? "bg-red-200 text-red-800" : "bg-amber-200 text-amber-800"
                    }`}>
                      {alert.severity}
                    </span>
                  </div>
                  <p className="text-xs text-foreground/80 mt-1">{alert.description}</p>
                  <p className="text-xs font-mono font-semibold text-primary mt-1">
                    Action: {alert.action}
                  </p>
                </div>
              </div>

              {alert.id === "INGESTION_DEAD_LETTER" && (
                <button
                  onClick={handleRetryDeadLetters}
                  disabled={retryingDeadLetters}
                  className="px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white text-xs font-medium rounded-lg shrink-0 flex items-center gap-1.5 shadow-sm"
                >
                  <RotateCcw className={`w-3.5 h-3.5 ${retryingDeadLetters ? "animate-spin" : ""}`} />
                  Retry Dead-Letters
                </button>
              )}
            </div>
          ))}
          {retryMessage && (
            <div className="text-xs text-green-700 bg-green-50 p-2 rounded-lg border border-green-200">
              {retryMessage}
            </div>
          )}
        </div>
      )}

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <MetricCard 
          icon={<Server className="w-4 h-4 text-blue-600" />}
          label="API Latency (p95)"
          value={`${m.api?.p95_latency_ms || 0} ms`}
          subtext={`Avg: ${m.api?.avg_latency_ms || 0} ms`}
        />
        <MetricCard 
          icon={<Activity className="w-4 h-4 text-green-600" />}
          label="Throughput"
          value={`${m.api?.requests_per_minute || 0} RPM`}
          subtext={`Total: ${m.api?.total_requests || 0}`}
        />
        <MetricCard 
          icon={<AlertCircle className={`w-4 h-4 ${m.api?.error_rate_percent > 1 ? "text-red-600" : "text-gray-500"}`} />}
          label="5xx Error Rate"
          value={`${m.api?.error_rate_percent || 0}%`}
          subtext={`${m.api?.requests_5xx || 0} failed`}
        />
        <MetricCard 
          icon={<Wifi className="w-4 h-4 text-purple-600" />}
          label="Live WebSockets"
          value={`${m.websockets?.active_connections || 0}`}
          subtext={`Peak: ${m.websockets?.peak_connections || 0}`}
        />
        <MetricCard 
          icon={<Layers className={`w-4 h-4 ${m.queue?.backlog_count > 10 ? "text-amber-600" : "text-primary"}`} />}
          label="Queue Backlog"
          value={`${m.queue?.backlog_count || 0}`}
          subtext={`Oldest: ${m.queue?.oldest_job_age_seconds || 0}s`}
        />
        <MetricCard 
          icon={<ShieldAlert className={`w-4 h-4 ${m.queue?.dead_letter_count > 0 ? "text-red-600" : "text-gray-400"}`} />}
          label="Dead Letter Jobs"
          value={`${m.queue?.dead_letter_count || 0}`}
          subtext={`${m.queue?.failed_count || 0} retrying`}
        />
      </div>

      {/* Cloudinary & System Infrastructure Gauges */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Cloudinary CDN Usage */}
        <div className="bg-white rounded-2xl p-6 border border-border shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-sm flex items-center gap-2">
              <Cloud className="w-4 h-4 text-blue-500" />
              Cloudinary CDN Usage
            </h3>
            <span className="text-xs font-mono font-medium text-muted-foreground">
              {m.cloudinary?.account_usage?.plan || "Standard"}
            </span>
          </div>

          <div className="space-y-3 text-xs">
            <div>
              <div className="flex justify-between mb-1">
                <span className="text-muted-foreground">Monthly Credits Used</span>
                <span className="font-semibold">{m.cloudinary?.account_usage?.credits?.used_percent || 0}%</span>
              </div>
              <div className="w-full bg-secondary h-2 rounded-full overflow-hidden">
                <div 
                  className={`h-full ${
                    (m.cloudinary?.account_usage?.credits?.used_percent || 0) > 80 ? "bg-red-500" : "bg-primary"
                  }`}
                  style={{ width: `${Math.min(100, m.cloudinary?.account_usage?.credits?.used_percent || 0)}%` }}
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2 pt-2 border-t border-border">
              <div>
                <span className="text-muted-foreground block">CDN Storage</span>
                <span className="font-semibold text-foreground text-sm">
                  {m.cloudinary?.account_usage?.storage?.usage_mb || 0} MB
                </span>
              </div>
              <div>
                <span className="text-muted-foreground block">Bandwidth Delivered</span>
                <span className="font-semibold text-foreground text-sm">
                  {m.cloudinary?.account_usage?.bandwidth?.usage_mb || 0} MB
                </span>
              </div>
              <div>
                <span className="text-muted-foreground block">Transformations</span>
                <span className="font-semibold text-foreground text-sm">
                  {m.cloudinary?.account_usage?.transformations?.usage || 0}
                </span>
              </div>
              <div>
                <span className="text-muted-foreground block">Upload Success</span>
                <span className="font-semibold text-green-600 text-sm">
                  {m.cloudinary?.uploads_success || 0} / {m.cloudinary?.uploads_total || 0}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Database & NeonDB Pooler */}
        <div className="bg-white rounded-2xl p-6 border border-border shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-sm flex items-center gap-2">
              <Database className="w-4 h-4 text-purple-500" />
              NeonDB & Connection Pool
            </h3>
            <span className={`text-xs px-2 py-0.5 rounded font-mono font-medium ${
              m.database?.status === "CONNECTED" ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"
            }`}>
              {m.database?.status || "UNKNOWN"}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-3 text-xs">
            <div>
              <span className="text-muted-foreground block">Ping Latency</span>
              <span className="font-semibold text-foreground text-sm">{m.database?.ping_ms || 0} ms</span>
            </div>
            <div>
              <span className="text-muted-foreground block">Engine</span>
              <span className="font-semibold text-foreground text-sm">{m.database?.engine || "PostgreSQL"}</span>
            </div>
            <div>
              <span className="text-muted-foreground block">Published Photos</span>
              <span className="font-semibold text-foreground text-sm">{m.database_growth?.total_photos || 0}</span>
            </div>
            <div>
              <span className="text-muted-foreground block">Faces in HNSW</span>
              <span className="font-semibold text-foreground text-sm">{m.database_growth?.total_faces || 0}</span>
            </div>
            <div>
              <span className="text-muted-foreground block">Photos Last Hour</span>
              <span className="font-semibold text-foreground text-sm">{m.database_growth?.photos_added_last_hour || 0}</span>
            </div>
            <div>
              <span className="text-muted-foreground block">Slow Queries (&gt;200ms)</span>
              <span className={`font-semibold text-sm ${m.database?.slow_queries_count > 0 ? "text-amber-600" : "text-foreground"}`}>
                {m.database?.slow_queries_count || 0}
              </span>
            </div>
          </div>
        </div>

        {/* Container & Android Device Resources */}
        <div className="bg-white rounded-2xl p-6 border border-border shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-sm flex items-center gap-2">
              <Cpu className="w-4 h-4 text-amber-500" />
              Container & Companion Device
            </h3>
            <span className="text-xs font-mono text-muted-foreground">
              {m.render?.instance_id || "Render"}
            </span>
          </div>

          <div className="space-y-3 text-xs">
            <div>
              <div className="flex justify-between mb-1">
                <span className="text-muted-foreground">Render RAM Usage</span>
                <span className="font-semibold">{m.system?.memory_process_rss_mb || 0} MB ({m.system?.memory_system_used_percent || 0}%)</span>
              </div>
              <div className="w-full bg-secondary h-2 rounded-full overflow-hidden">
                <div 
                  className={`h-full ${
                    (m.system?.memory_system_used_percent || 0) > 85 ? "bg-red-500" : "bg-amber-500"
                  }`}
                  style={{ width: `${Math.min(100, m.system?.memory_system_used_percent || 0)}%` }}
                />
              </div>
            </div>

            <div className="pt-2 border-t border-border space-y-2">
              <span className="font-medium text-foreground flex items-center gap-1.5">
                <Smartphone className="w-3.5 h-3.5 text-primary" />
                Ingestion Phone Status
              </span>
              {m.android_ingestion?.devices?.length > 0 ? (
                m.android_ingestion.devices.map((d: any) => (
                  <div key={d.device_id} className="bg-secondary/50 p-2 rounded-lg flex justify-between items-center text-[11px]">
                    <div>
                      <span className="font-mono font-bold text-foreground">{d.device_id}</span>
                      <span className="text-muted-foreground ml-2">FTP: {d.ftp_status}</span>
                    </div>
                    <div className="text-right">
                      <span className={`${d.is_low_storage ? "text-red-600 font-bold" : "text-muted-foreground"}`}>
                        {d.storage_usage_mb} MB used
                      </span>
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-muted-foreground text-xs italic">
                  No companion devices reporting.
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* End-to-End Photo Lifecycle Tracer */}
      <div className="bg-white rounded-2xl p-6 border border-border shadow-sm space-y-4">
        <div>
          <h3 className="font-semibold text-base flex items-center gap-2">
            <Search className="w-4 h-4 text-primary" />
            End-to-End Photograph Lifecycle Tracer
          </h3>
          <p className="text-xs text-muted-foreground mt-0.5">
            Trace an individual photograph across the entire pipeline: Camera FTP &rarr; Android Intake &rarr; Queue &rarr; Cloudinary CDN &rarr; NeonDB &rarr; Face Recognition &rarr; WebSocket Broadcast.
          </p>
        </div>

        <form onSubmit={handleTraceSearch} className="flex gap-2">
          <input
            type="text"
            value={traceQuery}
            onChange={(e) => setTraceQuery(e.target.value)}
            placeholder="Enter upload_id, photo_id (e.g. 501), SHA-256 checksum, or filename (e.g. DSC_0042.jpg)..."
            className="flex-1 px-4 py-2 text-xs border border-border rounded-xl focus:outline-none focus:ring-2 focus:ring-primary/20"
          />
          <button
            type="submit"
            disabled={traceLoading || !traceQuery.trim()}
            className="px-4 py-2 bg-primary text-primary-foreground text-xs font-medium rounded-xl hover:bg-primary/90 transition flex items-center gap-1.5 shadow-sm"
          >
            {traceLoading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Search className="w-3.5 h-3.5" />}
            Trace Photo
          </button>
        </form>

        {traceError && (
          <div className="text-xs text-red-600 bg-red-50 p-3 rounded-xl border border-red-200">
            {traceError}
          </div>
        )}

        {traceResult && (
          <div className="mt-4 p-4 rounded-xl border border-border bg-secondary/30 space-y-4">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 border-b border-border pb-3">
              <div>
                <span className="text-xs font-semibold text-foreground">
                  Trace for: <span className="font-mono text-primary">{traceResult.summary.filename || traceResult.query}</span>
                </span>
                <span className="text-xs text-muted-foreground ml-3">
                  Status: <span className="font-bold uppercase">{traceResult.current_status}</span>
                </span>
              </div>
              <div className="text-xs text-muted-foreground">
                Total Latency: <span className="font-bold text-foreground">{traceResult.total_duration_seconds ? `${traceResult.total_duration_seconds}s` : "In-flight"}</span>
              </div>
            </div>

            {/* Trace Milestones Timeline */}
            <div className="space-y-3">
              {traceResult.milestones.map((m) => (
                <div key={m.step} className="flex items-start gap-3 text-xs bg-white p-3 rounded-lg border border-border">
                  <div className={`w-5 h-5 rounded-full flex items-center justify-center shrink-0 font-bold text-[10px] ${
                    m.status === "COMPLETED" ? "bg-green-100 text-green-700" :
                    m.status === "FAILED" ? "bg-red-100 text-red-700" :
                    m.status === "IN_PROGRESS" ? "bg-blue-100 text-blue-700 animate-pulse" :
                    "bg-gray-100 text-gray-500"
                  }`}>
                    {m.status === "COMPLETED" ? "✓" : m.step}
                  </div>
                  <div className="flex-1">
                    <div className="flex justify-between items-center">
                      <span className="font-semibold text-foreground">{m.title}</span>
                      <span className="text-[10px] text-muted-foreground font-mono">
                        {m.timestamp ? new Date(m.timestamp).toLocaleTimeString() : "Pending"}
                      </span>
                    </div>
                    <div className="text-muted-foreground text-[11px] mt-1 font-mono">
                      {Object.entries(m.details)
                        .filter(([_, v]) => v !== null && v !== undefined)
                        .map(([k, v]) => `${k}=${v}`)
                        .join(" | ")}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Recent Ingestion Stream Table */}
      <div className="bg-white rounded-2xl p-6 border border-border shadow-sm space-y-4">
        <div className="flex justify-between items-center">
          <h3 className="font-semibold text-sm flex items-center gap-2">
            <Zap className="w-4 h-4 text-primary" />
            Live Ingestion Pipeline Stream (Recent Jobs)
          </h3>
          <span className="text-xs text-muted-foreground">Auto-refreshing every 10s</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left">
            <thead className="bg-secondary/60 text-muted-foreground uppercase text-[10px]">
              <tr>
                <th className="p-2.5 rounded-l-lg">Filename</th>
                <th className="p-2.5">Folder</th>
                <th className="p-2.5">Status</th>
                <th className="p-2.5">Attempts</th>
                <th className="p-2.5">Size</th>
                <th className="p-2.5">Duration</th>
                <th className="p-2.5">Received</th>
                <th className="p-2.5 rounded-r-lg">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {recentJobs.length > 0 ? (
                recentJobs.map((job) => (
                  <tr key={job.job_id} className="hover:bg-secondary/20 transition-colors">
                    <td className="p-2.5 font-medium text-foreground">
                      <span className="font-mono">{job.filename}</span>
                    </td>
                    <td className="p-2.5 text-muted-foreground">{job.folder}</td>
                    <td className="p-2.5">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        job.status === "COMPLETED" ? "bg-green-100 text-green-700" :
                        job.status === "DEAD_LETTER" ? "bg-red-100 text-red-700" :
                        job.status === "FAILED" ? "bg-amber-100 text-amber-700" :
                        "bg-blue-100 text-blue-700"
                      }`}>
                        {job.status}
                      </span>
                    </td>
                    <td className="p-2.5">{job.attempts}</td>
                    <td className="p-2.5 text-muted-foreground">{job.file_size_kb} KB</td>
                    <td className="p-2.5 font-mono">{job.duration_seconds ? `${job.duration_seconds}s` : "-"}</td>
                    <td className="p-2.5 text-muted-foreground">
                      {job.received_at ? new Date(job.received_at).toLocaleTimeString() : "-"}
                    </td>
                    <td className="p-2.5">
                      <button
                        onClick={() => {
                          setTraceQuery(job.upload_id || job.job_id);
                          window.scrollTo({ top: 500, behavior: "smooth" });
                        }}
                        className="text-primary hover:underline font-medium text-[11px]"
                      >
                        Trace
                      </button>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={8} className="p-4 text-center text-muted-foreground italic">
                    No ingestion jobs recorded yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function MetricCard({ icon, label, value, subtext }: { icon: React.ReactNode; label: string; value: string; subtext: string }) {
  return (
    <div className="bg-white p-4 rounded-xl border border-border shadow-sm space-y-1">
      <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
        {icon}
        <span>{label}</span>
      </div>
      <div className="text-xl font-bold font-serif text-foreground">{value}</div>
      <div className="text-[10px] text-muted-foreground">{subtext}</div>
    </div>
  );
}
