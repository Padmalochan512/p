import React, { useState, useEffect } from 'react';
import { 
  Settings as SettingsIcon, 
  Save, 
  ShieldCheck, 
  Cpu, 
  Database, 
  CheckCircle2,
  Lock,
  Zap,
  Info
} from 'lucide-react';
import { api } from '../services/api';
import { LoadingSpinner } from '../components/LoadingSpinner';

export function SettingsPage() {
  const [settingsData, setSettingsData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');

  // Form states
  const [fullName, setFullName] = useState('');
  const [defaultCurrency, setDefaultCurrency] = useState('INR');
  const [alertThreshold, setAlertThreshold] = useState(50000);
  const [llmProvider, setLlmProvider] = useState('heuristic');
  const [geminiKey, setGeminiKey] = useState('');
  const [openaiKey, setOpenaiKey] = useState('');
  const [webhookUrl, setWebhookUrl] = useState('');

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      setLoading(true);
      const res = await api.getSettings();
      setSettingsData(res);
      setFullName(res.user_profile?.full_name || '');
      setDefaultCurrency(res.default_currency || 'INR');
      setAlertThreshold(res.alert_threshold || 50000);
      setLlmProvider(res.llm_provider || 'heuristic');
    } catch (err) {
      console.error('Failed to load settings:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveSettings = async (e) => {
    e.preventDefault();
    setSaving(true);
    setMessage('');
    try {
      const res = await api.updateSettings({
        full_name: fullName,
        default_currency: defaultCurrency,
        alert_threshold: parseFloat(alertThreshold) || 50000,
        llm_provider: llmProvider,
        gemini_api_key: geminiKey || undefined,
        openai_api_key: openaiKey || undefined,
        webhook_alert_url: webhookUrl || undefined
      });
      setSettingsData(res);
      setMessage('Settings updated successfully.');
      setTimeout(() => setMessage(''), 4000);
    } catch (err) {
      alert('Failed to update settings: ' + err.message);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <LoadingSpinner message="Loading application settings..." />;
  }

  return (
    <div style={{ maxWidth: '850px', margin: '0 auto' }}>
      
      <div className="card" style={{ marginBottom: '24px' }}>
        <h2 className="card-title">System & User Configuration</h2>
        <p style={{ fontSize: '0.8rem', color: '#64748b' }}>
          Configure OCR engines, default currencies, AI LLM vision integrations, and policy thresholds.
        </p>
      </div>

      {message && (
        <div style={{
          backgroundColor: '#ecfdf5',
          border: '1px solid #a7f3d0',
          color: '#065f46',
          padding: '12px 16px',
          borderRadius: '8px',
          marginBottom: '20px',
          fontSize: '0.85rem',
          display: 'flex',
          alignItems: 'center',
          gap: '8px'
        }}>
          <CheckCircle2 size={16} />
          <span>{message}</span>
        </div>
      )}

      <form onSubmit={handleSaveSettings}>
        
        {/* User Profile Card */}
        <div className="card" style={{ marginBottom: '24px' }}>
          <h3 className="card-title" style={{ marginBottom: '16px' }}>User Profile & Accounting Defaults</h3>
          
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            <div className="form-group">
              <label className="form-label">Full Name</label>
              <input
                type="text"
                className="form-input"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
              />
            </div>

            <div className="form-group">
              <label className="form-label">Email Address (Read-only)</label>
              <input
                type="text"
                disabled
                className="form-input"
                style={{ backgroundColor: '#f1f5f9', color: '#64748b' }}
                value={settingsData?.user_profile?.email || ''}
              />
            </div>

            <div className="form-group">
              <label className="form-label">Default Base Currency</label>
              <select
                className="form-input"
                value={defaultCurrency}
                onChange={(e) => setDefaultCurrency(e.target.value)}
              >
                <option value="INR">INR (₹ - Indian Rupee)</option>
                <option value="USD">USD ($ - US Dollar)</option>
                <option value="EUR">EUR (€ - Euro)</option>
                <option value="GBP">GBP (£ - British Pound)</option>
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">High-Value Invoice Alert Threshold ({defaultCurrency})</label>
              <input
                type="number"
                min="100"
                step="1000"
                className="form-input"
                value={alertThreshold}
                onChange={(e) => setAlertThreshold(e.target.value)}
              />
              <span style={{ fontSize: '0.72rem', color: '#94a3b8' }}>
                Invoices with total ≥ this amount trigger high-value approval alerts.
              </span>
            </div>
          </div>
        </div>

        {/* AI & OCR Engine Configuration */}
        <div className="card" style={{ marginBottom: '24px' }}>
          <div className="card-header">
            <div>
              <h3 className="card-title">AI Extraction Engine</h3>
              <p style={{ fontSize: '0.78rem', color: '#64748b' }}>
                Rule-based OCR runs offline 100% free; optionally configure Vision LLMs for complex layouts
              </p>
            </div>
            <span className="badge badge-approved" style={{ fontSize: '0.75rem' }}>
              <Zap size={13} /> {settingsData?.llm_status}
            </span>
          </div>

          <div className="form-group">
            <label className="form-label">Primary Extraction Engine</label>
            <select
              className="form-input"
              value={llmProvider}
              onChange={(e) => setLlmProvider(e.target.value)}
            >
              <option value="heuristic">Built-in Deterministic OCR & Layout Parser (No API Key Required)</option>
              <option value="gemini">Google Gemini 1.5 Flash Vision API</option>
              <option value="openai">OpenAI GPT-4o Mini Vision API</option>
              <option value="ollama">Local Ollama Vision (LLaVA / Qwen-VL)</option>
            </select>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginTop: '14px' }}>
            <div className="form-group">
              <label className="form-label">Google Gemini API Key (Optional)</label>
              <input
                type="password"
                className="form-input"
                placeholder="AIzaSy..."
                value={geminiKey}
                onChange={(e) => setGeminiKey(e.target.value)}
              />
            </div>

            <div className="form-group">
              <label className="form-label">OpenAI API Key (Optional)</label>
              <input
                type="password"
                className="form-input"
                placeholder="sk-proj-..."
                value={openaiKey}
                onChange={(e) => setOpenaiKey(e.target.value)}
              />
            </div>
          </div>

          <div className="form-group" style={{ marginTop: '6px' }}>
            <label className="form-label">Webhook Alert Dispatch URL (Optional)</label>
            <input
              type="url"
              className="form-input"
              placeholder="https://hooks.slack.com/services/..."
              value={webhookUrl}
              onChange={(e) => setWebhookUrl(e.target.value)}
            />
          </div>
        </div>

        {/* System Diagnostics Card */}
        <div className="card" style={{ marginBottom: '24px', backgroundColor: '#f8fafc' }}>
          <h3 className="card-title" style={{ marginBottom: '14px', fontSize: '0.95rem' }}>System Health & Diagnostics</h3>
          
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px' }}>
            <div style={{ padding: '12px', backgroundColor: '#ffffff', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
              <span style={{ fontSize: '0.72rem', color: '#64748b', textTransform: 'uppercase', fontWeight: 700 }}>Database</span>
              <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#0f172a', marginTop: '2px' }}>
                {settingsData?.database_status}
              </div>
            </div>

            <div style={{ padding: '12px', backgroundColor: '#ffffff', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
              <span style={{ fontSize: '0.72rem', color: '#64748b', textTransform: 'uppercase', fontWeight: 700 }}>OCR Backend</span>
              <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#0f172a', marginTop: '2px' }}>
                PyMuPDF + Tesseract
              </div>
            </div>

            <div style={{ padding: '12px', backgroundColor: '#ffffff', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
              <span style={{ fontSize: '0.72rem', color: '#64748b', textTransform: 'uppercase', fontWeight: 700 }}>App Version</span>
              <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#4f46e5', marginTop: '2px' }}>
                v{settingsData?.app_version} Production
              </div>
            </div>
          </div>
        </div>

        {/* Save Button */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
          <button
            type="submit"
            className="btn btn-primary"
            disabled={saving}
          >
            <Save size={16} /> {saving ? 'Saving...' : 'Save Configuration'}
          </button>
        </div>

      </form>
    </div>
  );
}
