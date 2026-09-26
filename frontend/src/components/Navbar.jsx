import React from 'react';
import { Search, User as UserIcon, Sparkles } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { NotificationDropdown } from './NotificationDropdown';

export function Navbar({ pageTitle, onSelectInvoice, onGenerateSamples }) {
  const { user } = useAuth();
  const todayStr = new Date().toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    year: 'numeric'
  });

  return (
    <header className="topbar">
      {/* Title & Breadcrumb */}
      <div>
        <h1 style={{ fontSize: '1.25rem', fontWeight: 800, color: '#0f172a' }}>{pageTitle}</h1>
        <p style={{ fontSize: '0.75rem', color: '#64748b' }}>ApexInvoice AI Workspace • {todayStr}</p>
      </div>

      {/* Actions */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
        {/* Quick Test Samples Generator Button */}
        <button
          className="btn btn-secondary btn-sm"
          onClick={onGenerateSamples}
          title="Load 4 realistic sample invoice PDFs (INR/USD, Clean, High-Value, Discrepancies)"
          style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#4f46e5', fontWeight: 600 }}
        >
          <Sparkles size={15} color="#4f46e5" />
          <span>Load Test Invoices</span>
        </button>

        {/* Notifications */}
        <NotificationDropdown onSelectInvoice={onSelectInvoice} />

        {/* User Pill */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          padding: '6px 12px',
          backgroundColor: '#f8fafc',
          border: '1px solid #e2e8f0',
          borderRadius: '999px'
        }}>
          <div style={{
            width: '28px',
            height: '28px',
            borderRadius: '50%',
            backgroundColor: '#eef2ff',
            color: '#4f46e5',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontWeight: 700,
            fontSize: '0.8rem'
          }}>
            {user?.full_name ? user.full_name.charAt(0).toUpperCase() : 'U'}
          </div>
          <div style={{ lineHeight: 1.1 }}>
            <span style={{ fontSize: '0.82rem', fontWeight: 700, color: '#0f172a', display: 'block' }}>
              {user?.full_name || 'Accountant'}
            </span>
            <span style={{ fontSize: '0.7rem', color: '#94a3b8' }}>
              {user?.default_currency || 'INR'} ({user?.email})
            </span>
          </div>
        </div>
      </div>
    </header>
  );
}
