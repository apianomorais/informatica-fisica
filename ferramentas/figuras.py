#!/usr/bin/env python3
"""Gera as figuras das aulas de Matplotlib rodando o código das próprias aulas.

O material de origem traz as figuras como arquivos externos que não estão no
repositório. Em vez de desenhá-las de novo à mão, este programa acha, para
cada \\includegraphics do .tex, o último bloco de código que vem antes dele,
roda esse bloco com o backend Agg e grava cada figura exibida no nome que a
aula espera. Assim a figura da página é, por construção, o que o aluno vê ao
rodar o exemplo.

Uso:  python3 ferramentas/figuras.py            (todas)
      python3 ferramentas/figuras.py a07         (só as da aula de origem 7)
"""
import os
import pathlib
import re
import sys
import tempfile
import warnings

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

RAIZ = pathlib.Path(__file__).resolve().parent.parent
FONTE = RAIZ / 'fonte' / 'modulo1_python_basico.tex'
DESTINO = RAIZ / 'assets' / 'img'

CODIGO = re.compile(r'\\begin\{lstlisting\}(?:\[[^\]]*\])?\n(.*?)\\end\{lstlisting\}', re.S)
FIGURA = re.compile(r'\\includegraphics(?:\[[^\]]*\])?\{Figuras/([^}]+)\}')


def eventos(tex):
    """Blocos de código e figuras do arquivo, na ordem em que aparecem."""
    marcas = [(m.start(), 'codigo', m.group(1)) for m in CODIGO.finditer(tex)]
    marcas += [(m.start(), 'figura', m.group(1)) for m in FIGURA.finditer(tex)]
    marcas.sort()
    return marcas


def grava(fig, nome):
    fig.savefig(DESTINO / nome, dpi=110, bbox_inches='tight')


def main():
    filtro = sys.argv[1] if len(sys.argv) > 1 else ''
    DESTINO.mkdir(parents=True, exist_ok=True)
    tex = FONTE.read_text(encoding='utf-8')

    # vários exemplos gravam arquivos (csv, png) ao rodar; o trabalho sai
    # numa pasta temporária para não sujar a raiz do repositório
    os.chdir(tempfile.mkdtemp(prefix='figuras-'))

    # Os blocos de uma aula não são independentes: o primeiro importa numpy e
    # define os dados que os seguintes usam. Por isso tudo roda num espaço de
    # nomes só, na ordem do arquivo, como o aluno faria no console.
    ambiente = {'__name__': '__figura__'}
    exec('import numpy as np\nimport matplotlib.pyplot as plt', ambiente)

    pendentes = []          # figuras exibidas e ainda sem nome
    feitas, faltam = [], []

    def mostra(*a, **k):
        fig = plt.gcf()
        if fig.get_axes():
            pendentes.append(fig)
        else:
            plt.close(fig)

    plt.show = mostra

    for _, tipo, dado in eventos(tex):
        if tipo == 'codigo':
            # uma figura que o bloco anterior exibiu e que nenhuma
            # \includegraphics reclamou não entra na fila do bloco seguinte:
            # senão uma figura a mais numa aula desloca todas as outras
            for fig in pendentes:
                plt.close(fig)
            pendentes.clear()
            if 'input(' in dado:
                continue    # o bloco pediria algo ao teclado
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore')
                    exec(compile(dado, '<aula>', 'exec'), ambiente)
            except Exception as e:
                print('  bloco falhou: %s: %s' % (type(e).__name__, str(e)[:70]))
            # uma figura montada e nunca exibida também conta
            for num in plt.get_fignums():
                fig = plt.figure(num)
                if fig.get_axes() and fig not in pendentes:
                    pendentes.append(fig)
            continue

        # tipo == 'figura'
        if filtro and not dado.startswith(filtro):
            pendentes.clear() if False else None
            continue
        if not pendentes:
            faltam.append(dado)
            continue
        fig = pendentes.pop(0)
        grava(fig, dado)
        plt.close(fig)
        feitas.append(dado)

    plt.close('all')
    print('%d figuras geradas' % len(feitas))
    if faltam:
        print('sem figura: ' + ', '.join(faltam))


if __name__ == '__main__':
    main()
