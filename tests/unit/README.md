# Rencana unit test

Tambahkan pengujian saat logika inti diimplementasikan:

- Parser: konfigurasi valid diterima; referensi, subnet, port, dan ID tidak valid ditolak.
- Analyzer: konflik, shadowing penuh, redundansi, dan aturan yang tidak beririsan.
- Compiler: urutan aturan terjaga, layanan multi-protokol diekspansi, default deny tersedia.

Gunakan fixture kebijakan kecil yang memperlihatkan satu perilaku per kasus.
Belum ada unit test yang dapat dijalankan.
