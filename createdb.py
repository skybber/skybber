#!/usr/bin/python

import sqlite3

conn = sqlite3.connect('skybber.db')
c = conn.cursor()

# Create table users
c.execute('CREATE TABLE users  (user_id INTEGER PRIMARY KEY AUTOINCREMENT, jid TEXT, descr TEXT)')

# Create table location
c.execute('CREATE TABLE locations (location_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, name TEXT, lat real, long real)')

# idx_user_jid
c.execute('CREATE UNIQUE INDEX idx_user_jid ON users (jid)')

c.execute('CREATE UNIQUE INDEX idx_location_user_id_name ON locations (user_id, name)')

conn.commit()
conn.close()
