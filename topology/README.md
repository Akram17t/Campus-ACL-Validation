# Topologi Containerlab

Direktori ini disiapkan untuk definisi topologi Containerlab dan konfigurasi
router. `vlans.yaml` hanya inventaris VLAN, bukan definisi topologi Containerlab
yang dapat dijalankan. Image turunan, Dockerfile, dan file `*.clab.yml` belum dibuat.

## Backend router versi 1

Gunakan **router Linux Debian 13 + nftables**. Containerlab mendukung container
Linux melalui `kind: linux`; routing IP dan subinterface VLAN menggunakan Linux,
sedangkan ACL serta pelacakan koneksi menggunakan nftables/conntrack.
Lihat [Containerlab Linux](https://containerlab.dev/manual/kinds/linux/),
[nftables Debian](https://wiki.debian.org/nftables), dan
[manual Netfilter](https://www.netfilter.org/projects/nftables/manpage.html).

| Komponen | Pilihan |
| --- | --- |
| Image lokal hasil build tahap topologi | `campus-acl-router:1.0` |
| Base image resmi bertanggal | `debian:trixie-20261027-slim` |
| Paket pada image turunan | `nftables`, `iproute2`, `conntrack`, `iputils-ping` |
| Containerlab kind | `linux` |
| Akses deployer | Docker Engine lokal host lab, melalui `docker exec` |
| ACL | nftables, family `ip`, table `campus_acl`, hook `forward` |
| Trafik balasan | `conntrack_reply`, sesuai [arsitektur](../docs/architecture.md) |

Base image tersedia pada [daftar tag resmi Debian](https://hub.docker.com/_/debian/tags/).
`campus-acl-router:1.0` adalah nama image lokal yang harus dibangun oleh anggota
topologi, bukan image siap pull dari registry. Base image saja belum menyediakan
seluruh tool router. Catat digest base/final image dan versi paket saat build
supaya semua anggota menggunakan hasil yang sama; perubahan build memakai tag baru.

Host Linux perlu mendukung VLAN 802.1Q, forwarding IPv4, nftables, dan conntrack.
Image container menggunakan kernel host. Konfigurasi node mengaktifkan
`net.ipv4.ip_forward=1` dan menyediakan hak `NET_ADMIN` untuk konfigurasi jaringan;
lihat [opsi node Containerlab](https://containerlab.dev/manual/nodes/).
Router menggunakan subinterface VLAN dengan gateway sesuai `vlans.yaml`;
link/trunk dan penempatan host harus membawa tag VLAN yang sesuai.

Deployer membatasi perubahan ke namespace jaringan container router dan table
`campus_acl`. Gunakan pemeriksaan `nft -c -f`, transaksi file `nft -f`, pembacaan
balik, serta pemulihan table proyek sesuai kontrak arsitektur. Mekanisme transaksi
dijelaskan pada [atomic rule replacement](https://wiki.nftables.org/wiki-nftables/index.php/Atomic_rule_replacement).
Jangan mengubah firewall host Docker. Profil ini belum menggantikan pemeriksaan
kesiapan lab maupun pengujian akses end-to-end.

## Rencana topologi

Rancangan awal menggunakan routing antar-VLAN, empat VLAN sesuai `vlans.yaml`,
minimal satu host per VLAN, dan layanan HTTPS/DNS/MQTT pada VLAN Servers.
Routing antar-VLAN harus berfungsi sebelum enforcement ACL diuji.

Siapkan Containerlab dengan Docker pada Linux. Dokumentasikan interface/link,
konfigurasi VLAN/routing, perintah build, startup dan teardown saat topologi
diimplementasikan. Node router perlu proses utama yang tetap hidup selama lab
berjalan. Verifier Scapy dijalankan dari host uji pada VLAN sumber dengan hak akses
pengiriman paket yang sesuai. Bersihkan conntrack alur lab terkait atau buat ulang
node router sebelum pengukuran kebijakan baru.
