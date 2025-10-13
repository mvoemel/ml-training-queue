import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { jobAPI, gpuAPI } from "../services/api";
import type { Job, GPU } from "../services/api";
import JobForm from "./JobForm";
import UserManagement from "./UserManagement";
import "./Dashboard.css";

interface DashboardProps {
  onLogout: () => void;
}

function Dashboard({ onLogout }: DashboardProps) {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [gpus, setGPUs] = useState<GPU[]>([]);
  const [showJobForm, setShowJobForm] = useState(false);
  const [showUserManagement, setShowUserManagement] = useState(false);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 5000); // Refresh every 5 seconds
    return () => clearInterval(interval);
  }, []);

  const loadData = async () => {
    try {
      const [jobsRes, gpusRes] = await Promise.all([
        jobAPI.getJobs(),
        gpuAPI.getGPUs(),
      ]);
      setJobs(jobsRes.data);
      setGPUs(gpusRes.data);
    } catch (err) {
      console.error("Error loading data:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleCancelJob = async (jobId: number) => {
    if (confirm("Are you sure you want to cancel this job?")) {
      try {
        await jobAPI.cancelJob(jobId);
        loadData();
      } catch {
        alert("Error canceling job");
      }
    }
  };

  const handleDownload = (jobId: number) => {
    jobAPI.downloadOutput(jobId);
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

  return (
    <div className="dashboard">
      <header>
        <h1>ML Training Queue</h1>
        <div className="header-buttons">
          <button onClick={() => setShowUserManagement(true)}>
            Manage Users
          </button>
          <button onClick={() => setShowJobForm(true)} className="primary">
            New Job
          </button>
          <button onClick={onLogout}>Logout</button>
        </div>
      </header>

      <div className="gpu-overview">
        <h2>GPUs</h2>
        <div className="gpu-grid">
          {gpus.map((gpu) => (
            <div key={gpu.id} className="gpu-card">
              <h3>GPU {gpu.id}</h3>
              <p>{gpu.name}</p>
              <p>{Math.round(gpu.memory / 1024)} GB</p>
              <span
                className={gpu.available ? "status-available" : "status-busy"}
              >
                {gpu.available ? "Available" : "Busy"}
              </span>
            </div>
          ))}
        </div>
      </div>

      <div className="jobs-section">
        <h2>Jobs</h2>
        {jobs.length === 0 ? (
          <p className="no-jobs">No jobs yet!</p>
        ) : (
          <div className="jobs-table">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Name</th>
                  <th>Status</th>
                  <th>GPU</th>
                  <th>Created</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {jobs.map((job) => (
                  <tr key={job.id} onClick={() => navigate(`/jobs/${job.id}`)}>
                    <td>{job.id}</td>
                    <td>{job.name}</td>
                    <td>
                      <span
                        className="status-badge"
                        style={{ backgroundColor: getStatusColor(job.status) }}
                      >
                        {job.status}
                      </span>
                    </td>
                    <td>{job.gpu_id}</td>
                    <td>{new Date(job.created_at).toLocaleString()}</td>
                    <td onClick={(e) => e.stopPropagation()}>
                      {job.status === "completed" && (
                        <button
                          onClick={() => handleDownload(job.id)}
                          className="small"
                        >
                          Download
                        </button>
                      )}
                      {(job.status === "pending" ||
                        job.status === "running") && (
                        <button
                          onClick={() => handleCancelJob(job.id)}
                          className="small danger"
                        >
                          Cancel
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {showJobForm && (
        <JobForm
          gpus={gpus}
          onClose={() => setShowJobForm(false)}
          onJobCreated={() => {
            setShowJobForm(false);
            loadData();
          }}
        />
      )}

      {showUserManagement && (
        <UserManagement onClose={() => setShowUserManagement(false)} />
      )}
    </div>
  );
}

export default Dashboard;
