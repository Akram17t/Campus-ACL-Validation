# Campus ACL Validation

Proyek tugas besar Software Defined Networking (SDN) untuk mengotomatisasi
pembuatan dan validasi aturan akses jaringan kampus berbasis VLAN.

Sistem yang dituju menerima kebijakan akses, menerjemahkannya menjadi ACL,
mendeteksi aturan yang bertentangan atau tertutupi, lalu menguji apakah perilaku
jaringan sesuai dengan kebijakan tersebut.

## Status

Pembacaan dan validasi kebijakan YAML sudah tersedia di `src/compiler.py`,
beserta contoh konfigurasi dan topologi dasar. Rendering ACL router, checker
konflik/shadowing, deployer, dan verifier Scapy belum diimplementasikan.
Kebijakan belum dapat diterapkan ke jaringan.

## Struktur repositori

```text
.
├── README.md
├── requirements.txt
├── .gitignore
├── topology/               # Topologi Containerlab dan konfigurasi router
│   ├── README.md
│   ├── Dockerfile          # Image Linux dengan tool routing dan nftables
│   ├── campus.clab.yml     # Router, switch VLAN, dan empat host uji
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
deployment melalui Docker exec. Definisi image dan topologi dasar sudah tersedia;
ikuti panduan build, startup, uji routing, dan teardown di `topology/README.md`.

## Validasi input dan pengujian

Setelah memasang `requirements.txt`, jalankan seluruh unit test:

```powershell
python -B -m unittest discover -s tests -v
```

Pembacaan input dari Python:

```python
from src.compiler import ValidationError, load_inputs

try:
    policy, inventory = load_inputs("policies/campus.yaml", "topology/vlans.yaml")
except ValidationError as error:
    print(error)  # Memuat file/field, kode, dan alasan kesalahan.
```

`load_inputs` mengembalikan `(policy, inventory)` tanpa mengubah data atau urutan
aturan. Validator berhenti pada kesalahan pertama, termasuk file tidak terbaca,
YAML tidak valid, key duplikat, dan pelanggaran format versi 1. Fungsi ini belum
menghasilkan ACL atau memeriksa konflik/shadowing. Tes berjalan tanpa Docker dan
tidak membuktikan konektivitas jaringan. Belum tersedia CLI proyek.

## Contoh kebijakan

| VLAN sumber | VLAN tujuan | Layanan yang diizinkan |
| --- | --- | --- |
| Staff (10) | Servers (40) | HTTPS |
| Guest (20) | Servers (40) | DNS melalui UDP dan TCP |
| IoT (30) | Servers (40) | MQTT |

Akses antar-VLAN lainnya menggunakan kebijakan default `deny`.
Semantik aturan dan batas cakupan dijelaskan di [arsitektur](docs/architecture.md).

## Tahapan implementasi

1. Pembacaan dan validasi YAML sudah tersedia; berikutnya lengkapi compiler ACL.
2. Buat checker untuk mendeteksi konflik dan aturan yang tertutupi.
3. Siapkan topologi Containerlab dan deployer untuk router yang dipilih.
4. Buat verifier Scapy dan skenario eksperimen akses yang diizinkan/ditolak.
5. Simpan hasil pengukuran di `results/` dan dokumentasikan evaluasinya.
