import React, { useState, useEffect } from 'react';
import { 
  Search, 
  Filter, 
  Download, 
  Trash2, 
  Edit3, 
  Eye, 
  ChevronLeft, 
  ChevronRight,
  Sparkles,
  Plus
} from 'lucide-react';
import { api } from '../services/api';
import { StatusBadge } from '../components/StatusBadge';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { ConfirmModal } from '../components/ConfirmModal';

export function InvoicesPage({ onSelectInvoice, onNavigate }) {
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalCount, setTotalCount] = useState(0);

  // Modal state
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [invoiceToDelete, setInvoiceToDelete] = useState(null);

  useEffect(() => {
    loadInvoices();
  }, [searchQuery, statusFilter, startDate, endDate, page]);

  const loadInvoices = async () => {
    try {
      setLoading(true);
      const res = await api.getInvoices({
        q: searchQuery,
        status: statusFilter,
        start_date: startDate,
        end_date: endDate,
        page,
        limit: 10
      });
      setInvoices(res.items || []);
      setTotalPages(res.total_pages || 1);
      setTotalCount(res.total || 0);
    } catch (err) {
      console.error('Failed to load invoices:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteConfirm = async () => {
    if (!invoiceToDelete) return;
    try {
      await api.deleteInvoice(invoiceToDelete.id);
      setDeleteModalOpen(false);
      setInvoiceToDelete(null);
      loadInvoices();
    } catch (err) {
      alert('Failed to delete invoice: ' + err.message);
    }
  };

  return (
    <div>
      {/* Top Action Bar */}
      <div className="card" style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <h2 className="card-title">All Invoices & Ledger</h2>
            <p style={{ fontSize: '0.8rem', color: '#64748b' }}>
              {totalCount} total invoice records stored in database
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <a
              href="/api/reports/export"
              download
              className="btn btn-secondary btn-sm"
              style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
            >
              <Download size={14} /> Export CSV
            </a>
            <button
              className="btn btn-primary btn-sm"
              onClick={() => onNavigate('upload')}
            >
              <Plus size={15} /> Upload Invoices
            </button>
          </div>
        </div>

        {/* Filter Controls */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '14px', marginTop: '18px' }}>
          
          {/* Search Input */}
          <div style={{ position: 'relative' }}>
            <Search size={16} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: '#94a3b8' }} />
            <input
              type="text"
              placeholder="Search vendor, invoice #..."
              className="form-input"
              style={{ paddingLeft: '36px' }}
              value={searchQuery}
              onChange={(e) => { setSearchQuery(e.target.value); setPage(1); }}
            />
          </div>

          {/* Status Dropdown */}
          <div>
            <select
              className="form-input"
              value={statusFilter}
              onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
            >
              <option value="ALL">All Statuses</option>
              <option value="APPROVED">Approved (Validated)</option>
              <option value="NEEDS_REVIEW">Needs Review</option>
              <option value="FLAGGED">Flagged (Discrepancies)</option>
              <option value="REJECTED">Rejected</option>
            </select>
          </div>

          {/* Start Date */}
          <div>
            <input
              type="date"
              className="form-input"
              placeholder="Start Date"
              value={startDate}
              onChange={(e) => { setStartDate(e.target.value); setPage(1); }}
            />
          </div>

          {/* End Date */}
          <div>
            <input
              type="date"
              className="form-input"
              placeholder="End Date"
              value={endDate}
              onChange={(e) => { setEndDate(e.target.value); setPage(1); }}
            />
          </div>

        </div>
      </div>

      {/* Invoices Table Card */}
      <div className="card">
        {loading ? (
          <LoadingSpinner message="Fetching invoice records..." />
        ) : (
          <>
            <div className="table-container">
              <table className="app-table">
                <thead>
                  <tr>
                    <th>Status</th>
                    <th>Invoice #</th>
                    <th>Vendor Name</th>
                    <th>Issue Date</th>
                    <th>Due Date</th>
                    <th>Subtotal</th>
                    <th>Tax</th>
                    <th>Grand Total</th>
                    <th>Flags</th>
                    <th style={{ textAlign: 'right' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {invoices.length === 0 ? (
                    <tr>
                      <td colSpan={10} style={{ textAlign: 'center', padding: '48px 20px', color: '#94a3b8' }}>
                        No invoices match your filter criteria.
                      </td>
                    </tr>
                  ) : (
                    invoices.map((inv) => {
                      const currSym = inv.currency === 'INR' ? '₹' : (inv.currency === 'USD' ? '$' : inv.currency);
                      const issueCount = inv.validation_issues ? inv.validation_issues.length : 0;
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
                          <td>
                            <div style={{ fontWeight: 600, color: '#1e293b' }}>{inv.vendor_name}</div>
                            {inv.vendor_tax_id && (
                              <div style={{ fontSize: '0.72rem', color: '#64748b' }}>GST: {inv.vendor_tax_id}</div>
                            )}
                          </td>
                          <td style={{ color: '#475569' }}>{inv.invoice_date || '-'}</td>
                          <td style={{ color: '#475569' }}>{inv.due_date || '-'}</td>
                          <td style={{ color: '#475569' }}>{currSym}{inv.subtotal.toFixed(2)}</td>
                          <td style={{ color: '#475569' }}>{currSym}{inv.tax_amount.toFixed(2)}</td>
                          <td style={{ fontWeight: 700, color: '#0f172a' }}>{currSym}{inv.total_amount.toFixed(2)}</td>
                          <td>
                            {issueCount > 0 ? (
                              <span style={{ fontSize: '0.78rem', color: '#ef4444', fontWeight: 600 }}>
                                ⚠️ {issueCount} issue(s)
                              </span>
                            ) : (
                              <span style={{ fontSize: '0.78rem', color: '#10b981', fontWeight: 600 }}>
                                ✓ Verified
                              </span>
                            )}
                          </td>
                          <td style={{ textAlign: 'right' }}>
                            <div style={{ display: 'inline-flex', gap: '6px' }}>
                              <button
                                className="btn btn-secondary btn-sm"
                                onClick={() => onSelectInvoice(inv.id)}
                                title="Inspect & Review"
                              >
                                <Edit3 size={14} /> Review
                              </button>
                              <button
                                className="btn-icon"
                                onClick={() => {
                                  setInvoiceToDelete(inv);
                                  setDeleteModalOpen(true);
                                }}
                                title="Delete"
                                style={{ width: '32px', height: '32px', color: '#ef4444' }}
                              >
                                <Trash2 size={15} />
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>

            {/* Pagination Controls */}
            {totalPages > 1 && (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '20px' }}>
                <span style={{ fontSize: '0.82rem', color: '#64748b' }}>
                  Showing Page {page} of {totalPages}
                </span>
                <div style={{ display: 'flex', gap: '6px' }}>
                  <button
                    className="btn btn-secondary btn-sm"
                    disabled={page <= 1}
                    onClick={() => setPage(p => p - 1)}
                  >
                    <ChevronLeft size={16} /> Previous
                  </button>
                  <button
                    className="btn btn-secondary btn-sm"
                    disabled={page >= totalPages}
                    onClick={() => setPage(p => p + 1)}
                  >
                    Next <ChevronRight size={16} />
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* Confirmation Modal */}
      <ConfirmModal
        isOpen={deleteModalOpen}
        title="Delete Invoice Record"
        message={`Are you sure you want to permanently remove invoice #${invoiceToDelete?.invoice_number} from '${invoiceToDelete?.vendor_name}'? The associated uploaded file will also be deleted.`}
        confirmText="Delete Invoice"
        isDanger={true}
        onConfirm={handleDeleteConfirm}
        onCancel={() => setDeleteModalOpen(false)}
      />
    </div>
  );
}
