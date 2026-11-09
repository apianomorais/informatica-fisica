#!/usr/bin/env python3
"""Converte o módulo de Python em LaTeX para o corpo HTML das aulas.

O arquivo de origem usa subsection por aula, subsubsection por seção, e os
ambientes conceito, intuicao, exemplo, exercicio, tcolorbox, lstlisting,
itemize, description, figure e tabular. A saída é um dicionário de corpos
HTML, um por aula, pronto para ser embutido no molde do site.

Uso:  python3 ferramentas/tex2html.py            (gera conteudo/aulas.json)
      python3 ferramentas/tex2html.py 3          (mostra a aula 3 na tela)
"""
import json
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
FONTE = RAIZ / 'fonte' / 'modulo1_python_basico.tex'
SAIDA = RAIZ / 'conteudo' / 'aulas.json'

# ---------------------------------------------------------------- utilidades

def protege(texto, guardados):
    """Tira os blocos de código do caminho antes de mexer no resto."""
    def guarda(m):
        guardados.append(m.group(0))
        return '\x00%d\x00' % (len(guardados) - 1)
    padrao = re.compile(
        r'\\begin\{lstlisting\}(?:\[[^\]]*\])?.*?\\end\{lstlisting\}'
        r'|\\begin\{(?:Verbatim|pythoncode)\}(?:\[[^\]]*\])?.*?'
        r'\\end\{(?:Verbatim|pythoncode)\}', re.S)
    return padrao.sub(guarda, texto), guardados


def escapa(s):
    return (s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))


def codigo_html(bruto, n):
    """Um bloco de código vira <pre> com cabeçalho e botão de copiar."""
    corpo = re.sub(r'^\\begin\{[a-zA-Z]+\}(?:\[[^\]]*\])?\s*\n', '', bruto)
    corpo = re.sub(r'\n?\\end\{[a-zA-Z]+\}\s*$', '', corpo)
    corpo = corpo.replace('\t', '    ')
    lingua = 'Python'
    if 'language=' in bruto.split('\n')[0]:
        m = re.search(r'language=([A-Za-z]+)', bruto.split('\n')[0])
        if m:
            lingua = m.group(1)
    return ('<div class="codigo" data-lingua="%s"><pre><code>%s</code></pre></div>'
            % (lingua, escapa(corpo)))


# ------------------------------------------------------------------ inline

INLINE = [
    (r'\\pyth\{((?:[^{}]|\{[^{}]*\})*)\}', lambda m: '<code>%s</code>' % escapa(limpa_simples(m.group(1)))),
    (r'\\texttt\{((?:[^{}]|\{[^{}]*\})*)\}', lambda m: '<code>%s</code>' % escapa(limpa_simples(m.group(1)))),
    (r'\\textbf\{((?:[^{}]|\{[^{}]*\})*)\}', lambda m: '<strong>%s</strong>' % m.group(1)),
    (r'\\bfseries\s*', lambda m: ''),
    (r'\\textit\{((?:[^{}]|\{[^{}]*\})*)\}', lambda m: '<em>%s</em>' % m.group(1)),
    (r'\\emph\{((?:[^{}]|\{[^{}]*\})*)\}', lambda m: '<em>%s</em>' % m.group(1)),
    (r'\\underline\{((?:[^{}]|\{[^{}]*\})*)\}', lambda m: '<u>%s</u>' % m.group(1)),
    (r'\\textcolor\{[^}]*\}\{((?:[^{}]|\{[^{}]*\})*)\}', lambda m: m.group(1)),
    (r'\\href\{([^}]*)\}\{((?:[^{}]|\{[^{}]*\})*)\}',
     lambda m: '<a href="%s">%s</a>' % (m.group(1), m.group(2))),
    (r'\\url\{([^}]*)\}', lambda m: '<a href="%s">%s</a>' % (m.group(1), m.group(1))),
    (r'\\large\s*', lambda m: ''),
    (r'\\normalsize\s*', lambda m: ''),
    (r'\\small\s*', lambda m: ''),
    (r'\\centering\s*', lambda m: ''),
    (r'\\newpage\s*', lambda m: ''),
    (r'\\clearpage\s*', lambda m: ''),
    (r'\\noindent\s*', lambda m: ''),
    (r'\\LaTeX\b', lambda m: 'LaTeX'),
    (r'\\TeX\b', lambda m: 'TeX'),
    (r'\\ldots\b', lambda m: '…'),
    (r'\\dots\b', lambda m: '…'),
]


def limpa_simples(s):
    """Para o que vai dentro de <code>: desfaz só os escapes."""
    for a, b in [(r'\_', '_'), (r'\&', '&'), (r'\%', '%'), (r'\$', '$'),
                 (r'\#', '#'), (r'\{', '{'), (r'\}', '}'), (r'\textbackslash', '\\')]:
        s = s.replace(a, b)
    return s


MATH = re.compile(r'\\\[.*?\\\]|(?<!\\)\$\$.+?\$\$|(?<!\\)\$.+?(?<!\\)\$', re.S)


def inline(s):
    # A matemática sai do caminho antes de tudo: dentro dela \pyth{} é um
    # trecho de código para o MathJax compor, e não uma tag <code>, e os
    # escapes de \_ e \& têm outro significado. Sem isto, uma fórmula com
    # \text{\pyth{dados[a:b]}} chega à página com HTML cru no meio.
    guardadas = []

    def guarda(m):
        guardadas.append(m.group(0))
        return '\x03%d\x03' % (len(guardadas) - 1)

    s = MATH.sub(guarda, s)

    for padrao, f in INLINE:
        anterior = None
        while anterior != s:
            anterior = s
            s = re.sub(padrao, f, s)
    # escapes que sobraram, fora da matemática
    for a, b in [(r'\_', '_'), (r'\&', '&amp;'), (r'\%', '%'), (r'\$', '$'),
                 (r'\#', '#'), (r'~', ' ')]:
        s = s.replace(a, b)

    def repoe(m):
        t = guardadas[int(m.group(1))]
        t = re.sub(r'\\pyth\{((?:[^{}]|\{[^{}]*\})*)\}',
                   lambda q: r'\texttt{%s}' % q.group(1), t)
        # dentro de \text{} o MathJax não expande macro nenhuma: o
        # \texttt apareceria cru na página
        t = re.sub(r'\\text\{\s*\\texttt\{((?:[^{}]|\{[^{}]*\})*)\}\s*\}',
                   lambda q: r'\texttt{%s}' % q.group(1), t)
        if t.startswith('$$'):
            return r'\[%s\]' % t[2:-2]
        if t.startswith('$'):
            return r'\(%s\)' % t[1:-1]
        return t

    s = re.sub('\x03(\\d+)\x03', repoe, s)
    s = s.replace('``', '“').replace("''", '”')
    s = re.sub(r'(?<![\\A-Za-z0-9])-{3}(?![-])', '—', s)
    s = re.sub(r'(?<![\\A-Za-z0-9])-{2}(?![-])', '–', s)
    return s


# ------------------------------------------------------------------ blocos

def listas(s):
    """itemize, enumerate e description, inclusive aninhados."""
    while True:
        m = re.search(r'\\begin\{(itemize|enumerate|description)\}'
                      r'((?:(?!\\begin\{(?:itemize|enumerate|description)\}).)*?)'
                      r'\\end\{(?:itemize|enumerate|description)\}', s, re.S)
        if not m:
            break
        tipo, corpo = m.group(1), m.group(2)
        itens = re.split(r'\\item\b', corpo)[1:]
        saida = []
        for it in itens:
            it = it.strip()
            rot = ''
            mr = re.match(r'\[(.*?)\]', it, re.S)
            if mr:
                rot = mr.group(1).strip()
                it = it[mr.end():].strip()
                if rot.endswith(':'):
                    rot = rot[:-1]
            if tipo == 'description' or rot:
                saida.append('<li><b>%s</b> %s</li>' % (rot, it) if rot else '<li>%s</li>' % it)
            else:
                saida.append('<li>%s</li>' % it)
        tag = 'ol' if tipo == 'enumerate' else 'ul'
        s = s[:m.start()] + '\x01<%s>%s</%s>\x01' % (tag, ''.join(saida), tag) + s[m.end():]
    return s


CAIXAS = {
    'conceito': ('def', 'Conceito chave'),
    'intuicao': ('fisica', 'Intuição'),
    'exemplo': ('ex', 'Exemplo'),
    'exercicio': ('ex', 'Exercício'),
}


def caixas(s, estado):
    """conceito, intuicao, exemplo, exercicio e tcolorbox genérico."""
    while True:
        m = re.search(r'\\begin\{(conceito|intuicao|exemplo|exercicio)\}(\[[^\]]*\])?'
                      r'((?:(?!\\begin\{(?:conceito|intuicao|exemplo|exercicio)\}).)*?)'
                      r'\\end\{(?:conceito|intuicao|exemplo|exercicio)\}', s, re.S)
        if not m:
            break
        nome, opt, corpo = m.group(1), m.group(2), m.group(3)
        classe, rotulo = CAIXAS[nome]
        titulo = (opt or '')[1:-1].strip()
        if nome in ('exemplo', 'exercicio'):
            estado[nome] += 1
            rotulo = '%s %d.%d' % (rotulo, estado['aula'], estado[nome])
            if titulo:
                rotulo += ': ' + titulo
        elif titulo:
            rotulo = titulo
        s = (s[:m.start()]
             + '\x01<div class="bloco %s"><span class="rotulo">%s</span>\n%s\n</div>\x01'
               % (classe, rotulo, corpo.strip())
             + s[m.end():])
    # tcolorbox genérico: usa o título quando houver
    while True:
        m = re.search(r'\\begin\{tcolorbox\}(\[.*?\])?'
                      r'((?:(?!\\begin\{tcolorbox\}).)*?)\\end\{tcolorbox\}', s, re.S)
        if not m:
            break
        opt, corpo = m.group(1) or '', m.group(2)
        mt = re.search(r'title=\{(.*?)\}\s*,?\s*(?:\n|$)', opt, re.S)
        if not mt:
            mt = re.search(r'title=([^,\]]+)', opt)
        titulo = mt.group(1).strip() if mt else 'Para guardar'
        titulo = re.sub(r'\\large\b|\\bfseries\b', '', titulo)
        titulo = inline(titulo)
        titulo = re.sub(r'^\{+|\}+$', '', titulo).strip()
        s = (s[:m.start()]
             + '\x01<div class="bloco def"><span class="rotulo">%s</span>\n%s\n</div>\x01'
               % (titulo, corpo.strip())
             + s[m.end():])
    return s


# Algumas figuras do material de origem vêm sem \caption; a legenda abaixo
# descreve o que elas mostram, para que a página não fique com um texto
# alternativo genérico.
LEGENDAS = {
    'a08_11.png': 'Três modos de desenhar a mesma superfície tridimensional: '
                  'superfície preenchida, contornos projetados e malha de arame.',
}


def figuras(s, aula):
    """As figuras do LaTeX viram imagens do site, com legenda."""
    def troca(m):
        corpo = m.group(1)
        mi = re.search(r'\\includegraphics(?:\[[^\]]*\])?\{([^}]*)\}', corpo)
        mc = re.search(r'\\caption\{((?:[^{}]|\{[^{}]*\})*)\}', corpo)
        if not mi:
            return ''
        arq = pathlib.PurePath(mi.group(1)).name
        if not arq.endswith(('.png', '.jpg', '.pdf')):
            arq += '.png'
        arq = arq.replace('.pdf', '.png')
        leg = mc.group(1).strip() if mc else LEGENDAS.get(arq, '')
        return ('\x01<figure><img src="assets/img/%s" alt="%s" loading="lazy">'
                '%s</figure>\x01'
                % (arq, leg or 'figura da aula %d' % aula,
                   '<figcaption>%s</figcaption>' % leg if leg else ''))
    return re.sub(r'\\begin\{figure\}(?:\[[^\]]*\])?(.*?)\\end\{figure\}', troca, s, flags=re.S)


def tabelas(s):
    def troca(m):
        corpo = m.group(2)
        corpo = re.sub(r'\\(toprule|midrule|bottomrule|hline)\b', '', corpo)
        # uma célula pode conter $\begin{cases} a & b \\ c & d \end{cases}$:
        # esses & e \\ são da matemática, não da tabela
        guardadas = []

        def guarda(mm):
            guardadas.append(mm.group(0))
            return '\x04%d\x04' % (len(guardadas) - 1)

        corpo = MATH.sub(guarda, corpo)
        linhas = [l.strip() for l in corpo.split(r'\\') if l.strip()]
        if not linhas:
            return ''
        out = ['<div class="tabela-rolavel"><table>']
        for i, l in enumerate(linhas):
            cels = [c.strip() for c in l.split('&')]
            tag = 'th' if i == 0 else 'td'
            out.append('<tr>' + ''.join('<%s>%s</%s>' % (tag, c, tag) for c in cels) + '</tr>')
            if i == 0:
                out.insert(1, '<thead>')
                out.append('</thead><tbody>')
        out.append('</tbody></table></div>')
        tabela = ''.join(out)
        tabela = re.sub('\x04(\\d+)\x04',
                        lambda mm: guardadas[int(mm.group(1))], tabela)
        return '\x01' + tabela + '\x01'
    return re.sub(r'\\begin\{tabular\}\{([^}]*)\}(.*?)\\end\{tabular\}', troca, s, flags=re.S)


def paragrafos(s):
    """Quebra em <p>, preservando os blocos já montados (marcados com \\x01)."""
    partes = s.split('\x01')
    saida = []
    for i, parte in enumerate(partes):
        if i % 2 == 1:
            saida.append(parte)
            continue
        for bloco in re.split(r'\n\s*\n', parte):
            bloco = bloco.strip()
            if not bloco:
                continue
            if re.match(r'^<(h[1-6]|div|ul|ol|pre|figure|table|p)\b', bloco):
                saida.append(bloco)
            else:
                saida.append('<p>%s</p>' % bloco)
    return '\n\n'.join(saida)


# -------------------------------------------------------------------- aulas

def converte(tex):
    aulas = []
    pedacos = re.split(r'\\subsection\{Aula\s*(\d+)\s*:\s*(.*?)\}', tex)
    for i in range(1, len(pedacos), 3):
        num, titulo, corpo = int(pedacos[i]), pedacos[i + 1], pedacos[i + 2]
        aulas.append(converte_aula(num, titulo.strip(), corpo))
    return aulas


def converte_aula(num, titulo, corpo):
    guardados = []
    corpo, guardados = protege(corpo, guardados)
    estado = {'aula': num, 'exemplo': 0, 'exercicio': 0}

    # as seções viram h2 numeradas
    secoes = []
    def marca(m):
        # o índice lateral é texto puro: o título passa pela mesma conversão
        # do h2 e depois perde as tags, senão um \texttt{curve\_fit} aparece
        # cru no menu da aula
        secoes.append(re.sub(r'<[^>]+>', '', inline(m.group(1).strip())).strip())
        return '\x01<h2 id="s%d">%d. %s</h2>\x01' % (len(secoes), len(secoes),
                                                     inline(m.group(1).strip()))
    corpo = re.sub(r'\\subsubsection\{((?:[^{}]|\{[^{}]*\})*)\}', marca, corpo)

    corpo = figuras(corpo, num)
    corpo = caixas(corpo, estado)
    corpo = tabelas(corpo)
    corpo = listas(corpo)
    corpo = re.sub(r'\\begin\{center\}(.*?)\\end\{center\}',
                   lambda m: '\x01<p class="centro">%s</p>\x01' % m.group(1).strip(),
                   corpo, flags=re.S)
    def destacada(m):
        corpo_eq = m.group(2).strip()
        if m.group(1).startswith('align'):
            # o & e o \\ precisam de um ambiente de alinhamento; sem ele o
            # MathJax recusa a expressão inteira
            corpo_eq = '\\begin{aligned}%s\\end{aligned}' % corpo_eq
        return '\x01<p>\\[%s\\]</p>\x01' % corpo_eq

    corpo = re.sub(r'\\begin\{(equation\*?|align\*?|gather\*?)\}(.*?)\\end\{\1\}',
                   destacada, corpo, flags=re.S)
    corpo = inline(corpo)
    corpo = paragrafos(corpo)

    # devolve os blocos de código
    def repoe(m):
        return codigo_html(guardados[int(m.group(1))], int(m.group(1)))
    corpo = re.sub(r'<p>\s*\x00(\d+)\x00\s*</p>', repoe, corpo)
    corpo = re.sub(r'\x00(\d+)\x00', repoe, corpo)

    # limpeza final
    # comandos de espaçamento levam o argumento junto; sem isto um
    # \vspace{0.3cm} deixa o "{0.3cm}" solto no meio do texto
    corpo = re.sub(r'\\(?:v|h)space\*?\{[^{}]*\}|\\(?:vskip|hskip)\s*[^\s]+|'
                   r'\\(?:smallskip|medskip|bigskip|noindent|centering|raggedright)\b',
                   '', corpo)
    # A lista branca vale dentro da matemática. Fora dela um \quad não é
    # espaçamento nenhum: aparece cru na página, como apareceu nas listas de
    # parâmetros do Matplotlib.
    def limpa_fora(trecho):
        trecho = trecho.replace(r'\^{}', '^').replace(r'\~{}', '~')
        trecho = re.sub(r'\\textbackslash\b\s*\{?\}?', '\\\\', trecho)
        trecho = re.sub(r'\\q?quad\s*', ' ', trecho)
        return re.sub(r'\\[a-zA-Z]+\s*', '', trecho)

    def limpa_dentro(trecho):
        return re.sub(r'\\[a-zA-Z]+\s*', lambda m: m.group(0)
                      if m.group(0).strip('\\ ') in MATEMATICA else '', trecho)

    pedacos = []
    fim = 0
    for m in MATH.finditer(corpo):
        pedacos.append(limpa_fora(corpo[fim:m.start()]))
        pedacos.append(limpa_dentro(m.group(0)))
        fim = m.end()
    pedacos.append(limpa_fora(corpo[fim:]))
    corpo = ''.join(pedacos)
    corpo = re.sub(r'\n{3,}', '\n\n', corpo)
    return {'numero': num, 'titulo': titulo, 'secoes': secoes, 'html': corpo.strip(),
            'exemplos': estado['exemplo'], 'exercicios': estado['exercicio']}


MATEMATICA = set('''frac sqrt vec times cdot approx to rightarrow Delta pi theta omega
nu alpha beta gamma lambda mu sigma rho phi sum int infty partial left right
begin end text quad qquad ln log sin cos tan exp pm mp le ge neq equiv cdots
ldots dot ddot hat bar tilde mathrm mathbf boldsymbol bmatrix cases align
displaystyle lim prod binom aligned texttt dfrac tfrac det dots leq geq
in notin mid propto tau Omega Theta Lambda Gamma Pi Sigma Phi Psi xi zeta eta
chi psi kappa iota delta epsilon varepsilon varphi langle rangle overline
underbrace overbrace nabla oint iint simeq sim ne gg ll perp parallel circ
subset cup cap forall exists therefore hbar ell Re Im arg max min'''.split())


def main():
    tex = FONTE.read_text(encoding='utf-8')
    aulas = converte(tex)
    SAIDA.parent.mkdir(exist_ok=True)
    SAIDA.write_text(json.dumps(aulas, ensure_ascii=False, indent=1), encoding='utf-8')
    if len(sys.argv) > 1:
        alvo = int(sys.argv[1])
        for a in aulas:
            if a['numero'] == alvo:
                print(a['html'])
        return
    for a in aulas:
        print('aula %2d  %-58s %2d seções  %2d exemplos  %2d exercícios'
              % (a['numero'], a['titulo'][:58], len(a['secoes']),
                 a['exemplos'], a['exercicios']))
    print('→', SAIDA)


if __name__ == '__main__':
    main()
