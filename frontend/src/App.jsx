import React, { useState } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { DashboardLayout } from './layouts/DashboardLayout';
import { LoginPage } from './pages/LoginPage';
import { DashboardPage } from './pages/DashboardPage';
import { UploadPage } from './pages/UploadPage';
import { InvoicesPage } from './pages/InvoicesPage';
import { InvoiceReviewPage } from './pages/InvoiceReviewPage';
import { NeedsReviewPage } from './pages/NeedsReviewPage';
import { ReportsPage } from './pages/ReportsPage';
import { SettingsPage } from './pages/SettingsPage';
import { LoadingSpinner } from './components/LoadingSpinner';
import { api } from './services/api';

function MainApp() {
  const { user, loading } = useAuth();
  const [currentView, setCurrentView] = useState('dashboard');
  const [selectedInvoiceId, setSelectedInvoiceId] = useState(null);

  if (loading) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: '#f8fafc' }}>
        <LoadingSpinner message="Authenticating session..." />
      </div>
    );
  }

  if (!user) {
    return <LoginPage />;
  }

  const handleSelectInvoice = (id) => {
    setSelectedInvoiceId(id);
    setCurrentView('review');
  };

  const handleGenerateSamples = async () => {
    try {
      await api.generateSamples();
      setCurrentView('invoices');
    } catch (err) {
      alert('Sample generation failed: ' + err.message);
    }
  };

  const viewTitles = {
    dashboard: 'Dashboard Overview',
    upload: 'Upload Documents & Invoices',
    invoices: 'All Invoices & Ledger',
    review: 'Invoice Inspection & Review',
    'needs-review': 'Needs Review Queue',
    reports: 'Financial Reports & Analytics',
    settings: 'System & Policy Settings'
  };

  return (
    <DashboardLayout
      currentView={currentView}
      onChangeView={(v) => {
        setSelectedInvoiceId(null);
        setCurrentView(v);
      }}
      pageTitle={viewTitles[currentView] || 'ApexInvoice AI'}
      onSelectInvoice={handleSelectInvoice}
      onGenerateSamples={handleGenerateSamples}
    >
      {currentView === 'dashboard' && (
        <DashboardPage 
          onNavigate={(v) => setCurrentView(v)} 
          onSelectInvoice={handleSelectInvoice} 
        />
      )}

      {currentView === 'upload' && (
        <UploadPage 
          onSelectInvoice={handleSelectInvoice}
          onNavigate={(v) => setCurrentView(v)}
        />
      )}

      {currentView === 'invoices' && (
        <InvoicesPage 
          onSelectInvoice={handleSelectInvoice}
          onNavigate={(v) => setCurrentView(v)}
        />
      )}

      {currentView === 'review' && (
        <InvoiceReviewPage 
          invoiceId={selectedInvoiceId}
          onBack={() => setCurrentView('invoices')}
          onReloadList={() => {}}
        />
      )}

      {currentView === 'needs-review' && (
        <NeedsReviewPage 
          onSelectInvoice={handleSelectInvoice}
        />
      )}

      {currentView === 'reports' && (
        <ReportsPage />
      )}

      {currentView === 'settings' && (
        <SettingsPage />
      )}
    </DashboardLayout>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <MainApp />
    </AuthProvider>
  );
}
