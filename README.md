# Campus ACL Validation

Proyek tugas besar Software Defined Networking (SDN) untuk mengotomatisasi
pembuatan dan validasi aturan akses jaringan kampus berbasis VLAN.

Sistem yang dituju menerima kebijakan akses, menerjemahkannya menjadi ACL,
mendeteksi aturan yang bertentangan atau tertutupi, lalu menguji apakah perilaku
jaringan sesuai dengan kebijakan tersebut.

## Status

Repositori ini berisi struktur awal, contoh konfigurasi, dan rancangan alur kerja.
Compiler ACL, checker aturan, deployer router, dan verifier Scapy belum
diimplementasikan. Contoh kebijakan belum dapat diterapkan ke jaringan.

## Struktur repositori

```text
.
├── README.md
├── requirements.txt
├── .gitignore
├── topology/               # Topologi Containerlab dan konfigurasi router
│   ├── README.md
│   └── vlans.yaml          # Inventaris VLAN dan subnet kampus
├── policies/
│   └── campus.yaml         # Kebijakan akses dalam YAML
├── src/
│   ├── compiler.py         # Kebijakan -> aturan ACL
│   ├── checker.py          # Deteksi konflik dan shadowing
│   ├── deployer.py         # Terapkan aturan ke router
│   └── verifier.py         # Pengujian paket dengan Scapy
├── tests/                  # Pengujian compiler dan checker
├── experiments/            # Skenario dan skrip eksperimen
├── results/                # Hasil pengukuran lokal (diabaikan Git)
└── docs/                   # Diagram dan dokumentasi
```

CI di `.github/workflows/ci.yml` memeriksa sintaks Python dan contoh YAML.

## Persiapan pengembangan

Gunakan Python 3.11 atau lebih baru. Dari direktori repositori:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Dependensi awal adalah PyYAML untuk membaca kebijakan dan Scapy untuk pengujian
paket. Containerlab beserta container runtime disiapkan terpisah pada lingkungan
Linux; lihat [rencana topologi](topology/README.md). Backend yang dipilih adalah
router Linux Debian 13 + nftables dengan image lokal `campus-acl-router:1.0` dan
deployment melalui Docker exec. Image turunan dan topologi belum dibangun.

Pemeriksaan struktur awal:

```powershell
python -m compileall -q src
```

Perintah tersebut hanya memeriksa sintaks Python. CI juga membaca contoh YAML
dengan `yaml.safe_load`; pemeriksaan ini belum memvalidasi semantik kebijakan.
Belum tersedia CLI maupun pengujian otomatis fungsional.

## Contoh kebijakan

| VLAN sumber | VLAN tujuan | Layanan yang diizinkan |
| --- | --- | --- |
| Staff (10) | Servers (40) | HTTPS |
| Guest (20) | Servers (40) | DNS melalui UDP dan TCP |
| IoT (30) | Servers (40) | MQTT |

Akses antar-VLAN lainnya menggunakan kebijakan default `deny`.
Semantik aturan dan batas cakupan dijelaskan di [arsitektur](docs/architecture.md).

## Tahapan implementasi

1. Buat compiler untuk membaca YAML, memvalidasi input, dan menghasilkan ACL.
2. Buat checker untuk mendeteksi konflik dan aturan yang tertutupi.
3. Siapkan topologi Containerlab dan deployer untuk router yang dipilih.
4. Buat verifier Scapy dan skenario eksperimen akses yang diizinkan/ditolak.
5. Simpan hasil pengukuran di `results/` dan dokumentasikan evaluasinya.
