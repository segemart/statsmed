'use client';

import { useState, useEffect, useCallback, FormEvent } from 'react';
import {
  listFiles,
  uploadFile,
  getPreview,
  getTests,
  runAnalysis,
  deleteResult,
  deleteFile,
  downloadPdf,
  type FileInfo,
  type PreviewResponse,
  type TestSchema,
  type PreviewResult,
} from '../lib/api';
import styles from './Dashboard.module.css';

export default function Dashboard() {
  const [files, setFiles] = useState<FileInfo[]>([]);
  const [tests, setTests] = useState<Record<string, TestSchema>>({});
  const [selectedFileId, setSelectedFileId] = useState<number | null>(null);
  const [preview, setPreview] = useState<PreviewResponse | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState('');
  const [csvDelimiter, setCsvDelimiter] = useState('comma');
  const [runLoading, setRunLoading] = useState(false);
  const [runError, setRunError] = useState('');
  const [selectedTestId, setSelectedTestId] = useState('');
  const [params, setParams] = useState<Record<string, unknown>>({});
  const [pdfLoading, setPdfLoading] = useState(false);

  const loadFiles = useCallback(async () => {
    try {
      const list = await listFiles();
      setFiles(list);
      if (list.length > 0 && !selectedFileId) {
        setSelectedFileId(list[0].id);
      }
    } catch {
      setFiles([]);
    }
  }, [selectedFileId]);

  const loadTests = useCallback(async () => {
    try {
      const t = await getTests();
      setTests(t);
    } catch {
      setTests({});
    }
  }, []);

  const loadPreview = useCallback(async (fileId: number) => {
    try {
      const p = await getPreview(fileId);
      setPreview(p);
      setSelectedTestId('');
      setParams({});
    } catch {
      setPreview(null);
    }
  }, []);

  useEffect(() => {
    loadFiles();
    loadTests();
  }, [loadFiles, loadTests]);

  useEffect(() => {
    if (selectedFileId) {
      loadPreview(selectedFileId);
    } else {
      setPreview(null);
    }
  }, [selectedFileId, loadPreview]);

  const handleUpload = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const input = (e.target as HTMLFormElement).elements.namedItem('file') as HTMLInputElement;
    const file = input?.files?.[0];
    if (!file) {
      setUploadError('Please select a file.');
      return;
    }
    setUploadError('');
    setUploading(true);
    try {
      const created = await uploadFile(file, csvDelimiter);
      await loadFiles();
      setSelectedFileId(created.id);
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const handleRemoveFile = async (fileId: number) => {
    try {
      await deleteFile(fileId);
      await loadFiles();
      if (selectedFileId === fileId) {
        setSelectedFileId(files.length > 1 ? files.find((f) => f.id !== fileId)?.id ?? null : null);
      }
    } catch {
      // ignore
    }
  };

  const handleRun = async (e: FormEvent) => {
    e.preventDefault();
    if (!selectedFileId || !selectedTestId) return;
    setRunError('');
    setRunLoading(true);
    try {
      await runAnalysis(selectedFileId, selectedTestId, params);
      await loadPreview(selectedFileId);
    } catch (err) {
      setRunError(err instanceof Error ? err.message : 'Run failed');
    } finally {
      setRunLoading(false);
    }
  };

  const handleDeleteResult = async (resultId: number) => {
    if (!selectedFileId) return;
    try {
      await deleteResult(selectedFileId, resultId);
      await loadPreview(selectedFileId);
    } catch {
      // ignore
    }
  };

  const handleDownloadPdf = async () => {
    if (!selectedFileId) return;
    setPdfLoading(true);
    try {
      const blob = await downloadPdf(selectedFileId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `statsmed_report_${new Date().toISOString().slice(0, 10)}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      // ignore
    } finally {
      setPdfLoading(false);
    }
  };

  const test = selectedTestId ? tests[selectedTestId] : null;

  return (
    <main className={styles.main}>
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Upload data</h2>
        <p className={styles.muted}>CSV, XLSX, or XLS. Data is saved to your account.</p>
        <form onSubmit={handleUpload} className={styles.uploadForm}>
          <select
            className={styles.select}
            value={csvDelimiter}
            onChange={(e) => setCsvDelimiter(e.target.value)}
          >
            <option value="comma">Comma</option>
            <option value="semicolon">Semicolon</option>
            <option value="tab">Tab</option>
            <option value="pipe">Pipe</option>
          </select>
          <input type="file" name="file" accept=".csv,.xlsx,.xls" className={styles.fileInput} />
          <button type="submit" className={styles.primaryButton} disabled={uploading}>
            {uploading ? 'Uploading...' : 'Upload'}
          </button>
        </form>
        {uploadError && <p className={styles.error}>{uploadError}</p>}
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Your files</h2>
        {files.length === 0 ? (
          <p className={styles.muted}>No files yet. Upload a file above.</p>
        ) : (
          <div className={styles.fileList}>
            {files.map((f) => (
              <div
                key={f.id}
                className={`${styles.fileItem} ${selectedFileId === f.id ? styles.fileItemActive : ''}`}
              >
                <button
                  type="button"
                  className={styles.fileItemName}
                  onClick={() => setSelectedFileId(f.id)}
                >
                  {f.original_filename}
                </button>
                <button
                  type="button"
                  className={styles.removeButton}
                  onClick={() => handleRemoveFile(f.id)}
                  title="Remove file"
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        )}
      </section>

      {preview && (
        <>
          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>Data preview — {preview.original_filename}</h2>
            <div
              className={styles.previewTable}
              dangerouslySetInnerHTML={{ __html: preview.preview_html }}
            />
          </section>

          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>Run test</h2>
            <form onSubmit={handleRun} className={styles.runForm}>
              <div className={styles.formRow}>
                <label className={styles.label}>Test</label>
                <select
                  className={styles.select}
                  value={selectedTestId}
                  onChange={(e) => {
                    setSelectedTestId(e.target.value);
                    setParams({});
                  }}
                >
                  <option value="">— Select a test —</option>
                  {Object.entries(tests).map(([id, t]) => (
                    <option key={id} value={id}>
                      {t.label}
                    </option>
                  ))}
                </select>
              </div>

              {test && (
                <>
                  <p className={styles.testDescription}>{test.description}</p>
                  {test.inputs.map((inp) => (
                    <div key={inp.name} className={styles.formRow}>
                      <label className={styles.label}>{inp.label}</label>
                      {inp.type === 'column' && (
                        <select
                          className={styles.select}
                          value={(params[inp.name] as string) || ''}
                          onChange={(e) => setParams((p) => ({ ...p, [inp.name]: e.target.value }))}
                        >
                          <option value="">— Select —</option>
                          {preview.columns.map((c) => (
                            <option key={c} value={c}>
                              {c}
                            </option>
                          ))}
                        </select>
                      )}
                      {inp.type === 'multi_column' && (
                        <select
                          className={styles.select}
                          multiple
                          size={5}
                          value={(params[inp.name] as string[]) || []}
                          onChange={(e) => {
                            const opts = e.target.options;
                            const selected = Array.from(opts)
                              .filter((o) => o.selected)
                              .map((o) => o.value);
                            setParams((p) => ({ ...p, [inp.name]: selected }));
                          }}
                        >
                          {preview.columns.map((c) => (
                            <option key={c} value={c}>
                              {c}
                            </option>
                          ))}
                        </select>
                      )}
                      {inp.type === 'boolean' && (
                        <label className={styles.checkLabel}>
                          <input
                            type="checkbox"
                            checked={(params[inp.name] as boolean) ?? inp.default ?? false}
                            onChange={(e) =>
                              setParams((p) => ({ ...p, [inp.name]: e.target.checked }))
                            }
                          />
                          {inp.label}
                        </label>
                      )}
                      {inp.type === 'number' && (
                        <input
                          type="number"
                          className={styles.input}
                          step="any"
                          value={(params[inp.name] as number) ?? inp.default ?? ''}
                          onChange={(e) =>
                            setParams((p) => ({
                              ...p,
                              [inp.name]: e.target.value === '' ? undefined : Number(e.target.value),
                            }))
                          }
                        />
                      )}
                      {inp.type === 'select' && (
                        <select
                          className={styles.select}
                          value={(params[inp.name] as string) ?? inp.default ?? ''}
                          onChange={(e) => setParams((p) => ({ ...p, [inp.name]: e.target.value }))}
                        >
                          {inp.options?.map((opt) => (
                            <option key={opt.value} value={opt.value}>
                              {opt.label}
                            </option>
                          ))}
                        </select>
                      )}
                    </div>
                  ))}
                  <button type="submit" className={styles.primaryButton} disabled={runLoading}>
                    {runLoading ? 'Running...' : 'Run'}
                  </button>
                </>
              )}
            </form>
            {runError && <p className={styles.error}>{runError}</p>}
          </section>

          <section className={styles.section}>
            <div className={styles.resultsHeader}>
              <h2 className={styles.sectionTitle}>Results</h2>
              {preview.results.length > 0 && (
                <button
                  type="button"
                  className={styles.secondaryButton}
                  onClick={handleDownloadPdf}
                  disabled={pdfLoading}
                >
                  {pdfLoading ? '...' : 'Download PDF'}
                </button>
              )}
            </div>
            {preview.results.length === 0 ? (
              <p className={styles.muted}>No results yet. Run a test above.</p>
            ) : (
              <div className={styles.resultsList}>
                {preview.results.map((r) => (
                  <ResultCard
                    key={r.id}
                    result={r}
                    onDelete={() => handleDeleteResult(r.id)}
                  />
                ))}
              </div>
            )}
          </section>
        </>
      )}
    </main>
  );
}

function ResultCard({
  result,
  onDelete,
}: {
  result: PreviewResult;
  onDelete: () => void;
}) {
  const [expanded, setExpanded] = useState(true);
  return (
    <div className={styles.resultCard}>
      <div className={styles.resultHeader}>
        <button
          type="button"
          className={styles.resultLabel}
          onClick={() => setExpanded((e) => !e)}
        >
          {expanded ? '▼' : '▶'} {result.label}
        </button>
        <button type="button" className={styles.removeButton} onClick={onDelete} title="Delete">
          ×
        </button>
      </div>
      <p className={styles.resultMeta}>
        {result.description} — {result.timestamp}
      </p>
      {expanded && (
        <>
          <pre className={styles.resultText}>{result.text}</pre>
          {result.figure && (
            <img
              src={`data:image/png;base64,${result.figure}`}
              alt="Figure"
              className={styles.resultFigure}
            />
          )}
        </>
      )}
    </div>
  );
}
