# Spesifikasi kebijakan dan alur validasi ACL

Dokumen ini adalah acuan implementasi versi 1. Modul Python masih berupa kerangka;
format keluaran di bawah adalah kontrak yang direncanakan, bukan hasil uji jaringan.

## Status backend router

Backend versi 1 ditetapkan sebagai router Linux berbasis Debian 13 dengan
nftables, dijalankan pada Containerlab `kind: linux`. Profil lengkap, kebutuhan
build image, dan sumber resmi dicatat di [rencana topologi](../topology/README.md).

| Parameter | Nilai |
| --- | --- |
| Image router lokal yang akan dibangun | `campus-acl-router:1.0` |
| Base image | `debian:trixie-20261027-slim` |
| `access_method` | `docker_exec` pada host lab Linux |
| `return_traffic_mode` | `conntrack_reply` |
| ACL native | File nftables `results/acl.nft`, table IPv4 `campus_acl` |

Ini keputusan desain; image turunan, topologi, dan modul belum diimplementasikan
atau diuji. Validasi, checker, dan pengembangan compiler dapat dilanjutkan dengan
profil ini. Deployment berstatus `blocked` sampai image, topologi, akses target,
dan dukungan kernel untuk VLAN/nftables/conntrack lolos pemeriksaan kesiapan.
Jangan mengganti backend atau memperlonggar kebijakan otomatis jika prasyarat gagal.

## Alur data

```text
Inventaris VLAN + kebijakan YAML
              |
              v
 Compiler: baca, validasi, uraikan layanan
              |
              v
 Checker: analisis konflik dan shadowing
              |
              v
 Compiler: render ACL native jika pemeriksaan lolos dan backend siap
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
| `src/compiler.py` | Inventaris VLAN dan kebijakan YAML | Match terurai, lalu ACL native setelah checker lolos dan backend siap |
| `src/checker.py` | Aturan kebijakan yang terurut | Temuan konflik, redundansi, dan shadowing beserta ID aturan |
| `src/deployer.py` | ACL yang sudah lolos pemeriksaan dan koneksi router | Status pemasangan aturan |
| `src/verifier.py` | Skenario layanan dan akses host uji | Ekspektasi, hasil aktual, dan pengukuran paket dengan Scapy |

Compiler dan checker bekerja tanpa koneksi router. Compiler memvalidasi input
sebelum checker menganalisis match terurai. Keduanya harus lolos sebelum rendering
ACL native dan deployment. Kompilasi tidak sekaligus memasang aturan.

## Format input YAML versi 1

Kedua file berupa mapping dengan `schema_version: 1` (integer). Baca menggunakan
`yaml.safe_load`, lalu validasi struktur dan field. Loader juga harus menolak key
YAML duplikat; `safe_load` saja belum menjamin pemeriksaan tersebut. Tolak field
tidak dikenal, field wajib yang hilang, dan versi yang tidak didukung.

Semua field pada tabel wajib ada. String tidak boleh kosong atau memiliki spasi
awal/akhir; nama layanan dan ID aturan peka huruf besar/kecil. Integer tidak boleh
berupa boolean, string angka, atau pecahan. Tidak ada wildcard, rentang port,
substitusi variabel, maupun field prioritas pada versi ini.

### Inventaris: `topology/vlans.yaml`

| Field | Tipe dan ketentuan |
| --- | --- |
| `schema_version` | Integer `1` |
| `vlans` | List tidak kosong berisi inventaris VLAN |
| `vlans[].id` | Integer 1–4094, unik |
| `vlans[].name` | String nama VLAN, unik |
| `vlans[].subnet` | String CIDR IPv4 dengan alamat network yang benar; subnet antar-VLAN tidak tumpang tindih |
| `vlans[].gateway` | String alamat IPv4 host dalam subnet VLAN, bukan alamat network/broadcast |

Inventaris bukan file topologi Containerlab. Interface, alamat host uji, penempatan
layanan, dan image router ditentukan pada konfigurasi topologi.

### Kebijakan: `policies/campus.yaml`

| Field | Tipe dan ketentuan |
| --- | --- |
| `schema_version` | Integer `1` |
| `default_action` | String `deny`; versi ini tidak mendukung default allow |
| `services` | Mapping tidak kosong dari nama layanan ke list pasangan protokol/port |
| `services.<nama>[]` | Mapping dengan `protocol` dan `destination_port`; list tidak kosong dan pasangan tidak duplikat |
| `protocol` | String `tcp` atau `udp` |
| `destination_port` | Integer 1–65535 |
| `rules` | List aturan terurut; list kosong berarti seluruh akses dalam cakupan ditolak |
| `rules[].id` | String ID aturan yang unik |
| `rules[].source_vlan` | Integer ID VLAN yang ada di inventaris |
| `rules[].destination_vlan` | Integer ID VLAN yang ada di inventaris, berbeda dari sumber |
| `rules[].service` | String nama yang ada di `services` |
| `rules[].action` | String `allow` atau `deny` |

Input invalid ditolak sebelum checker berjalan. Error menyebut lokasi field,
kode, dan alasan. Referensi layanan yang tidak dipakai boleh ada; aturan atau
layanan tidak dihapus otomatis.

## Semantik contoh kebijakan

- VLAN dirujuk dengan ID numerik yang terdapat dalam `topology/vlans.yaml`.
- Layanan merupakan daftar pasangan protokol (`tcp`/`udp`) dan port tujuan.
- Match aturan adalah subnet sumber, subnet tujuan, protokol, dan port tujuan;
  port sumber tidak dibatasi. Nama layanan hanya singkatan pasangan protokol/port.
- `rules` dievaluasi dari atas ke bawah; aturan pertama yang cocok menentukan
  tindakan (`allow` atau `deny`). Aturan yang lebih spesifik di bawah tidak
  otomatis menang. Penguraian layanan mempertahankan urutan induk dan urutan
  pasangan layanan, serta menyimpan ID aturan induk.
- Trafik antar-VLAN yang tidak cocok dengan aturan menggunakan `default_action`,
  yaitu `deny`, termasuk saat `rules` kosong. Default deny adalah penutup implisit,
  bukan aturan pengguna yang ikut dianalisis checker sebagai konflik.

Contoh: jika Guest→Servers DNS `deny` mendahului `allow` untuk match yang sama,
hasil evaluasi adalah `deny`; checker tetap melaporkan konflik dan shadowing.
Allow DNS UDP tidak memberi izin ke DNS TCP atau HTTPS. Backend wajib
mempertahankan semantik first-match ini pada konfigurasi native router.

### Trafik balasan dan batas cakupan

Kebijakan menjelaskan akses layanan yang diinisiasi sumber. Penanganan paket
balasan mengikuti profil backend yang disepakati. Izin Staff ke Servers HTTPS
harus memungkinkan balasan koneksi tersebut kembali, tanpa sekaligus memberi
izin Servers menginisiasi koneksi baru ke Staff.

Mode `conntrack_reply` memakai connection tracking nftables. Dalam cakupan ACL,
buang paket dengan state `invalid`, kemudian izinkan TCP/UDP dengan
`ct state established` dan `ct direction reply`. Trafik arah asli tetap melewati
aturan pengguna sesuai first-match, diikuti default deny. Koneksi baru dari arah
sebaliknya juga dievaluasi sebagai inisiasi baru, bukan diberi allow penuh.

Jangan menambahkan allow umum untuk seluruh state `related`; kebutuhan kontrol
di luar TCP/UDP ditangani terpisah pada topologi. Conntrack menyimpan state TCP
dan tuple/alur UDP dengan timeout, bukan identitas pengguna atau sesi aplikasi.
Sebelum eksperimen kebijakan baru, bersihkan state alur lab terkait atau buat
ulang node router agar hasil tidak dipengaruhi sesi dari baseline/kebijakan lama.

Cakupan versi 1 adalah komunikasi layanan TCP/UDP IPv4 antar-subnet VLAN terdaftar.
Trafik intra-VLAN, IPv6, Internet, trafik ke router sendiri, serta kontrol jaringan
seperti ARP/DHCP berada di luar kebijakan ini. Topologi mendokumentasikan
penanganannya terpisah; default deny bukan instruksi memutus trafik kontrol atau
manajemen tanpa rancangan yang sesuai.

## Analisis checker dan syarat melanjutkan

Checker membandingkan cakupan match yang sudah diurai, bukan nama layanan saja.
Dua layanan bernama berbeda dapat berisi pasangan protokol/port yang sama.

| Temuan `kind` | Arti | `severity` |
| --- | --- | --- |
| `conflict` | Ada irisan match antara aturan dengan tindakan berbeda | `error` |
| `shadowing` | Seluruh match aturan sudah dicakup gabungan aturan sebelumnya sehingga tidak pernah menentukan hasil | `warning` |
| `redundancy` | Seluruh match sudah memiliki hasil efektif yang sama dari aturan sebelumnya, termasuk duplikat identik | `warning` |

Satu aturan boleh memiliki beberapa temuan. Cakupan sebagian tidak boleh disebut
shadowing penuh. Redundansi menggunakan tindakan efektif first-match dari aturan
sebelumnya. Checker tidak menyusun ulang atau memperbaiki kebijakan otomatis.

Status checker `blocked` jika ada error; selain itu `pass`. Warning tetap
ditampilkan tetapi tidak menghentikan kompilasi. Input invalid menghasilkan error
validator dan tidak diteruskan ke checker. Contoh kebijakan saat ini diharapkan
menghasilkan `pass` dengan `findings: []`.

## Kontrak keluaran modul

Laporan terstruktur menggunakan JSON UTF-8 dengan `schema_version: 1`. Path di
bawah adalah lokasi keluaran yang direncanakan dalam `results/`, bukan file yang
sudah tersedia. Field yang dijelaskan wajib ada; list tanpa isi menggunakan `[]`.
`null` berarti nilai belum tersedia, bukan string kosong.

### Compiler — `results/compiled-acl.json`

| Field | Isi |
| --- | --- |
| `status` | `ready`, `blocked` (backend/checker menghambat), atau `error` (input/render gagal) |
| `policy_file`, `inventory_file` | Path input yang digunakan |
| `backend` | Mapping string `image` (referensi beserta tag/digest), `access_method`, dan `return_traffic_mode` sesuai kesepakatan; `null` jika belum disepakati |
| `rules` | List match terurai dengan `rule_id`, `position` (urutan induk mulai 1), `source_vlan`, `destination_vlan`, `source_subnet`, `destination_subnet`, `protocol`, `destination_port`, `action` |
| `default_action` | `deny` |
| `acl_file` | Path file konfigurasi native router; hanya terisi pada status `ready` |
| `errors` | List objek `code`, `location`, dan `message`; memuat alasan status selain `ready` |

Nilai `backend` untuk profil yang dipilih:

```json
{
  "image": "campus-acl-router:1.0",
  "access_method": "docker_exec",
  "return_traffic_mode": "conntrack_reply"
}
```

Contoh kebijakan menghasilkan empat match: Staff HTTPS TCP/443, Guest DNS UDP/53,
Guest DNS TCP/53, dan IoT MQTT TCP/1883. Default deny dilaporkan terpisah dari list
tersebut dan dirender sebagai perilaku penutup ACL native.

Jika input invalid, `rules` kosong. Jika hanya backend belum tersedia, aturan
terurai boleh terisi untuk ditinjau, tetapi `status: blocked` dan `acl_file: null`.
File native tidak dibuat pada status selain `ready`; kegagalan tidak boleh
meninggalkan artefak lama yang terlihat sebagai hasil baru siap deployment.

Compiler merender `allow` menjadi `accept`, `deny` menjadi `drop`, dan default
deny menjadi drop penutup dengan counter. Setiap aturan memakai komentar ID
aturan induk dan counter untuk pelacakan. Table `ip campus_acl` hanya menangani
trafik TCP/UDP forward antara VLAN terdaftar yang berbeda; penanganan trafik di
luar cakupan dan interface manajemen tidak diubah. Jangan memakai default drop global
yang memutus seluruh trafik host/router.

### Checker — `results/checker.json`

Laporan memiliki `status` (`pass`/`blocked`) dan `findings` (list). Setiap temuan
berisi `kind`, `severity`, `rule_id` (aturan yang diperiksa), `earlier_rule_ids`,
`message`, serta `match_example` dengan `source_vlan`, `destination_vlan`,
`protocol`, dan `destination_port`. Contoh match memperlihatkan temuan dan tidak
mengarang alamat host. Gunakan ID aturan pengguna, bukan default deny.

Contoh bentuk laporan tanpa temuan:

```json
{
  "schema_version": 1,
  "status": "pass",
  "findings": []
}
```

### Deployer — `results/deployment.json`

| Field | Isi |
| --- | --- |
| `status` | `applied`, `blocked` (prasyarat belum siap), atau `error` (pemasangan/pemeriksaan gagal) |
| `target` | Identitas node router lab, tanpa kredensial |
| `acl_file` | Artefak native dari compiler |
| `verification` | `matched`, `mismatch`, atau `not_run` untuk pemeriksaan konfigurasi terpasang |
| `rollback_status` | `not_needed`, `restored`, atau `failed` |
| `errors` | List objek `code`, `location`, dan `message` |

`applied` hanya dilaporkan setelah konfigurasi yang dibaca kembali cocok dengan
ACL yang dimaksud. Ini belum membuktikan perilaku paket. Deployer menolak compiler
selain `ready`, checker selain `pass`, target belum ditetapkan, atau artefak/laporan
yang bukan untuk input yang sama. Mekanisme pengikatan input dan artefak ditetapkan
saat implementasi bersama. Kegagalan parsial berstatus `error`, termasuk hasil
pemulihan baseline, bukan deployment sukses.

Backend `docker_exec` menjalankan `nft -c -f` untuk memeriksa artefak, lalu
`nft -f` untuk transaksi pemasangan di dalam container router target. Pemeriksaan
balik memakai `nft -j list table ip campus_acl` dan membandingkan konfigurasi
secara semantik, tanpa menyamakan counter/handle dinamis. Ganti hanya table milik
proyek dan siapkan pemulihannya; jangan melakukan flush ruleset host Docker.
Perintah pada paragraf ini adalah kontrak implementasi, belum CLI proyek.

### Verifier — `results/verification.json`

Laporan memiliki `status` (`pass`/`fail`/`error`), `summary` berupa mapping integer
`pass`, `fail`, `error` yang menghitung status kasus, dan `cases` (list tidak
kosong). Setiap kasus memuat:

| Field | Isi |
| --- | --- |
| `case_id`, `source_vlan`, `destination_vlan` | Identitas skenario dan VLAN yang diuji |
| `source_ip`, `destination_ip`, `interface` | Host konkret dan interface pengiriman dari topologi |
| `protocol`, `destination_port` | Match yang diuji |
| `rule_id` | ID first-match yang diharapkan; `null` untuk default deny |
| `expected` | `allow` atau `deny` dari kebijakan, bukan tebakan probe |
| `actual` | `allow`, `deny`, atau `unknown` berdasarkan bukti |
| `status` | `pass`, `fail`, atau `error` |
| `baseline_ready` | Boolean hasil pemeriksaan routing dan layanan |
| `duration_ms` | Durasi kasus dalam milidetik, nonnegatif |
| `evidence` | List bukti seperti respons layanan, capture paket, atau counter drop ACL yang terkait kasus |
| `message` | Alasan penilaian atau kesalahan lingkungan |

Respons harus sesuai layanan/probe; ACK TCP saja tidak membuktikan respons HTTPS
atau MQTT. Tidak ada balasan saja berarti `actual: unknown` dan `error`, bukan
bukti `deny`. Klaim `deny` memerlukan kesiapan baseline dan bukti pemblokiran yang
terkait probe, misalnya kenaikan counter aturan drop pada lab yang terisolasi.
Metode korelasi bukti dijelaskan pada skenario eksperimen.

Kasus `pass` jika hasil teramati sesuai ekspektasi, `fail` jika ada bukti hasil
berlawanan, dan `error` jika kesiapan/bukti tidak cukup atau probe gagal dijalankan.
Status laporan `fail` jika ada kasus fail; jika tidak, `error` jika ada kasus error;
selain itu `pass`. List kasus kosong merupakan error dan tidak boleh lolos.

## Pengujian jaringan

| Sumber → tujuan | Probe | Ekspektasi | Dasar |
| --- | --- | --- | --- |
| Staff → Servers | TCP/443 | allow | `staff-https` |
| Guest → Servers | UDP/53 dan TCP/53, dua kasus | allow | `guest-dns` |
| IoT → Servers | TCP/1883 | allow | `iot-mqtt` |
| Guest → Servers | TCP/443 | deny | default deny |
| Servers → Staff | Inisiasi TCP/443 baru | deny | default deny |
| Staff → Servers | UDP/443 | deny | default deny |

Kasus positif juga memeriksa jalur balasan. Alamat host dan interface tidak
diturunkan dari gateway otomatis; gunakan penempatan layanan pada topologi.
Saat kebijakan berubah, hitung ulang ekspektasi dengan first-match, termasuk
aturan deny eksplisit, lalu sesuaikan skenario.

Jalankan pemeriksaan kesiapan layanan terlebih dahulu. Timeout saja tidak cukup
untuk menyimpulkan bahwa ACL berhasil memblokir: layanan mati dan routing rusak
juga dapat menyebabkan timeout. Gunakan kriteria bukti dan status verifier di atas.

Skenario dan skrip eksperimen ditempatkan di `experiments/`. Simpan ACL hasil
kompilasi, hasil pengukuran, dan laporan lokal di `results/`. Jangan memasukkan
kredensial router atau data jaringan nyata ke contoh konfigurasi.
