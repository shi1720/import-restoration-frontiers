"""Recompute the complete analysis from the selected, verified data snapshot."""
from pathlib import Path
import argparse,hashlib,json,subprocess,sys,os
ROOT=Path(__file__).resolve().parent

def verify():
    manifest=json.loads((ROOT/'data/source_manifest.json').read_text())
    for name,info in manifest['members'].items():
        if name.startswith('BACI_'):
            year=name.split('_Y')[1][:4]; path=ROOT/'data'/f'baci_selected_{year}.csv'
        else:path=ROOT/'data'/name
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        if digest!=info['sha256_selected']:raise ValueError(f'Data checksum mismatch: {path.name}')
    print('All selected source-data hashes verified.',flush=True)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--verify',action='store_true');ap.add_argument('--paper',action='store_true');args=ap.parse_args()
    if args.verify:verify()
    env=dict(os.environ,OPENBLAS_NUM_THREADS='1')
    commands=[['-m','unittest','discover','-s','src','-p','test_model.py','-v'],['src/analyze.py']+list(map(str,range(2017,2025))),['src/diagnostics.py'],['src/robustness.py'],['src/case_study.py'],['src/figures.py'],['src/tables.py']]
    for command in commands:
        subprocess.run([sys.executable]+command,cwd=ROOT,env=env,check=True)
    if args.paper:
        if not (ROOT/'paper/manuscript.tex').exists():raise FileNotFoundError('Manuscript source is available in the local deliverable archive after author review.')
        subprocess.run(['tectonic','--keep-logs','--outdir','paper','paper/manuscript.tex'],cwd=ROOT,check=True)
    print('Complete reproduction succeeded.',flush=True)
if __name__=='__main__':main()
