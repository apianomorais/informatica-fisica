# -*- coding: utf-8 -*-
"""Extrai texto + equações de cada slide de cada deck para arquivos .md."""
import glob, os, re, sys, zipfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from omml import texto_do_slide

LIXO = re.compile(r'^(\d{1,3}|\d{1,2}/\d{1,2}/\d{4}|'
                  r'Mec[âa]nica dos Meios Cont[íi]nuos.*|'
                  r'Mec[âa]nica Cl[áa]ssica I*.*|'
                  r'F[íi]sica para Ci[êe]ncias Biol[óo]gicas.*|'
                  r'Inform[áa]tica para F[íi]sica.*|'
                  r'Prof\.? ?Dr\.? ?Apiano.*)$', re.I)

def limpa_rodape(t):
    return '\n'.join(l for l in t.split('\n') if not LIXO.match(l.strip()))

os.makedirs('conteudo', exist_ok=True)
for f in sorted(glob.glob('fonte/slides/*.pptx')):
    z = zipfile.ZipFile(f)
    slides = sorted([n for n in z.namelist()
                     if re.match(r'ppt/slides/slide\d+\.xml$', n)],
                    key=lambda s: int(re.search(r'(\d+)', s.split('/')[-1]).group(1)))
    nome = re.sub(r'^[0-9a-f]{8}-', '', os.path.basename(f))[:-5]
    saida = ['# ' + nome.replace('_', ' ')]
    for i, s in enumerate(slides, 1):
        t = limpa_rodape(texto_do_slide(z.read(s).decode('utf-8')))
        saida.append('\n## slide %d\n\n%s' % (i, t))
    open('conteudo/%s.md' % nome, 'w', encoding='utf-8').write('\n'.join(saida))
    print('%-50s %3d slides' % (nome, len(slides)))
