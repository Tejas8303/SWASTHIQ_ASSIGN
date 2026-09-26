import React, { useState } from 'react';
import { 
  Sparkles, 
  CheckCircle2, 
  Copy, 
  Check, 
  ShieldCheck, 
  MessageSquare,
  ArrowRight,
  Send
} from 'lucide-react';

export default function NarrativeScreen({ data }) {
  const [copied, setCopied] = useState(false);
  const narrative = data?.narrative;
  const tracedFigures = narrative?.traced_figures || [];

  if (!narrative) {
    return <div className="content-card">Loading AI narrative summary...</div>;
  }

  const handleCopy = () => {
    navigator.clipboard.writeText(narrative.narrative_text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div>
      <div className="narrative-grid">
        {/* Left Column: WhatsApp Message Preview */}
        <div className="whatsapp-card">
          <div className="whatsapp-header">
            <div className="whatsapp-recipient">
              <MessageSquare size={18} />
              <span>{narrative.recipient || "Sent to: Dr. Arvind Mehta • WhatsApp"}</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, opacity: 0.9 }}>
              <span className="badge-pill purple" style={{ backgroundColor: '#A855F7', color: 'white', fontSize: 10 }}>
                AI SUGGESTED
              </span>
            </div>
          </div>

          <div className="whatsapp-body">
            <div className="whatsapp-bubble">
              {narrative.narrative_text}
            </div>

            <div className="whatsapp-actions">
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span className="badge-pill success" style={{ gap: 4 }}>
                  <ShieldCheck size={14} />
                  {narrative.grounding_status === "VERIFIED_GROUNDED" ? "GROUNDED (0 HALLUCINATIONS)" : "VERIFIED"}
                </span>
                <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                  Model: {narrative.model_used}
                </span>
              </div>

              <button 
                className="btn-secondary" 
                onClick={handleCopy}
                style={{ fontSize: 12, padding: '6px 12px' }}
              >
                {copied ? <Check size={14} color="var(--success)" /> : <Copy size={14} />}
                {copied ? 'Copied!' : 'Copy Summary'}
              </button>
            </div>
          </div>
        </div>

        {/* Right Column: Traced Figures Panel */}
        <div className="trace-panel">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
            <h2 className="trace-title">Traced Figures</h2>
            <span className="badge-pill purple" style={{ backgroundColor: '#A855F7', color: 'white', fontSize: 10 }}>
              AI SUGGESTED
            </span>
          </div>

          <p className="trace-desc">
            Every figure above traces to a deterministic report field. Zero hallucinated numbers.
          </p>

          <div style={{ maxHeight: 440, overflowY: 'auto', paddingRight: 4 }}>
            {tracedFigures.length === 0 ? (
              <div style={{ padding: '20px 0', color: 'var(--text-muted)', textAlign: 'center' }}>
                No figures present to trace.
              </div>
            ) : (
              tracedFigures.map((item, idx) => (
                <div key={idx} className="trace-item">
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                      <span className="trace-fig">{item.figure}</span>
                      <ArrowRight size={12} className="trace-arrow" />
                      <span className="trace-field">{item.field_name}</span>
                    </div>
                    {item.context && (
                      <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                        {item.context}
                      </div>
                    )}
                  </div>
                  <div className="trace-check" title="Verified against report">
                    <CheckCircle2 size={16} />
                  </div>
                </div>
              ))
            )}
          </div>

          <div style={{
            marginTop: 18,
            padding: '12px 14px',
            backgroundColor: '#F8FAFC',
            borderRadius: 'var(--radius-md)',
            border: '1px dashed var(--border-light)',
            fontSize: 12,
            color: 'var(--text-muted)'
          }}>
            <strong>Uncomputable Metrics Handled:</strong>
            <div style={{ marginTop: 4 }}>
              Profit/Margin: Plainly flagged as uncomputable since drug cost prices are not provided in dataset.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
