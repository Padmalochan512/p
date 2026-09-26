import React, { useState, useEffect } from 'react';
import { 
  FileText, 
  CheckCircle2, 
  AlertTriangle, 
  IndianRupee, 
  UploadCloud, 
  ArrowRight,
  TrendingUp,
  Clock,
  PieChart as PieIcon,
  Layers
} from 'lucide-react';
import { 
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, 
  PieChart, Pie, Cell, AreaChart, Area 
} from 'recharts';
import { api } from '../services/api';
import { StatusBadge } from '../components/StatusBadge';
import { LoadingSpinner } from '../components/LoadingSpinner';

export function DashboardPage({ onNavigate, onSelectInvoice }) {
  const [summary, setSummary] = useState(null);
  const [activity, setActivity] = useState(null);
  const [recentInvoices, setRecentInvoices] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      const [sumData, actData, invData] = await Promise.all([
        api.getDashboardSummary(),
        api.getDashboardActivity(),
        api.getInvoices({ limit: 5 })
      ]);
      setSummary(sumData);
      setActivity(actData);
      setRecentInvoices(invData?.items || []);
    } catch (err) {
      console.error('Failed to load dashboard:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <LoadingSpinner message="Loading financial dashboard metrics..." />;
  }

  const currencySymbol = summary?.currency === 'INR' ? '₹' : (summary?.currency === 'USD' ? '$' : summary?.currency || '₹');

  return (
    <div>
      {/* KPI Cards Grid */}
      <div className="kpi-grid">
        <div className="kpi-card">
          <div>
            <div className="kpi-title">Total Invoices</div>
            <div className="kpi-value">{summary?.total_invoices || 0}</div>
            <div className="kpi-sub">Avg Confidence: {summary?.avg_confidence || 0}%</div>
          </div>
          <div className="kpi-icon-box kpi-icon-indigo">
            <FileText size={24} />
          </div>
        </div>

        <div className="kpi-card">
          <div>
            <div className="kpi-title">Validated & Passed</div>
            <div className="kpi-value" style={{ color: '#10b981' }}>{summary?.validated_invoices || 0}</div>
            <div className="kpi-sub">100% Math Match</div>
          </div>
          <div className="kpi-icon-box kpi-icon-emerald">
            <CheckCircle2 size={24} />
          </div>
        </div>

        <div className="kpi-card">
          <div>
            <div className="kpi-title">Needs Human Review</div>
            <div className="kpi-value" style={{ color: '#f59e0b' }}>
              {(summary?.needs_review_invoices || 0) + (summary?.flagged_invoices || 0)}
            </div>
            <div className="kpi-sub">{summary?.high_value_count || 0} High-Value Flagged</div>
          </div>
          <div className="kpi-icon-box kpi-icon-amber">
            <AlertTriangle size={24} />
          </div>
        </div>

        <div className="kpi-card">
          <div>
            <div className="kpi-title">Total Invoiced Value</div>
            <div className="kpi-value" style={{ color: '#4f46e5' }}>
              {currencySymbol}{(summary?.total_spend || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </div>
            <div className="kpi-sub">Across All Vendors</div>
          </div>
          <div className="kpi-icon-box kpi-icon-indigo">
            <TrendingUp size={24} />
          </div>
        </div>
      </div>

      {/* Charts Section */}
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '24px', marginBottom: '28px' }}>
        
        {/* Left: Processing Activity Over Time */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Document Processing Activity</h3>
            <span style={{ fontSize: '0.8rem', color: '#64748b' }}>Cumulative Timeline</span>
          </div>
          {activity?.timeline && activity.timeline.length > 0 ? (
            <div style={{ width: '100%', height: '260px' }}>
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={activity.timeline} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#4f46e5" stopOpacity={0.25}/>
                      <stop offset="95%" stopColor="#4f46e5" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="date" stroke="#94a3b8" fontSize={12} tickLine={false} />
                  <YAxis stroke="#94a3b8" fontSize={12} tickLine={false} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#ffffff', borderRadius: '8px', border: '1px solid #e2e8f0', boxShadow: '0 4px 6px rgba(0,0,0,0.05)' }}
                  />
                  <Area type="monotone" dataKey="processed_count" stroke="#4f46e5" strokeWidth={2.5} fillOpacity={1} fill="url(#colorCount)" name="Invoices Processed" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div style={{ padding: '60px 0', textAlign: 'center', color: '#94a3b8' }}>
              <Layers size={36} style={{ margin: '0 auto 10px', opacity: 0.5 }} />
              <p style={{ fontSize: '0.85rem' }}>No processing activity yet. Upload an invoice to view trends.</p>
            </div>
          )}
        </div>

        {/* Right: Status Distribution Donut Chart */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Status Breakdown</h3>
          </div>
          {activity?.status_distribution && activity.status_distribution.length > 0 ? (
            <div style={{ width: '100%', height: '220px', position: 'relative' }}>
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={activity.status_distribution}
                    cx="50%"
                    cy="50%"
                    innerRadius={55}
                    outerRadius={80}
                    paddingAngle={4}
                    dataKey="value"
                  >
                    {activity.status_distribution.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ backgroundColor: '#ffffff', borderRadius: '8px', border: '1px solid #e2e8f0' }} />
                </PieChart>
              </ResponsiveContainer>
              <div style={{ display: 'flex', justifyContent: 'center', gap: '12px', flexWrap: 'wrap', marginTop: '10px' }}>
                {activity.status_distribution.map((entry) => (
                  <div key={entry.name} style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '0.75rem', color: '#475569' }}>
                    <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: entry.color }} />
                    <span>{entry.name}: {entry.value}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div style={{ padding: '60px 0', textAlign: 'center', color: '#94a3b8' }}>
              <PieIcon size={36} style={{ margin: '0 auto 10px', opacity: 0.5 }} />
              <p style={{ fontSize: '0.85rem' }}>No status distribution data.</p>
            </div>
          )}
        </div>

      </div>

      {/* Recent Invoices Table */}
      <div className="card">
        <div className="card-header">
          <div>
            <h3 className="card-title">Recent Invoices</h3>
            <p style={{ fontSize: '0.8rem', color: '#64748b' }}>Latest extracted and cross-validated business documents</p>
          </div>
          <button 
            className="btn btn-secondary btn-sm"
            onClick={() => onNavigate('invoices')}
          >
            <span>View All Invoices</span>
            <ArrowRight size={14} />
          </button>
        </div>

        <div className="table-container">
          <table className="app-table">
            <thead>
              <tr>
                <th>Status</th>
                <th>Invoice #</th>
                <th>Vendor Name</th>
                <th>Date</th>
                <th>Total Amount</th>
                <th>Confidence</th>
                <th style={{ textAlign: 'right' }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {recentInvoices.length === 0 ? (
                <tr>
                  <td colSpan={7} style={{ textAlign: 'center', padding: '40px', color: '#94a3b8' }}>
                    No invoices recorded yet. Click "Upload Documents" or "Load Test Invoices" to begin!
                  </td>
                </tr>
              ) : (
                recentInvoices.map((inv) => (
                  <tr key={inv.id}>
                    <td>
                      <StatusBadge 
                        status={inv.review_status} 
                        isHighValue={inv.is_high_value} 
                        isDuplicate={inv.is_duplicate} 
                      />
                    </td>
                    <td style={{ fontWeight: 700, color: '#0f172a' }}>{inv.invoice_number}</td>
                    <td style={{ fontWeight: 600, color: '#334155' }}>{inv.vendor_name}</td>
                    <td style={{ color: '#64748b' }}>{inv.invoice_date || '-'}</td>
                    <td style={{ fontWeight: 700, color: '#0f172a' }}>
                      {inv.currency === 'INR' ? '₹' : (inv.currency === 'USD' ? '$' : inv.currency)}
                      {inv.total_amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </td>
                    <td>
                      <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#475569' }}>
                        {Math.round((inv.confidence_score || 1.0) * 100)}%
                      </span>
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <button
                        className="btn btn-secondary btn-sm"
                        onClick={() => onSelectInvoice(inv.id)}
                      >
                        Review
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
