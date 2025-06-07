import React, { FormEvent } from 'react';
import type { SessionInfo, DriversLogEntry, PastSession } from '../../types';

interface LogFormProps {
  showLogForm: boolean;
  sessionInfo: SessionInfo | null;
  selectedLog: DriversLogEntry | null;
  selectedSession: PastSession | null;
  sessionAlreadySaved: boolean;
  logFormData: { purpose: string; notes: string };
  logSaveError: string | null;
  onFormDataChange: (data: { purpose: string; notes: string }) => void;
  onSubmit: (e: FormEvent) => void;
  onCancel: () => void;
}

export const LogForm: React.FC<LogFormProps> = ({
  showLogForm,
  sessionInfo,
  selectedLog,
  selectedSession,
  sessionAlreadySaved,
  logFormData,
  logSaveError,
  onFormDataChange,
  onSubmit,
  onCancel
}) => {
  // Don't show if conditions aren't met
  if (!showLogForm || !sessionInfo || selectedLog || (!selectedSession && sessionAlreadySaved)) {
    return null;
  }

  const handlePurposeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    onFormDataChange({ ...logFormData, purpose: e.target.value });
  };

  const handleNotesChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    onFormDataChange({ ...logFormData, notes: e.target.value });
  };

  return (
    <div style={{
      position: "absolute",
      bottom: "220px",
      left: "10px",
      backgroundColor: "#2b2b2b",
      color: "white",
      padding: "15px",
      borderRadius: "8px",
      boxShadow: "0 2px 10px rgba(0,0,0,0.5)",
      zIndex: 1000,
      maxWidth: "300px"
    }}>
      <h3 style={{ margin: "0 0 10px 0" }}>Save to Driver's Log</h3>
      
      <form onSubmit={onSubmit}>
        <div style={{ marginBottom: "10px" }}>
          <label style={{ display: "block", marginBottom: "5px" }}>
            Purpose:
          </label>
          <select 
            value={logFormData.purpose}
            onChange={handlePurposeChange}
            style={{ 
              width: "100%", 
              padding: "8px", 
              borderRadius: "4px", 
              border: "1px solid #444",
              backgroundColor: "#333",
              color: "white" 
            }}
            required
          >
            <option value="">Select purpose</option>
            <option value="business">Business</option>
            <option value="commute">Commute</option>
            <option value="personal">Personal</option>
            <option value="delivery">Delivery</option>
            <option value="other">Other</option>
          </select>
        </div>
        
        <div style={{ marginBottom: "15px" }}>
          <label style={{ display: "block", marginBottom: "5px" }}>
            Notes:
          </label>
          <textarea
            value={logFormData.notes}
            onChange={handleNotesChange}
            style={{ 
              width: "100%", 
              padding: "8px", 
              borderRadius: "4px", 
              border: "1px solid #444", 
              height: "60px",
              backgroundColor: "#333",
              color: "white" 
            }}
          />
        </div>
        
        {logSaveError && (
          <div style={{ color: "red", marginBottom: "10px" }}>
            Error: {logSaveError}
          </div>
        )}
        
        <div style={{ display: "flex", justifyContent: "space-between" }}>
          <button
            type="button"
            onClick={onCancel}
            style={{ 
              padding: "8px 12px",
              backgroundColor: "#f0f0f0",
              border: "1px solid #ccc",
              borderRadius: "4px",
              cursor: "pointer"
            }}
          >
            Cancel
          </button>
          <button
            type="submit"
            style={{ 
              padding: "8px 12px",
              backgroundColor: "#4CAF50",
              color: "white",
              border: "none",
              borderRadius: "4px",
              cursor: "pointer"
            }}
          >
            Save
          </button>
        </div>
      </form>
    </div>
  );
};