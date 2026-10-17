"""Extrait le texte principal d'un HTML (non fiable) : python -I html_txt.py fichier.html > sortie.txt"""
import sys, re, html
s = open(sys.argv[1], encoding='utf-8', errors='replace').read()
s = re.sub(r'(?is)<(script|style|noscript)[^>]*>.*?</\1>', ' ', s)
s = re.sub(r'(?i)<br\s*/?>|</p>|</div>|</h\d>|</li>|</tr>', '\n', s)
s = re.sub(r'(?s)<[^>]+>', ' ', s)
s = html.unescape(s)
s = re.sub(r'[ \t]+', ' ', s)
s = re.sub(r'\n\s*\n+', '\n', s)
sys.stdout.write(s)
