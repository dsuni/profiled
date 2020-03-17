#! /usr/bin/env python3

# =============================================================================
# This file is part of profile-qt
#
# Copyright (C) 2010 Nokia Corporation and/or its subsidiary(-ies).
# All rights reserved.
#
# Contact: Sakari Poussa <sakari.poussa@nokia.com>
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer. Redistributions in
# binary form must reproduce the above copyright notice, this list of
# conditions and the following disclaimer in the documentation  and/or
# other materials provided with the distribution.
#
# Neither the name of Nokia Corporation nor the names of its contributors
# may be used to endorse or promote products derived from this software without
# specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS
# BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY,
# OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED
# OF THE POSSIBILITY OF SUCH DAMAGE.
# =============================================================================

import sys,os,string

COLORMAP = (
"#e633e6", "#33e633", "#33338c", "#8ce6e6", "#e66e33", "#e6e68c", "#336e33", "#33ab8c", "#8c6e8c",
"#8c3333", "#336ee6", "#8cab33", "#e66ee6", "#8c33e6", "#e6338c", "#33e6e6", "#8cabe6", "#8ce68c",
"#e6ab8c", "#e6e633", "#33ab33", "#e63333", "#336e8c", "#8c6e33", "#3333e6", "#33e68c", "#8c338c",
"#33abe6", "#8c6ee6", "#8cab8c", "#e66e8c", "#8ce633", "#e6ab33", "#e6abe6",
)

def bgcolor(i):
    rgb = COLORMAP[i % len(COLORMAP)]
    rgb = int(rgb[1:],16)
    r = (rgb >> 16) & 255
    g = (rgb >>  8) & 255
    b = (rgb >>  0) & 255
    r = (255 * 2 + r * 1)//3
    g = (255 * 2 + g * 1)//3
    b = (255 * 2 + b * 1)//3
    rgb = "#%02x%02x%02x" % (r,g,b)
    return rgb

MAP_MODULE = {}
def set_module_mapping(real, show):
    MAP_MODULE[real] = show
def map_module(name):
    return MAP_MODULE.get(name,name)

IGNORE_FUNCTIONS = {}
IGNORE_MODULES   = { "" : None }
def ignore_function(name):
    IGNORE_FUNCTIONS[name + "()"] = None
def ignore_module(name):
    IGNORE_MODULES[name] = None
def is_ignored(sym,mod):
    if mod in IGNORE_MODULES:
        return 1
    if sym in IGNORE_FUNCTIONS:
        return 1
    return None

def parse_line(s):
    s = s.expandtabs()
    s = s.rstrip()

    if ' at ' in s:
        s,f = s.split(' at ')
        f = f.split(":")[0]
        f = os.path.splitext(f)[0]
    else:
        s,f = s, ""

    i,n = 0,len(s)
    while i < n and s[i] == ' ':
        i += 1
    k = i + 1
    while k < n and s[k] != ' ':
        k += 1

    s = s[i:k]
    assert (i&3) == 0

    f = map_module(f)

    return i/4, s, f

def parse_bool(s):
    try:
        return int(s) != 0
    except ValueError:
        pass
    return s.lower() in ("y","yes","t","true")

if __name__ == "__main__":

    CLUSTERIZE = 0
    INTERFACE  = 0
    TOPLEVEL   = 0

    # - - - - - - - - - - - - - - - - - - - -
    # parse args
    # - - - - - - - - - - - - - - - - - - - -

    args = sys.argv[1:]
    args.reverse()
    while args:
        a = args.pop()
        k,v = a[:2],a[2:]
        if k == "-c":
            CLUSTERIZE = parse_bool(v or args.pop())
        elif k == "-i":
            INTERFACE = parse_bool(v or args.pop())
        elif k == "-t":
            TOPLEVEL = parse_bool(v or args.pop())
        elif k == "-x":
            for s in (v or args.pop()).split(","):
                ignore_function(s)
        elif k == "-X":
            for s in (v or args.pop()).split(","):
                ignore_module(s)
        elif k == "-M":
            for s in (v or args.pop()).split(","):
                real,show = s.split("=")
                set_module_mapping(real,show)
        else:
            print("Unknown option:", a, file=sys.stderr)
            sys.exit(1)

    if TOPLEVEL:
        INTERFACE = CLUSTERIZE = 0

    if INTERFACE:
        CLUSTERIZE = 1

    # - - - - - - - - - - - - - - - - - - - -
    # parse cflow output
    # - - - - - - - - - - - - - - - - - - - -

    stk,dep,ign = [],{},999
    for s in sys.stdin:
        lev,sym,mod = parse_line(s)
        while len(stk) > lev:
            stk.pop()
        if len(stk) <= ign:
            ign = 999
        if is_ignored(sym,mod):
            ign = min(ign, lev)
        key = (sym,mod)
        if 0 < len(stk) < ign:
            dep[(stk[-1],key)]=None
        stk.append(key)

    if INTERFACE:
        tmp = {}
        for src,dst in dep:
            if src[1] != dst[1]:
                #print>>sys.stderr, "USE: %s -> %s" % (str(src),str(dst))
                mod = src[1]
                fun = mod.upper()
                src = (fun,mod)
                tmp[(src,dst)]=None
            else:
                pass
                #print>>sys.stderr, "IGN: %s -> %s" % (str(src),str(dst))
## QUARANTINE                 mod = dst[1].upper()
## QUARANTINE                 dst = (mod,mod)
## QUARANTINE                 tmp[(src,dst)]=None
        dep = tmp

    if TOPLEVEL:
        tmp = {}
        for src,dst in dep:
            if src[1] != dst[1]:
                src = (src[1],src[1])
                dst = (dst[1],dst[1])
                tmp[(src,dst)]=None
        dep = tmp
    dep = list(dep.keys())

    # - - - - - - - - - - - - - - - - - - - -
    # enumerate nodes & clusters
    # - - - - - - - - - - - - - - - - - - - -

    col = {}
    obj = {}
    clu = {}

    def ref(cur):
        if cur not in obj:
            obj[cur] = "node%04d" % len(obj)

        sym,mod = cur

        if mod not in clu:
            col[mod] = bgcolor(len(col))
            clu[mod] = [cur]
        else:
            clu[mod].append(cur)

    for src,dst in dep:
        ref(src)
        ref(dst)

    dot = []
    _ = lambda x:dot.append(x)

    _('digraph flow {')

    _('rankdir = LR;')
    _('ranksep = 0.4;')
    _('nodesep = 0.2;')

    _('node[width=.1];')
    _('node[height=.1];')
    _('node[fontsize=7];')
    if TOPLEVEL:
        _('node[shape=ellipse];')
    else:
        _('node[shape=box];')
    _('node[style=filled, fillcolor=yellow];')

    _('')
    for cur,name in list(obj.items()):
        if CLUSTERIZE:
            _('%s[label="%s"];' % (name,cur[0]))
        else:
            lab=cur[0]
            pen=col[cur[1]]
            _('%s[label="%s",style=filled,fillcolor="%s"];' % (name,lab,pen))

    _('')
    for src,dst in dep:
        _('%s->%s;' % (obj[src], obj[dst]))

    if CLUSTERIZE:
        for mod,syms in list(clu.items()):
            _('')
            _('subgraph cluster%s {' % mod.replace('-','_'))
            #_('bgcolor="#f0f0f0";')
            _('bgcolor="%s";' % col[mod])
            for sym in syms:
                _('%s;' % obj[sym])
            _('}')

    _('}')

    print("\n".join(dot))
