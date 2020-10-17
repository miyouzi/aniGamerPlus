import os
import sqlite3

FILE_CURRENT = "sn_list.txt"
FILE_TEMP = "sn_list-temp.txt"
FILE_DB = "aniGamer.db"

# Backup sn_list
if os.path.isfile(FILE_TEMP):
    print("Restore sn_list")
    os.remove(FILE_CURRENT)
    os.rename(FILE_TEMP, FILE_CURRENT)
    exit()
elif os.path.isfile(FILE_CURRENT):
    print("Backup sn_list")
    os.rename(FILE_CURRENT, FILE_TEMP)

print("Fetch history list")
conn = sqlite3.connect(FILE_DB)
c = conn.cursor()
history_list = c.execute("SELECT sn, anime_name FROM anime GROUP BY anime_name;")
with open(FILE_CURRENT, "w", encoding='UTF-8') as file:
    for row in history_list:
        file.write(str(row[0])+" all # "+row[1]+"\n")