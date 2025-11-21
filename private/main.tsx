import React from "react";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

// Simple enterprise version - just display the message
const EnterpriseApp = () => {
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        height: "100vh",
        backgroundColor: "#1a1a2e",
        color: "#eee",
        fontFamily: "system-ui, -apple-system, sans-serif",
      }}
    >
      <div style={{ textAlign: "center" }}>
        <h1
          style={{
            fontSize: "3rem",
            marginBottom: "1rem",
            background: "linear-gradient(45deg, #667eea 0%, #764ba2 100%)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
            backgroundClip: "text",
          }}
        >
          🏢 This is Enterprise Ragbits
        </h1>
        <p
          style={{
            fontSize: "1.2rem",
            opacity: 0.8,
            marginTop: "2rem",
          }}
        >
          Enterprise features and authentication enabled
        </p>
        <div
          style={{
            marginTop: "2rem",
            padding: "1rem",
            backgroundColor: "rgba(102, 126, 234, 0.1)",
            borderRadius: "8px",
            border: "1px solid rgba(102, 126, 234, 0.3)",
          }}
        >
          <p style={{ margin: 0, fontSize: "0.9rem" }}>
            Build Type: <strong>ENTERPRISE</strong>
            <br />
            Version: <strong>1.0.0-enterprise</strong>
            <br />
            Environment: <strong>{import.meta.env.MODE}</strong>
          </p>
        </div>
      </div>
    </div>
  );
};

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <EnterpriseApp />
  </StrictMode>
);

