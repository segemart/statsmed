'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  listQCOperations,
  createQCOperation,
  deleteQCOperation,
  listQCFunctions,
  createQCFunction,
  deleteQCFunction,
  runQualityControl,
  getTests,
  type QCOperation,
  type QCFunction,
} from '../lib/api';
import type { TestSchema } from '../lib/api';
import styles from './QualityControl.module.css';

const FUNCTION_TYPES = [
  { value: 'statsmed_test', label: 'Statsmed test', configHint: 'Select test and map columns' },
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
  const [addFnType, setAddFnType] = useState('statsmed_test');
  const [addFnConfig, setAddFnConfig] = useState('{}');
  const [testsSchema, setTestsSchema] = useState<Record<string, TestSchema>>({});
  const [addFnTestId, setAddFnTestId] = useState('');
  const [addFnParams, setAddFnParams] = useState<Record<string, unknown>>({});
  const [testDataJson, setTestDataJson] = useState('[{"a":1,"b":2},{"a":null,"b":3}]');
  const [testResult, setTestResult] = useState<{ success: boolean; results: { name: string; passed: boolean; message: string }[] } | null>(null);

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

  useEffect(() => {
    if (addFnOpen && addFnType === 'statsmed_test') {
      getTests().then(setTestsSchema).catch(() => setTestsSchema({}));
    }
  }, [addFnOpen, addFnType]);

  useEffect(() => {
    if (!addFnTestId || !testsSchema[addFnTestId]) {
      setAddFnParams({});
      return;
    }
    const test = testsSchema[addFnTestId];
    const initial: Record<string, unknown> = {};
    test.inputs.forEach((inp) => {
      if (inp.type === 'boolean') initial[inp.name] = inp.default ?? false;
      else if (inp.type === 'number' || inp.type === 'select') initial[inp.name] = inp.default ?? '';
      else if (inp.type === 'multi_column') initial[inp.name] = [];
      else initial[inp.name] = '';
    });
    setAddFnParams((prev) => {
      const next = { ...initial };
      test.inputs.forEach((inp) => {
        if (prev[inp.name] !== undefined && prev[inp.name] !== '') next[inp.name] = prev[inp.name];
      });
      return next;
    });
  }, [addFnTestId, testsSchema]);

  const selectedOp = operations.find((o) => o.id === selectedOpId);
  const selectedTest = addFnTestId ? testsSchema[addFnTestId] : null;

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
      if (op.api_key) setCreatedApiKey(op.api_key);
      await loadOperations();
      setSelectedOpId(op.id);
      setCreateName('');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Create failed');
    } finally {
      setLoading(false);
    }
  };

  const handleAddFunction = async () => {
    if (!selectedOpId) return;
    const name = addFnName.trim() || 'Unnamed';
    let config: Record<string, unknown> = {};
    if (addFnType === 'statsmed_test') {
      if (!addFnTestId) {
        setError('Select a Statsmed test');
        return;
      }
      config = { test_id: addFnTestId, params: { ...addFnParams } };
      if (selectedTest) {
        selectedTest.inputs.forEach((inp) => {
          if (inp.type === 'multi_column') {
            const v = (config.params as Record<string, unknown>)[inp.name];
            (config.params as Record<string, unknown>)[inp.name] = typeof v === 'string'
              ? (v ? (v as string).split(',').map((s) => s.trim()).filter(Boolean) : [])
              : Array.isArray(v) ? v : [];
          }
        });
      }
    } else {
      try {
        config = addFnConfig.trim() ? JSON.parse(addFnConfig) : {};
      } catch {
        setError('Invalid JSON config');
        return;
      }
    }
    setError('');
    setLoading(true);
    try {
      await createQCFunction(selectedOpId, name, addFnType, config);
      await loadFunctions(selectedOpId);
      setAddFnOpen(false);
      setAddFnName('');
      setAddFnConfig('{}');
      setAddFnTestId('');
      setAddFnParams({});
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
      if (selectedOpId === opId) setSelectedOpId(null);
      await loadOperations();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed');
    }
  };

  const handleTestRun = async () => {
    if (!selectedOpId || !selectedOp) return;
    const key = selectedOp.api_key;
    if (!key) {
      setError('No API key for this operation.');
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
                <p className={styles.success}>Operation created. Your API key is shown below and in the operation details; you can copy it anytime.</p>
                <div className={styles.apiKeyBox}>
                  <code className={styles.apiKey}>{createdApiKey}</code>
                  <button
                    type="button"
                    className={styles.smallButton}
                    onClick={() => navigator.clipboard.writeText(createdApiKey)}
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
              <code className={styles.apiKey}>{selectedOp.api_key ?? '—'}</code>
              <button
                type="button"
                className={styles.smallButton}
                onClick={() => selectedOp.api_key && navigator.clipboard.writeText(selectedOp.api_key)}
                disabled={!selectedOp.api_key}
              >
                Copy
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
                  placeholder={addFnType === 'statsmed_test' ? 'e.g. Normality check on Age' : 'e.g. Check missing in critical columns'}
                />
                <label className={styles.label}>Type</label>
                <select className={styles.select} value={addFnType} onChange={(e) => { setAddFnType(e.target.value); setAddFnTestId(''); setAddFnParams({}); }}>
                  {FUNCTION_TYPES.map((t) => (
                    <option key={t.value} value={t.value}>{t.label}</option>
                  ))}
                </select>

                {addFnType === 'statsmed_test' ? (
                  <>
                    <label className={styles.label}>Statsmed test</label>
                    <select
                      className={styles.select}
                      value={addFnTestId}
                      onChange={(e) => setAddFnTestId(e.target.value)}
                    >
                      <option value="">— Select a test —</option>
                      {Object.entries(testsSchema).map(([id, t]) => (
                        <option key={id} value={id}>{t.label}</option>
                      ))}
                    </select>
                    {selectedTest && (
                      <>
                        <p className={styles.muted}>{selectedTest.description}</p>
                        {selectedTest.inputs.map((inp) => (
                          <div key={inp.name}>
                            <label className={styles.label}>{inp.label}</label>
                            {inp.type === 'column' && (
                              <input
                                type="text"
                                className={styles.input}
                                value={(addFnParams[inp.name] as string) ?? ''}
                                onChange={(e) => setAddFnParams((p) => ({ ...p, [inp.name]: e.target.value }))}
                                placeholder="Column name in your data"
                              />
                            )}
                            {inp.type === 'multi_column' && (
                              <input
                                type="text"
                                className={styles.input}
                                value={Array.isArray(addFnParams[inp.name]) ? (addFnParams[inp.name] as string[]).join(', ') : (addFnParams[inp.name] as string) ?? ''}
                                onChange={(e) => setAddFnParams((p) => ({ ...p, [inp.name]: e.target.value }))}
                                placeholder="Column names, comma-separated"
                              />
                            )}
                            {inp.type === 'number' && (
                              <input
                                type="number"
                                className={styles.input}
                                step="any"
                                value={(addFnParams[inp.name] as number) ?? inp.default ?? ''}
                                onChange={(e) => setAddFnParams((p) => ({ ...p, [inp.name]: e.target.value === '' ? inp.default : Number(e.target.value) }))}
                              />
                            )}
                            {inp.type === 'boolean' && (
                              <label className={styles.checkLabel}>
                                <input
                                  type="checkbox"
                                  checked={(addFnParams[inp.name] as boolean) ?? inp.default ?? false}
                                  onChange={(e) => setAddFnParams((p) => ({ ...p, [inp.name]: e.target.checked }))}
                                />
                                {inp.label}
                              </label>
                            )}
                            {inp.type === 'select' && (
                              <select
                                className={styles.select}
                                value={(addFnParams[inp.name] as string) ?? inp.default ?? ''}
                                onChange={(e) => setAddFnParams((p) => ({ ...p, [inp.name]: e.target.value }))}
                              >
                                {inp.options?.map((opt) => (
                                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                                ))}
                              </select>
                            )}
                          </div>
                        ))}
                      </>
                    )}
                  </>
                ) : (
                  <>
                    <label className={styles.label}>Config (JSON) — e.g. missing: {`{"columns": ["col1", "col2"]}`}, range: {`{"column": "x", "min": 0, "max": 100}`}</label>
                    <textarea
                      className={styles.textarea}
                      value={addFnConfig}
                      onChange={(e) => setAddFnConfig(e.target.value)}
                      rows={3}
                    />
                  </>
                )}

                <div className={styles.buttonRow}>
                  <button type="button" className={styles.primaryButton} onClick={handleAddFunction} disabled={loading}>
                    {loading ? 'Adding...' : 'Add'}
                  </button>
                  <button type="button" className={styles.secondaryButton} onClick={() => { setAddFnOpen(false); setAddFnTestId(''); setAddFnParams({}); }}>Cancel</button>
                </div>
              </div>
            )}

            <ul className={styles.functionList}>
              {functions.map((fn) => (
                <li key={fn.id} className={styles.functionItem}>
                  <span className={styles.functionName}>{fn.name}</span>
                  <span className={styles.functionType}>
                    {fn.function_type === 'statsmed_test' && fn.config && typeof fn.config === 'object' && 'test_id' in fn.config
                      ? `Statsmed: ${(fn.config as { test_id?: string }).test_id}`
                      : fn.function_type}
                  </span>
                  {fn.config && typeof fn.config === 'object' && 'params' in fn.config && fn.function_type === 'statsmed_test' && (
                    <code className={styles.functionConfig}>
                      {(fn.config as { params?: Record<string, unknown> }).params && Object.entries((fn.config as { params: Record<string, unknown> }).params).length > 0
                        ? Object.entries((fn.config as { params: Record<string, unknown> }).params)
                            .map(([k, v]) => `${k} → ${Array.isArray(v) ? v.join(', ') : String(v)}`)
                            .join('; ')
                        : (fn.config as { test_id?: string }).test_id}
                    </code>
                  )}
                  {fn.config && fn.function_type !== 'statsmed_test' && Object.keys(fn.config).length > 0 && (
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
