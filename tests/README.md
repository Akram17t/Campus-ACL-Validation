# Rencana pengujian compiler dan checker

Tambahkan unit test saat logika inti diimplementasikan:

- Compiler: YAML dibaca dengan aman; referensi, subnet, port, dan ID tidak valid ditolak.
- Compiler: urutan aturan terjaga, layanan multi-protokol diekspansi, default deny tersedia.
- Checker: konflik, shadowing penuh, redundansi, dan aturan yang tidak beririsan.

Gunakan fixture kebijakan kecil yang memperlihatkan satu perilaku per kasus.
Belum ada unit test compiler/checker yang dapat dijalankan. Pengujian jaringan
end-to-end direncanakan di `experiments/` setelah topologi dan deployer tersedia.

Pemeriksaan statis topologi dasar sudah tersedia di `test_topology.py`:

```bash
python -B -m unittest discover -s tests -p test_topology.py -v
```

Pengujian ini memeriksa konsistensi konfigurasi tanpa menjalankan Containerlab;
tidak menggantikan build image dan pengujian routing pada lab.
