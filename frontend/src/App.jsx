import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import ReconciliationScreen from './components/ReconciliationScreen';
import AnalyticsScreen from './components/AnalyticsScreen';
import NarrativeScreen from './components/NarrativeScreen';
import DateSelector from './components/DateSelector';
import UploadModal from './components/UploadModal';
import { fetchAvailableDays, fetchEODBundle } from './api';

export default function App() {
  const [currentScreen, setCurrentScreen] = useState('reconciliation'); // 'reconciliation' | 'analytics' | 'narrative'
  const [availableDays, setAvailableDays] = useState([]);
  const [selectedDate, setSelectedDate] = useState('2026-07-27');
  const [eodData, setEodData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isUploadOpen, setIsUploadOpen] = useState(false);

  // Load available clinic dates on mount
  useEffect(() => {
    loadDays();
  }, []);

  const loadDays = async () => {
    try {
      const days = await fetchAvailableDays();
      setAvailableDays(days);
      if (days.length > 0 && !selectedDate) {
        setSelectedDate(days[0].date);
      }
    } catch (err) {
      console.warn("Could not load available days:", err);
      // Fallback days matching dataset
      setAvailableDays([
        { date: '2026-07-27', visit_count: 18 },
        { date: '2026-07-26', visit_count: 0 },
        { date: '2026-07-25', visit_count: 3 }
      ]);
    }
  };

  // Load EOD Bundle whenever selectedDate changes
  useEffect(() => {
    if (!selectedDate) return;
    loadEODReport(selectedDate);
  }, [selectedDate]);

  const loadEODReport = async (date) => {
    setLoading(true);
    setError(null);
    try {
      const bundle = await fetchEODBundle(date);
      setEodData(bundle);
    } catch (err) {
      setError(err.message || 'Failed to load EOD bundle');
    } finally {
      setLoading(false);
    }
  };

  const handleIngestionSuccess = (newDate) => {
    loadDays();
    setSelectedDate(newDate);
    setIsUploadOpen(false);
  };

  const clinicName = eodData?.reconciliation?.clinic_name || "Mehta Multi-Specialty Clinic";
  const clinicLocation = eodData?.reconciliation?.clinic_location || "Kanpur, Uttar Pradesh";

  // Screen header content
  const renderHeader = () => {
    switch (currentScreen) {
      case 'reconciliation':
        return {
          title: "EOD Reconciliation",
          subtitle: `${clinicName} — ${clinicLocation}`
        };
      case 'analytics':
        return {
          title: "Analytics",
          subtitle: `${clinicName} — ${selectedDate}`
        };
      case 'narrative':
        return {
          title: "AI Narrative Summary",
          subtitle: `Generated from today's reconciliation — ${clinicName}`
        };
      default:
        return { title: "Dashboard", subtitle: clinicName };
    }
  };

  const headerInfo = renderHeader();

  return (
    <div className="app-container">
      {/* Persistent Left Sidebar */}
      <Sidebar 
        currentScreen={currentScreen} 
        onSelectScreen={setCurrentScreen}
        onOpenUpload={() => setIsUploadOpen(true)}
      />

      {/* Main Content Area */}
      <div className="main-wrapper">
        {/* Top Navbar */}
        <header className="top-navbar">
          <div className="top-title-group">
            <h1>{headerInfo.title}</h1>
            <p>{headerInfo.subtitle}</p>
          </div>

          <div className="top-actions">
            <DateSelector 
              availableDays={availableDays}
              selectedDate={selectedDate}
              onSelectDate={(dt) => setSelectedDate(dt)}
            />
          </div>
        </header>

        {/* Screen Content */}
        <main className="screen-content">
          {loading ? (
            <div className="content-card" style={{ textAlign: 'center', padding: 48, color: 'var(--text-muted)' }}>
              Loading EOD billing & reconciliation data...
            </div>
          ) : error ? (
            <div className="content-card" style={{ borderColor: 'var(--danger)', color: 'var(--danger)' }}>
              Error: {error}
            </div>
          ) : (
            <>
              {currentScreen === 'reconciliation' && (
                <ReconciliationScreen 
                  data={eodData} 
                  ingestionSummary={eodData?.ingestion_summary}
                />
              )}
              {currentScreen === 'analytics' && (
                <AnalyticsScreen 
                  data={eodData} 
                />
              )}
              {currentScreen === 'narrative' && (
                <NarrativeScreen 
                  data={eodData} 
                />
              )}
            </>
          )}
        </main>
      </div>

      {/* Upload & Ingest Modal */}
      <UploadModal 
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
        onIngestionSuccess={handleIngestionSuccess}
      />
    </div>
  );
}
