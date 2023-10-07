import sqlite3


con = sqlite3.connect("tutorial.db")


cur = con.cursor()
res = cur.execute("select * from sensor_readings")
print(res.fetchall())
