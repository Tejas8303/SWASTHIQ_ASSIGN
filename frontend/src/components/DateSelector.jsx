import React, { useState } from 'react';
import { Calendar, ChevronDown, Check } from 'lucide-react';

function formatDateDisplay(dateStr) {
  if (!dateStr) return 'Select Date';
  try {
    const parts = dateStr.split('-');
    if (parts.length === 3) {
      const d = new Date(parts[0], parts[1] - 1, parts[2]);
      return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
    }
  } catch (e) {}
  return dateStr;
}

export default function DateSelector({ availableDays, selectedDate, onSelectDate }) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div style={{ position: 'relative' }}>
      <button 
        className="date-badge"
        onClick={() => setIsOpen(!isOpen)}
        style={{ cursor: 'pointer' }}
      >
        <Calendar size={16} color="var(--primary)" />
        <span>{formatDateDisplay(selectedDate)}</span>
        <ChevronDown size={14} color="var(--text-muted)" />
      </button>

      {isOpen && (
        <>
          <div 
            style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, zIndex: 40 }}
            onClick={() => setIsOpen(false)}
          />
          <div style={{
            position: 'absolute',
            top: '100%',
            right: 0,
            marginTop: 8,
            backgroundColor: 'white',
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--border-light)',
            boxShadow: 'var(--shadow-lg)',
            width: 240,
            zIndex: 50,
            overflow: 'hidden'
          }}>
            <div style={{ padding: '10px 14px', borderBottom: '1px solid var(--border-light)', fontSize: 11, fontWeight: 600, color: 'var(--text-muted)' }}>
              AVAILABLE CLINIC DAYS
            </div>
            {availableDays.map((item) => (
              <div
                key={item.date}
                onClick={() => {
                  onSelectDate(item.date);
                  setIsOpen(false);
                }}
                style={{
                  padding: '12px 14px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  cursor: 'pointer',
                  backgroundColor: selectedDate === item.date ? 'var(--primary-soft)' : 'transparent',
                  borderBottom: '1px solid #F1F5F9'
                }}
              >
                <div>
                  <div style={{ fontSize: 13, fontWeight: selectedDate === item.date ? 600 : 500, color: 'var(--text-main)' }}>
                    {formatDateDisplay(item.date)}
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                    {item.visit_count} visits • {item.date === "2026-07-26" ? "Empty day" : item.date === "2026-07-25" ? "Refunds only" : "Sales & partial"}
                  </div>
                </div>
                {selectedDate === item.date && <Check size={16} color="var(--primary)" />}
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
