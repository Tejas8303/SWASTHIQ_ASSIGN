import React, { useState } from 'react';
import { UploadCloud, X, AlertCircle, CheckCircle, FileJson } from 'lucide-react';
import { uploadBillingFile, ingestJsonPayload } from '../api';

export default function UploadModal({ isOpen, onClose, onIngestionSuccess }) {
  const [file, setFile] = useState(null);
  const [jsonText, setJsonText] = useState('');
  const [strict, setStrict] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  if (!isOpen) return null;

  const handleUploadFile = async () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await uploadBillingFile(file, strict);
      setResult(res);
      if (res.date) {
        onIngestionSuccess(res.date);
      }
    } catch (err) {
      setError(err.message || 'Ingestion failed');
    } finally {
      setLoading(false);
    }
  };

  const handlePasteIngest = async () => {
    if (!jsonText.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const parsed = JSON.parse(jsonText);
      const res = await ingestJsonPayload(parsed, strict);
      setResult(res);
      if (res.date) {
        onIngestionSuccess(res.date);
      }
    } catch (err) {
      setError(err.message || 'Invalid JSON format or ingestion failure');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      position: 'fixed',
      top: 0, left: 0, right: 0, bottom: 0,
      backgroundColor: 'rgba(15, 23, 42, 0.6)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 100,
      padding: 20
    }}>
      <div style={{
        backgroundColor: 'white',
        borderRadius: 'var(--radius-lg)',
        maxWidth: 580,
        width: '100%',
        padding: 30,
        boxShadow: 'var(--shadow-lg)',
        position: 'relative'
      }}>
        <button 
          onClick={onClose}
          style={{ position: 'absolute', top: 20, right: 20, color: 'var(--text-muted)' }}
        >
          <X size={20} />
        </button>

        <h3 style={{ fontSize: 18, fontWeight: 700, marginBottom: 6, color: 'var(--text-main)' }}>
          Ingest Billing Log
        </h3>
        <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 20 }}>
          Upload a daily billing log JSON array. The deterministic pipeline will validate rows and calculate EOD reports.
        </p>

        {/* File Input */}
        <div style={{
          border: '2px dashed var(--border-light)',
          borderRadius: 'var(--radius-md)',
          padding: 24,
          textAlign: 'center',
          backgroundColor: 'var(--bg-page)',
          marginBottom: 16
        }}>
          <UploadCloud size={32} color="var(--primary)" style={{ margin: '0 auto 8px' }} />
          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 4 }}>
            {file ? file.name : "Select a billing log JSON file"}
          </div>
          <input 
            type="file" 
            accept=".json"
            onChange={(e) => setFile(e.target.files[0])}
            style={{ fontSize: 12, marginTop: 8 }}
          />
          {file && (
            <div style={{ marginTop: 12 }}>
              <button 
                className="btn-primary"
                disabled={loading}
                onClick={handleUploadFile}
              >
                {loading ? 'Ingesting...' : 'Ingest Selected File'}
              </button>
            </div>
          )}
        </div>

        {/* Paste JSON Option */}
        <div style={{ marginBottom: 16 }}>
          <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>
            Or Paste Raw JSON Array:
          </label>
          <textarea
            value={jsonText}
            onChange={(e) => setJsonText(e.target.value)}
            placeholder='[ { "clinic_id": "CLN-KNP-014", "visit_id": "V-1", ... } ]'
            style={{
              width: '100%',
              height: 100,
              padding: 10,
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--border-light)',
              fontFamily: 'var(--font-mono)',
              fontSize: 12,
              resize: 'vertical'
            }}
          />
          {jsonText.trim() && (
            <div style={{ marginTop: 8 }}>
              <button 
                className="btn-primary"
                disabled={loading}
                onClick={handlePasteIngest}
              >
                {loading ? 'Processing...' : 'Ingest Pasted JSON'}
              </button>
            </div>
          )}
        </div>

        {/* Strict Mode Toggle */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
          <input 
            type="checkbox" 
            id="strictMode" 
            checked={strict} 
            onChange={(e) => setStrict(e.target.checked)} 
          />
          <label htmlFor="strictMode" style={{ fontSize: 13, color: 'var(--text-main)' }}>
            Strict Mode (Rejects entire batch if even 1 row has validation errors)
          </label>
        </div>

        {/* Status Message */}
        {error && (
          <div style={{
            padding: 12,
            backgroundColor: '#FEF2F2',
            color: '#991B1B',
            borderRadius: 'var(--radius-md)',
            fontSize: 13,
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            marginBottom: 16
          }}>
            <AlertCircle size={16} />
            {error}
          </div>
        )}

        {result && (
          <div style={{
            padding: 12,
            backgroundColor: '#F0FDF4',
            color: '#166534',
            borderRadius: 'var(--radius-md)',
            fontSize: 13,
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            marginBottom: 16
          }}>
            <CheckCircle size={16} />
            {result.message}
          </div>
        )}

        <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
          <button className="btn-secondary" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
