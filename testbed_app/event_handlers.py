from testbed_app.controllers.database import create_db

on_startup = [create_db]
on_shutdown = []
