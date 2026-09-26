import React from 'react';
import { Sidebar } from '../components/Sidebar';
import { Navbar } from '../components/Navbar';

export function DashboardLayout({ 
  currentView, 
  onChangeView, 
  pageTitle, 
  onSelectInvoice, 
  onGenerateSamples, 
  children 
}) {
  return (
    <div className="app-container">
      <Sidebar currentView={currentView} onChangeView={onChangeView} />
      <div className="main-content">
        <Navbar 
          pageTitle={pageTitle} 
          onSelectInvoice={onSelectInvoice}
          onGenerateSamples={onGenerateSamples}
        />
        <main className="page-body">
          {children}
        </main>
      </div>
    </div>
  );
}
