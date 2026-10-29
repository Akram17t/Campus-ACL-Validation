# Topologi emulasi

Direktori ini disiapkan untuk skrip topologi Mininet dan konfigurasi Open vSwitch.
Belum tersedia skrip emulasi atau dependensi controller.

Rancangan awal menggunakan satu domain routing antar-VLAN, empat VLAN sesuai
`configs/vlans.json`, minimal satu host per VLAN, dan layanan HTTPS/DNS/MQTT pada
VLAN Servers. Routing antar-VLAN harus berfungsi sebelum enforcement ACL diuji.

Jalankan emulasi pada Linux atau VM Linux yang mendukung Mininet dan Open vSwitch.
Versi perangkat lunak, controller, perintah startup, teardown, serta pemasangan
ACL harus didokumentasikan saat backend dipilih.
