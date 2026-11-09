# -*- coding: utf-8 -*-
"""Converte OMML (a matemática do PowerPoint) em LaTeX.

O PowerPoint guarda equações em Office Math Markup, não em imagens. Cada
equação vive num <m:oMath> dentro do XML do slide, intercalada com o texto
corrido. Este módulo percorre essa árvore e devolve LaTeX, de modo que o
conteúdo matemático dos slides possa ser lido e reaproveitado como texto.
"""
import re
import unicodedata
from xml.etree import ElementTree as ET

M = '{http://schemas.openxmlformats.org/officeDocument/2006/math}'
A = '{http://schemas.openxmlformats.org/drawingml/2006/main}'

GREGO = {
    'α': r'\alpha', 'β': r'\beta', 'γ': r'\gamma', 'δ': r'\delta',
    'ε': r'\varepsilon', 'ϵ': r'\epsilon', 'ζ': r'\zeta', 'η': r'\eta',
    'θ': r'\theta', 'ϑ': r'\vartheta', 'ι': r'\iota', 'κ': r'\kappa',
    'λ': r'\lambda', 'μ': r'\mu', 'µ': r'\mu', 'ν': r'\nu', 'ξ': r'\xi',
    'π': r'\pi', 'ρ': r'\rho', 'σ': r'\sigma', 'ς': r'\sigma',
    'τ': r'\tau', 'υ': r'\upsilon', 'φ': r'\varphi', 'ϕ': r'\phi',
    'χ': r'\chi', 'ψ': r'\psi', 'ω': r'\omega',
    'Γ': r'\Gamma', 'Δ': r'\Delta', 'Θ': r'\Theta', 'Λ': r'\Lambda',
    'Ξ': r'\Xi', 'Π': r'\Pi', 'Σ': r'\Sigma', 'Υ': r'\Upsilon',
    'Φ': r'\Phi', 'Ψ': r'\Psi', 'Ω': r'\Omega',
    '∂': r'\partial', '𝜕': r'\partial', '∇': r'\nabla',
    '𝛁': r'\nabla', '∞': r'\infty',
    '≈': r'\approx', '≠': r'\neq', '≤': r'\leq', '≥': r'\geq',
    '≡': r'\equiv', '∼': r'\sim', '≪': r'\ll', '≫': r'\gg',
    '×': r'\times', '⋅': r'\cdot', '·': r'\cdot', '±': r'\pm', '∓': r'\mp',
    '→': r'\to', '⟨': r'\langle', '⟩': r'\rangle', '∈': r'\in',
    '∑': r'\sum', '∏': r'\prod', '∫': r'\int', '∮': r'\oint',
    '√': r'\sqrt', 'ℏ': r'\hbar', 'ℎ': 'h', '′': "'", '″': "''",
    '−': '-', '℘': r'\wp', '∙': r'\cdot', '∆': r'\Delta',
    '…': r'\dots', '⋯': r'\cdots', '∝': r'\propto', '∀': r'\forall',
    '⇒': r'\Rightarrow', '⟹': r'\Longrightarrow', '⇔': r'\Leftrightarrow',
}

# acentos: m:accPr/m:chr -> comando LaTeX
ACENTO = {'̅': r'\overline', '¯': r'\overline', '¯': r'\overline',
          '⃗': r'\vec', '→': r'\vec', '̂': r'\hat', '^': r'\hat',
          '̃': r'\tilde', '~': r'\tilde', '̇': r'\dot',
          '.': r'\dot', '̈': r'\ddot'}

NARY = {'∑': r'\sum', '∏': r'\prod', '∫': r'\int', '∬': r'\iint',
        '∭': r'\iiint', '∮': r'\oint', '⋃': r'\bigcup', '⋂': r'\bigcap'}

FUNCOES = ('sen', 'sin', 'cos', 'tan', 'tg', 'cot', 'cotg', 'sec', 'csc',
           'ln', 'log', 'exp', 'lim', 'max', 'min', 'senh', 'sinh', 'cosh',
           'tanh', 'coth', 'arcsen', 'arcsin', 'arccos', 'arctan', 'arctg')


def _ascii_matematico(c):
    """𝑁 -> N, 𝑥 -> x: desfaz os alfabetos matemáticos do plano 1."""
    if ord(c) < 0x1D400:
        return None
    try:
        nome = unicodedata.name(c)
    except ValueError:
        return None
    if not nome.startswith('MATHEMATICAL'):
        return None
    partes = nome.split()
    letra = partes[-1]
    if len(letra) == 1:
        return letra if 'CAPITAL' in nome else letra.lower()
    if letra == 'DOTLESS' or partes[-2] == 'DOTLESS':
        return 'i'
    g = {'ALPHA': 'α', 'BETA': 'β', 'GAMMA': 'γ', 'DELTA': 'δ',
         'EPSILON': 'ε', 'ZETA': 'ζ', 'ETA': 'η', 'THETA': 'θ',
         'IOTA': 'ι', 'KAPPA': 'κ', 'LAMDA': 'λ', 'LAMBDA': 'λ', 'MU': 'μ',
         'NU': 'ν', 'XI': 'ξ', 'PI': 'π', 'RHO': 'ρ', 'SIGMA': 'σ',
         'TAU': 'τ', 'UPSILON': 'υ', 'PHI': 'φ', 'CHI': 'χ', 'PSI': 'ψ',
         'OMEGA': 'ω', 'NABLA': '∂'}.get(letra)
    if g:
        return g.upper() if 'CAPITAL' in nome and g != '∂' else g
    return None


def normaliza(txt):
    saida = []
    for c in txt:
        a = _ascii_matematico(c)
        if a is not None:
            c = a
        if c in GREGO:
            saida.append(GREGO[c] + ' ')
        else:
            saida.append(c)
    return ''.join(saida)


def _chr_de(no, tag, padrao=''):
    """Lê o atributo m:val de um m:chr dentro das propriedades do nó."""
    for pr in no:
        if pr.tag.endswith('Pr'):
            for f in pr:
                if f.tag == M + tag:
                    return f.get(M + 'val', padrao)
    return padrao


def _filhos(no, nome):
    return [f for f in no if f.tag == M + nome]


def _um(no, nome):
    f = _filhos(no, nome)
    return f[0] if f else None


def _chaves(s):
    """Envolve em chaves só quando precisa, para o LaTeX não ficar ilegível."""
    s = s.strip()
    if len(s) == 1 or re.fullmatch(r'\\[a-zA-Z]+', s):
        return s
    return '{%s}' % s


def conv(no):
    """Converte recursivamente um nó OMML em LaTeX."""
    t = no.tag
    if t == M + 'r':                                    # run de texto
        return ''.join(normaliza(x.text or '') for x in no if x.tag == M + 't')
    if t == A + 't':
        return normaliza(no.text or '')
    if t == M + 'f':                                    # fração
        n, d = _um(no, 'num'), _um(no, 'den')
        return r'\frac{%s}{%s}' % (filhos(n), filhos(d))
    if t == M + 'sSub':
        return '%s_%s' % (_chaves(filhos(_um(no, 'e'))),
                          _chaves(filhos(_um(no, 'sub'))))
    if t == M + 'sSup':
        return '%s^%s' % (_chaves(filhos(_um(no, 'e'))),
                          _chaves(filhos(_um(no, 'sup'))))
    if t == M + 'sSubSup':
        return '%s_%s^%s' % (_chaves(filhos(_um(no, 'e'))),
                             _chaves(filhos(_um(no, 'sub'))),
                             _chaves(filhos(_um(no, 'sup'))))
    if t == M + 'sPre':                                 # índices à esquerda
        return '{}_%s^%s%s' % (_chaves(filhos(_um(no, 'sub'))),
                               _chaves(filhos(_um(no, 'sup'))),
                               _chaves(filhos(_um(no, 'e'))))
    if t == M + 'rad':                                  # raiz
        deg = _um(no, 'deg')
        d = filhos(deg) if deg is not None else ''
        corpo = filhos(_um(no, 'e'))
        return r'\sqrt[%s]{%s}' % (d, corpo) if d.strip() else r'\sqrt{%s}' % corpo
    if t == M + 'nary':                                 # somatório, integral
        op = NARY.get(_chr_de(no, 'chr', '∑'), r'\sum')
        sub, sup = _um(no, 'sub'), _um(no, 'sup')
        s = op
        if sub is not None and filhos(sub).strip():
            s += '_%s' % _chaves(filhos(sub))
        if sup is not None and filhos(sup).strip():
            s += '^%s' % _chaves(filhos(sup))
        return s + ' ' + filhos(_um(no, 'e'))
    if t == M + 'd':                                    # delimitadores
        ini = _chr_de(no, 'begChr', '(')
        fim = _chr_de(no, 'endChr', ')')
        dentro = ' , '.join(filhos(e) for e in _filhos(no, 'e'))
        par = {'(': (r'\left(', r'\right)'), '[': (r'\left[', r'\right]'),
               '{': (r'\left\{', r'\right\}'), '|': (r'\left|', r'\right|'),
               '⟨': (r'\left\langle', r'\right\rangle'),
               '‖': (r'\left\|', r'\right\|'), '': ('', '')}
        if ini == '⟨' or fim == '⟩':
            return r'\left\langle %s \right\rangle' % dentro
        a, b = par.get(ini, (r'\left' + ini if ini else '', ''))
        if ini in par:
            a, b = par[ini]
        else:
            a, b = r'\left(', r'\right)'
        return '%s %s %s' % (a, dentro, b)
    if t == M + 'func':                                 # sen, cos, lim...
        nome = filhos(_um(no, 'fName')).strip()
        base = nome.lstrip('\\').split('_')[0].split('^')[0]
        if base in FUNCOES:
            nome = '\\operatorname{%s}%s' % (base, nome[len(base):])
        return '%s %s' % (nome, filhos(_um(no, 'e')))
    if t == M + 'acc':                                  # barra, vetor, chapéu
        cmd = ACENTO.get(_chr_de(no, 'chr', '̅'), r'\overline')
        return '%s{%s}' % (cmd, filhos(_um(no, 'e')))
    if t == M + 'bar':
        pos = _chr_de(no, 'pos', 'top')
        cmd = r'\underline' if pos == 'bot' else r'\overline'
        return '%s{%s}' % (cmd, filhos(_um(no, 'e')))
    if t == M + 'groupChr':
        return r'\underbrace{%s}' % filhos(_um(no, 'e'))
    if t == M + 'limLow':
        return '%s_{%s}' % (_chaves(filhos(_um(no, 'e'))),
                            filhos(_um(no, 'lim')))
    if t == M + 'limUpp':
        return '%s^{%s}' % (_chaves(filhos(_um(no, 'e'))),
                            filhos(_um(no, 'lim')))
    if t == M + 'm':                                    # matriz
        linhas = [' & '.join(filhos(e) for e in _filhos(mr, 'e'))
                  for mr in _filhos(no, 'mr')]
        return r'\begin{matrix} %s \end{matrix}' % r' \\ '.join(linhas)
    if t == M + 'eqArr':
        return r' \\ '.join(filhos(e) for e in _filhos(no, 'e'))
    if t.endswith('Pr'):                                # propriedades: ignora
        return ''
    return filhos(no)


def filhos(no):
    return '' if no is None else ''.join(conv(f) for f in no)


def limpa(s):
    s = re.sub(r'[ \t]+', ' ', s)
    s = re.sub(r' ?\\ ', r'\\', s)
    return s.strip()


def de_oMath(no):
    """LaTeX de um único <m:oMath>."""
    return limpa(filhos(no))


MC = '{http://schemas.openxmlformats.org/markup-compatibility/2006}'


def texto_do_slide(xml):
    """Texto corrido de um slide, com as equações em \\(...\\) e \\[...\\].

    As equações centralizadas vêm embrulhadas em mc:AlternateContent, que
    oferece duas versões do mesmo conteúdo: mc:Choice com o OMML de verdade
    e mc:Fallback com uma imagem. Descer pelos dois ramos duplicaria tudo,
    então o percurso ignora o Fallback. Fora disso, é uma travessia em ordem
    de documento: o texto sai na sequência em que foi escrito no slide.
    """
    raiz = ET.fromstring(xml)
    partes = []

    def anda(no, em_para):
        if no.tag == MC + 'Fallback':
            return
        if no.tag == M + 'oMath':
            tex = de_oMath(no)
            if tex:
                # oMathPara (equação em bloco) vira display; o resto, inline
                partes.append(' \\[%s\\] ' % tex if em_para else ' \\(%s\\) ' % tex)
            return
        if no.tag == A + 't':
            partes.append(no.text or '')
            return
        if no.tag == A + 'br':
            partes.append('\n')
            return
        em_para = em_para or no.tag == M + 'oMathPara'
        for f in no:
            anda(f, em_para)
        if no.tag == A + 'p':
            partes.append('\n')

    anda(raiz, False)
    linhas = [re.sub(r'[ \t]{2,}', ' ', l).strip()
              for l in ''.join(partes).split('\n')]
    return '\n'.join(l for l in linhas if l)
