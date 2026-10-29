# Rancangan sistem

Dokumen ini mendefinisikan rancangan awal; belum ada enforcement jaringan.

## Alur data

```text
Inventaris VLAN + kebijakan JSON
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
 Pemasangan aturan melalui backend SDN
              |
              v
 Probe akses -> hasil aktual vs ekspektasi -> laporan
```

## Tanggung jawab modul

| Modul | Masukan | Keluaran yang direncanakan |
| --- | --- | --- |
| `policy.py` | Inventaris VLAN dan kebijakan JSON | Kebijakan tervalidasi atau kesalahan input |
| `analyzer.py` | Aturan kebijakan yang terurut | Temuan konflik, redundansi, dan shadowing beserta ID aturan |
| `compiler.py` | Kebijakan yang sudah lolos pemeriksaan | ACL untuk backend yang dipilih |
| `probes.py` | Skenario layanan dan akses host uji | Ekspektasi, hasil aktual, dan status pengujian |

Integrasi pemasangan aturan ditambahkan setelah controller dan format ACL
ditentukan. Kompilasi dan pemasangan aturan merupakan dua langkah terpisah.

## Semantik contoh kebijakan

- `schema_version` bernilai `1` untuk rancangan format awal ini.
- VLAN dirujuk dengan ID numerik yang terdapat dalam `configs/vlans.json`.
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
analyzer, sebelum pemasangan aturan diaktifkan.

## Pengujian jaringan

Skenario positif mencakup Staff→Servers HTTPS, Guest→Servers DNS (TCP/UDP), dan
IoT→Servers MQTT. Skenario negatif mencakup Guest→Servers HTTPS serta akses
antar-VLAN lainnya yang tidak diizinkan.

Jalankan pemeriksaan kesiapan layanan terlebih dahulu. Timeout saja tidak cukup
untuk menyimpulkan bahwa ACL berhasil memblokir: layanan mati dan routing rusak
juga dapat menyebabkan timeout. Laporan harus membedakan `pass`, `fail`, dan
kesalahan lingkungan uji, serta mencatat aturan dan probe yang relevan.

Simpan ACL hasil kompilasi dan laporan di `outputs/`. Jangan memasukkan kredensial
controller atau data jaringan nyata ke contoh konfigurasi.
