# Environment setup

Target: the same setup on both machines, so code written by one of us runs unchanged for the other.

## 1. WSL2 (Windows only)

KDB-X does not install natively on Windows; it runs under WSL2. On macOS, skip to step 2.

```powershell
wsl --install -d Ubuntu     # admin PowerShell, then reboot
```

**Keep the repo and the data on the WSL filesystem** (`~/code/...`), *not* under `/mnt/c/...` and never in OneDrive. Cross-filesystem I/O is slow, and OneDrive will try to sync gigabytes of tick partitions.

```bash
mkdir -p ~/code && cd ~/code
git clone https://github.com/EthanTait/HEX-Research-Crypto.git
```

## 2. kdb+/q: KDB-X Community Edition (free)

- Sign up at the KX Developer Center (developer.kx.com). The welcome email contains a base64 `kc.lic` licence key.
- Run the online installer from the Developer Center page. It installs to `~/.kx` and puts `q` on your PATH.
- Terms at the time of writing: free, no expiry, commercial and offline use allowed; limits of about 16 GB RAM per process, 4 secondary threads and 8 IPC connections. Check the current terms on the KX site.
- Each of us uses **our own** licence. Licences never go in the repo.

Check the install:
```bash
q
q)1+1
q)\\
```

## 3. Python

```bash
# Miniforge inside WSL (a separate install from any Windows conda)
curl -L -O https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh
bash Miniforge3-Linux-x86_64.sh
conda create -n notset python=3.12 numpy pandas scipy statsmodels scikit-learn matplotlib pyarrow pyyaml jupyter
conda activate notset
pip install pykx nbstripout
```

PyKX runs q embedded when it can find a licence. Point `QLIC` at the folder holding `kc.lic` (e.g. `export QLIC=~/.kx` in `~/.bashrc`). Once the package list settles, freeze it into `environment.yml` and commit that.

## 4. Java

```bash
sudo apt update && sudo apt install -y openjdk-21-jdk maven
java -version && mvn -version
```

The q ↔ Java interface is KX's `javakdb` client (github.com/KxSystems/javakdb), added as a Maven dependency or vendored `c.java` once the `java/` project is created.

## 5. VS Code

Open the repo from WSL (`code .` inside `~/code/HEX-Research-Crypto`), then install:
- **WSL** (Microsoft)
- **kdb** (KX): connect to a running q process and run `.q` files or selections
- **Python** + **Jupyter** (Microsoft)
- **Extension Pack for Java** (Microsoft)

## 6. Course data

The 1-min archive (`binance_fordham.tar`, about 2.3 GB) lives outside the repo. Copy it into the WSL filesystem rather than reading it from OneDrive:

```bash
mkdir -p data/raw/fordham
tar -xf /path/to/binance_fordham.tar -C data/raw/fordham     # top level of the tar is binance/
```

Then write `config/local.yaml` (gitignored) with `paths.raw_fordham: data/raw/fordham`.

## 7. Claude Code (VS Code extension)

- Install the Claude Code extension and open the repo folder. `CLAUDE.md` loads automatically, together with the subagents in `.claude/agents/` and the skills in `.claude/skills/`.
- Start a session with `/m1-step` to pick up the next step of the Milestone 1 plan, or `/iterate` once the improvement loop is running.
- Personal permission tweaks go in `.claude/settings.local.json` (gitignored).

## 8. Git identity (inside WSL)

```bash
git config --global user.name  "Your Name"
git config --global user.email "you@fordham.edu"
git config --global core.autocrlf input
sudo apt install -y gh && gh auth login        # simplest way to authenticate pushes
```

## WSL stability (learned the hard way, 2026-11-06/07)

Four WSL hangs in two days (the VM stops answering, `wsl --shutdown` itself hangs, only `wsl --shutdown --force` recovers it). Two things correlate with them:

- **Large writes from inside WSL to `/mnt/c/...`** (the Windows-mounted side, through the 9p bridge and Defender's real-time scan). Keep every output on the Linux side (`output/`, `data/`), and read Linux files from Windows through `\\wsl.localhost\...` instead.
- **Host memory starvation.** With Chrome and VS Code open, Windows had under 1 GB free while the VM could take 50% of RAM. `C:\Users\<you>\.wslconfig` now caps it: `[wsl2] memory=4GB, swap=0, processors=4`. Our biggest job uses about 2.3 GB; run heavy Python one process at a time.

## Checklist

- [ ] `q` starts and prints no licence error
- [ ] `python -c "import pykx as kx; print(kx.q('til 3'))"` works
- [ ] `java -version` shows 21, `mvn -version` works
- [ ] repo cloned under `~/code`, not `/mnt/c`
- [ ] `config/local.yaml` points at the course archive
- [ ] Claude Code opens the repo and lists the project agents (`/agents`)
