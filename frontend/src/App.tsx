import React, { useState, useEffect, useCallback } from 'react';
import type {
  ConfigStatus,
  RunSummary,
  RunDetail,
  EvidenceReport,
  RunCreatePayload,
} from './lib/api';
import {
  fetchConfigStatus,
  fetchRuns,
  fetchRun,
  fetchRunEvidence,
  triggerDemoRun,
  createRun,
} from './lib/api';
import { Header } from './components/Header';
import { DashboardView } from './features/dashboard/DashboardView';
import { NewRepairView } from './features/runs/NewRepairView';
import { RunsListView } from './features/runs/RunsListView';
import { RunDetailsView } from './features/runs/RunDetailsView';
import { EvidenceView } from './features/evidence/EvidenceView';
import { SettingsView } from './features/settings/SettingsView';
import './styles/index.css';

export const App: React.FC = () => {
  const [currentTab, setCurrentTab] = useState<string>('dashboard');
  const [config, setConfig] = useState<ConfigStatus | null>(null);
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [activeRunDetail, setActiveRunDetail] = useState<RunDetail | null>(null);
  const [activeRunEvidence, setActiveRunEvidence] = useState<EvidenceReport | null>(null);

  const [isTriggeringDemo, setIsTriggeringDemo] = useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Load initial system data
  const loadInitialData = useCallback(async () => {
    try {
      const [configData, runsData] = await Promise.all([
        fetchConfigStatus().catch(() => null),
        fetchRuns().catch(() => []),
      ]);
      if (configData) setConfig(configData);
      setRuns(runsData);
      setErrorMessage(null);
    } catch (err: any) {
      console.warn('Backend API connection warning:', err);
    }
  }, []);

  useEffect(() => {
    loadInitialData();
  }, [loadInitialData]);

  // Load specific run details and evidence
  const handleSelectRun = async (runId: string) => {
    try {
      setSelectedRunId(runId);
      setCurrentTab('run-details');
      const [detail, ev] = await Promise.all([
        fetchRun(runId),
        fetchRunEvidence(runId).catch(() => null),
      ]);
      setActiveRunDetail(detail);
      setActiveRunEvidence(ev);
    } catch (err: any) {
      console.error('Error fetching run details:', err);
    }
  };

  // Launch deterministic demo repair
  const handleTriggerDemo = async () => {
    try {
      setIsTriggeringDemo(true);
      setErrorMessage(null);
      const newRun = await triggerDemoRun();
      // Reload runs list
      const updatedRuns = await fetchRuns().catch(() => []);
      setRuns(updatedRuns);
      // Select the newly finished run
      await handleSelectRun(newRun.id);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to trigger demo run.');
    } finally {
      setIsTriggeringDemo(false);
    }
  };

  // Submit custom repair
  const handleSubmitRepair = async (payload: RunCreatePayload) => {
    try {
      setIsSubmitting(true);
      setErrorMessage(null);
      const newRun = await createRun(payload);
      const updatedRuns = await fetchRuns().catch(() => []);
      setRuns(updatedRuns);
      await handleSelectRun(newRun.id);
    } catch (err: any) {
      throw err;
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="app-container">
      <Header
        currentTab={currentTab}
        onSelectTab={(tab) => {
          setCurrentTab(tab);
          if (tab !== 'run-details') {
            setSelectedRunId(null);
          }
        }}
        onTriggerDemo={handleTriggerDemo}
        isTriggeringDemo={isTriggeringDemo}
        mode={config?.mode || 'demo'}
      />

      {errorMessage && (
        <div
          style={{
            maxWidth: '1280px',
            margin: '16px auto 0',
            padding: '12px 20px',
            background: 'var(--status-failed-bg)',
            border: '1px solid var(--status-failed-border)',
            color: 'var(--status-failed)',
            borderRadius: 'var(--radius-md)',
            fontSize: '0.88rem',
            width: 'calc(100% - 48px)',
          }}
        >
          {errorMessage}
        </div>
      )}

      <main className="main-content">
        {currentTab === 'dashboard' && (
          <DashboardView
            runs={runs}
            config={config}
            onSelectRun={handleSelectRun}
            onTriggerDemo={handleTriggerDemo}
            onNewRepair={() => setCurrentTab('new-repair')}
            isTriggeringDemo={isTriggeringDemo}
          />
        )}

        {currentTab === 'new-repair' && (
          <NewRepairView
            config={config}
            onSubmit={handleSubmitRepair}
            onTriggerDemo={handleTriggerDemo}
            isSubmitting={isSubmitting}
          />
        )}

        {currentTab === 'runs' && (
          <RunsListView
            runs={runs}
            onSelectRun={handleSelectRun}
            onNewRepair={() => setCurrentTab('new-repair')}
            onTriggerDemo={handleTriggerDemo}
            isTriggeringDemo={isTriggeringDemo}
          />
        )}

        {currentTab === 'evidence' && (
          <EvidenceView runs={runs} onSelectRun={handleSelectRun} />
        )}

        {currentTab === 'settings' && (
          <SettingsView config={config} onRefresh={loadInitialData} />
        )}

        {currentTab === 'run-details' && activeRunDetail && (
          <RunDetailsView
            run={activeRunDetail}
            evidence={activeRunEvidence}
            onBack={() => setCurrentTab('runs')}
            onRefresh={() => selectedRunId && handleSelectRun(selectedRunId)}
          />
        )}
      </main>
    </div>
  );
};

export default App;
