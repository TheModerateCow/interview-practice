# Reads a query log and a target from stdin and prints fewest_keystrokes(log, target):
#   n          (number of logged searches)
#   <query>    (n lines)
#   <target>
import sys

from search_box import fewest_keystrokes

lines = sys.stdin.read().split("\n")
n = int(lines[0])
log = [line.strip() for line in lines[1:n + 1]]
print(fewest_keystrokes(log, lines[n + 1].strip()))
