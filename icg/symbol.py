
import abc

# Type begin
class Type(object):
    def __init__(self, name, size):
        self.name = name
        self.size = size

    def __repr__(self):
        return self.name+'('+str(self.size)+')'

    @abc.abstractmethod
    def gen_symbol(self, name:str):
        pass


class StructType(Type):
    def __init__(self, name, member_types:list):
        sz = 0
        for t in member_types:
            sz += t.size
        self.member_types = member_types
        super().__init__(name, sz)
    
    def gen_symbol(self, name):
        return StructSymbol(name, self)

class BasicType(Type):
    SIZE_OF = {
        'long long':8,
        'long long int':8,
        'long':4,
        'long int':4,
        'signed':4,
        'unsigned':4,
        'int':4,
        'short int':2,
        'short':2,
        'char':1,
        'unsigned long long':8,
        'unsigned long long int':8,
        'unsigned long':4,
        'unsigned long int':4,
        'unsigned int':4,
        'unsigned short int':2,
        'unsigned short':2,
        'unsigned char':1
    }
    def __init__(self, type_str:str):
        szof = BasicType.SIZE_OF
        if szof.get(type_str) is None:
            raise NotImplementedError('类型"'+a+'"尚不支持')
        super().__init__(type_str, szof[type_str])
    
    def gen_symbol(self, name):
        return BasicSymbol(name, self)

class FuncType(Type):
    def __init__(self, return_type:Type, param_types:list):
        super().__init__('function', 0)
        self.return_type = return_type
        if param_types is None:
            param_types = []
        self.param_types = param_types
    
    def gen_symbol(self, name):
        param_names = []
        for i in range(len(self.param_types)):
            param_names.append('__param%d__'%i)
        return FuncSymbol(name, self)

class PtrType(Type):
    def __init__(self, target_type:Type):
        super().__init__('pointer', 4)
        self.target_type = target_type

    def gen_symbol(self, name):
        return PtrSymbol(name, self)

# Type end

# Symbol begin
class Symbol(object):
    def __init__(self, name, sym_type:Type):
        self.name = name
        self.type = sym_type
        self.size = sym_type.size
        self.isTmp = False
        self.isConst = False
        self.val = 0 # isConst 为 True 才有意义

    def __repr__(self):
        return '\033[1;33m%s\033[0m,type=%s'%(self.name,repr(self.type))

class BasicSymbol(Symbol):
    def __init__(self, name, basic_type:BasicType):
        super().__init__(name, basic_type)       

class StructSymbol(Symbol):
    def __init__(self, name, struct_type:StructType):
        super().__init__(name, struct_type)

class PtrSymbol(Symbol):
    def __init__(self, name, ptr_type:PtrType):
        super().__init__(name, ptr_type)

    def __repr__(self):
        ans = super().__repr__()
        ans += ',ttype=' + repr(self.type)
        return ans

class FuncSymbol(Symbol):
    '''
    return_symbol: Symbol
    param_symbols: list
    '''
    def __init__(self, name, func_type:FuncType, param_names:list):
        super().__init__(name, func_type)
        self.return_symbol = func_type.return_type.gen_symbol('__ret__')
        param_symbols = []
        
        if param_names is None:
            param_names = []
        
        assert len(func_type.param_types) == len(param_names)

        for t,name in zip(func_type.param_types, param_names):
            param_symbols.append(t.gen_symbol(name))

        if param_symbols is None:
            param_symbols = []
        self.param_symbols = param_symbols

    def __repr__(self):
        ans = super().__repr__()
        params = ''
        for syb in self.param_symbols:
            params += syb.name+','
        ans += ',params=['+params[:-1]+'],rtype='+repr(self.return_symbol.type)
        return ans
# Symbol end