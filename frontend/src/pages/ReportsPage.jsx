import React, { useState, useEffect } from 'react';
import { 
  BarChart3, 
  Download, 
  Calendar, 
  FileSpreadsheet, 
  IndianRupee,
  Layers
} from 'lucide-react';
import { 
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid 
} from 'recharts';
import { api } from '../services/api';
import { LoadingSpinner } from '../components/LoadingSpinner';

export function ReportsPage() {
  const [reportsData, setReportsData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  useEffect(() => {
    loadReports();
  }, [startDate, endDate]);

  const loadReports = async () => {
    try {
      setLoading(true);
      const data = await api.getReportsSummary({ start_date: startDate, end_date: endDate });
      setReportsData(data);
    } catch (err) {
      console.error('Failed to load reports:', err);
    } finally {
      setLoading(false);
    }
  };

  const currSym = reportsData?.currency === 'INR' ? '₹' : (reportsData?.currency === 'USD' ? '$' : reportsData?.currency || '₹');

  return (
    <div>
      {/* Header & Export Bar */}
      <div className="card" style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <h2 className="card-title">Financial Reports & Spend Analytics</h2>
            <p style={{ fontSize: '0.8rem', color: '#64748b' }}>
              Vendor expenditure breakdowns, monthly volume analysis, and structured ledger exports
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <a
              href={`/api/reports/export?${startDate ? `start_date=${startDate}&` : ''}${endDate ? `end_date=${endDate}` : ''}`}
              download
              className="btn btn-secondary btn-sm"
              style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
            >
              <Download size={14} /> Export Invoices CSV
            </a>
            <a
              href="/api/reports/line-items-export"
              download
              className="btn btn-primary btn-sm"
              style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
            >
              <FileSpreadsheet size={14} /> Export Line Items CSV
            </a>
          </div>
        </div>

        {/* Date Filter */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px', marginTop: '16px', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '0.82rem', fontWeight: 600, color: '#475569' }}>Filter Dates:</span>
            <input
              type="date"
              className="form-input"
              style={{ width: '160px' }}
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
            />
            <span style={{ fontSize: '0.82rem', color: '#94a3b8' }}>to</span>
            <input
              type="date"
              className="form-input"
              style={{ width: '160px' }}
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
            />
          </div>
          {(startDate || endDate) && (
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => { setStartDate(''); setEndDate(''); }}
            >
              Reset Filters
            </button>
          )}
        </div>
      </div>

      {loading ? (
        <LoadingSpinner message="Calculating financial aggregations..." />
      ) : (
        <>
          {/* Summary Cards */}
          <div className="kpi-grid">
            <div className="kpi-card">
              <div>
                <div className="kpi-title">Total Spend Billed</div>
                <div className="kpi-value" style={{ color: '#4f46e5' }}>
                  {currSym}{(reportsData?.total_spend || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                </div>
                <div className="kpi-sub">{reportsData?.total_invoices || 0} Invoices Filtered</div>
              </div>
            </div>

            <div className="kpi-card">
              <div>
                <div className="kpi-title">Total Tax / GST Paid</div>
                <div className="kpi-value" style={{ color: '#10b981' }}>
                  {currSym}{(reportsData?.total_tax || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                </div>
                <div className="kpi-sub">Input Tax Credit eligible</div>
              </div>
            </div>

            <div className="kpi-card">
              <div>
                <div className="kpi-title">Unique Vendors</div>
                <div className="kpi-value" style={{ color: '#0f172a' }}>
                  {(reportsData?.vendor_breakdown || []).length}
                </div>
                <div className="kpi-sub">Active Suppliers</div>
              </div>
            </div>
          </div>

          {/* Monthly Spend Chart */}
          <div className="card" style={{ marginBottom: '24px' }}>
            <div className="card-header">
              <h3 className="card-title">Monthly Expenditure Breakdown</h3>
            </div>
            {reportsData?.monthly_breakdown && reportsData.monthly_breakdown.length > 0 ? (
              <div style={{ width: '100%', height: '280px' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={reportsData.monthly_breakdown} margin={{ top: 10, right: 10, left: 10, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                    <XAxis dataKey="month" stroke="#94a3b8" fontSize={12} tickLine={false} />
                    <YAxis stroke="#94a3b8" fontSize={12} tickLine={false} />
                    <Tooltip contentStyle={{ backgroundColor: '#ffffff', borderRadius: '8px', border: '1px solid #e2e8f0' }} />
                    <Bar dataKey="total_amount" fill="#4f46e5" radius={[6, 6, 0, 0]} name={`Total (${currSym})`} />
                    <Bar dataKey="tax_amount" fill="#10b981" radius={[6, 6, 0, 0]} name={`Tax (${currSym})`} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: '50px 0', color: '#94a3b8' }}>
                No monthly data found.
              </div>
            )}
          </div>

          {/* Vendor-Wise Spend Table */}
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">Vendor-Wise Spending Breakdown</h3>
            </div>
            <div className="table-container">
              <table className="app-table">
                <thead>
                  <tr>
                    <th>Vendor Name</th>
                    <th>Invoices Count</th>
                    <th>Total Spend ({currSym})</th>
                    <th>Share of Total</th>
                  </tr>
                </thead>
                <tbody>
                  {(reportsData?.vendor_breakdown || []).length === 0 ? (
                    <tr>
                      <td colSpan={4} style={{ textAlign: 'center', padding: '30px', color: '#94a3b8' }}>
                        No vendor records.
                      </td>
                    </tr>
                  ) : (
                    reportsData.vendor_breakdown.map((v, i) => {
                      const share = reportsData.total_spend > 0 
                        ? ((v.total_amount / reportsData.total_spend) * 100).toFixed(1)
                        : '0';
                      return (
                        <tr key={i}>
                          <td style={{ fontWeight: 600, color: '#0f172a' }}>{v.vendor}</td>
                          <td>{v.count}</td>
                          <td style={{ fontWeight: 700, color: '#4f46e5' }}>
                            {currSym}{v.total_amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                          </td>
                          <td>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                              <div style={{ flex: 1, height: '6px', backgroundColor: '#e2e8f0', borderRadius: '99px', overflow: 'hidden' }}>
                                <div style={{ height: '100%', width: `${share}%`, backgroundColor: '#4f46e5' }} />
                              </div>
                              <span style={{ fontSize: '0.78rem', color: '#64748b', minWidth: '36px' }}>{share}%</span>
                            </div>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
