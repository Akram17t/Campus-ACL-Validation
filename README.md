# Campus ACL Validation

Proyek tugas besar Software Defined Networking (SDN) untuk mengotomatisasi
pembuatan dan validasi aturan akses jaringan kampus berbasis VLAN.

Sistem yang dituju menerima kebijakan akses, menerjemahkannya menjadi ACL,
mendeteksi aturan yang bertentangan atau tertutupi, lalu menguji apakah perilaku
jaringan sesuai dengan kebijakan tersebut.

## Status

Repositori ini berisi struktur awal, contoh konfigurasi, dan rancangan alur kerja.
Compiler ACL, analisis aturan, integrasi controller, dan probe jaringan belum
diimplementasikan. Contoh kebijakan belum dapat diterapkan ke jaringan.

## Struktur repositori

```text
.
├── .github/workflows/ci.yml  # Pemeriksaan dasar Python dan contoh JSON
├── configs/vlans.json       # Inventaris VLAN dan subnet kampus
├── policies/campus.json     # Contoh kebijakan akses antar-VLAN
├── docs/architecture.md     # Kontrak modul dan tahapan implementasi
├── src/campus_acl/
│   ├── __init__.py
│   ├── policy.py            # Pembacaan dan validasi kebijakan
│   ├── compiler.py          # Penerjemahan kebijakan menjadi ACL
│   ├── analyzer.py          # Deteksi konflik dan shadowing
│   └── probes.py            # Pengujian konektivitas dan pelaporan
├── topologies/              # Rencana lingkungan emulasi jaringan
├── tests/
│   ├── unit/               # Rencana pengujian logika inti
│   └── integration/        # Rencana pengujian jaringan
├── outputs/                 # Hasil ACL dan laporan lokal (diabaikan Git)
└── pyproject.toml
```

## Persiapan pengembangan

Gunakan Python 3.11 atau lebih baru. Dari direktori repositori:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

Paket inti belum memiliki dependensi runtime. Lingkungan controller dan emulator
akan ditentukan saat integrasi jaringan dibuat; direktori `topologies/` mencatat
rencana penggunaan Mininet dan Open vSwitch pada Linux.

Pemeriksaan struktur awal:

```powershell
python -m compileall -q src
python -m json.tool configs/vlans.json
python -m json.tool policies/campus.json
```

Perintah tersebut hanya memeriksa sintaks Python dan JSON, bukan kebenaran ACL
atau perilaku jaringan. Belum tersedia CLI maupun pengujian otomatis fungsional.

## Contoh kebijakan

| VLAN sumber | VLAN tujuan | Layanan yang diizinkan |
| --- | --- | --- |
| Staff (10) | Servers (40) | HTTPS |
| Guest (20) | Servers (40) | DNS melalui UDP dan TCP |
| IoT (30) | Servers (40) | MQTT |

Akses antar-VLAN lainnya menggunakan kebijakan default `deny`.
Semantik aturan dan batas cakupan dijelaskan di [arsitektur](docs/architecture.md).

## Tahapan implementasi

1. Validasi inventaris VLAN, layanan, dan aturan kebijakan.
2. Analisis konflik serta aturan yang tertutupi berdasarkan urutan evaluasi.
3. Kompilasi aturan ke backend ACL/controller yang dipilih.
4. Siapkan topologi dan pemasangan aturan pada lingkungan emulasi.
5. Jalankan skenario akses yang diizinkan dan ditolak, lalu hasilkan laporan.
