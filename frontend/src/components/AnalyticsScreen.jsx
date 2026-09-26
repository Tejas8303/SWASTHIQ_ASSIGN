import React from 'react';
import { TrendingUp, Package, IndianRupee } from 'lucide-react';

function formatRupee(amount) {
  if (amount === null || amount === undefined) return '₹0';
  return '₹' + Number(amount).toLocaleString('en-IN', {
    maximumFractionDigits: 2,
    minimumFractionDigits: 0
  });
}

export default function AnalyticsScreen({ data }) {
  const analytics = data?.analytics;
  const hours = analytics?.hourly_revenue || [];
  const peak = analytics?.peak_hour;
  const topByQty = analytics?.top_by_quantity || [];
  const topByRev = analytics?.top_by_revenue || [];

  if (!analytics) {
    return <div className="content-card">Loading analytics report...</div>;
  }

  // Calculate max revenue for chart scaling
  const maxRevenue = Math.max(...hours.map(h => h.revenue_rupees), 100);

  return (
    <div>
      {/* Revenue by Hour of Day Chart Card */}
      <div className="content-card">
        <div className="card-header-bar">
          <div>
            <h2 className="card-title">Revenue by Hour of Day</h2>
            <p style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 2 }}>
              UTC timestamps bucketed into clinic operating hours
            </p>
          </div>
          {peak && (
            <div className="badge-pill purple" style={{ gap: 6, padding: '6px 12px', fontSize: 12 }}>
              <TrendingUp size={14} />
              Peak: {peak.time_range} — {formatRupee(peak.revenue_rupees)}
            </div>
          )}
        </div>

        {hours.length === 0 || hours.every(h => h.revenue_rupees === 0) ? (
          <div style={{ textAlign: 'center', padding: '48px 0', color: 'var(--text-muted)' }}>
            No revenue recorded during clinic hours on this date.
          </div>
        ) : (
          <div className="chart-container">
            {hours.map((h, i) => {
              const heightPercent = maxRevenue > 0 ? Math.max((h.revenue_rupees / maxRevenue) * 100, 6) : 6;
              const isPeak = h.is_peak;

              return (
                <div key={i} className="chart-bar-col">
                  {isPeak && (
                    <div className="peak-tooltip">
                      Peak: {h.time_range_label} — {formatRupee(h.revenue_rupees)}
                    </div>
                  )}
                  <div
                    className={`chart-bar ${isPeak ? 'peak' : ''}`}
                    style={{ height: `${heightPercent}%` }}
                    title={`${h.time_range_label}: ${formatRupee(h.revenue_rupees)} (${h.visits_count} visits)`}
                  />
                  <div className="chart-label">{h.hour_label}</div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Two Distinct Rankings */}
      <div className="rankings-grid">
        {/* Top Medicines — by Quantity */}
        <div className="content-card" style={{ marginBottom: 0 }}>
          <div className="card-header-bar">
            <h2 className="card-title" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Package size={18} color="var(--primary)" />
              Top Medicines — by Quantity
            </h2>
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Volume Ranking</span>
          </div>

          {topByQty.length === 0 ? (
            <div style={{ padding: '24px 0', color: 'var(--text-muted)', textAlign: 'center' }}>
              No medicines dispensed today.
            </div>
          ) : (
            <div>
              {topByQty.map((item, idx) => (
                <div key={idx} className="rank-item">
                  <div className="rank-left">
                    <span className="rank-num">{item.rank}</span>
                    <span className="rank-name">{item.drug_name}</span>
                  </div>
                  <span className="rank-value" style={{ color: 'var(--text-muted)' }}>
                    {item.quantity} units
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Top Medicines — by Revenue */}
        <div className="content-card" style={{ marginBottom: 0 }}>
          <div className="card-header-bar">
            <h2 className="card-title" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <IndianRupee size={18} color="var(--success)" />
              Top Medicines — by Revenue
            </h2>
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Revenue Ranking</span>
          </div>

          {topByRev.length === 0 ? (
            <div style={{ padding: '24px 0', color: 'var(--text-muted)', textAlign: 'center' }}>
              No sales revenue recorded today.
            </div>
          ) : (
            <div>
              {topByRev.map((item, idx) => (
                <div key={idx} className="rank-item">
                  <div className="rank-left">
                    <span className="rank-num">{item.rank}</span>
                    <span className="rank-name">{item.drug_name}</span>
                  </div>
                  <span className="rank-value">
                    {formatRupee(item.revenue_rupees)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
