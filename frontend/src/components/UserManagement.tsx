import { useState, useEffect } from "react";
import { userAPI } from "../services/api";
import type { User } from "../services/api";
import "./UserManagement.css";

interface UserManagementProps {
  onClose: () => void;
}

function UserManagement({ onClose }: UserManagementProps) {
  const [users, setUsers] = useState<User[]>([]);
  const [showAddUser, setShowAddUser] = useState(false);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadUsers();
  }, []);

  const loadUsers = async () => {
    try {
      const response = await userAPI.getUsers();
      setUsers(response.data);
    } catch (err) {
      console.error("Error loading users:", err);
    }
  };

  const handleAddUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      await userAPI.createUser(username, password);
      setUsername("");
      setPassword("");
      setShowAddUser(false);
      loadUsers();
    } catch (err: any) {
      setError(err.response?.data?.detail || "Error creating user");
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteUser = async (userId: number, username: string) => {
    if (confirm(`Are you sure you want to delete user "${username}"?`)) {
      try {
        await userAPI.deleteUser(userId);
        loadUsers();
      } catch (err: any) {
        alert(err.response?.data?.detail || "Error deleting user");
      }
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>User Management</h2>
          <button className="close-btn" onClick={onClose}>
            ×
          </button>
        </div>

        <div className="user-list">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Username</th>
                <th>Created</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.id}>
                  <td>{user.id}</td>
                  <td>{user.username}</td>
                  <td>{new Date(user.created_at).toLocaleString()}</td>
                  <td>
                    <button
                      onClick={() => handleDeleteUser(user.id, user.username)}
                      className="danger small"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {!showAddUser ? (
          <button
            onClick={() => setShowAddUser(true)}
            className="primary"
            style={{ marginTop: "20px" }}
          >
            Add New User
          </button>
        ) : (
          <div className="add-user-form">
            <h3>Add New User</h3>
            {error && <div className="error">{error}</div>}
            <form onSubmit={handleAddUser}>
              <input
                type="text"
                placeholder="Username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
              />
              <input
                type="password"
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
              <div className="form-actions">
                <button
                  type="button"
                  onClick={() => {
                    setShowAddUser(false);
                    setError("");
                  }}
                  disabled={loading}
                >
                  Cancel
                </button>
                <button type="submit" className="primary" disabled={loading}>
                  {loading ? "Creating..." : "Create User"}
                </button>
              </div>
            </form>
          </div>
        )}
      </div>
    </div>
  );
}

export default UserManagement;
