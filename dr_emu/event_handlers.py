from dr_emu.controllers.database import create_db

on_startup = [create_db]
on_shutdown = []
