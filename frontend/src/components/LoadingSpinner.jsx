import React from 'react';

export function LoadingSpinner({ size = 24, message = 'Loading...' }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '40px 20px', gap: '12px' }}>
      <div
        style={{
          width: size,
          height: size,
          border: '3px solid #e2e8f0',
          borderTopColor: '#4f46e5',
          borderRadius: '50%',
          animation: 'spin 0.7s linear infinite'
        }}
      />
      {message && <p style={{ fontSize: '0.85rem', color: '#64748b', fontWeight: 500 }}>{message}</p>}
      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
