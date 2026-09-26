import React, { useState, useEffect } from 'react';
import { 
  ArrowLeft, 
  CheckCircle2, 
  AlertTriangle, 
  Clock, 
  RefreshCw, 
  Save, 
  ZoomIn, 
  ZoomOut, 
  RotateCcw, 
  ExternalLink,
  Plus,
  Trash2,
  Calculator,
  ShieldCheck
} from 'lucide-react';
import { api } from '../services/api';
import { StatusBadge } from '../components/StatusBadge';
import { LoadingSpinner } from '../components/LoadingSpinner';

export function InvoiceReviewPage({ invoiceId, onBack, onReloadList }) {
  const [invoice, setInvoice] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [zoom, setZoom] = useState(1.0);
  const [saveMessage, setSaveMessage] = useState('');

  // Editable Form State
  const [formData, setFormData] = useState({
    vendor_name: '',
    vendor_tax_id: '',
    invoice_number: '',
    po_number: '',
    invoice_date: '',
    due_date: '',
    currency: 'INR',
    subtotal: 0,
    tax_amount: 0,
    shipping_amount: 0,
    discount_amount: 0,
    total_amount: 0,
    reviewer_notes: '',
    line_items: []
  });

  useEffect(() => {
    if (invoiceId) {
      loadInvoiceDetails(invoiceId);
    }
  }, [invoiceId]);

  const loadInvoiceDetails = async (id) => {
    try {
      setLoading(true);
      const data = await api.getInvoice(id);
      setInvoice(data);
      setFormData({
        vendor_name: data.vendor_name || '',
        vendor_tax_id: data.vendor_tax_id || '',
        invoice_number: data.invoice_number || '',
        po_number: data.po_number || '',
        invoice_date: data.invoice_date || '',
        due_date: data.due_date || '',
        currency: data.currency || 'INR',
        subtotal: data.subtotal || 0,
        tax_amount: data.tax_amount || 0,
        shipping_amount: data.shipping_amount || 0,
        discount_amount: data.discount_amount || 0,
        total_amount: data.total_amount || 0,
        reviewer_notes: data.reviewer_notes || '',
        line_items: data.line_items || []
      });
    } catch (err) {
      console.error('Failed to load invoice details:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleFieldChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleLineItemChange = (index, field, value) => {
    const updated = [...formData.line_items];
    const item = { ...updated[index], [field]: value };
    
    if (field === 'quantity' || field === 'unit_price') {
      const q = parseFloat(field === 'quantity' ? value : item.quantity) || 0;
      const p = parseFloat(field === 'unit_price' ? value : item.unit_price) || 0;
      item.line_total = parseFloat((q * p).toFixed(2));
      item.is_math_match = true;
    }
    
    updated[index] = item;
    setFormData(prev => ({ ...prev, line_items: updated }));
    autoRecalculateTotals(updated);
  };

  const handleAddLineItem = () => {
    setFormData(prev => ({
      ...prev,
      line_items: [
        ...prev.line_items,
        {
          description: 'New Line Item',
          quantity: 1,
          unit_price: 0,
          tax_rate: 0,
          line_total: 0,
          is_math_match: true
        }
      ]
    }));
  };

  const handleRemoveLineItem = (index) => {
    const updated = formData.line_items.filter((_, i) => i !== index);
    setFormData(prev => ({ ...prev, line_items: updated }));
    autoRecalculateTotals(updated);
  };

  const autoRecalculateTotals = (items) => {
    const lineSum = items.reduce((acc, it) => acc + (parseFloat(it.line_total) || 0), 0);
    const sub = parseFloat(lineSum.toFixed(2));
    const tax = parseFloat(formData.tax_amount) || 0;
    const ship = parseFloat(formData.shipping_amount) || 0;
    const disc = parseFloat(formData.discount_amount) || 0;
    const grand = parseFloat((sub + tax + ship - disc).toFixed(2));

    setFormData(prev => ({
      ...prev,
      subtotal: sub,
      total_amount: grand
    }));
  };

  const handleSaveChanges = async (forcedStatus = null) => {
    setSaving(true);
    setSaveMessage('');
    try {
      const payload = {
        ...formData,
        subtotal: parseFloat(formData.subtotal) || 0,
        tax_amount: parseFloat(formData.tax_amount) || 0,
        shipping_amount: parseFloat(formData.shipping_amount) || 0,
        discount_amount: parseFloat(formData.discount_amount) || 0,
        total_amount: parseFloat(formData.total_amount) || 0,
        review_status: forcedStatus || invoice.review_status
      };

      const updated = await api.updateInvoice(invoice.id, payload);
      setInvoice(updated);
      setFormData(prev => ({
        ...prev,
        subtotal: updated.subtotal,
        total_amount: updated.total_amount,
        line_items: updated.line_items
      }));
      setSaveMessage('Invoice details successfully updated and re-validated.');
      setTimeout(() => setSaveMessage(''), 4000);
      if (onReloadList) onReloadList();
    } catch (err) {
      alert('Save failed: ' + err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleApprove = async () => {
    setSaving(true);
    try {
      const updated = await api.approveInvoice(invoice.id);
      setInvoice(updated);
      setSaveMessage('Invoice marked as Approved.');
      setTimeout(() => setSaveMessage(''), 4000);
      if (onReloadList) onReloadList();
    } catch (err) {
      alert('Approval failed: ' + err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleMarkReview = async () => {
    setSaving(true);
    try {
      const updated = await api.markForReview(invoice.id);
      setInvoice(updated);
      setSaveMessage('Invoice marked for review.');
      setTimeout(() => setSaveMessage(''), 4000);
      if (onReloadList) onReloadList();
    } catch (err) {
      alert('Action failed: ' + err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleReprocess = async () => {
    if (!confirm('Re-run AI and OCR extraction on the original document? Unsaved changes will be replaced.')) return;
    setSaving(true);
    try {
      const updated = await api.reprocessInvoice(invoice.id);
      setInvoice(updated);
      loadInvoiceDetails(updated.id);
      setSaveMessage('Document reprocessed successfully.');
      setTimeout(() => setSaveMessage(''), 4000);
    } catch (err) {
      alert('Reprocess error: ' + err.message);
    } finally {
      setSaving(false);
    }
  };

  if (loading || !invoice) {
    return <LoadingSpinner message="Loading document and verification data..." />;
  }

  const issues = invoice.validation_issues || [];

  return (
    <div>
      {/* Top Header Controls */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
        <button
          className="btn btn-secondary btn-sm"
          onClick={onBack}
          style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
        >
          <ArrowLeft size={16} /> Back to Invoices
        </button>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <StatusBadge 
            status={invoice.review_status} 
            isHighValue={invoice.is_high_value} 
            isDuplicate={invoice.is_duplicate} 
          />
          <button
            className="btn btn-secondary btn-sm"
            onClick={handleReprocess}
            disabled={saving}
            title="Re-run AI extraction pipeline"
          >
            <RefreshCw size={14} /> Reprocess
          </button>
          <button
            className="btn btn-primary btn-sm"
            onClick={() => handleSaveChanges()}
            disabled={saving}
          >
            <Save size={14} /> Save Changes
          </button>
          <button
            className="btn btn-success btn-sm"
            onClick={handleApprove}
            disabled={saving}
          >
            <CheckCircle2 size={14} /> Approve Invoice
          </button>
        </div>
      </div>

      {saveMessage && (
        <div style={{
          backgroundColor: '#ecfdf5',
          border: '1px solid #a7f3d0',
          color: '#065f46',
          padding: '10px 16px',
          borderRadius: '8px',
          marginBottom: '18px',
          fontSize: '0.85rem',
          fontWeight: 600
        }}>
          {saveMessage}
        </div>
      )}

      {/* Two-Column Split Screen */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1.2fr',
        gap: '24px',
        minHeight: 'calc(100vh - 190px)'
      }}>
        
        {/* Left Column: Original Document Viewport */}
        <div className="card" style={{ padding: '0', display: 'flex', flexDirection: 'column', overflow: 'hidden', height: '100%' }}>
          <div style={{
            padding: '12px 18px',
            borderBottom: '1px solid #e2e8f0',
            backgroundColor: '#f8fafc',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between'
          }}>
            <span style={{ fontWeight: 700, fontSize: '0.85rem', color: '#0f172a' }}>
              Original Document Preview
            </span>
            <div style={{ display: 'flex', gap: '6px' }}>
              <button
                className="btn-icon"
                style={{ width: '30px', height: '30px' }}
                onClick={() => setZoom(z => Math.min(z + 0.2, 3.0))}
                title="Zoom In"
              >
                <ZoomIn size={14} />
              </button>
              <button
                className="btn-icon"
                style={{ width: '30px', height: '30px' }}
                onClick={() => setZoom(z => Math.max(z - 0.2, 0.5))}
                title="Zoom Out"
              >
                <ZoomOut size={14} />
              </button>
              <button
                className="btn-icon"
                style={{ width: '30px', height: '30px' }}
                onClick={() => setZoom(1.0)}
                title="Reset Zoom"
              >
                <RotateCcw size={14} />
              </button>
              <a
                href={`/api/documents/${invoice.document_id}/file`}
                target="_blank"
                rel="noreferrer"
                className="btn-icon"
                style={{ width: '30px', height: '30px', textDecoration: 'none' }}
                title="Open Raw File in New Tab"
              >
                <ExternalLink size={14} />
              </a>
            </div>
          </div>

          <div style={{
            flex: 1,
            backgroundColor: '#0f172a',
            overflow: 'auto',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '20px'
          }}>
            <img
              src={`/api/documents/${invoice.document_id}/preview`}
              alt="Document Preview"
              style={{
                maxWidth: '100%',
                transform: `scale(${zoom})`,
                transition: 'transform 0.15s ease',
                boxShadow: '0 10px 25px rgba(0,0,0,0.5)',
                borderRadius: '4px'
              }}
              onError={(e) => {
                e.target.style.display = 'none';
                e.target.parentElement.innerHTML = '<div style="color: #94a3b8; font-size: 0.85rem;">Document preview rendering...</div>';
              }}
            />
          </div>
        </div>

        {/* Right Column: Extracted Fields & Live Validation */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', overflowY: 'auto', maxHeight: '820px' }}>
          
          {/* Validation Issues Alert Banner */}
          {issues.length > 0 && (
            <div style={{
              backgroundColor: '#fef2f2',
              border: '1px solid #fecaca',
              borderRadius: '10px',
              padding: '14px',
              marginBottom: '20px'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 700, color: '#991b1b', fontSize: '0.88rem', marginBottom: '8px' }}>
                <AlertTriangle size={18} />
                <span>Validation Issues & Discrepancies ({issues.length})</span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {issues.map((iss, idx) => (
                  <div key={idx} style={{ fontSize: '0.8rem', color: '#b91c1c', lineHeight: 1.4 }}>
                    • {iss.message}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Form Fields Header */}
          <div className="card-header" style={{ marginBottom: '16px' }}>
            <div>
              <h3 className="card-title">Extracted Data & Verification</h3>
              <p style={{ fontSize: '0.78rem', color: '#64748b' }}>
                Extracted via {invoice.extraction_method} ({Math.round(invoice.confidence_score * 100)}% confidence)
              </p>
            </div>
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => autoRecalculateTotals(formData.line_items)}
              title="Recalculate totals from line rows"
            >
              <Calculator size={14} /> Recalculate
            </button>
          </div>

          {/* Metadata Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
            <div className="form-group">
              <label className="form-label">Vendor Name</label>
              <input
                type="text"
                className="form-input"
                value={formData.vendor_name}
                onChange={(e) => handleFieldChange('vendor_name', e.target.value)}
              />
            </div>
            <div className="form-group">
              <label className="form-label">Vendor GSTIN / Tax ID</label>
              <input
                type="text"
                className="form-input"
                value={formData.vendor_tax_id}
                onChange={(e) => handleFieldChange('vendor_tax_id', e.target.value)}
              />
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '14px' }}>
            <div className="form-group">
              <label className="form-label">Invoice Number #</label>
              <input
                type="text"
                className="form-input"
                value={formData.invoice_number}
                onChange={(e) => handleFieldChange('invoice_number', e.target.value)}
              />
            </div>
            <div className="form-group">
              <label className="form-label">Invoice Date</label>
              <input
                type="date"
                className="form-input"
                value={formData.invoice_date}
                onChange={(e) => handleFieldChange('invoice_date', e.target.value)}
              />
            </div>
            <div className="form-group">
              <label className="form-label">Due Date</label>
              <input
                type="date"
                className="form-input"
                value={formData.due_date}
                onChange={(e) => handleFieldChange('due_date', e.target.value)}
              />
            </div>
          </div>

          {/* Line Items Editor */}
          <div style={{ margin: '16px 0' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
              <span style={{ fontSize: '0.82rem', fontWeight: 700, color: '#0f172a', textTransform: 'uppercase' }}>
                Line Items ({formData.line_items.length})
              </span>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={handleAddLineItem}
              >
                <Plus size={14} /> Add Item
              </button>
            </div>

            <div className="table-container" style={{ maxHeight: '220px', overflowY: 'auto' }}>
              <table className="app-table">
                <thead>
                  <tr>
                    <th>Description</th>
                    <th style={{ width: '70px' }}>Qty</th>
                    <th style={{ width: '110px' }}>Unit Price</th>
                    <th style={{ width: '110px' }}>Total</th>
                    <th style={{ width: '40px' }}></th>
                  </tr>
                </thead>
                <tbody>
                  {formData.line_items.map((item, idx) => (
                    <tr key={idx}>
                      <td>
                        <input
                          type="text"
                          className="form-input"
                          style={{ padding: '6px 8px' }}
                          value={item.description}
                          onChange={(e) => handleLineItemChange(idx, 'description', e.target.value)}
                        />
                      </td>
                      <td>
                        <input
                          type="number"
                          step="0.5"
                          className="form-input"
                          style={{ padding: '6px 8px', textAlign: 'right' }}
                          value={item.quantity}
                          onChange={(e) => handleLineItemChange(idx, 'quantity', e.target.value)}
                        />
                      </td>
                      <td>
                        <input
                          type="number"
                          step="0.01"
                          className="form-input"
                          style={{ padding: '6px 8px', textAlign: 'right' }}
                          value={item.unit_price}
                          onChange={(e) => handleLineItemChange(idx, 'unit_price', e.target.value)}
                        />
                      </td>
                      <td>
                        <input
                          type="number"
                          step="0.01"
                          className={`form-input ${!item.is_math_match ? 'error' : ''}`}
                          style={{ padding: '6px 8px', textAlign: 'right', fontWeight: 700 }}
                          value={item.line_total}
                          onChange={(e) => handleLineItemChange(idx, 'line_total', e.target.value)}
                        />
                      </td>
                      <td style={{ textAlign: 'center' }}>
                        <button
                          type="button"
                          onClick={() => handleRemoveLineItem(idx)}
                          style={{ background: 'none', border: 'none', color: '#ef4444', cursor: 'pointer' }}
                        >
                          <Trash2 size={15} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Summary Totals Form */}
          <div style={{
            backgroundColor: '#f8fafc',
            border: '1px solid #e2e8f0',
            borderRadius: '10px',
            padding: '16px',
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            gap: '14px',
            marginBottom: '16px'
          }}>
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label className="form-label">Subtotal</label>
              <input
                type="number"
                step="0.01"
                className="form-input"
                value={formData.subtotal}
                onChange={(e) => handleFieldChange('subtotal', parseFloat(e.target.value) || 0)}
              />
            </div>
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label className="form-label">Tax / GST Amount</label>
              <input
                type="number"
                step="0.01"
                className="form-input"
                value={formData.tax_amount}
                onChange={(e) => handleFieldChange('tax_amount', parseFloat(e.target.value) || 0)}
              />
            </div>
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label className="form-label">Shipping / Freight</label>
              <input
                type="number"
                step="0.01"
                className="form-input"
                value={formData.shipping_amount}
                onChange={(e) => handleFieldChange('shipping_amount', parseFloat(e.target.value) || 0)}
              />
            </div>
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label className="form-label">Discount Amount</label>
              <input
                type="number"
                step="0.01"
                className="form-input"
                value={formData.discount_amount}
                onChange={(e) => handleFieldChange('discount_amount', parseFloat(e.target.value) || 0)}
              />
            </div>
            <div className="form-group" style={{ gridColumn: 'span 2', marginBottom: 0 }}>
              <label className="form-label" style={{ color: '#4f46e5', fontWeight: 700 }}>
                Grand Total Amount ({formData.currency})
              </label>
              <input
                type="number"
                step="0.01"
                className="form-input"
                style={{ fontSize: '1.2rem', fontWeight: 800, color: '#4f46e5' }}
                value={formData.total_amount}
                onChange={(e) => handleFieldChange('total_amount', parseFloat(e.target.value) || 0)}
              />
            </div>
          </div>

          {/* Reviewer Notes */}
          <div className="form-group">
            <label className="form-label">Auditor & Verification Notes</label>
            <textarea
              className="form-input"
              rows={2}
              placeholder="Add comments regarding corrections, PO matching, or sign-off..."
              value={formData.reviewer_notes}
              onChange={(e) => handleFieldChange('reviewer_notes', e.target.value)}
            />
          </div>

          {/* Bottom Action Buttons */}
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '10px' }}>
            <button
              className="btn btn-secondary"
              onClick={handleMarkReview}
              disabled={saving}
            >
              <Clock size={16} /> Mark for Review
            </button>
            <button
              className="btn btn-primary"
              onClick={() => handleSaveChanges()}
              disabled={saving}
            >
              <Save size={16} /> Save Changes
            </button>
            <button
              className="btn btn-success"
              onClick={handleApprove}
              disabled={saving}
            >
              <CheckCircle2 size={16} /> Approve & Finalize
            </button>
          </div>

        </div>

      </div>
    </div>
  );
}
