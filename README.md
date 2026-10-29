# Configuration Drift Detection

Prototype penelitian **Out-of-Band Configuration Drift Detection and Intent Resynchronization via Graph Differentials**. Proyek ini membandingkan konfigurasi yang diharapkan dengan state router yang sedang berjalan.

## Isi proyek

- `topology/`: topologi ring Containerlab dan konfigurasi FRR untuk enam router.
- `intent/baseline.yml`: source of truth untuk interface, alamat IP, MTU, static route, dan OSPF.
- `src/drift_detection/`: collector FRR, normalisasi data, graph builder, dan drift detector.
- `tests/`: unit test untuk parser, normalisasi, dan perbandingan graf.
- `docs/addressing.md`: rencana alamat IP.
- `docs/validation.md`: hasil pengujian yang benar-benar dijalankan.

## Runtime Windows dan WSL2

Containerlab perlu berjalan pada Docker Engine yang network namespace Linux-nya bisa diakses dari WSL. Di lingkungan proyek ini, lab dijalankan dengan Docker Engine lokal di Ubuntu WSL. Docker Desktop tetap terpasang sebagai daemon terpisah; gunakan shell Ubuntu WSL untuk perintah Containerlab dan Docker yang mengelola lab ini.

Repository tetap berada di `/mnt/c`. Bind mount konfigurasi dari lokasi tersebut sudah digunakan saat deployment. Setelah container router di-restart, jalankan lagi `containerlab deploy` agar Containerlab memasang kembali link data-plane.

## Menjalankan lab

Buka Ubuntu WSL, masuk ke direktori repository, lalu jalankan:

```bash
containerlab deploy -t topology/drift.clab.yml
containerlab inspect -t topology/drift.clab.yml
```

Untuk memeriksa OSPF atau interface:

```bash
docker exec clab-drift-detection-r1 vtysh -c "show ip ospf neighbor"
docker exec clab-drift-detection-r1 vtysh -c "show interface brief"
```

## Menjalankan collector dan detector

Dari PowerShell di direktori repository, siapkan virtual environment dan install dependensi:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
```

Collector di Windows menggunakan `wsl.exe` untuk menjalankan Docker CLI pada distro WSL default. Kumpulkan state dan jalankan detector:

```powershell
.\.venv\Scripts\python.exe -m drift_detection.cli collect --baseline intent/baseline.yml --output artifacts/live_state.json
.\.venv\Scripts\python.exe -m drift_detection.cli detect --baseline intent/baseline.yml --observed artifacts/live_state.json
```

Untuk laporan JSON:

```powershell
.\.venv\Scripts\python.exe -m drift_detection.cli detect --baseline intent/baseline.yml --observed artifacts/live_state.json --format json
```

Snapshot `artifacts/live_state.json` memisahkan configuration state dari operational state. Route dinamis OSPF dicatat untuk debugging, tetapi tidak dibandingkan sebagai static-route intent.

## Unit test

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Prototype saat ini mencakup fondasi awal: lab FRR, OSPF, baseline YAML, collector, dan graph-based drift detection. Remediasi otomatis, kampanye eksperimen, dan analisis metrik akhir belum termasuk tahap ini.

FRR masih menampilkan peringatan bahwa `/etc/frr/vtysh.conf` tidak tersedia; perintah `vtysh` yang diuji tetap berhasil.
