# Topologi Containerlab

Topologi dasar tersedia di `campus.clab.yml`. Terdapat satu router, satu switch
Linux VLAN-aware, dan empat host. `vlans.yaml` tetap menjadi inventaris VLAN;
`Dockerfile` menyediakan definisi image lokal yang digunakan semua node.

Tahap ini hanya menyiapkan jaringan dan routing, tanpa memasang ACL. Seluruh
akses antar-VLAN pada baseline diharapkan bisa lewat. Kebijakan pada `policies/`
belum diterapkan. Layanan HTTPS/DNS/MQTT dan verifier Scapy disiapkan pada tahap
berikutnya.

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
`campus-acl-router:1.0` dibangun dari `topology/Dockerfile`, bukan image siap pull
dari registry. Base image saja belum menyediakan seluruh tool router. Catat
digest base/final image dan versi paket saat build
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

## Node, alamat, dan interface

```text
router eth1 (trunk VLAN 10,20,30,40)
  |
switch eth1 -- br0 (vlan_filtering=1, tanpa native VLAN)
  |-- eth2 access VLAN 10 -- staff:eth1
  |-- eth3 access VLAN 20 -- guest:eth1
  |-- eth4 access VLAN 30 -- iot:eth1
  `-- eth5 access VLAN 40 -- servers:eth1
```

| Node | VLAN | IP host/interface | Gateway | Port switch |
| --- | --- | --- | --- | --- |
| `staff` | 10 | `eth1`: `10.10.10.10/24` | `10.10.10.1` | `eth2` access untagged |
| `guest` | 20 | `eth1`: `10.10.20.10/24` | `10.10.20.1` | `eth3` access untagged |
| `iot` | 30 | `eth1`: `10.10.30.10/24` | `10.10.30.1` | `eth4` access untagged |
| `servers` | 40 | `eth1`: `10.10.40.10/24` | `10.10.40.1` | `eth5` access untagged |

Router memiliki `eth1.10`, `eth1.20`, `eth1.30`, dan `eth1.40`, masing-masing
memakai alamat gateway `/24` pada tabel di atas. Semua subnet terhubung langsung
ke router, sehingga tidak memerlukan protokol routing dinamis atau NAT. Default
route setiap host menggunakan gateway VLAN melalui `eth1`.

Switch hanya melakukan bridging; forwarding IPv4 diaktifkan pada router saja.
Port trunk membawa empat VLAN bertag, sedangkan port access menambah/melepas tag
sesuai VLAN host. `br0` tidak memiliki IP dan tidak membawa default VLAN 1.
Sintaks VLAN mengacu pada [ip-link](https://man7.org/linux/man-pages/man8/ip-link.8.html)
dan [bridge](https://man7.org/linux/man-pages/man8/bridge.8.html).

`eth0` disediakan Containerlab/Docker untuk manajemen dan tidak dimasukkan ke
`br0`. Alamat manajemen dipilih Containerlab; gunakan `inspect` untuk melihatnya.
Uji kebijakan harus memakai alamat `10.10.x.x` dan interface data `eth1`, karena
trafik melalui jaringan manajemen tidak melewati router ACL.

## Build dan startup

Jalankan perintah berikut dari root repo pada **host Linux dengan Docker dan
Containerlab**. Docker harus aktif dan pengguna perlu akses Docker Engine;
gunakan `sudo docker` bila akun belum memiliki akses tersebut. Pada Windows,
gunakan lingkungan Linux/WSL yang sudah dikonfigurasi untuk Containerlab.

```bash
docker info
containerlab version
docker build -t campus-acl-router:1.0 -f topology/Dockerfile topology
sudo containerlab deploy -t topology/campus.clab.yml
sudo containerlab inspect -t topology/campus.clab.yml
```

`image-pull-policy: Never` memastikan Containerlab memakai hasil build lokal.
Proses utama `sleep infinity` menjaga container tetap hidup. Perintah `exec`
topologi menyiapkan link, VLAN, IP, dan route setelah link terbentuk, sesuai
[mekanisme exec Containerlab](https://containerlab.dev/manual/nodes/#exec).
Konfigurasi memakai `NET_ADMIN`/`NET_RAW` tanpa container privileged.

Nama container adalah `clab-campus-acl-<node>`, misalnya
`clab-campus-acl-router`. Setelah build, simpan identitas image dan versi paket
sebagai catatan eksperimen lokal:

```bash
mkdir -p results
docker image inspect debian:trixie-20261027-slim campus-acl-router:1.0 > results/images.json
docker run --rm campus-acl-router:1.0 dpkg-query -W conntrack iproute2 iputils-ping nftables > results/router-packages.txt
```

Digest hasil build belum tersedia sampai image benar-benar dibangun. Image
bertanggal membatasi base yang dipakai; versi paket apt dan image ID tetap perlu
dicatat karena repo paket dapat diperbarui.

## Pemeriksaan routing baseline

Periksa konfigurasi router/switch dan pastikan belum ada ruleset ACL:

```bash
docker exec clab-campus-acl-router ip -br address
docker exec clab-campus-acl-router ip route
docker exec clab-campus-acl-switch bridge vlan show
docker exec clab-campus-acl-router nft list ruleset
```

Router harus menampilkan empat subnet connected, switch harus menampilkan trunk
dan access VLAN sesuai tabel, dan ruleset nftables harus kosong pada lab baru.
Jika startup gagal, perbaiki error `exec` terlebih dahulu; container berstatus
running saja tidak membuktikan konfigurasi VLAN berhasil.

Blok Bash berikut menguji empat gateway dan 12 pasangan host antar-VLAN. Return
code akhir harus nol dan semua ping harus berhasil pada baseline tanpa ACL.
Gunakan pada lab baru, sebelum pemasangan aturan:

```bash
failed=0
while read -r host address gateway; do
  docker exec "clab-campus-acl-$host" ping -I eth1 -c 2 -W 2 "$gateway" || failed=1
  for target in 10.10.10.10 10.10.20.10 10.10.30.10 10.10.40.10; do
    if [ "$target" != "$address" ]; then
      docker exec "clab-campus-acl-$host" ping -I eth1 -c 2 -W 2 "$target" || failed=1
    fi
  done
done <<'HOSTS'
staff 10.10.10.10 10.10.10.1
guest 10.10.20.10 10.10.20.1
iot 10.10.30.10 10.10.30.1
servers 10.10.40.10 10.10.40.1
HOSTS
test "$failed" -eq 0
```

Ping memeriksa routing ICMP, bukan kebenaran kebijakan TCP/UDP. Kesiapan layanan
dan enforcement ACL memerlukan pengujian terpisah pada tahap berikutnya.

## Teardown

```bash
sudo containerlab destroy -t topology/campus.clab.yml --cleanup
```

Teardown menghapus node dan direktori runtime lab, termasuk state conntrack
router; image hasil build dan catatan `results/` tetap ada. Untuk mulai ulang,
jalankan kembali `deploy` setelah `destroy`. Jangan hanya me-restart container:
link data dan konfigurasi runtime perlu dibuat ulang oleh Containerlab.

## Validasi yang sudah dilakukan

- Tiga pengujian statis memeriksa konsistensi VLAN, link access/trunk, gateway,
  IP host, default route, forwarding, dan ketiadaan pemasangan ACL saat startup.
- YAML lolos [schema resmi Containerlab v0.82.0](https://github.com/srl-labs/containerlab/blob/v0.82.0/schemas/clab.schema.json).
- Build image, startup, dan ping belum dijalankan: pada lingkungan pengembangan
  Windows ini Docker daemon tidak aktif dan Containerlab belum tersedia di Ubuntu
  WSL. Belum ada klaim keberhasilan konektivitas runtime.

Jalankan pemeriksaan statis dari root repo setelah menginstal `requirements.txt`:

```bash
python -B -m unittest discover -s tests -p test_topology.py -v
```
