
rnamelist = [
        ['zero'],
        ['ra'],
        ['sp'],
        ['gp'],
        ['tp'],
        ['t0'],
        ['t1'],
        ['t2'],
        ['s0', 'fp'],
        ['s1'],
        ['a0'],
        ['a1'],
        ['a2'],
        ['a3'],
        ['a4'],
        ['a5'],
        ['a6'],
        ['a7'],
        ['s2'],
        ['s3'],
        ['s4'],
        ['s5'],
        ['s6'],
        ['s7'],
        ['s8'],
        ['s9'],
        ['s10'],
        ['s11'],
        ['t3'],
        ['t4'],
        ['t5'],
        ['t6']
]

vert_cast = {}

for i in range(len(rnamelist)):
    rnames = rnamelist[i]
    for rname in rnames:
        vert_cast[rname] = '$'+str(i)

def register_replace(src):
    global vert_cast
    dst = vert_cast.get(src)
    if dst is None:
        return src
    else:
        return dst