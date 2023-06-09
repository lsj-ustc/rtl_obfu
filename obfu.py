from argparse import ArgumentParser
from pyverilog.vparser.parser import parse, ParseError
import pyverilog.vparser.ast as vast
from sys import stdout
from pyverilog.ast_code_generator.codegen import ASTCodeGenerator
import random

def find_graph_node(ast, node_type, no_children=True):
	ret = []
	queue = [ast]

	while queue:
		current_node = queue.pop(0)

		if isinstance(current_node, node_type):
			ret.append(current_node)
			if no_children: continue

		for node in current_node.children():
			queue.append(node)

	return ret

def get_moduledef_nodes(ast):
    moduledef = ast.children()[0].children()
    return moduledef

def get_always_nodes(ast):
	if isinstance(ast, vast.ModuleDef):
		return find_graph_node(ast, vast.Always)

	moduledef = ast.children()[0].children()[0]
	assert isinstance(moduledef, vast.ModuleDef), \
			f'node is not a ModuleDef, got {type(moduledef)}'

	return find_graph_node(moduledef, vast.Always)

def get_assignblocking_substitutions(ast):
    return find_graph_node(ast, vast.NonblockingSubstitution) + find_graph_node(ast, vast.BlockingSubstitution)

def get_ifstatement(ast):
    return find_graph_node(ast, vast.IfStatement, False)

def output_verilog(ast, file=stdout):
    generator = ASTCodeGenerator()
    print(generator.visit(ast), file=file)

def const_obfu(constvalue, assign, k, index):
    if len(constvalue) > 3:
        if constvalue[2] == 'b':
            length = len(constvalue) - 3
            k = k + constvalue[3:len(constvalue)]
        else:
            length = int(int(constvalue)/2) + 1
            binvalue = detobin(constvalue)
            k = k + binvalue
    else:
        length = int(int(constvalue)/2) + 1
        binvalue = detobin(constvalue)
        k = k + binvalue

    if length == 1:
        kc = vast.Pointer(var=vast.Identifier("k"), ptr=vast.IntConst(str(index)), lineno=assign.lineno)
    else:
        kc = vast.Partselect(vast.Identifier("k", lineno=assign.lineno), 
                            vast.IntConst(str(index), lineno=assign.lineno), 
                            vast.IntConst(str(index + length - 1), lineno=assign.lineno), 
                            lineno=assign.lineno)
    index += length
    # kc = vast.Identifier(kname, lineno=assign.lineno)
    # rv = vast.Rvalue(kc, lineno=assign.lineno)
    # assign.right = rv

    return kc, k, index

def oper_obfu(assign, k, index, oper):
    k_0 = random.getrandbits(1)
    var1 = assign.right.var
    a = var1.left
    b = var1.right
    rep_not = vast.Repeat(vast.Concat([vast.Unot(vast.Pointer(var=vast.Identifier("k"), ptr=vast.IntConst(str(index))))]), vast.IntConst(8))
    rep = vast.Repeat(vast.Concat([vast.Pointer(var=vast.Identifier("k"), ptr=vast.IntConst(str(index)))]), vast.IntConst(8))

    if oper == '-':
        tmp = rep_not
        rep_not = rep
        rep = tmp

    if k_0 == 1:
        a1 = vast.And(vast.Minus(a, b), rep_not)
        a2 = vast.And(vast.Plus(a, b), rep)
        kc = vast.Or(a1, a2)
    else:
        a1 = vast.And(vast.Minus(a, b), rep)
        a2 = vast.And(vast.Plus(a, b), rep_not)
        kc = vast.Or(a1, a2)
    
    index += 1
    k = k + str(k_0)
    return kc, k, index

def bran_obfu(cond, k, index):
    k_b = random.getrandbits(1)

    if k_b == 1:
        if isinstance(cond, vast.GreaterEq):
            kc = vast.Xor(vast.LessThan(cond.left, cond.right), vast.Pointer(var=vast.Identifier("k"), ptr=vast.IntConst(str(index))))
        elif isinstance(cond, vast.GreaterThan):
            kc = vast.Xor(vast.LessEq(cond.left, cond.right), vast.Pointer(var=vast.Identifier("k"), ptr=vast.IntConst(str(index))))
        elif isinstance(cond, vast.LessEq):
            kc = vast.Xor(vast.GreaterThan(cond.left, cond.right), vast.Pointer(var=vast.Identifier("k"), ptr=vast.IntConst(str(index))))
        elif isinstance(cond, vast.LessThan):
            kc = vast.Xor(vast.GreaterEq(cond.left, cond.right), vast.Pointer(var=vast.Identifier("k"), ptr=vast.IntConst(str(index))))
        else:
            return cond, k, index
    else:
        if isinstance(cond, vast.GreaterEq) or isinstance(cond, vast.GreaterThan)or isinstance(cond, vast.LessEq) or isinstance(cond, vast.LessThan):
            kc = vast.Xor(cond, vast.Pointer(var=vast.Identifier("k"), ptr=vast.IntConst(str(index))))
        else:
            return cond, k, index
    
    k = k + str(k_b)
    index += 1
    
    return kc, k, index 

def detobin(dec):
    num = int(dec)
    if num == 0:
        bin = '0'
        return bin
    
    bin = ''
    while num > 0:
        y = num % 2
        y = str(y)
        num = int(num/2)
        bin = y + bin
    
    return bin

def main(args):
	
    full_ast, directives = parse(args.file_list, 
				preprocess_include = args.include, 
		        preprocess_define = args.define, debug=False)
    
    # full_ast.show()
    modules = get_moduledef_nodes(full_ast)

    key = {}
    keylen = {}
    for module in modules:
        always_nodes = get_always_nodes(module)

        for always_node in always_nodes:
            assignments = get_assignblocking_substitutions(always_node)
            ifstatements = get_ifstatement(always_node)
            index = 0
            k = ''
            for assign in assignments:
                if isinstance(assign.right.var, vast.IntConst):
                    # intc = vast.IntConst('3')
                    constvalue = assign.right.var.value
                    kc, k, index = const_obfu(constvalue, assign, k, index)
                    assign.right = vast.Rvalue(kc, lineno=assign.lineno)

                if isinstance(assign.right.var, vast.Plus) | isinstance(assign.right.var, vast.Minus) | isinstance(assign.right.var, vast.Divide):
                    var1 = assign.right.var
                    if isinstance(var1.left, vast.IntConst):
                        constvalue = var1.left.value
                        kc, k, index = const_obfu(constvalue, assign, k, index)
                        var1.left = kc
                    if isinstance(var1.right, vast.IntConst):
                        constvalue = var1.right.value
                        kc, k, index = const_obfu(constvalue, assign, k, index)
                        var1.right = kc
                    if isinstance(var1, vast.Plus):
                        kc, k, index = oper_obfu(assign, k, index, '+')
                        assign.right = vast.Rvalue(kc, lineno=assign.lineno)
                    if isinstance(var1, vast.Minus):
                        kc, k, index = oper_obfu(assign, k, index, '-')
                        assign.right = vast.Rvalue(kc, lineno=assign.lineno)
            
            for ifstatement in ifstatements:
                if isinstance(ifstatement.cond, vast.GreaterEq):
                    kc, k, index = bran_obfu(ifstatement.cond, k, index)
                    ifstatement.cond = kc

        keylen[module.name] = index

        if index != 0: 
            key[module.name] = k
            portlist = find_graph_node(module, vast.Portlist)

            for pl in portlist:
                plist = list(pl.ports)
                k_width = vast.Width(msb=vast.IntConst(0),lsb=vast.IntConst(index - 1))
                plist.append(vast.Ioport(first=vast.Input(name="k", width=k_width)))
                pl.ports = tuple(plist)
                # pl.show()  
        else:
            key[module.name] = 'no'


    for module in modules:
        ret = find_graph_node(module, vast.InstanceList)
        if len(ret) == 0:
            continue
        instancelist = ret[0]
        instance = instancelist.instances[0]
        portlist_ins = list(instance.portlist)

        index = keylen[module.name]
        length_ins = int(len(key[instancelist.module]))
        new_end = index + length_ins - 1

        argn = vast.Partselect(vast.Identifier("k"), 
                            vast.IntConst(str(index), lineno=assign.lineno), 
                            vast.IntConst(str(new_end)))
        portlist_ins.append(vast.PortArg(portname= 'k', argname= argn))
        instance.portlist = tuple(portlist_ins)

        portlist = find_graph_node(module, vast.Portlist)

        plist = list(portlist[0].ports)
        k_width = vast.Width(msb=vast.IntConst(0),lsb=vast.IntConst(new_end))
        plist.append(vast.Ioport(first=vast.Input(name="k", width=k_width)))
        portlist[0].ports = tuple(plist)
        # pl.show()

    # full_ast.show()
    with open('modus_code.v', 'w+') as f:
        output_verilog(full_ast, file=f)
        miyao = "// K: " + k 
        f.writelines(miyao)
	

if __name__ == "__main__":
	arguments = [
			(['-I'], {'dest':'include', 'action':'append','default':[],
				'help':"verilog includes directory"}),
			(['-D'], {'dest':'define', 'action':'append', 'default':[],
				'help':"Define preprocessor constant"}),
			(['file_list'], {'nargs':'+'})]

	parser = ArgumentParser()
	for param, arg in arguments:
		parser.add_argument(*param, **arg)

	args = parser.parse_args()
	exit(main(args))