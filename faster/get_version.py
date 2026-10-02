import re
print(re.search(r'__version__\s*=\s*"([^"]+)"', open("faster.py", encoding="utf-8").read()).group(1))
