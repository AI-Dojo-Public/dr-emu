from testbed_app.database import create_db, destroy_db

on_startup = [create_db]
on_shutdown = [destroy_db]
