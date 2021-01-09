
TAC_ID = 0

class TAC(object):
    def __init__(self, op, dest, *args):
        self.op = op
        self.dest = dest
        self.args = args

        global TAC_ID
        self.id = TAC_ID
        TAC_ID += 1

    # def is_used(self, arg):
    #    return self.arg1 == arg or self.arg2 == arg

    def isGoto(self):
        return (self.op=='goto' or self.op=='if')

    def __str__(self):
        line = str(self.id) + " : "
        if self.op is None:
            return line + ' <None>'
        line += self.op + " "
        if isinstance(self.dest, TAC):
            line += str(self.dest.id)
        else:
            line += self.dest.name
        if len(self.args):
            line += " <-"
        for arg in self.args:
            line += " " + arg.name
        return line

    def __repr__(self):
        return str(self)

class TAC_block(object):
    def __init__(self, *combined_blocks):
        self.TACs = []
        for block in combined_blocks:
            self.TACs += block.TACs

    def appendTAC(self, newTAC):
        self.TACs.append(newTAC)

    def __str__(self):
        if len(self.TACs)==0:
            return "<empty>"
        lines = ""
        for TAC in self.TACs:
            lines += str(TAC)+"\n"
        return lines
    def __repr__(self):
        return str(self)

if __name__=='__main__':

    t1 = TAC("+", "x", "y", "z")
    t2 = TAC("-", "w", "x")
    t3 = TAC("goto", t2)
    tb1 = TAC_block()
    tb1.appendTAC(t1)
    tb1.appendTAC(t2)
    tb2 = TAC_block()
    tb2.appendTAC(t3)
    tb3 = TAC_block(tb1, tb2)

    print(t1)
    print(t2)
    print(t3)
    print(tb1)
    print(tb2)
    print(tb3)