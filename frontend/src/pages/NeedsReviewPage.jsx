import React, { useState, useEffect } from 'react';
import { 
  AlertCircle, 
  Search, 
  Edit3, 
  Clock, 
  CheckCircle2,
  Filter
} from 'lucide-react';
import { api } from '../services/api';
import { StatusBadge } from '../components/StatusBadge';
import { LoadingSpinner } from '../components/LoadingSpinner';

export function NeedsReviewPage({ onSelectInvoice }) {
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    loadNeedsReviewInvoices();
  }, [searchQuery]);

  const loadNeedsReviewInvoices = async () => {
    try {
      setLoading(true);
      // Fetch both FLAGGED and NEEDS_REVIEW
      const [resNeeds, resFlagged] = await Promise.all([
        api.getInvoices({ status: 'NEEDS_REVIEW', q: searchQuery, limit: 50 }),
        api.getInvoices({ status: 'FLAGGED', q: searchQuery, limit: 50 })
      ]);
      const combined = [...(resFlagged.items || []), ...(resNeeds.items || [])];
      setInvoices(combined);
    } catch (err) {
      console.error('Failed to load review queue:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="card" style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <h2 className="card-title">Invoices Requiring Human Attention</h2>
              <span className="badge badge-flagged">{invoices.length} Pending Queue</span>
            </div>
            <p style={{ fontSize: '0.8rem', color: '#64748b', marginTop: '2px' }}>
              Invoices with calculation mismatches, policy flags, high values, or missing information.
            </p>
          </div>

          <div style={{ position: 'relative', width: '260px' }}>
            <Search size={16} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: '#94a3b8' }} />
            <input
              type="text"
              placeholder="Search in review queue..."
              className="form-input"
              style={{ paddingLeft: '36px' }}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
        </div>
      </div>

      <div className="card">
        {loading ? (
          <LoadingSpinner message="Loading review queue..." />
        ) : invoices.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '60px 20px', color: '#64748b' }}>
            <CheckCircle2 size={48} color="#10b981" style={{ margin: '0 auto 12px' }} />
            <h3 style={{ fontSize: '1.15rem', fontWeight: 700, color: '#0f172a', marginBottom: '4px' }}>
              All Caught Up!
            </h3>
            <p style={{ fontSize: '0.85rem' }}>No invoices currently require human review.</p>
          </div>
        ) : (
          <div className="table-container">
            <table className="app-table">
              <thead>
                <tr>
                  <th>Status</th>
                  <th>Invoice #</th>
                  <th>Vendor</th>
                  <th>Detected Issues</th>
                  <th>Total Amount</th>
                  <th>Uploaded Date</th>
                  <th style={{ textAlign: 'right' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {invoices.map((inv) => {
                  const currSym = inv.currency === 'INR' ? '₹' : (inv.currency === 'USD' ? '$' : inv.currency);
                  const issues = inv.validation_issues || [];
                  return (
                    <tr key={inv.id}>
                      <td>
                        <StatusBadge 
                          status={inv.review_status} 
                          isHighValue={inv.is_high_value} 
                          isDuplicate={inv.is_duplicate} 
                        />
                      </td>
                      <td style={{ fontWeight: 700, color: '#0f172a' }}>{inv.invoice_number}</td>
                      <td style={{ fontWeight: 600, color: '#1e293b' }}>{inv.vendor_name}</td>
                      <td>
                        {issues.length > 0 ? (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
                            {issues.slice(0, 2).map((iss, i) => (
                              <span key={i} style={{ fontSize: '0.75rem', color: '#ef4444', fontWeight: 600 }}>
                                • {iss.message}
                              </span>
                            ))}
                            {issues.length > 2 && (
                              <span style={{ fontSize: '0.7rem', color: '#94a3b8' }}>
                                + {issues.length - 2} more issues
                              </span>
                            )}
                          </div>
                        ) : (
                          <span style={{ fontSize: '0.78rem', color: '#f59e0b' }}>
                            {inv.is_high_value ? 'High value policy trigger' : 'Pending review'}
                          </span>
                        )}
                      </td>
                      <td style={{ fontWeight: 700, color: '#0f172a' }}>
                        {currSym}{inv.total_amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                      </td>
                      <td style={{ color: '#64748b', fontSize: '0.8rem' }}>
                        {inv.created_at ? new Date(inv.created_at).toLocaleDateString() : '-'}
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        <button
                          className="btn btn-primary btn-sm"
                          onClick={() => onSelectInvoice(inv.id)}
                        >
                          <Edit3 size={14} /> Review & Fix
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
