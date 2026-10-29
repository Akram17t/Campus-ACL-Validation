# Rencana integration test

Tambahkan pengujian setelah topologi dan backend tersedia:

- Verifikasi routing serta kesiapan layanan sebelum memasang ACL.
- Terapkan contoh kebijakan dan periksa akses layanan yang diizinkan.
- Periksa akses yang ditolak, termasuk port/protokol lain pada tujuan yang sama.
- Bedakan blokir ACL dari kegagalan layanan, controller, atau routing.
- Bersihkan topologi dan aturan setelah pengujian, termasuk ketika pengujian gagal.

Pengujian memerlukan lingkungan emulasi Linux. Belum ada integration test yang
dapat dijalankan.
