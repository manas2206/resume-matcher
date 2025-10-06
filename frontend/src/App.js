// frontend/src/App.js
import React, { useState, useEffect } from "react";

const API_BASE = "http://localhost:8000";

function ConfirmModal({ open, title, message, onConfirm, onCancel }) {
  if (!open) return null;
  return (
    <div style={{
      position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)",
      display: "flex", alignItems: "center", justifyContent: "center", zIndex: 9999
    }}>
      <div style={{
        background: "#fff", padding: "24px 28px", borderRadius: 12,
        width: 420, boxShadow: "0 8px 30px rgba(0,0,0,0.2)"
      }}>
        <h2 style={{ marginTop: 0 }}>{title}</h2>
        <p style={{ color: "#444", fontSize: 15 }}>{message}</p>
        <div style={{ display: "flex", justifyContent: "flex-end", gap: 12, marginTop: 20 }}>
          <button
            onClick={onCancel}
            style={{
              background: "#ddd", border: "none", padding: "8px 14px",
              borderRadius: 6, cursor: "pointer"
            }}
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            style={{
              background: "#d9534f", color: "#fff", border: "none",
              padding: "8px 14px", borderRadius: 6, cursor: "pointer"
            }}
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  );
}

export default function App() {
  const [jd, setJd] = useState("");
  const [files, setFiles] = useState([]);
  const [matches, setMatches] = useState([]);
  const [message, setMessage] = useState("");
  const [resumes, setResumes] = useState([]);
  const [loadingResumes, setLoadingResumes] = useState(false);
  const [modal, setModal] = useState({ open: false, id: null, filename: "" });

  useEffect(() => {
    fetchResumes();
  }, []);

  async function fetchResumes() {
    setLoadingResumes(true);
    try {
      const resp = await fetch(`${API_BASE}/resumes/`);
      const j = await resp.json();
      setResumes(j.resumes || []);
    } catch (err) {
      setMessage("Error fetching resumes: " + err.message);
    } finally {
      setLoadingResumes(false);
    }
  }

  async function uploadResumes() {
    if (!files.length) {
      setMessage("Select one or more resume files first.");
      return;
    }
    setMessage("Uploading...");
    for (let f of files) {
      const form = new FormData();
      form.append("file", f);
      await fetch(`${API_BASE}/resumes/upload`, { method: "POST", body: form });
    }
    setMessage("Upload complete.");
    fetchResumes();
  }

  async function uploadJob() {
    if (!jd.trim()) return setMessage("Enter JD text first.");
    setMessage("Uploading JD...");
    const body = { title: "Uploaded JD", description: jd };
    await fetch(`${API_BASE}/jobs/upload`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    });
    setMessage("Job uploaded. Click 'Get Top Matches'.");
  }

  async function getMatches() {
    setMessage("Fetching matches...");
    const resp = await fetch(`${API_BASE}/match/top?n=10`);
    const j = await resp.json();
    setMatches(j.matches || []);
    setMessage("Matches retrieved.");
  }

  async function confirmDelete() {
    const id = modal.id;
    setModal({ open: false, id: null, filename: "" });
    await fetch(`${API_BASE}/resumes/${id}`, { method: "DELETE" });
    setMessage("Resume deleted.");
    fetchResumes();
    if (matches.length) getMatches();
  }

  return (
    <div style={{
      minHeight: "100vh", background: "#f8fafc",
      padding: "30px 50px", fontFamily: "Segoe UI, Roboto, sans-serif"
    }}>
      <h1 style={{ textAlign: "center", marginBottom: 30 }}>📄 Resume Matcher</h1>

      <div style={{
        display: "grid", gridTemplateColumns: "2fr 1fr", gap: 24,
        maxWidth: 1200, margin: "0 auto"
      }}>
        {/* Left Panel */}
        <div>
          <div style={{
            background: "#fff", padding: 20, borderRadius: 12,
            boxShadow: "0 2px 10px rgba(0,0,0,0.08)", marginBottom: 20
          }}>
            <h3>1️⃣ Upload Resumes</h3>
            <input type="file" multiple onChange={(e) => setFiles(e.target.files)} />
            <button style={btn} onClick={uploadResumes}>Upload</button>
          </div>

          <div style={{
            background: "#fff", padding: 20, borderRadius: 12,
            boxShadow: "0 2px 10px rgba(0,0,0,0.08)", marginBottom: 20
          }}>
            <h3>2️⃣ Upload Job Description</h3>
            <textarea
              value={jd} onChange={(e) => setJd(e.target.value)}
              rows={6} style={{
                width: "100%", padding: 10, borderRadius: 6,
                border: "1px solid #ccc", resize: "vertical"
              }}
              placeholder="Paste job description here..."
            />
            <div style={{ marginTop: 8 }}>
              <button style={btn} onClick={uploadJob}>Upload JD</button>
              <button style={{ ...btn, background: "#2563eb" }} onClick={getMatches}>
                Get Top Matches
              </button>
            </div>
          </div>

          <div style={{
            background: "#fff", padding: 20, borderRadius: 12,
            boxShadow: "0 2px 10px rgba(0,0,0,0.08)"
          }}>
            <h3>📊 Results</h3>
            {matches.length === 0 && <p style={{ color: "#555" }}>No matches yet.</p>}
            {matches.map((m) => (
              <div key={m.id} style={{
                background: "#f9f9f9", borderRadius: 8,
                padding: 12, marginBottom: 10
              }}>
                <strong>{m.filename}</strong> — score: {m.score.toFixed(3)}
                <div style={{
                  marginTop: 6, fontSize: 14, background: "#f1f5f9",
                  padding: "6px 8px", borderRadius: 6
                }}>{m.snippet}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Right Panel */}
        <div>
          <div style={{
            background: "#fff", padding: 20, borderRadius: 12,
            boxShadow: "0 2px 10px rgba(0,0,0,0.08)", marginBottom: 20
          }}>
            <h3>📂 Indexed Resumes</h3>
            {loadingResumes && <p>Loading...</p>}
            {!loadingResumes && resumes.length === 0 && <p>No resumes indexed.</p>}
            <table style={{ width: "100%", fontSize: 14, borderSpacing: 0 }}>
              <tbody>
                {resumes.map((r) => (
                  <tr key={r.id} style={{ borderBottom: "1px solid #eee" }}>
                    <td style={{ padding: "8px 0" }}>{r.filename}</td>
                    <td style={{ textAlign: "right" }}>
                      <button style={delBtn} onClick={() => setModal({ open: true, id: r.id, filename: r.filename })}>
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div style={{
            background: "#fff", padding: 20, borderRadius: 12,
            boxShadow: "0 2px 10px rgba(0,0,0,0.08)"
          }}>
            <h3>ℹ Messages</h3>
            <p style={{
              color: message.startsWith("Error") ? "crimson" : "green",
              minHeight: 40
            }}>{message}</p>
          </div>
        </div>
      </div>

      <ConfirmModal
        open={modal.open}
        title="Confirm Delete"
        message={`Delete resume "${modal.filename}"? This cannot be undone.`}
        onConfirm={confirmDelete}
        onCancel={() => setModal({ open: false, id: null, filename: "" })}
      />
    </div>
  );
}

// Button styles
const btn = {
  background: "#10b981", color: "white", border: "none",
  padding: "8px 14px", marginLeft: 8, borderRadius: 6, cursor: "pointer"
};

const delBtn = {
  background: "#f87171", color: "white", border: "none",
  padding: "4px 10px", borderRadius: 6, cursor: "pointer", fontSize: 13
};
