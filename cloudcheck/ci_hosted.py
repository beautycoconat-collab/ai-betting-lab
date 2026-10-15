"""Temporary CA material, removed on exit; secret values never printed."""
import os
import subprocess
import sys
import tempfile

def main():
    with tempfile.TemporaryDirectory(prefix='ai-lab-ca-') as directory:
        path=os.path.join(directory,'ca.pem')
        with open(path,'w') as output:output.write(os.environ.get('LAB_CA_PEM',''))
        os.chmod(path,0o600)
        env=dict(os.environ,LAB_SSLROOTCERT=path)
        return subprocess.run([sys.executable,'-m','cloudcheck.runner','--mode','hosted','--out','reports/phase01/hosted.json'],env=env,check=False).returncode

if __name__=='__main__':raise SystemExit(main())
