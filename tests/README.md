# Pengujian

Jalankan dari root repo setelah menginstal `requirements.txt`:

```bash
python -B -m unittest discover -s tests -v
```

- `test_compiler.py`: input contoh, urutan aturan, YAML aman, key/ID duplikat,
  format dokumen, versi, VLAN/subnet/gateway, layanan/protokol/port, serta
  referensi dan tindakan aturan. Setiap kasus tidak valid memeriksa kode/lokasi error.
- `test_topology.py`: konsistensi link, VLAN access/trunk, IP/gateway, routing,
  dan ketiadaan pemasangan ACL saat startup.

Belum ada pengujian rendering ACL atau checker karena implementasinya belum
tersedia. Tes ini tidak menjalankan Containerlab atau membuktikan enforcement
jaringan; pengujian end-to-end dilanjutkan melalui `experiments/`.
