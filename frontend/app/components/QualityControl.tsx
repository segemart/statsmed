'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  listQCOperations,
  createQCOperation,
  deleteQCOperation,
  listQCFunctions,
  createQCFunction,
  updateQCFunction,
  deleteQCFunction,
  regenerateQCApiKey,
  runQualityControl,
  type QCOperation,
  type QCFunction,
} from '../lib/api';
import styles from './QualityControl.module.css';

const FUNCTION_TYPES = [
  { value: 'missing', label: 'Check missing values', configHint: 'columns: array of column names' },
  { value: 'range', label: 'Check range', configHint: 'column, min, max' },
  { value: 'custom', label: 'Custom (placeholder)', configHint: '-' },
];

export default function QualityControl() {
  const [operations, setOperations] = useState<QCOperation[]>([]);
  const [selectedOpId, setSelectedOpId] = useState<number | null>(null);
  const [functions, setFunctions] = useState<QCFunction[]>([]);
  const [createName, setCreateName] = useState('');
  const [createOpen, setCreateOpen] = useState(false);
  const [createdApiKey, setCreatedApiKey] = useState<string | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [addFnOpen, setAddFnOpen] = useState(false);
  const [addFnName, setAddFnName] = useState('');
  const [addFnType, setAddFnType] = useState('missing');
  const [addFnConfig, setAddFnConfig] = useState('{}');
  const [testDataJson, setTestDataJson] = useState('[{"a":1,"b":2},{"a":null,"b":3}]');
  const [testResult, setTestResult] = useState<{ success: boolean; results: { name: string; passed: boolean; message: string }[] } | null>(null);
  const [revealedKey, setRevealedKey] = useState<number | null>(null);
  const [storedKeys, setStoredKeys] = useState<Record<number, string>>({});

  const loadOperations = useCallback(async () => {
    try {
      const list = await listQCOperations();
      setOperations(list);
    } catch {
      setOperations([]);
    }
  }, []);

  const loadFunctions = useCallback(async (opId: number) => {
    try {
      const list = await listQCFunctions(opId);
      setFunctions(list);
    } catch {
      setFunctions([]);
    }
  }, []);

  useEffect(() => {
    loadOperations();
  }, [loadOperations]);

  useEffect(() => {
    if (selectedOpId) loadFunctions(selectedOpId);
    else setFunctions([]);
  }, [selectedOpId, loadFunctions]);

  const selectedOp = operations.find((o) => o.id === selectedOpId);

  const handleCreate = async () => {
    const name = createName.trim();
    if (!name) {
      setError('Name is required');
      return;
    }
    setError('');
    setLoading(true);
    try {
      const op = await createQCOperation(name);
      if (op.api_key) {
        setCreatedApiKey(op.api_key);
        setStoredKeys((k) => ({ ...k, [op.id]: op.api_key! }));
      }
      await loadOperations();
      setSelectedOpId(op.id);
      setCreateName('');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Create failed');
    } finally {
      setLoading(false);
    }
  };

  const handleRegenerateKey = async (opId: number) => {
    try {
      const op = await regenerateQCApiKey(opId);
      if (op.api_key) {
        setStoredKeys((k) => ({ ...k, [opId]: op.api_key! }));
        setRevealedKey(opId);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed');
    }
  };

  const handleAddFunction = async () => {
    if (!selectedOpId) return;
    const name = addFnName.trim() || 'Unnamed';
    let config: Record<string, unknown> = {};
    try {
      config = addFnConfig.trim() ? JSON.parse(addFnConfig) : {};
    } catch {
      setError('Invalid JSON config');
      return;
    }
    setError('');
    setLoading(true);
    try {
      await createQCFunction(selectedOpId, name, addFnType, config);
      await loadFunctions(selectedOpId);
      setAddFnOpen(false);
      setAddFnName('');
      setAddFnConfig('{}');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteFunction = async (functionId: number) => {
    if (!selectedOpId) return;
    try {
      await deleteQCFunction(selectedOpId, functionId);
      await loadFunctions(selectedOpId);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed');
    }
  };

  const handleDeleteOperation = async (opId: number) => {
    try {
      await deleteQCOperation(opId);
      setStoredKeys((k) => {
        const next = { ...k };
        delete next[opId];
        return next;
      });
      if (selectedOpId === opId) setSelectedOpId(null);
      await loadOperations();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed');
    }
  };

  const handleTestRun = async () => {
    if (!selectedOpId) return;
    const key = storedKeys[selectedOpId];
    if (!key) {
      setError('Regenerate API key first to get the key for testing.');
      return;
    }
    let data: Record<string, unknown>[];
    try {
      data = JSON.parse(testDataJson);
      if (!Array.isArray(data)) throw new Error('Data must be an array');
    } catch {
      setError('Invalid JSON: use an array of objects, e.g. [{"col1":1},{"col1":2}]');
      return;
    }
    setError('');
    setTestResult(null);
    try {
      const result = await runQualityControl(key, data);
      setTestResult({ success: result.success, results: result.results });
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Run failed');
    }
  };

  const displayKey = (op: QCOperation) => {
    const key = storedKeys[op.id];
    if (key) return key;
    return op.api_key ? op.api_key : '•••••••• (regenerate to see)';
  };

  return (
    <main className={styles.main}>
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Quality control operations</h2>
        <p className={styles.muted}>
          Create an operation with a unique name and API key. Add functions (e.g. check missing, check range) that run when you send data to the API.
        </p>
        {error && <p className={styles.error}>{error}</p>}
        <div className={styles.toolbar}>
          <button type="button" className={styles.primaryButton} onClick={() => { setCreateOpen(true); setCreatedApiKey(null); setError(''); }}>
            Create operation
          </button>
        </div>

        {createOpen && (
          <div className={styles.card}>
            <h3 className={styles.cardTitle}>New operation</h3>
            {createdApiKey ? (
              <div>
                <p className={styles.success}>Operation created. Copy your API key now — it won’t be shown again in full.</p>
                <div className={styles.apiKeyBox}>
                  <code className={styles.apiKey}>{createdApiKey}</code>
                  <button
                    type="button"
                    className={styles.smallButton}
                    onClick={() => {
                      navigator.clipboard.writeText(createdApiKey);
                    }}
                  >
                    Copy
                  </button>
                </div>
                <button type="button" className={styles.secondaryButton} onClick={() => { setCreateOpen(false); setCreatedApiKey(null); }}>
                  Close
                </button>
              </div>
            ) : (
              <>
                <label className={styles.label}>Name (unique)</label>
                <input
                  type="text"
                  className={styles.input}
                  value={createName}
                  onChange={(e) => setCreateName(e.target.value)}
                  placeholder="e.g. Lab QC 2024"
                />
                <div className={styles.buttonRow}>
                  <button type="button" className={styles.primaryButton} onClick={handleCreate} disabled={loading}>
                    {loading ? 'Creating...' : 'Create'}
                  </button>
                  <button type="button" className={styles.secondaryButton} onClick={() => { setCreateOpen(false); setError(''); }}>
                    Cancel
                  </button>
                </div>
              </>
            )}
          </div>
        )}

        <div className={styles.operationList}>
          {operations.map((op) => (
            <div
              key={op.id}
              className={`${styles.operationItem} ${selectedOpId === op.id ? styles.operationItemActive : ''}`}
            >
              <button type="button" className={styles.operationName} onClick={() => setSelectedOpId(op.id)}>
                {op.name}
              </button>
              <button type="button" className={styles.removeButton} onClick={() => handleDeleteOperation(op.id)} title="Delete operation">
                ×
              </button>
            </div>
          ))}
        </div>
      </section>

      {selectedOp && (
        <>
          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>{selectedOp.name}</h2>
            <p className={styles.muted}>API key — use header <code>X-API-Key</code> when calling POST /api/quality/run</p>
            <div className={styles.apiKeyBox}>
              <code className={styles.apiKey}>
                {revealedKey === selectedOp.id || storedKeys[selectedOp.id] ? displayKey(selectedOp) : '••••••••••••'}
              </code>
              <button
                type="button"
                className={styles.smallButton}
                onClick={() => storedKeys[selectedOp.id] ? navigator.clipboard.writeText(storedKeys[selectedOp.id]) : undefined}
                disabled={!storedKeys[selectedOp.id]}
              >
                Copy
              </button>
              <button type="button" className={styles.smallButton} onClick={() => handleRegenerateKey(selectedOp.id)}>
                Regenerate key
              </button>
            </div>
          </section>

          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>Functions</h2>
            <p className={styles.muted}>Functions run in order when you send data to the API.</p>
            <button type="button" className={styles.primaryButton} onClick={() => { setAddFnOpen(true); setError(''); }}>
              Add function
            </button>

            {addFnOpen && (
              <div className={styles.card}>
                <h3 className={styles.cardTitle}>New function</h3>
                <label className={styles.label}>Name</label>
                <input
                  type="text"
                  className={styles.input}
                  value={addFnName}
                  onChange={(e) => setAddFnName(e.target.value)}
                  placeholder="e.g. Check missing in critical columns"
                />
                <label className={styles.label}>Type</label>
                <select className={styles.select} value={addFnType} onChange={(e) => setAddFnType(e.target.value)}>
                  {FUNCTION_TYPES.map((t) => (
                    <option key={t.value} value={t.value}>{t.label}</option>
                  ))}
                </select>
                <label className={styles.label}>Config (JSON) — e.g. missing: {`{"columns": ["col1", "col2"]}`}, range: {`{"column": "x", "min": 0, "max": 100}`}</label>
                <textarea
                  className={styles.textarea}
                  value={addFnConfig}
                  onChange={(e) => setAddFnConfig(e.target.value)}
                  rows={3}
                />
                <div className={styles.buttonRow}>
                  <button type="button" className={styles.primaryButton} onClick={handleAddFunction} disabled={loading}>
                    {loading ? 'Adding...' : 'Add'}
                  </button>
                  <button type="button" className={styles.secondaryButton} onClick={() => setAddFnOpen(false)}>Cancel</button>
                </div>
              </div>
            )}

            <ul className={styles.functionList}>
              {functions.map((fn) => (
                <li key={fn.id} className={styles.functionItem}>
                  <span className={styles.functionName}>{fn.name}</span>
                  <span className={styles.functionType}>{fn.function_type}</span>
                  {fn.config && Object.keys(fn.config).length > 0 && (
                    <code className={styles.functionConfig}>{JSON.stringify(fn.config)}</code>
                  )}
                  <button type="button" className={styles.removeButton} onClick={() => handleDeleteFunction(fn.id)}>×</button>
                </li>
              ))}
            </ul>
          </section>

          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>Test run</h2>
            <p className={styles.muted}>Send sample data (JSON array of objects). You need the API key (regenerate if needed).</p>
            <textarea
              className={styles.textarea}
              value={testDataJson}
              onChange={(e) => setTestDataJson(e.target.value)}
              rows={4}
              placeholder='[{"col1": 1, "col2": 2}, {"col1": null}]'
            />
            <button type="button" className={styles.primaryButton} onClick={handleTestRun}>
              Run
            </button>
            {testResult && (
              <div className={styles.testResult}>
                <p className={testResult.success ? styles.passed : styles.failed}>
                  {testResult.success ? 'All checks passed' : 'Some checks failed'}
                </p>
                <ul>
                  {testResult.results.map((r, i) => (
                    <li key={i}><strong>{r.name}</strong>: {r.passed ? '✓' : '✗'} {r.message}</li>
                  ))}
                </ul>
              </div>
            )}
          </section>
        </>
      )}
    </main>
  );
}
