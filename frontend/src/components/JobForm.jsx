import { useState } from "react";
import axios from "axios";

function JobForm({ gpus, dockerImages, onClose, fetchJobs }) {
  const [selectedFile, setSelectedFile] = useState(null);
  const [resource, setResource] = useState("cpu");
  const [dockerImage, setDockerImage] = useState("pytorch/pytorch:latest");

  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);

  const handleFileChange = (e) => {
    setSelectedFile(e.target.files[0]);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!selectedFile) {
      alert("Please select a file");
      return;
    }

    setUploading(true);
    setUploadProgress(0);

    const formData = new FormData();
    formData.append("file", selectedFile);
    formData.append("resource", resource);
    formData.append("docker_image", dockerImage);

    try {
      await axios.post("/api/jobs", formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
        onUploadProgress: (progressEvent) => {
          const progress = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          );
          setUploadProgress(progress);
        },
        timeout: 7200000, // 2 hours timeout
      });

      setSelectedFile(null);
      document.getElementById("file-input").value = "";
      fetchJobs();
    } catch (error) {
      console.error("Error creating job:", error);
      alert(
        `Error creating job: ${error.response?.data?.detail || error.message}`
      );
    } finally {
      setUploading(false);
      setUploadProgress(0);
      onClose();
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

        <form onSubmit={handleSubmit} className="upload-form">
          <div className="form-group">
            <label htmlFor="file-input">Upload ZIP File:</label>
            <input
              id="file-input"
              type="file"
              accept=".zip"
              onChange={handleFileChange}
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="resource-select">Resource:</label>
            <select
              id="resource-select"
              value={resource}
              onChange={(e) => setResource(e.target.value)}
            >
              <option value="cpu">CPU</option>
              {gpus.map((gpu) => (
                <option key={gpu.id} value={`gpu:${gpu.id}`}>
                  GPU {gpu.id} ({gpu.name})
                </option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="docker-select">Docker Image:</label>
            <select
              id="docker-select"
              value={dockerImage}
              onChange={(e) => setDockerImage(e.target.value)}
            >
              {dockerImages.map((image) => (
                <option key={image} value={image}>
                  {image}
                </option>
              ))}
            </select>
          </div>

          {uploading && (
            <div className="upload-progress-bar">
              <div
                className="upload-progress-fill"
                style={{
                  width: `${uploadProgress}%`,
                }}
              >
                {uploadProgress}%
              </div>
            </div>
          )}

          <button type="submit" disabled={uploading}>
            {uploading ? "Uploading..." : "Create Job"}
          </button>
        </form>
      </div>
    </div>
  );
}

export { JobForm };
