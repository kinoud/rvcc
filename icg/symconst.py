from symtab import Symbol, BasicSymbol as Bsym, SymTab

label_cnt = 0

class LabelSymbol():
    def __init__(self):
        global label_cnt
        super.__init__("__label__"+str(label_cnt))
        label_cnt += 1
        self.type_str = 'label'

def genSimpleConst(val, vtype):
    while len(val)>0 and (val[-1]<'0' or val[-1]>'9'):
        val = val[:-1]
    name = val+'('+vtype+')'
    bsym = Bsym(name, vtype)
    bsym.isTmp = True
    bsym.isConst = True
    bsym.val = int(val)
    return bsym

def genType(op, *args):
    assert(len(args)!=0)
    # 暂未考虑逻辑运算
    unsigned = False
    maxWidth = 0
    for arg in args:
        sym = Bsym.gen_symbol("", arg.type)
        if sym.unsigned:
            unsigned = True
        maxWidth = max(maxWidth, sym.size)
    ansType = "long long"
    if maxWidth==1:
        ansType = "char"
    elif maxWidth==2:
        ansType = "short"
    elif maxWidth==4:
        ansType = "int"
    if unsigned:
        ansType = "unsigned "+ ansType
    return ansType


def genConstant(op, *args):
    assert(len(args)!=0)

    ansType = genType(op, *args)

    sym = Bsym.gen_symbol("", ansType )
    unsigned = sym.unsigned
    maxWidth = sym.size * 8

    vals = []
    for arg in args:
        sym = Bsym.gen_symbol("", arg.type)
        val = arg.val
        if unsigned and (not sym.unsigned):
            print('Waring : Implicit cast from signed to unsigned')
            if val<0:
                val = val + 1 << (maxWidth-1)
        vals.append(val)
    ans = 0
    if op=='+':
        for val in vals:
            ans +=val
    elif op=='-':
        if len(args)==1:
            ans = -vals[0]
        else:
            ans = vals[0] - vals[1]
    elif op=='*':
        ans = 1
        for val in vals:
            ans *=val
    elif op=='/':
        ans = vals[0] // vals[1]
    while ans>=(1 << (maxWidth-1)):
        ans -= 1 << maxWidth
    while ans<(-(1 << (maxWidth-1))):
        ans += 1 << maxWidth
    ans = str(ans)
    if unsigned:
        ans += "u"
    if maxWidth//8==8: # 暂不考虑int long问题
        ans += "LL"
    return genSimpleConst(ans, ansType)
