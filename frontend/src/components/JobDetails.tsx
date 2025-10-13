import { useState, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { jobAPI, createWebSocket } from "../services/api";
import type { Job, GPUStats } from "../services/api";
import "./JobDetails.css";

interface JobDetailsProps {
  onLogout: () => void;
}

function JobDetails({ onLogout }: JobDetailsProps) {
  const { jobId } = useParams<{ jobId: string }>();
  const [job, setJob] = useState<Job | null>(null);
  const [logs, setLogs] = useState("");
  const [gpuStats, setGpuStats] = useState<GPUStats | null>(null);
  const [loading, setLoading] = useState(true);
  const wsRef = useRef<WebSocket | null>(null);
  const logsEndRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (!jobId) return;

    loadJob();
    connectWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [jobId]);

  useEffect(() => {
    // Auto-scroll logs to bottom
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  const loadJob = async () => {
    try {
      const response = await jobAPI.getJob(Number(jobId));
      setJob(response.data);
    } catch (err) {
      console.error("Error loading job:", err);
    } finally {
      setLoading(false);
    }
  };

  const connectWebSocket = () => {
    const ws = createWebSocket(Number(jobId));

    ws.onopen = () => {
      console.log("WebSocket connected");
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.status) {
        setJob((prev) => (prev ? { ...prev, status: data.status } : null));
      }

      if (data.gpu_stats) {
        setGpuStats(data.gpu_stats);
      }

      if (data.logs) {
        setLogs(data.logs);
      }
    };

    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
    };

    ws.onclose = () => {
      console.log("WebSocket disconnected");
      // Reconnect after 5 seconds if job is still running
      setTimeout(() => {
        if (job?.status === "running") {
          connectWebSocket();
        }
      }, 5000);
    };

    wsRef.current = ws;
  };

  const handleCancel = async () => {
    if (confirm("Are you sure you want to cancel this job?")) {
      try {
        await jobAPI.cancelJob(Number(jobId));
        loadJob();
      } catch (err) {
        alert("Error canceling job");
      }
    }
  };

  const handleDownload = () => {
    jobAPI.downloadOutput(Number(jobId));
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "completed":
        return "green";
      case "running":
        return "blue";
      case "failed":
        return "red";
      case "cancelled":
        return "gray";
      default:
        return "orange";
    }
  };

  if (loading) {
    return <div className="loading">Loading...</div>;
  }

  if (!job) {
    return <div className="error">Job not found</div>;
  }

  return (
    <div className="job-details">
      <header>
        <div>
          <button onClick={() => navigate("/")} className="back-btn">
            ← Back
          </button>
          <h1>Job: {job.name}</h1>
        </div>
        <button onClick={onLogout}>Logout</button>
      </header>

      <div className="job-info-section">
        <div className="info-card">
          <h2>Job Information</h2>
          <div className="info-grid">
            <div>
              <label>Status</label>
              <span
                className="status-badge"
                style={{ backgroundColor: getStatusColor(job.status) }}
              >
                {job.status}
              </span>
            </div>
            <div>
              <label>GPU</label>
              <span>GPU {job.gpu_id}</span>
            </div>
            <div>
              <label>CPU Cores</label>
              <span>{job.cpu_cores}</span>
            </div>
            <div>
              <label>Created</label>
              <span>{new Date(job.created_at).toLocaleString()}</span>
            </div>
            {job.started_at && (
              <div>
                <label>Started</label>
                <span>{new Date(job.started_at).toLocaleString()}</span>
              </div>
            )}
            {job.completed_at && (
              <div>
                <label>Completed</label>
                <span>{new Date(job.completed_at).toLocaleString()}</span>
              </div>
            )}
          </div>

          <div className="actions">
            {job.status === "completed" && (
              <button onClick={handleDownload} className="primary">
                Download Output
              </button>
            )}
            {(job.status === "pending" || job.status === "running") && (
              <button onClick={handleCancel} className="danger">
                Cancel Job
              </button>
            )}
          </div>
        </div>

        {gpuStats && job.status === "running" && (
          <div className="info-card">
            <h2>GPU Statistics</h2>
            <div className="gpu-stats">
              <div className="stat">
                <label>Utilization</label>
                <div className="stat-bar">
                  <div
                    className="stat-fill"
                    style={{ width: `${gpuStats.utilization}%` }}
                  />
                </div>
                <span>{gpuStats.utilization.toFixed(1)}%</span>
              </div>
              <div className="stat">
                <label>Memory</label>
                <div className="stat-bar">
                  <div
                    className="stat-fill"
                    style={{
                      width: `${
                        (gpuStats.memory_used / gpuStats.memory_total) * 100
                      }%`,
                    }}
                  />
                </div>
                <span>
                  {gpuStats.memory_used} / {gpuStats.memory_total} MB
                </span>
              </div>
              <div className="stat">
                <label>Temperature</label>
                <span className="temp">
                  {gpuStats.temperature.toFixed(1)}°C
                </span>
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="logs-section">
        <h2>Training Logs</h2>
        <div className="logs-container">
          <pre>{logs || "No logs available yet..."}</pre>
          <div ref={logsEndRef} />
        </div>
      </div>

      {job.error_log && (
        <div className="error-section">
          <h2>Error Log</h2>
          <pre className="error-log">{job.error_log}</pre>
        </div>
      )}
    </div>
  );
}

export default JobDetails;
