import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { JobForm } from "./components/JobForm";

function App() {
  const [jobs, setJobs] = useState([]);
  const [gpus, setGpus] = useState([]);

  const [showJobForm, setShowJobForm] = useState(false);

  const navigate = useNavigate();

  const dockerImages = [
    "pytorch/pytorch:2.9.1-cuda12.6-cudnn9-runtime",
    "pytorch/pytorch:2.9.1-cuda12.8-cudnn9-runtime",
    "pytorch/pytorch:2.9.1-cuda13.0-cudnn9-runtime",
    "pytorch/pytorch:2.9.1-cuda13.0-cudnn9-devel",
    "tensorflow/tensorflow:latest-gpu",
    "tensorflow/tensorflow:latest-devel-gpu",
    "tensorflow/tensorflow:latest",
    "tensorflow/tensorflow:latest-devel",
    "python:latest",
    "python:3.12-alpine",
    "python:3.11-alpine",
  ];

  useEffect(() => {
    fetchJobs();
    fetchGPUs();

    const interval = setInterval(() => {
      fetchJobs();
      fetchGPUs();
    }, 3000);

    return () => clearInterval(interval);
  }, []);

  const fetchJobs = async () => {
    try {
      const response = await axios.get("/api/jobs");
      setJobs(response.data.jobs);
    } catch (error) {
      console.error("Error fetching jobs:", error);
    }
  };

  const fetchGPUs = async () => {
    try {
      const response = await axios.get("/api/gpus");
      setGpus(response.data.gpus);
    } catch (error) {
      console.error("Error fetching GPUs:", error);
    }
  };

  const handleCancelJob = async (jobId, e) => {
    e.stopPropagation();

    if (!confirm("Are you sure you want to cancel this job?")) {
      return;
    }

    try {
      await axios.post(`/api/jobs/${jobId}/cancel`);
      fetchJobs();
    } catch (error) {
      console.error("Error cancelling job:", error);
      alert("Error cancelling job");
    }
  };

  const handleDownload = async (jobId, e) => {
    e.stopPropagation();

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

  return (
    <div className="container">
      <div className="header">
        <h1>ML Training Job Queue</h1>
      </div>

      <div className="section">
        <h2>Available GPUs</h2>
        {gpus.length === 0 ? (
          <p className="muted-text">No GPUs detected</p>
        ) : (
          <div className="gpu-grid">
            {gpus.map((gpu) => (
              <div key={gpu.id} className="gpu-card">
                <h3>
                  GPU {gpu.id}: {gpu.name}
                </h3>
                <div className="gpu-info">
                  <div className="gpu-info-row">
                    <span>Total Memory:</span>
                    <span>{formatBytes(gpu.memory_total)}</span>
                  </div>
                  <div className="gpu-info-row">
                    <span>Used Memory:</span>
                    <span>{formatBytes(gpu.memory_used)}</span>
                  </div>
                  <div className="gpu-info-row">
                    <span>Free Memory:</span>
                    <span>{formatBytes(gpu.memory_free)}</span>
                  </div>
                  <div className="gpu-info-row">
                    <span>Utilization:</span>
                    <span>{gpu.utilization}%</span>
                  </div>
                  <div className="progress-bar">
                    <div
                      className="progress-fill"
                      style={{ width: `${gpu.utilization}%` }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="section">
        <h2>Jobs</h2>
        <button onClick={() => setShowJobForm(true)}>Create Job</button>
        {jobs.length === 0 ? (
          <p className="muted-text">No jobs yet</p>
        ) : (
          <table className="jobs-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Status</th>
                <th>Resource</th>
                <th>Created</th>
                <th>Started</th>
                <th>Completed</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((job) => (
                <tr key={job.id} onClick={() => navigate(`/jobs/${job.id}`)}>
                  <td>{job.name}</td>
                  <td>
                    <span className={`status-badge status-${job.status}`}>
                      {job.status}
                    </span>
                  </td>
                  <td>{job.resource}</td>
                  <td>{formatDate(job.created_at)}</td>
                  <td>{formatDate(job.started_at)}</td>
                  <td>{formatDate(job.completed_at)}</td>
                  <td>
                    <div className="action-buttons">
                      {(job.status === "pending" ||
                        job.status === "running") && (
                        <button
                          className="danger"
                          onClick={(e) => handleCancelJob(job.id, e)}
                        >
                          Cancel
                        </button>
                      )}
                      {job.status === "completed" && (
                        <button
                          className="success"
                          onClick={(e) => handleDownload(job.id, e)}
                        >
                          Download
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showJobForm && (
        <JobForm
          gpus={gpus}
          dockerImages={dockerImages}
          onClose={() => setShowJobForm(false)}
          fetchJobs={fetchJobs}
        />
      )}
    </div>
  );
}

export default App;
