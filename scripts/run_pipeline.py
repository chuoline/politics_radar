# scripts/run_pipeline.py
import subprocess, sys

def run(cmd):
    print("\n$ " + " ".join(cmd))
    r = subprocess.run(cmd)
    if r.returncode != 0:
        raise SystemExit(r.returncode)

def main():
    run([sys.executable, "-m", "scripts.doctor_env"])
    run([sys.executable, "-m", "scripts.10_init_db"])
    run([sys.executable, "-m", "scripts.30_build_chunks", "--rebuild"])
    run([sys.executable, "-m", "scripts.40_build_metrics", "--rebuild"])

if __name__ == "__main__":
    main()