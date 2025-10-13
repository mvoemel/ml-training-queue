import { useState } from "react";
import { jobAPI } from "../services/api";
import type { GPU } from "../services/api";
import "./JobForm.css";

interface JobFormProps {
  gpus: GPU[];
  onClose: () => void;
  onJobCreated: () => void;
}

function JobForm({ gpus, onClose, onJobCreated }: JobFormProps) {
  const [name, setName] = useState("");
  const [gpuId, setGpuId] = useState(gpus[0]?.id || 0);
  const [dataset, setDataset] = useState<File | null>(null);
  const [script, setScript] = useState<File | null>(null);
  const [requirements, setRequirements] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!dataset || !script || !requirements) {
      setError("Please select all required files");
      return;
    }

    setUploading(true);
    setError("");

    try {
      const formData = new FormData();
      formData.append("name", name);
      formData.append("gpu_id", gpuId.toString());
      formData.append("dataset", dataset);
      formData.append("script", script);
      formData.append("requirements", requirements);

      await jobAPI.createJob(formData, (progress) => {
        setUploadProgress(progress);
      });

      onJobCreated();
    } catch (err: any) {
      setError(err.response?.data?.detail || "Error creating job");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Create New Job</h2>
          <button className="close-btn" onClick={onClose}>
            ×
          </button>
        </div>

        {error && <div className="error">{error}</div>}

        <div className="form-description">
          <p>
            It is assumed that the <code>.py</code> file is run next to the
            dataset folder, with relative path <code>./dataset</code>.
          </p>
          <p>
            The python file runs in a <code>Docker</code> container using either
            the <code>pytorch/pytorch:latest</code> or the{" "}
            <code>tensorflow/tensorflow:latest-gpu</code> image depending what
            is defined in the <code>requirements.txt</code> file. If both
            packets are defined it prefers <code>tensorflow</code>, if none are
            defined it defaults to <code>pytorch</code>.
          </p>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Job Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              placeholder="e.g., MNIST Training"
            />
          </div>

          <div className="form-group">
            <label>GPU</label>
            <select
              value={gpuId}
              onChange={(e) => setGpuId(Number(e.target.value))}
            >
              {gpus.map((gpu) => (
                <option key={gpu.id} value={gpu.id}>
                  GPU {gpu.id} - {gpu.name} ({Math.round(gpu.memory / 1024)} GB)
                </option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label>Dataset (ZIP file)</label>
            <input
              type="file"
              accept=".zip"
              onChange={(e) => setDataset(e.target.files?.[0] || null)}
              required
            />
            {dataset && (
              <p className="file-info">
                {dataset.name} ({(dataset.size / 1024 / 1024).toFixed(2)} MB)
              </p>
            )}
          </div>

          <div className="form-group">
            <label>Training Script (Python file)</label>
            <input
              type="file"
              accept=".py"
              onChange={(e) => setScript(e.target.files?.[0] || null)}
              required
            />
            {script && <p className="file-info">{script.name}</p>}
          </div>

          <div className="form-group">
            <label>Requirements (requirements.txt)</label>
            <input
              type="file"
              accept=".txt"
              onChange={(e) => setRequirements(e.target.files?.[0] || null)}
              required
            />
            {requirements && <p className="file-info">{requirements.name}</p>}
          </div>

          {uploading && (
            <div className="upload-progress">
              <div className="progress-bar">
                <div
                  className="progress-fill"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
              <p>Uploading: {uploadProgress}%</p>
            </div>
          )}

          <div className="form-actions">
            <button type="button" onClick={onClose} disabled={uploading}>
              Cancel
            </button>
            <button type="submit" className="primary" disabled={uploading}>
              {uploading ? "Creating..." : "Create Job"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default JobForm;
