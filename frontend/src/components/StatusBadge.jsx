import React from 'react';
import { CheckCircle2, AlertTriangle, Clock, XCircle } from 'lucide-react';

export function StatusBadge({ status, isHighValue, isDuplicate }) {
  let badgeClass = 'badge-needs-review';
  let Icon = Clock;
  let label = status || 'PENDING';

  if (status === 'APPROVED') {
    badgeClass = 'badge-approved';
    Icon = CheckCircle2;
    label = 'Validated';
  } else if (status === 'FLAGGED') {
    badgeClass = 'badge-flagged';
    Icon = AlertTriangle;
    label = 'Flagged';
  } else if (status === 'NEEDS_REVIEW') {
    badgeClass = 'badge-needs-review';
    Icon = Clock;
    label = 'Needs Review';
  } else if (status === 'REJECTED') {
    badgeClass = 'badge-rejected';
    Icon = XCircle;
    label = 'Rejected';
  }

  return (
    <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
      <span className={`badge ${badgeClass}`}>
        <Icon size={12} strokeWidth={2.5} />
        {label}
      </span>
      {isHighValue && (
        <span className="badge" style={{ backgroundColor: '#f3e8ff', color: '#7e22ce', borderColor: 'rgba(147, 51, 234, 0.2)' }}>
          High Value
        </span>
      )}
      {isDuplicate && (
        <span className="badge" style={{ backgroundColor: '#fee2e2', color: '#b91c1c', borderColor: 'rgba(239, 68, 68, 0.3)' }}>
          Duplicate
        </span>
      )}
    </div>
  );
}
