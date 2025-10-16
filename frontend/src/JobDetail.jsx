import { useState, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import axios from "axios";

function JobDetail() {
  const { jobId } = useParams();
  const navigate = useNavigate();
  const [job, setJob] = useState(null);
  const [gpuInfo, setGpuInfo] = useState(null);
  const [logs, setLogs] = useState("");
  const logsEndRef = useRef(null);

  useEffect(() => {
    fetchJobDetails();

    const interval = setInterval(() => {
      fetchJobDetails();
      fetchLogs();
    }, 2000);

    return () => clearInterval(interval);
  }, [jobId]);

  useEffect(() => {
    // Auto-scroll to bottom when logs update
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  const fetchJobDetails = async () => {
    try {
      const response = await axios.get(`/api/jobs/${jobId}`);
      setJob(response.data.job);
      setGpuInfo(response.data.gpu_info);
    } catch (error) {
      console.error("Error fetching job details:", error);
    }
  };

  const fetchLogs = async () => {
    try {
      const response = await axios.get(`/api/jobs/${jobId}/logs`);
      setLogs(response.data.logs);
    } catch (error) {
      console.error("Error fetching logs:", error);
    }
  };

  const handleCancelJob = async () => {
    if (!confirm("Are you sure you want to cancel this job?")) {
      return;
    }

    try {
      await axios.post(`/api/jobs/${jobId}/cancel`);
      fetchJobDetails();
    } catch (error) {
      console.error("Error cancelling job:", error);
      alert("Error cancelling job");
    }
  };

  const handleDownload = async () => {
    try {
      const response = await axios.get(`/api/jobs/${jobId}/download`, {
        responseType: "blob",
      });

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `${jobId}_output.zip`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (error) {
      console.error("Error downloading output:", error);
      alert("Error downloading output");
    }
  };

  const formatBytes = (bytes) => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB", "TB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + " " + sizes[i];
  };

  const formatDate = (dateString) => {
    if (!dateString) return "N/A";
    return new Date(dateString).toLocaleString();
  };

  if (!job) {
    return (
      <div className="job-detail">
        <div className="header">
          <h1>Loading...</h1>
        </div>
      </div>
    );
  }

  return (
    <div className="job-detail">
      <div className="sticky-header">
        <button className="secondary" onClick={() => navigate("/")}>
          ← Back to Dashboard
        </button>
        <h1>{job.name}</h1>
      </div>

      <div className="detail-grid">
        <div className="section">
          <h2>Job Information</h2>
          <div className="info-card">
            <div className="info-row">
              <span className="info-label">Job ID:</span>
              <span className="info-value">{job.id}</span>
            </div>
            <div className="info-row">
              <span className="info-label">Name:</span>
              <span className="info-value">{job.name}</span>
            </div>
            <div className="info-row">
              <span className="info-label">Status:</span>
              <span className="info-value">
                <span className={`status-badge status-${job.status}`}>
                  {job.status}
                </span>
              </span>
            </div>
            <div className="info-row">
              <span className="info-label">Resource:</span>
              <span className="info-value">{job.resource}</span>
            </div>
            <div className="info-row">
              <span className="info-label">Docker Image:</span>
              <span className="info-value">{job.docker_image}</span>
            </div>
            <div className="info-row">
              <span className="info-label">Created:</span>
              <span className="info-value">{formatDate(job.created_at)}</span>
            </div>
            <div className="info-row">
              <span className="info-label">Started:</span>
              <span className="info-value">{formatDate(job.started_at)}</span>
            </div>
            <div className="info-row">
              <span className="info-label">Completed:</span>
              <span className="info-value">{formatDate(job.completed_at)}</span>
            </div>
            {job.error && (
              <div className="info-row">
                <span className="info-label">Error:</span>
                <span className="info-value" style={{ color: "red" }}>
                  {job.error}
                </span>
              </div>
            )}
          </div>

          <div style={{ marginTop: "15px", display: "flex", gap: "10px" }}>
            {(job.status === "pending" || job.status === "running") && (
              <button className="danger" onClick={handleCancelJob}>
                Cancel Job
              </button>
            )}
            {job.status === "completed" && (
              <button className="success" onClick={handleDownload}>
                Download Output
              </button>
            )}
          </div>
        </div>

        {gpuInfo && (
          <div className="section">
            <h2>GPU Information</h2>
            <div className="info-card">
              <h3>{gpuInfo.name}</h3>
              <div className="info-row">
                <span className="info-label">GPU ID:</span>
                <span className="info-value">{gpuInfo.id}</span>
              </div>
              <div className="info-row">
                <span className="info-label">Total Memory:</span>
                <span className="info-value">
                  {formatBytes(gpuInfo.memory_total)}
                </span>
              </div>
              <div className="info-row">
                <span className="info-label">Used Memory:</span>
                <span className="info-value">
                  {formatBytes(gpuInfo.memory_used)}
                </span>
              </div>
              <div className="info-row">
                <span className="info-label">Free Memory:</span>
                <span className="info-value">
                  {formatBytes(gpuInfo.memory_free)}
                </span>
              </div>
              <div className="info-row">
                <span className="info-label">Utilization:</span>
                <span className="info-value">{gpuInfo.utilization}%</span>
              </div>
              <div className="progress-bar" style={{ marginTop: "10px" }}>
                <div
                  className="progress-fill"
                  style={{ width: `${gpuInfo.utilization}%` }}
                />
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="section">
        <h2>Console Output</h2>
        <div className="logs-container">
          {logs || "No logs yet..."}
          <div ref={logsEndRef} />
        </div>
      </div>
    </div>
  );
}

export default JobDetail;
