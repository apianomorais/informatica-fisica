#!/usr/bin/env python3
"""Monta as páginas da unidade de Python a partir de conteudo/aulas.json.

O material de origem está em LaTeX e é convertido por tex2html.py. Este
programa só o embrulha no molde do site: cabeçalho, índice lateral montado a
partir dos h2, chapéu da unidade e navegação. As aulas das unidades I e II
são escritas à mão e não passam por aqui.

Uso:  python3 ferramentas/monta.py
"""
import json
import pathlib
import re

RAIZ = pathlib.Path(__file__).resolve().parent.parent
AULAS = json.loads((RAIZ / 'conteudo' / 'aulas.json').read_text(encoding='utf-8'))

# a numeração do material de origem começa em 1; no site, a unidade de
# Python começa na aula 9
DESLOCA = 8

TITULOS = {
    9: 'Introdução ao Python e ao Spyder',
    10: 'Tipos de dados e variáveis',
    11: 'Estruturas de dados: listas e tuplas',
    12: 'Estruturas de controle',
    13: 'Funções e modularização',
    14: 'Introdução ao NumPy',
    15: 'Introdução ao Matplotlib: gráficos básicos',
    16: 'Matplotlib avançado: personalização e visualizações especiais',
    17: 'Entrada e saída: teclado, arquivos e CSV',
    18: 'Análise de dados com Pandas',
    19: 'Métodos numéricos com SciPy',
    20: 'Matemática simbólica com SymPy',
}

SUB = {
    9: 'A linguagem, o ambiente de trabalho e os primeiros programas. Tudo o que '
       'vem depois nesta unidade se apoia no que acontece aqui: escrever, rodar, '
       'errar e ler a mensagem de erro.',
    10: 'Números, texto, lógico e as conversões entre eles. É curto e parece '
        'burocrático, mas quase todo erro de aluno iniciante nasce de um tipo que '
        'não era o que se pensava.',
    11: 'Como guardar muitos valores num nome só, percorrê-los e modificá-los. '
        'Listas e tuplas são a base de tudo o que vem a seguir, do NumPy ao Pandas.',
    12: 'Decidir e repetir, que é o que separa um programa de uma calculadora. '
        'Condicionais, laços e a arte de não escrever o mesmo trecho duas vezes.',
    13: 'Empacotar um trecho de código num nome, com entrada e saída bem '
        'definidas. É o passo que transforma um script numa ferramenta reutilizável.',
    14: 'O vetor que a física pedia: operações elemento a elemento, sem laços, '
        'com a velocidade de código compilado e a legibilidade de Python.',
    15: 'O gráfico é o resultado de um experimento tanto quanto o número. Esta '
        'aula monta os tipos básicos e ensina a lê-los com olho crítico.',
    16: 'Do gráfico que funciona ao gráfico publicável: estilos, cores, anotações, '
        'painéis múltiplos e exportação em resolução de revista.',
    17: 'Programas úteis conversam com o mundo: leem do teclado, leem e escrevem '
        'arquivos, e não quebram quando o dado vem errado.',
    18: 'A planilha programável. Tudo o que a unidade I fez à mão no Google '
        'Planilhas, agora feito em código e com dezenas de milhares de linhas.',
    19: 'Ajuste de curvas, integração, equações diferenciais, raízes e '
        'interpolação. É a caixa de ferramentas numérica do físico.',
    20: 'O computador fazendo álgebra em vez de aritmética: derivadas, integrais e '
        'equações resolvidas em símbolos, com a resposta saindo em LaTeX.',
}

CABECA = '''<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Aula {n}: {titulo} | Informática para Física</title>
<link rel="icon" type="image/png" href="assets/img/favicon.png">
<link rel="stylesheet" href="assets/css/estilo.css">
<script src="assets/js/codigo.js"></script>
<script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js"></script>
</head>
<body>

<header class="topo">
  <div class="topo-interno">
    <a class="marca" href="index.html">Informática para Física <span>· LFCA/URCA</span></a>
    <nav class="menu">
      <a href="index.html">Início</a>
    </nav>
  </div>
</header>

<div class="envoltorio">

<aside class="lateral">
  <h4>Nesta aula</h4>
  <ol>
{indice}
  </ol>
</aside>

<main class="conteudo">

  <p class="chapeu">Aula {n} · Programação em Python</p>
  <h1>{titulo}</h1>
  <p class="subtitulo">{sub}</p>

{corpo}

  <nav class="nav-aulas">
{navegacao}
  </nav>

</main>
</div>

<footer class="rodape">
  <img class="logo-rodape" src="assets/img/logo-lfca.png" alt="LFCA | URCA">
  <p><strong>Prof. Apiano Morais</strong> · <a href="mailto:apiano.morais@urca.br">apiano.morais@urca.br</a><br>
  Laboratório de Física Computacional Aplicada (LFCA) · Universidade Regional do Cariri</p>
</footer>

<script src="assets/js/comum.js"></script>
</body>
</html>
'''


def renumera(html):
    """As referências a 'Aula NN' do material de origem apontam para a
    numeração antiga; aqui passam a apontar para a do site."""
    def troca(m):
        return 'Aula %02d' % (int(m.group(1)) + DESLOCA)
    return re.sub(r'Aula\s+0?(\d{1,2})\b', troca, html)


def monta():
    feitas = []
    for a in AULAS:
        n = a['numero'] + DESLOCA
        titulo = TITULOS[n]
        corpo = renumera(a['html'])
        corpo = '\n'.join('  ' + l if l.strip() else l for l in corpo.split('\n'))
        indice = '\n'.join(
            '    <li><a href="#s%d">%d. %s</a></li>' % (i + 1, i + 1, s)
            for i, s in enumerate(a['secoes']))
        nav = []
        if n - 1 >= 1:
            nav.append('    <a href="aula%02d.html"><small>Aula anterior</small>'
                       '← %d. %s</a>' % (n - 1, n - 1, TITULOS.get(n - 1, '')))
        if n + 1 <= 20:
            nav.append('    <a href="aula%02d.html"><small>Próxima aula</small>'
                       '%d. %s →</a>' % (n + 1, n + 1, TITULOS.get(n + 1, '')))
        pagina = CABECA.format(n=n, titulo=titulo, sub=SUB[n], indice=indice,
                               corpo=corpo, navegacao='\n'.join(nav))
        (RAIZ / ('aula%02d.html' % n)).write_text(pagina, encoding='utf-8')
        feitas.append(n)
    print('páginas de Python montadas:', ', '.join('aula%02d' % n for n in feitas))


if __name__ == '__main__':
    monta()
