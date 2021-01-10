
from symbol import Type, BasicType, Symbol, BasicSymbol as Bsym
from symtab import SymTab

class VirtualType(Type):
    def __init__(self, name):
        super().__init__(name, 0)

TYPE_LABEL = VirtualType('label')
TYPE_GOTO = VirtualType('goto')

label_cnt = 0

class LabelSymbol(Symbol):
    def __init__(self):
        global label_cnt
        super().__init__("__label__"+str(label_cnt), TYPE_LABEL)
        label_cnt += 1
        self.type_str = 'label'

goto_cnt = 0

class GotoSymbol(Symbol):
    def __init__(self, tgtTAC):
        global goto_cnt
        super().__init__("__goto("+tgtTAC.dest.name+")_"+str(goto_cnt), TYPE_GOTO)
        goto_cnt += 1
        self.type_str = 'goto'
        self.tgt = tgtTAC

def genSimpleConst(val, vtype):
    while len(val)>0 and (val[-1]<'0' or val[-1]>'9'):
        val = val[:-1]

    name = val+'('+str(vtype)+')'
    
    bsym = Bsym(name, vtype)

    bsym.isTmp = True
    bsym.isConst = True
    bsym.val = int(val)
    return bsym

def genType(op, *args)->BasicType:
    assert(len(args)!=0)
    if op in ['!', '&&', '||', '<', '>', '<=', '>=', '==', '!=']:
        return BasicType('int')
    unsigned = False
    maxWidth = 0

    for arg in args:
        if arg.type.name.startswith('unsigned'):
            unsigned = True
        maxWidth = max(maxWidth, arg.type.size)
    ansType = "long long"
    if maxWidth==1:
        ansType = "char"
    elif maxWidth==2:
        ansType = "short"
    elif maxWidth==4:
        ansType = "int"
    if unsigned:
        ansType = "unsigned "+ ansType
    return BasicType(ansType)


def genConstant(op, *args):
    assert(len(args)!=0)

    ansType = genType(op, *args)

    unsigned = ansType.name.startswith('unsigned')
    maxWidth = ansType.size * 8

    vals = []
    for arg in args:
        val = arg.val
        if unsigned and (not arg.type.name.startswith('unsigned')):
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
    elif op =='!':
        if vals[0] == 0:
            ans = 1
        else:
            ans = 0
    elif op == '&&':
        if vals[0] and vals[1]:
            ans = 1
        else:
            ans = 0
    elif op == '||':
        if vals[0] or vals[1]:
            ans = 1
        else:  
            ans = 0
    elif op == '<':
        if vals[0] < vals[1]:
            ans = 1
        else:
            ans = 0
    elif op == '>':
        if vals[0] > vals[1]:
            ans = 1
        else:
            ans = 0
    elif op == '<=':
        if vals[0] <= vals[1]:
            ans = 1
        else:
            ans = 0
    elif op == '>=':
        if vals[0] >= vals[1]:
            ans = 1
        else:
            ans = 0
    elif op == '==':
        if vals[0] == vals[1]:
            ans = 1
        else:
            ans = 0
    elif op == '!=':
        if vals[0] != vals[1]:
            ans = 1
        else:
            ans = 0

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
