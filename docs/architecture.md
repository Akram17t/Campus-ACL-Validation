# Rancangan sistem

Dokumen ini mendefinisikan rancangan awal; belum ada enforcement jaringan.

## Alur data

```text
Inventaris VLAN + kebijakan YAML
              |
              v
     Pembacaan dan validasi
              |
              v
 Analisis konflik dan shadowing
              |
              v
         Kompilasi ACL
              |
              v
 Deployer -> router pada Containerlab
              |
              v
 Verifier Scapy -> hasil aktual vs ekspektasi -> results/
```

## Tanggung jawab modul

| Modul | Masukan | Keluaran yang direncanakan |
| --- | --- | --- |
| `src/compiler.py` | Inventaris VLAN dan kebijakan YAML | Aturan ACL terurut atau kesalahan validasi input |
| `src/checker.py` | Aturan kebijakan yang terurut | Temuan konflik, redundansi, dan shadowing beserta ID aturan |
| `src/deployer.py` | ACL yang sudah lolos pemeriksaan dan koneksi router | Status pemasangan aturan |
| `src/verifier.py` | Skenario layanan dan akses host uji | Ekspektasi, hasil aktual, dan pengukuran paket dengan Scapy |

Compiler membaca YAML menggunakan `yaml.safe_load` dan memvalidasi kebijakan
sebelum checker menganalisis aturan. Keduanya harus lolos sebelum deployment.
Integrasi pemasangan aturan ditambahkan setelah image router dan format ACL
ditentukan. Kompilasi dan pemasangan aturan merupakan dua langkah terpisah.

## Semantik contoh kebijakan

- `schema_version` bernilai `1` untuk rancangan format awal ini.
- VLAN dirujuk dengan ID numerik yang terdapat dalam `topology/vlans.yaml`.
- Layanan merupakan daftar pasangan protokol (`tcp`/`udp`) dan port tujuan.
- Aturan berlaku dari subnet VLAN sumber menuju subnet VLAN tujuan.
- `rules` dievaluasi dari atas ke bawah; aturan pertama yang cocok menentukan
  tindakan (`allow` atau `deny`). ID setiap aturan harus unik.
- Trafik antar-VLAN yang tidak cocok dengan aturan menggunakan `default_action`,
  yang pada contoh bernilai `deny`.
- Kebijakan ini belum mencakup trafik intra-VLAN, Internet, dan trafik kontrol
  seperti ARP atau DHCP. Penanganannya harus ditentukan sebelum integrasi.

Kebijakan menjelaskan akses layanan yang diinisiasi sumber. Penanganan paket
balasan belum dipilih. Implementasi backend harus mendefinisikan mekanisme
stateful atau aturan balik yang terbatas sebelum pengujian koneksi end-to-end.
Jangan menganggap aturan satu arah sudah cukup untuk koneksi TCP atau UDP.

## Pemeriksaan yang harus dibuat

Validasi input memeriksa keunikan ID/nama VLAN, ID VLAN 1–4094, subnet IPv4 yang
valid dan tidak tumpang tindih, gateway di dalam subnet, referensi VLAN/layanan,
port 1–65535, protokol, tindakan, serta keunikan ID aturan.

Analisis membandingkan cakupan match dan urutan aturan:

- **Konflik:** aturan memiliki cakupan yang beririsan dengan tindakan berbeda.
- **Shadowing penuh:** seluruh cakupan aturan telah dicakup aturan sebelumnya,
  sehingga aturan tersebut tidak pernah menentukan hasil.
- **Redundansi:** cakupan sudah memiliki tindakan yang sama dari aturan sebelumnya.

Temuan perlu menunjukkan ID aturan terkait dan contoh trafik yang terdampak.
Kriteria temuan yang menghentikan kompilasi ditentukan bersama implementasi
checker, sebelum pemasangan aturan diaktifkan.

## Pengujian jaringan

Skenario positif mencakup Staff→Servers HTTPS, Guest→Servers DNS (TCP/UDP), dan
IoT→Servers MQTT. Skenario negatif mencakup Guest→Servers HTTPS serta akses
antar-VLAN lainnya yang tidak diizinkan.

Jalankan pemeriksaan kesiapan layanan terlebih dahulu. Timeout saja tidak cukup
untuk menyimpulkan bahwa ACL berhasil memblokir: layanan mati dan routing rusak
juga dapat menyebabkan timeout. Laporan harus membedakan `pass`, `fail`, dan
kesalahan lingkungan uji, serta mencatat aturan dan probe yang relevan.

Skenario dan skrip eksperimen ditempatkan di `experiments/`. Simpan ACL hasil
kompilasi, hasil pengukuran, dan laporan lokal di `results/`. Jangan memasukkan
kredensial router atau data jaringan nyata ke contoh konfigurasi.
