/**
 * ============================================================================
 * Agentic Health Dashboard - Main React Component
 * ============================================================================
 * This component provides the visual interface for the Human-in-the-Loop workflow.
 * It handles:
 * 1. Connecting to the backend SSE stream for real-time updates.
 * 2. Rendering the chat-like log of agent activities.
 * 3. Displaying the current draft state.
 * 4. Enabling the "Interrupt" mode where humans can edit/approve drafts.
 *
 * Created by: Human Developer
 * Last Updated: 2025
 * ============================================================================
 */

import { useState, useEffect, useRef } from 'react'

const API_URL = 'http://localhost:8000';

function App() {
  const [intent, setIntent] = useState('');
  const [threadId, setThreadId] = useState(null);
  const [logs, setLogs] = useState([]);
  const [status, setStatus] = useState('idle');
  const [currentDraft, setCurrentDraft] = useState(null);
  const [humanFeedback, setHumanFeedback] = useState('');

  const logsEndRef = useRef(null);

  const startWorkflow = async () => {
    setStatus('running');
    setLogs([]);
    setCurrentDraft(null);
    
    try {
      const res = await fetch(`${API_URL}/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ intent })
      });
      const data = await res.json();
      setThreadId(data.thread_id);
      connectStream(data.thread_id, intent);
    } catch (err) {
      console.error(err);
      setStatus('error');
    }
  };

  const connectStream = (id, intentParam) => {
    const url = intentParam 
      ? `${API_URL}/stream/${id}?intent=${encodeURIComponent(intentParam)}`
      : `${API_URL}/stream/${id}`;

    const evtSource = new EventSource(url);
    
    evtSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.type === 'completed') {
        setStatus('completed');
        evtSource.close();
        return;
      }
      
      if (data.type === 'interrupt') {
        setStatus('reviewing');
        fetchState(id);
        evtSource.close();
        return;
      }
      
      if (data.scratchpad && data.scratchpad.length > 0) {
         const lastNote = data.scratchpad[data.scratchpad.length - 1];
         setLogs(prev => [...prev, lastNote]);
      }
      
      if (data.current_draft) {
        setCurrentDraft(data.current_draft);
      }
    };
    
    evtSource.onerror = (err) => {
      console.error("Stream error", err);
      evtSource.close();
    };
  };

  const fetchState = async (id) => {
    const res = await fetch(`${API_URL}/state/${id}`);
    const data = await res.json();
    setCurrentDraft(data.current_draft);
  };

  const handleApprove = async () => {
    setStatus('running');
    await fetch(`${API_URL}/resume/${threadId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: 'approve', modified_draft: currentDraft }) 
    });
    connectStream(threadId);
  };

  const handleRevise = async () => {
    setStatus('running');
    await fetch(`${API_URL}/resume/${threadId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: 'revise', feedback: humanFeedback })
    });
    connectStream(threadId);
  };
  
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  const getStatusBadge = () => {
    const badges = {
      idle: { text: 'Ready', color: '#64748b', bg: '#e2e8f0' },
      running: { text: 'Processing', color: '#0284c7', bg: '#e0f2fe' },
      reviewing: { text: 'Human Review Required', color: '#ea580c', bg: '#ffedd5' },
      completed: { text: 'Completed', color: '#16a34a', bg: '#dcfce7' },
      error: { text: 'Error', color: '#dc2626', bg: '#fee2e2' }
    };
    const badge = badges[status] || badges.idle;
    return (
      <span style={{ 
        padding: '6px 16px', 
        borderRadius: '20px', 
        fontSize: '0.85rem',
        fontWeight: '600',
        color: badge.color,
        backgroundColor: badge.bg
      }}>
        {status === 'running' && <span className="spinner"></span>}
        {badge.text}
      </span>
    );
  };

  return (
    <div className="app">
      <header className="header">
        <div className="header-content">
          <h1 className="title">
            <span className="icon">🧠</span>
            Agentic Health Dashboard
          </h1>
          <div className="status-badge">
            {getStatusBadge()}
          </div>
        </div>
      </header>
      
      <main className="main">
        <section className="input-section">
          <div className="input-group">
            <label className="label">What would you like to create?</label>
            <textarea 
              className="input-textarea"
              value={intent} 
              onChange={e => setIntent(e.target.value)} 
              placeholder="e.g., Create an exposure hierarchy for agoraphobia, Design a sleep hygiene protocol..."
              disabled={status === 'running' || status === 'reviewing'}
              rows={2}
            />
          </div>
          <button 
            className="primary-button"
            onClick={startWorkflow} 
            disabled={status !== 'idle' && status !== 'completed' && status !== 'error' || !intent.trim()}
          >
            <span>✨</span> Start Agent Workflow
          </button>
        </section>
        
        <div className="workspace">
          <section className="panel logs-panel">
            <h2 className="panel-title">
              <span className="panel-icon">📡</span>
              Agent Activity Stream
            </h2>
            <div className="logs-window">
              {logs.length === 0 ? (
                <div className="empty-state">
                  <span className="empty-icon">💭</span>
                  <p>Agent activity will appear here...</p>
                </div>
              ) : (
                logs.map((log, i) => (
                  <div key={i} className={`log-entry agent-${log.agent_name}`}>
                    <div className="log-header">
                      <span className="agent-badge">{log.agent_name}</span>
                      <span className="timestamp">{new Date(log.timestamp).toLocaleTimeString()}</span>
                    </div>
                    <p className="log-content">{log.content}</p>
                  </div>
                ))
              )}
              <div ref={logsEndRef} />
            </div>
          </section>
          
          <section className="panel draft-panel">
            <h2 className="panel-title">
              <span className="panel-icon">📝</span>
              Current Draft
            </h2>
            {currentDraft ? (
               <div className="draft-content">
                 {status === 'reviewing' ? (
                   <>
                     <div className="review-banner">
                       <span className="banner-icon">⚠️</span>
                       <div>
                         <strong>Human Review Required</strong>
                         <p>Edit the draft below or provide feedback for revision</p>
                       </div>
                     </div>
                     <div className="editor">
                       <div className="form-group">
                         <label className="field-label">Title</label>
                         <input 
                           className="field-input"
                           value={currentDraft.title} 
                           onChange={e => setCurrentDraft({...currentDraft, title: e.target.value})}
                         />
                       </div>
                       
                       <div className="form-group">
                         <label className="field-label">Description</label>
                         <textarea 
                           className="field-textarea"
                           value={currentDraft.description}
                           onChange={e => setCurrentDraft({...currentDraft, description: e.target.value})}
                           rows={3}
                         />
                       </div>
                       
                       <div className="form-group">
                         <label className="field-label">Steps (one per line)</label>
                         <textarea 
                           className="field-textarea"
                           value={currentDraft.steps.join('\n')}
                           onChange={e => setCurrentDraft({...currentDraft, steps: e.target.value.split('\n')})}
                           rows={6}
                         />
                       </div>
                       
                       <div className="form-group">
                         <label className="field-label">Rationale</label>
                         <textarea 
                           className="field-textarea"
                           value={currentDraft.rationale}
                           onChange={e => setCurrentDraft({...currentDraft, rationale: e.target.value})}
                           rows={3}
                         />
                       </div>
                       
                       <div className="form-group">
                         <label className="field-label">Safety Notes</label>
                         <textarea 
                           className="field-textarea"
                           value={currentDraft.safety_notes || ''}
                           onChange={e => setCurrentDraft({...currentDraft, safety_notes: e.target.value})}
                           rows={2}
                         />
                       </div>
                     </div>
                     <div className="review-controls">
                       <button className="approve-btn" onClick={handleApprove}>
                         <span>✓</span> Approve & Finalize
                       </button>
                       <div className="revise-group">
                         <input 
                           className="feedback-input"
                           placeholder="Provide feedback for revision..." 
                           value={humanFeedback}
                           onChange={e => setHumanFeedback(e.target.value)}
                         />
                         <button className="revise-btn" onClick={handleRevise}>
                           <span>↻</span> Request Revision
                         </button>
                       </div>
                     </div>
                   </>
                 ) : (
                   <div className="preview">
                     <h3 className="draft-title">{currentDraft.title}</h3>
                     <p className="draft-description">{currentDraft.description}</p>
                     
                     <div className="section">
                       <h4 className="section-title">Steps</h4>
                       <ol className="steps-list">
                         {currentDraft.steps.map((s, i) => <li key={i}>{s}</li>)}
                       </ol>
                     </div>
                     
                     <div className="section">
                       <h4 className="section-title">Rationale</h4>
                       <p>{currentDraft.rationale}</p>
                     </div>
                     
                     {currentDraft.safety_notes && (
                       <div className="safety-alert">
                         <span className="alert-icon">🛡️</span>
                         <div>
                           <strong>Safety Notes</strong>
                           <p>{currentDraft.safety_notes}</p>
                         </div>
                       </div>
                     )}
                   </div>
                 )}
               </div>
            ) : (
              <div className="empty-state">
                <span className="empty-icon">📄</span>
                <p>No draft generated yet</p>
              </div>
            )}
          </section>
        </div>
      </main>
      
      <style>{`
        * {
          margin: 0;
          padding: 0;
          box-sizing: border-box;
        }
        
        .app {
          min-height: 100vh;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', sans-serif;
        }
        
        .header {
          background: rgba(255, 255, 255, 0.98);
          backdrop-filter: blur(10px);
          border-bottom: 1px solid rgba(0, 0, 0, 0.1);
          padding: 1.5rem 2rem;
          box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        }
        
        .header-content {
          max-width: 1400px;
          margin: 0 auto;
          display: flex;
          justify-content: space-between;
          align-items: center;
        }
        
        .title {
          font-size: 1.75rem;
          font-weight: 700;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          display: flex;
          align-items: center;
          gap: 0.75rem;
        }
        
        .icon {
          font-size: 2rem;
        }
        
        .main {
          max-width: 1400px;
          margin: 0 auto;
          padding: 2rem;
        }
        
        .input-section {
          background: rgba(255, 255, 255, 0.98);
          backdrop-filter: blur(10px);
          border-radius: 16px;
          padding: 2rem;
          margin-bottom: 2rem;
          box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
        }
        
        .input-group {
          margin-bottom: 1.5rem;
        }
        
        .label {
          display: block;
          font-size: 0.95rem;
          font-weight: 600;
          color: #374151;
          margin-bottom: 0.75rem;
        }
        
        .input-textarea {
          width: 100%;
          padding: 1rem;
          border: 2px solid #e5e7eb;
          border-radius: 12px;
          font-size: 1rem;
          font-family: inherit;
          resize: vertical;
          transition: all 0.2s;
        }
        
        .input-textarea:focus {
          outline: none;
          border-color: #667eea;
          box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        
        .input-textarea:disabled {
          background: #f9fafb;
          cursor: not-allowed;
        }
        
        .primary-button {
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
          border: none;
          padding: 1rem 2rem;
          border-radius: 12px;
          font-size: 1rem;
          font-weight: 600;
          cursor: pointer;
          display: flex;
          align-items: center;
          gap: 0.5rem;
          transition: all 0.3s;
          box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }
        
        .primary-button:hover:not(:disabled) {
          transform: translateY(-2px);
          box-shadow: 0 8px 20px rgba(102, 126, 234, 0.5);
        }
        
        .primary-button:disabled {
          opacity: 0.6;
          cursor: not-allowed;
          transform: none;
        }
        
        .workspace {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 2rem;
          height: calc(100vh - 350px);
          min-height: 600px;
        }
        
        .panel {
          background: rgba(255, 255, 255, 0.98);
          backdrop-filter: blur(10px);
          border-radius: 16px;
          box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
          overflow: hidden;
          display: flex;
          flex-direction: column;
        }
        
        .panel-title {
          padding: 1.5rem;
          border-bottom: 1px solid #e5e7eb;
          font-size: 1.125rem;
          font-weight: 600;
          color: #1f2937;
          display: flex;
          align-items: center;
          gap: 0.75rem;
          background: linear-gradient(to right, #f9fafb, #ffffff);
        }
        
        .panel-icon {
          font-size: 1.5rem;
        }
        
        .logs-window {
          flex: 1;
          overflow-y: auto;
          padding: 1.5rem;
          background: #f9fafb;
        }
        
        .empty-state {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          height: 100%;
          color: #9ca3af;
          text-align: center;
          padding: 2rem;
        }
        
        .empty-icon {
          font-size: 3rem;
          margin-bottom: 1rem;
          opacity: 0.5;
        }
        
        .log-entry {
          background: white;
          border-radius: 12px;
          padding: 1rem;
          margin-bottom: 1rem;
          border-left: 4px solid #e5e7eb;
          box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
          animation: slideIn 0.3s ease-out;
        }
        
        @keyframes slideIn {
          from {
            opacity: 0;
            transform: translateY(10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        
        .log-entry.agent-Drafter { border-left-color: #3b82f6; }
        .log-entry.agent-SafetyGuardian { border-left-color: #ef4444; }
        .log-entry.agent-ClinicalCritic { border-left-color: #f59e0b; }
        .log-entry.agent-Supervisor { border-left-color: #8b5cf6; }
        .log-entry.agent-Human { border-left-color: #10b981; }
        
        .log-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 0.5rem;
        }
        
        .agent-badge {
          font-weight: 600;
          font-size: 0.875rem;
          padding: 0.25rem 0.75rem;
          border-radius: 6px;
          background: #f3f4f6;
          color: #374151;
        }
        
        .timestamp {
          font-size: 0.75rem;
          color: #9ca3af;
        }
        
        .log-content {
          color: #4b5563;
          font-size: 0.925rem;
          line-height: 1.5;
        }
        
        .draft-content {
          flex: 1;
          overflow-y: auto;
          padding: 1.5rem;
        }
        
        .review-banner {
          background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
          border: 2px solid #fbbf24;
          border-radius: 12px;
          padding: 1rem;
          margin-bottom: 1.5rem;
          display: flex;
          gap: 1rem;
          align-items: start;
        }
        
        .banner-icon {
          font-size: 1.5rem;
        }
        
        .review-banner strong {
          display: block;
          color: #92400e;
          margin-bottom: 0.25rem;
        }
        
        .review-banner p {
          color: #92400e;
          font-size: 0.875rem;
        }
        
        .editor {
          margin-bottom: 1.5rem;
        }
        
        .form-group {
          margin-bottom: 1.25rem;
        }
        
        .field-label {
          display: block;
          font-size: 0.875rem;
          font-weight: 600;
          color: #374151;
          margin-bottom: 0.5rem;
        }
        
        .field-input, .field-textarea {
          width: 100%;
          padding: 0.75rem;
          border: 2px solid #e5e7eb;
          border-radius: 8px;
          font-size: 0.95rem;
          font-family: inherit;
          transition: all 0.2s;
        }
        
        .field-input:focus, .field-textarea:focus {
          outline: none;
          border-color: #667eea;
          box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        
        .field-textarea {
          resize: vertical;
        }
        
        .review-controls {
          border-top: 2px solid #e5e7eb;
          padding-top: 1.5rem;
        }
        
        .approve-btn {
          width: 100%;
          background: linear-gradient(135deg, #10b981 0%, #059669 100%);
          color: white;
          border: none;
          padding: 1rem;
          border-radius: 12px;
          font-size: 1rem;
          font-weight: 600;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 0.5rem;
          margin-bottom: 1rem;
          transition: all 0.3s;
          box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
        }
        
        .approve-btn:hover {
          transform: translateY(-2px);
          box-shadow: 0 8px 20px rgba(16, 185, 129, 0.4);
        }
        
        .revise-group {
          display: flex;
          gap: 0.75rem;
        }
        
        .feedback-input {
          flex: 1;
          padding: 0.75rem;
          border: 2px solid #e5e7eb;
          border-radius: 8px;
          font-size: 0.95rem;
          transition: all 0.2s;
        }
        
        .feedback-input:focus {
          outline: none;
          border-color: #667eea;
          box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        
        .revise-btn {
          background: #f59e0b;
          color: white;
          border: none;
          padding: 0.75rem 1.5rem;
          border-radius: 8px;
          font-weight: 600;
          cursor: pointer;
          display: flex;
          align-items: center;
          gap: 0.5rem;
          transition: all 0.3s;
        }
        
        .revise-btn:hover {
          background: #d97706;
          transform: translateY(-2px);
        }
        
        .preview {
          padding: 1rem;
        }
        
        .draft-title {
          font-size: 1.5rem;
          font-weight: 700;
          color: #1f2937;
          margin-bottom: 1rem;
        }
        
        .draft-description {
          color: #6b7280;
          font-size: 1rem;
          line-height: 1.7;
          margin-bottom: 1.5rem;
        }
        
        .section {
          margin-bottom: 1.5rem;
        }
        
        .section-title {
          font-size: 1.125rem;
          font-weight: 600;
          color: #374151;
          margin-bottom: 0.75rem;
          display: flex;
          align-items: center;
          gap: 0.5rem;
        }
        
        .steps-list {
          padding-left: 1.5rem;
          color: #4b5563;
          line-height: 1.8;
        }
        
        .steps-list li {
          margin-bottom: 0.5rem;
        }
        
        .safety-alert {
          background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
          border: 2px solid #ef4444;
          border-radius: 12px;
          padding: 1rem;
          display: flex;
          gap: 1rem;
          align-items: start;
        }
        
        .alert-icon {
          font-size: 1.5rem;
        }
        
        .safety-alert strong {
          display: block;
          color: #991b1b;
          margin-bottom: 0.25rem;
        }
        
        .safety-alert p {
          color: #991b1b;
          font-size: 0.95rem;
          line-height: 1.6;
        }
        
        .spinner {
          display: inline-block;
          width: 12px;
          height: 12px;
          border: 2px solid rgba(255, 255, 255, 0.3);
          border-top-color: currentColor;
          border-radius: 50%;
          animation: spin 0.6s linear infinite;
          margin-right: 0.5rem;
        }
        
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
        
        ::-webkit-scrollbar {
          width: 8px;
          height: 8px;
        }
        
        ::-webkit-scrollbar-track {
          background: #f1f5f9;
        }
        
        ::-webkit-scrollbar-thumb {
          background: #cbd5e1;
          border-radius: 4px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
          background: #94a3b8;
        }
      `}</style>
    </div>
  )
}

export default App
