# Topologi Containerlab

Direktori ini disiapkan untuk definisi topologi Containerlab dan konfigurasi
router. `vlans.yaml` hanya inventaris VLAN, bukan definisi topologi Containerlab
yang dapat dijalankan. Image router dan file `*.clab.yml` belum dibuat.

Rancangan awal menggunakan routing antar-VLAN, empat VLAN sesuai `vlans.yaml`,
minimal satu host per VLAN, dan layanan HTTPS/DNS/MQTT pada VLAN Servers.
Routing antar-VLAN harus berfungsi sebelum enforcement ACL diuji.

Siapkan Containerlab dan container runtime pada Linux. Dokumentasikan image dan
versi router, interface/link, konfigurasi VLAN dan routing, perintah startup serta
teardown saat topologi diimplementasikan. Verifier Scapy dijalankan dari host uji
pada VLAN sumber dengan hak akses pengiriman paket yang sesuai.
