import React, { useState, useRef } from 'react';
import { 
  UploadCloud, 
  FileText, 
  X, 
  CheckCircle2, 
  AlertCircle, 
  Sparkles, 
  ArrowRight,
  ShieldCheck,
  Zap
} from 'lucide-react';
import { api } from '../services/api';

export function UploadPage({ onSelectInvoice, onNavigate }) {
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const fileInputRef = useRef(null);

  const allowedExtensions = ['.pdf', '.png', '.jpg', '.jpeg', '.webp'];

  const handleFileSelection = (fileList) => {
    setErrorMessage('');
    setSuccessMessage('');
    const valid = [];
    const maxBytes = 10 * 1024 * 1024; // 10 MB

    for (let i = 0; i < fileList.length; i++) {
      const file = fileList[i];
      const ext = '.' + file.name.split('.').pop().toLowerCase();
      
      if (!allowedExtensions.includes(ext)) {
        setErrorMessage(`File '${file.name}' is not supported. Please upload PDF, PNG, JPG, JPEG, or WEBP.`);
        continue;
      }
      if (file.size > maxBytes) {
        setErrorMessage(`File '${file.name}' exceeds the 10 MB size limit.`);
        continue;
      }
      valid.push(file);
    }
    setSelectedFiles(prev => [...prev, ...valid]);
  };

  const handleRemoveFile = (index) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index));
  };

  const handleProcessUpload = async () => {
    if (selectedFiles.length === 0) return;
    setUploading(true);
    setUploadProgress(20);
    setErrorMessage('');
    setSuccessMessage('');

    try {
      const progressTimer = setInterval(() => {
        setUploadProgress(p => (p < 85 ? p + 15 : p));
      }, 400);

      const docs = await api.uploadDocuments(selectedFiles);
      clearInterval(progressTimer);
      setUploadProgress(100);

      setSuccessMessage(`Successfully processed ${docs.length} document(s) with AI OCR and Validation.`);
      setSelectedFiles([]);

      // If document was created, automatically open its review page
      if (docs.length > 0 && docs[0].invoice) {
        setTimeout(() => {
          onSelectInvoice(docs[0].invoice.id);
        }, 1200);
      } else {
        setTimeout(() => {
          onNavigate('invoices');
        }, 1500);
      }
    } catch (err) {
      setErrorMessage(err.message || 'Upload and processing failed.');
    } finally {
      setUploading(false);
    }
  };

  const handleLoadPresets = async () => {
    setUploading(true);
    setErrorMessage('');
    setSuccessMessage('');
    try {
      const invoices = await api.generateSamples();
      setSuccessMessage(`Loaded ${invoices.length} realistic test invoices (IT Services, Server Rack, Discrepancies, Date Issue).`);
      setTimeout(() => {
        onNavigate('invoices');
      }, 1000);
    } catch (err) {
      setErrorMessage('Failed to load sample invoices.');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div style={{ maxWidth: '900px', margin: '0 auto' }}>
      
      {/* Workflow Step Indicator */}
      <div style={{
        backgroundColor: '#ffffff',
        borderRadius: '12px',
        border: '1px solid #e2e8f0',
        padding: '16px 24px',
        marginBottom: '24px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }}>
        {[
          { step: '1', title: 'Upload', desc: 'PDF or Image' },
          { step: '2', title: 'Extract', desc: 'OCR & Vision AI' },
          { step: '3', title: 'Validate', desc: 'Math Cross-Checks' },
          { step: '4', title: 'Review', desc: 'Verify & Approve' },
          { step: '5', title: 'Save', desc: 'Structured DB & CSV' }
        ].map((item, idx) => (
          <div key={item.step} style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{
              width: '28px',
              height: '28px',
              borderRadius: '50%',
              backgroundColor: '#eef2ff',
              color: '#4f46e5',
              fontWeight: 700,
              fontSize: '0.8rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              {item.step}
            </div>
            <div>
              <div style={{ fontSize: '0.82rem', fontWeight: 700, color: '#0f172a' }}>{item.title}</div>
              <div style={{ fontSize: '0.7rem', color: '#64748b' }}>{item.desc}</div>
            </div>
            {idx < 4 && <ArrowRight size={14} style={{ color: '#cbd5e1', marginLeft: '12px' }} />}
          </div>
        ))}
      </div>

      {/* Upload Drop Zone Card */}
      <div className="card" style={{ marginBottom: '24px' }}>
        <div
          onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setIsDragging(false);
            if (e.dataTransfer.files) handleFileSelection(e.dataTransfer.files);
          }}
          onClick={() => fileInputRef.current.click()}
          style={{
            border: `2px dashed ${isDragging ? '#4f46e5' : '#cbd5e1'}`,
            borderRadius: '14px',
            padding: '48px 20px',
            textAlign: 'center',
            backgroundColor: isDragging ? '#eef2ff' : '#f8fafc',
            cursor: 'pointer',
            transition: 'all 0.2s ease'
          }}
        >
          <input
            type="file"
            ref={fileInputRef}
            multiple
            accept=".pdf,.png,.jpg,.jpeg,.webp"
            style={{ display: 'none' }}
            onChange={(e) => {
              if (e.target.files) handleFileSelection(e.target.files);
            }}
          />

          <div style={{
            width: '64px',
            height: '64px',
            borderRadius: '50%',
            backgroundColor: '#ffffff',
            color: '#4f46e5',
            boxShadow: '0 4px 6px -1px rgba(0,0,0,0.05)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 16px'
          }}>
            <UploadCloud size={32} />
          </div>

          <h3 style={{ fontSize: '1.2rem', fontWeight: 700, color: '#0f172a', marginBottom: '6px' }}>
            Choose invoices or drag & drop them here
          </h3>
          <p style={{ fontSize: '0.85rem', color: '#64748b', marginBottom: '18px' }}>
            Supports PDF, Scanned Images (PNG, JPG, JPEG, WEBP) • Up to 10 MB per file
          </p>

          <button
            type="button"
            className="btn btn-primary btn-sm"
            onClick={(e) => { e.stopPropagation(); fileInputRef.current.click(); }}
          >
            Browse Files from Computer
          </button>
        </div>

        {/* Quick Sample Presets Trigger */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginTop: '20px',
          paddingTop: '16px',
          borderTop: '1px solid #f1f5f9'
        }}>
          <span style={{ fontSize: '0.82rem', color: '#64748b', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Zap size={15} color="#f59e0b" /> Need test documents without uploading?
          </span>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={handleLoadPresets}
            disabled={uploading}
            style={{ color: '#4f46e5', fontWeight: 600 }}
          >
            <Sparkles size={14} /> Load 4 Realistic Preset Scenarios
          </button>
        </div>
      </div>

      {/* Feedback Alerts */}
      {errorMessage && (
        <div style={{
          backgroundColor: '#fef2f2',
          border: '1px solid #fecaca',
          color: '#991b1b',
          padding: '12px 16px',
          borderRadius: '8px',
          marginBottom: '20px',
          fontSize: '0.85rem',
          display: 'flex',
          alignItems: 'center',
          gap: '8px'
        }}>
          <AlertCircle size={16} />
          <span>{errorMessage}</span>
        </div>
      )}

      {successMessage && (
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
          <span>{successMessage}</span>
        </div>
      )}

      {/* Selected Files Queue */}
      {selectedFiles.length > 0 && (
        <div className="card" style={{ marginBottom: '24px' }}>
          <div className="card-header">
            <h3 className="card-title">Selected Files ({selectedFiles.length})</h3>
            <button
              className="btn btn-primary"
              onClick={handleProcessUpload}
              disabled={uploading}
            >
              {uploading ? `Processing (${uploadProgress}%)...` : `Process ${selectedFiles.length} Document(s)`}
            </button>
          </div>

          {uploading && (
            <div style={{ marginBottom: '16px' }}>
              <div style={{ height: '6px', backgroundColor: '#e2e8f0', borderRadius: '999px', overflow: 'hidden' }}>
                <div style={{
                  height: '100%',
                  width: `${uploadProgress}%`,
                  backgroundColor: '#4f46e5',
                  transition: 'width 0.3s ease'
                }} />
              </div>
            </div>
          )}

          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {selectedFiles.map((file, idx) => (
              <div
                key={idx}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '10px 14px',
                  backgroundColor: '#f8fafc',
                  border: '1px solid #e2e8f0',
                  borderRadius: '8px'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <FileText size={18} color="#4f46e5" />
                  <div>
                    <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#0f172a' }}>{file.name}</div>
                    <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>{(file.size / 1024).toFixed(1)} KB</div>
                  </div>
                </div>
                {!uploading && (
                  <button
                    onClick={() => handleRemoveFile(idx)}
                    style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer', padding: '4px' }}
                  >
                    <X size={16} />
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

    </div>
  );
}
