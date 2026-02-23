import os
import io
import uuid
import base64
import logging
import tempfile
from datetime import datetime
import pandas as pd
from flask import Flask, render_template, request, redirect, send_file
from fpdf import FPDF
from web.interface import TESTS

SESSION_TTL = 48 * 3600  # 48 hours in seconds

def create_app(test_config=None):

    app = Flask(__name__)
    logger = logging.getLogger(__name__)
    UPLOAD_DIR = os.path.join(os.path.dirname(__file__), 'tmp')
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    HISTORY = {}  # filepath → list of result dicts (newest first)
    DELIMITERS = {}  # filepath → delimiter char for CSV (e.g. ',', ';', '\t')

    @app.before_request
    def cleanup_stale_sessions():
        """Evict HISTORY entries and temp files older than SESSION_TTL."""
        now = datetime.now()
        stale = []
        for filepath, results in HISTORY.items():
            if not results:
                if os.path.exists(filepath):
                    age = now.timestamp() - os.path.getmtime(filepath)
                    if age > SESSION_TTL:
                        stale.append(filepath)
                else:
                    stale.append(filepath)
            else:
                last = datetime.strptime(results[0]['timestamp'], "%Y-%m-%d %H:%M:%S")
                if (now - last).total_seconds() > SESSION_TTL:
                    stale.append(filepath)
        for filepath in stale:
            logger.info(f"Cleanup: evicting stale session for {filepath}")
            HISTORY.pop(filepath, None)
            if os.path.exists(filepath):
                os.remove(filepath)

    def _read_df(filepath):
        if filepath.endswith('.csv'):
            sep = DELIMITERS.get(filepath, ',')
            return pd.read_csv(filepath, sep=sep)
        return pd.read_excel(filepath)

    def _col_types(df):
        """Return dict of column name → 'numeric' or 'string'."""
        return {col: 'numeric' if df[col].dtype.kind in 'iufb' else 'string'
                for col in df.columns}

    def _render_upload(filepath, filename, **extra):
        """Helper to render upload.html with common context."""
        df = _read_df(filepath)
        return render_template('upload.html',
            tests=TESTS,
            columns=df.columns.tolist(),
            col_types=_col_types(df),
            preview=df.head(10).to_html(classes='table table-sm table-bordered table-striped', index=False),
            filepath=filepath,
            filename=filename,
            results_history=HISTORY.get(filepath, []),
            **extra)

    @app.route('/')
    def index():
        logger.info("Home page accessed")
        return render_template('home.html')

    @app.route('/upload', methods=['POST'])
    def upload():
        f = request.files.get('file')
        if not f or not f.filename:
            return redirect('/')
        ext = os.path.splitext(f.filename)[1].lower()
        if ext not in {'.csv', '.xlsx', '.xls'}:
            logger.warning(f"Upload rejected: invalid extension '{ext}' for file '{f.filename}'")
            return redirect('/')
        safe_name = f"{uuid.uuid4().hex}_{f.filename}"
        path = os.path.join(UPLOAD_DIR, safe_name)
        f.save(path)
        # Store CSV delimiter for this file (only used when reading CSV)
        delim = request.form.get('csv_delimiter', ',')
        if delim == 'semicolon':
            delim = ';'
        elif delim == 'tab':
            delim = '\t'
        elif delim == 'pipe':
            delim = '|'
        else:
            delim = ','
        DELIMITERS[path] = delim
        try:
            _read_df(path)
        except Exception:
            logger.error(f"Upload failed: could not read file '{f.filename}'")
            os.remove(path)
            DELIMITERS.pop(path, None)
            return redirect('/')
        logger.info(f"File uploaded: '{f.filename}' -> {safe_name}")
        HISTORY[path] = []
        return _render_upload(path, f.filename)

    @app.route('/clear', methods=['POST'])
    def clear():
        filepath = request.form.get('filepath')
        if filepath:
            logger.info(f"File removed: {filepath}")
            HISTORY.pop(filepath, None)
            DELIMITERS.pop(filepath, None)
            if os.path.exists(filepath):
                os.remove(filepath)
        return redirect('/')

    @app.route('/run', methods=['POST'])
    def run():
        filepath = request.form.get('filepath')
        filename = request.form.get('filename', '')
        if not filepath or not os.path.exists(filepath):
            return redirect('/')
        test_id = request.form['test']
        test = TESTS[test_id]
        df = _read_df(filepath)

        # Collect params
        params = {}
        col_names = []
        cols_to_convert = []  # column names that need categorical conversion
        for inp in test['inputs']:
            if inp['type'] == 'boolean':
                params[inp['name']] = request.form.get(inp['name']) == 'on'
            elif inp['type'] == 'number':
                params[inp['name']] = float(request.form[inp['name']])
            elif inp['type'] == 'multi_column':
                params[inp['name']] = request.form.getlist(inp['name'])
                col_names.extend(params[inp['name']])
            elif inp['type'] == 'select':
                params[inp['name']] = request.form[inp['name']]
            else:
                params[inp['name']] = request.form[inp['name']]
                if inp['type'] == 'column':
                    col_names.append(params[inp['name']])
                    if request.form.get(f'convert_{inp["name"]}') == 'on':
                        cols_to_convert.append(params[inp['name']])

        # Also collect multi-column conversion requests
        multi_convert = request.form.getlist('convert_multi_col')
        for col in multi_convert:
            if col not in cols_to_convert:
                cols_to_convert.append(col)

        # Apply categorical conversion
        convert_mode = request.form.get('convert_mode', 'shared')
        conversions = []
        if cols_to_convert:
            if convert_mode == 'shared':
                # Build one mapping from the union of all values across columns
                all_values = sorted(set(str(v) for col in cols_to_convert
                                        for v in df[col].dropna().unique()))
                shared_mapping = {v: i for i, v in enumerate(all_values)}
                mapping_str = ', '.join(f'{v} -> {i}' for v, i in shared_mapping.items())
                for col in cols_to_convert:
                    df[col] = df[col].astype(str).map(shared_mapping).astype(int)
                    conversions.append(f"Column '{col}' converted (shared): {mapping_str}")
            else:
                # Independent mapping per column
                for col in cols_to_convert:
                    uniques = sorted(df[col].dropna().unique(), key=str)
                    mapping = {str(v): i for i, v in enumerate(uniques)}
                    df[col] = df[col].astype(str).map(mapping).astype(int)
                    mapping_str = ', '.join(f'{v} -> {i}' for v, i in mapping.items())
                    conversions.append(f"Column '{col}' converted: {mapping_str}")

        # Warn if the same column is used for multiple inputs
        dup_warning = ''
        if len(col_names) != len(set(col_names)):
            dup_warning = ("WARNING: The same column was selected for multiple inputs. "
                           "Results may be erroneous.\n\n")

        logger.info(f"Running test '{test_id}' on columns: {col_names}")
        try:
            text, figure = test['run'](df, params)
        except Exception as e:
            logger.error(f"Test '{test_id}' failed: {e}")
            text, figure = f"Error: {e}", None

        # Prepend warnings and conversion info to text output
        prefix_parts = []
        if dup_warning:
            prefix_parts.append(dup_warning.strip())
        if conversions:
            prefix_parts.append('\n'.join(conversions))
        if prefix_parts:
            text = '\n\n'.join(prefix_parts) + '\n\n' + text

        label = f"{test['label']} ({', '.join(col_names)})"

        if filepath not in HISTORY:
            HISTORY[filepath] = []
        HISTORY[filepath].insert(0, {
            "label": label,
            "description": test['description'],
            "text": text,
            "figure": figure,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })

        return _render_upload(filepath, filename,
            selected_test=test_id, selected_params=params)

    @app.route('/delete_result', methods=['POST'])
    def delete_result():
        filepath = request.form.get('filepath')
        filename = request.form.get('filename', '')
        idx = int(request.form.get('idx', -1))
        history = HISTORY.get(filepath, [])
        if 0 <= idx < len(history):
            logger.info(f"Result deleted: index {idx} for {filename}")
            history.pop(idx)
        if not filepath or not os.path.exists(filepath):
            return redirect('/')
        return _render_upload(filepath, filename)

    @app.route('/download', methods=['POST'])
    def download():
        filepath = request.form.get('filepath')
        filename = request.form.get('filename', 'data')
        history = HISTORY.get(filepath, [])
        logger.info(f"PDF download requested for '{filename}' ({len(history)} results)")

        logo_path = os.path.join(os.path.dirname(__file__), 'static', 'images', 'statsmed_logo_transp.png')

        class StatsmedPDF(FPDF):
            def footer(self):
                self.set_y(-15)
                self.set_font('Helvetica', 'I', 8)
                self.set_text_color(150, 150, 150)
                self.cell(0, 10, f'\u00a9 {datetime.now().year} Martin Segeroth, Ashraya Indrakanti', align='C')

        pdf = StatsmedPDF()
        pdf.set_auto_page_break(auto=True, margin=20)
        pdf.add_page()

        if os.path.exists(logo_path):
            logo_w = 25
            pdf.image(logo_path, x=pdf.w - pdf.r_margin - logo_w, y=pdf.t_margin, w=logo_w)

        pdf.set_font('Helvetica', 'B', 18)
        pdf.cell(0, 12, 'Statsmed Analysis Report', ln=True)
        pdf.set_font('Helvetica', '', 10)
        pdf.set_text_color(120, 120, 120)
        pdf.cell(0, 8, f'File: {filename}    Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', ln=True)
        pdf.ln(4)

        for r in history:
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Helvetica', 'B', 13)
            pdf.cell(0, 10, r['label'], ln=True)
            pdf.set_font('Helvetica', '', 9)
            pdf.set_text_color(120, 120, 120)
            pdf.cell(0, 6, f"{r['description']}  |  {r['timestamp']}", ln=True)
            pdf.ln(2)
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('Courier', '', 9)
            pdf.multi_cell(0, 4.5, r['text'])
            if r['figure']:
                img_bytes = base64.b64decode(r['figure'])
                tmp = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
                tmp.write(img_bytes)
                tmp.close()
                img_w = pdf.w - pdf.l_margin - pdf.r_margin
                pdf.image(tmp.name, w=img_w)
                os.unlink(tmp.name)
            pdf.ln(6)

        buf = io.BytesIO()
        pdf.output(buf)
        buf.seek(0)
        dl_name = f"statsmed_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        return send_file(buf, as_attachment=True, download_name=dl_name, mimetype='application/pdf')

    return app
