import React, { useState } from 'react';
import { 
  AlertTriangle, 
  CheckCircle, 
  HelpCircle, 
  CreditCard, 
  Banknote, 
  Smartphone, 
  ChevronRight,
  Info
} from 'lucide-react';

function formatRupee(amount) {
  if (amount === null || amount === undefined) return '₹0';
  return '₹' + Number(amount).toLocaleString('en-IN', {
    maximumFractionDigits: 2,
    minimumFractionDigits: 0
  });
}

export default function ReconciliationScreen({ data, ingestionSummary }) {
  const [showErrorModal, setShowErrorModal] = useState(false);
  const recon = data?.reconciliation;
  const byMode = recon?.by_payment_mode || {};

  if (!recon) {
    return <div className="content-card">Loading reconciliation report...</div>;
  }

  const rejectedCount = ingestionSummary?.rejected_count || 0;
  const errors = ingestionSummary?.errors || [];

  return (
    <div>
      {/* Actionable Error Banner if any row failed validation */}
      {rejectedCount > 0 && (
        <div className="alert-banner">
          <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
            <AlertTriangle size={20} color="#D97706" style={{ marginTop: 2, flexShrink: 0 }} />
            <div>
              <div className="alert-title">
                {recon.total_visits} valid visits processed • {rejectedCount} malformed row rejected with actionable error
              </div>
              <div className="alert-desc">
                Production ingestion quarantined malformed rows without crashing the EOD report.
              </div>
            </div>
          </div>
          <button 
            className="btn-secondary" 
            style={{ fontSize: 12, padding: '4px 10px' }}
            onClick={() => setShowErrorModal(true)}
          >
            View Error Details
          </button>
        </div>
      )}

      {/* 4 Stat Cards */}
      <div className="stats-grid">
        {/* TOTAL BILLED */}
        <div className="stat-card">
          <div className="stat-title">TOTAL BILLED</div>
          <div className="stat-value">{formatRupee(recon.total_billed_rupees)}</div>
          <div className="stat-subtext">
            <span>{recon.total_visits} visits</span>
          </div>
        </div>

        {/* TOTAL COLLECTED */}
        <div className="stat-card">
          <div className="stat-title">TOTAL COLLECTED</div>
          <div className="stat-value">{formatRupee(recon.total_collected_rupees)}</div>
          <div className="stat-subtext">
            <span className="badge-pill success">
              {Math.round(recon.collection_rate_percent)}% of billed
            </span>
          </div>
        </div>

        {/* OUTSTANDING */}
        <div className="stat-card">
          <div className="stat-title">OUTSTANDING</div>
          <div className="stat-value">{formatRupee(recon.total_outstanding_rupees)}</div>
          <div className="stat-subtext">
            <span style={{ color: recon.pending_invoices_count > 0 ? 'var(--warning)' : 'var(--text-muted)' }}>
              {recon.pending_invoices_count} pending {recon.pending_invoices_count === 1 ? 'invoice' : 'invoices'}
            </span>
          </div>
        </div>

        {/* REFUNDS */}
        <div className="stat-card">
          <div className="stat-title">REFUNDS</div>
          <div className="stat-value">{formatRupee(recon.total_refunds_rupees)}</div>
          <div className="stat-subtext">
            <span>{recon.refund_visits_count} {recon.refund_visits_count === 1 ? 'refund' : 'refunds'}</span>
          </div>
        </div>
      </div>

      {/* Payment Mode Breakdown Table */}
      <div className="content-card">
        <div className="card-header-bar">
          <h2 className="card-title">Payment Mode Breakdown</h2>
          <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
            Integer paise arithmetic • Ground Truth
          </span>
        </div>

        <table className="data-table">
          <thead>
            <tr>
              <th style={{ width: '25%' }}>Mode</th>
              <th className="num-cell">Billed</th>
              <th className="num-cell">Collected</th>
              <th className="num-cell">Outstanding</th>
            </tr>
          </thead>
          <tbody>
            {/* Cash */}
            <tr>
              <td>
                <span className="mode-tag">
                  <Banknote size={16} color="#16A34A" />
                  Cash
                </span>
              </td>
              <td className="num-cell">{formatRupee(byMode.cash?.billed_rupees || 0)}</td>
              <td className="num-cell">{formatRupee(byMode.cash?.collected_rupees || 0)}</td>
              <td className="num-cell" style={{ color: byMode.cash?.outstanding_rupees > 0 ? 'var(--warning)' : 'inherit' }}>
                {formatRupee(byMode.cash?.outstanding_rupees || 0)}
              </td>
            </tr>

            {/* Card */}
            <tr>
              <td>
                <span className="mode-tag">
                  <CreditCard size={16} color="#2563EB" />
                  Card
                </span>
              </td>
              <td className="num-cell">{formatRupee(byMode.card?.billed_rupees || 0)}</td>
              <td className="num-cell">{formatRupee(byMode.card?.collected_rupees || 0)}</td>
              <td className="num-cell" style={{ color: byMode.card?.outstanding_rupees > 0 ? 'var(--warning)' : 'inherit' }}>
                {formatRupee(byMode.card?.outstanding_rupees || 0)}
              </td>
            </tr>

            {/* UPI */}
            <tr>
              <td>
                <span className="mode-tag">
                  <Smartphone size={16} color="#7C3AED" />
                  UPI
                </span>
              </td>
              <td className="num-cell">{formatRupee(byMode.upi?.billed_rupees || 0)}</td>
              <td className="num-cell">{formatRupee(byMode.upi?.collected_rupees || 0)}</td>
              <td className="num-cell" style={{ color: byMode.upi?.outstanding_rupees > 0 ? 'var(--warning)' : 'inherit' }}>
                {formatRupee(byMode.upi?.outstanding_rupees || 0)}
              </td>
            </tr>

            {/* Totals Summary Row */}
            <tr style={{ fontWeight: 700, backgroundColor: 'var(--bg-muted)' }}>
              <td>Total</td>
              <td className="num-cell">{formatRupee(recon.total_billed_rupees)}</td>
              <td className="num-cell">{formatRupee(recon.total_collected_rupees)}</td>
              <td className="num-cell">{formatRupee(recon.total_outstanding_rupees)}</td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* Error Details Modal */}
      {showErrorModal && (
        <div style={{
          position: 'fixed',
          top: 0, left: 0, right: 0, bottom: 0,
          backgroundColor: 'rgba(15, 23, 42, 0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 50,
          padding: 20
        }}>
          <div style={{
            backgroundColor: 'white',
            borderRadius: 'var(--radius-lg)',
            maxWidth: 600,
            width: '100%',
            padding: 28,
            boxShadow: 'var(--shadow-lg)'
          }}>
            <h3 style={{ fontSize: 18, fontWeight: 700, marginBottom: 8, color: 'var(--text-main)' }}>
              Actionable Validation Diagnostics
            </h3>
            <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 20 }}>
              The ingestion engine rejected the following malformed rows with specific errors instead of a generic 500:
            </p>

            <div style={{ maxHeight: 300, overflowY: 'auto' }}>
              {errors.map((err, idx) => (
                <div key={idx} style={{
                  padding: 14,
                  backgroundColor: '#FEF2F2',
                  border: '1px solid #FECACA',
                  borderRadius: 'var(--radius-md)',
                  marginBottom: 12
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                    <strong style={{ fontSize: 13, color: '#991B1B' }}>
                      Row {err.row_index + 1} {err.visit_id ? `(${err.visit_id})` : ''}
                    </strong>
                    <span style={{ fontSize: 11, backgroundColor: '#FEE2E2', color: '#B91C1C', padding: '2px 6px', borderRadius: 4, fontFamily: 'var(--font-mono)' }}>
                      field: {err.field}
                    </span>
                  </div>
                  <div style={{ fontSize: 13, color: '#7F1D1D' }}>
                    {err.error_message}
                  </div>
                </div>
              ))}
            </div>

            <div style={{ marginTop: 24, display: 'flex', justifyContent: 'flex-end' }}>
              <button 
                className="btn-primary"
                onClick={() => setShowErrorModal(false)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
