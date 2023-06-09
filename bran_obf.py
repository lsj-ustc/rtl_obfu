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

def get_always_nodes(ast):
	if isinstance(ast, vast.ModuleDef):
		return find_graph_node(ast, vast.Always)

	moduledef = ast.children()[0].children()[0]
	assert isinstance(moduledef, vast.ModuleDef), \
			f'node is not a ModuleDef, got {type(moduledef)}'

	return find_graph_node(moduledef, vast.Always)

def get_ifstatement(ast):
    return find_graph_node(ast, vast.IfStatement, False)

def output_verilog(ast, file=stdout):
    generator = ASTCodeGenerator()
    print(generator.visit(ast), file=file)


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
    always_nodes = get_always_nodes(full_ast)

    for always_node in always_nodes:
        ifstatements = get_ifstatement(always_node)
        index = 0
        k = ''
        for ifstatement in ifstatements:
            if isinstance(ifstatement.cond, vast.GreaterEq):
                kc, k, index = bran_obfu(ifstatement.cond, k, index)
                ifstatement.cond = kc

            # if isinstance(non.right.var, vast.IntConst):
            #     # intc = vast.IntConst('3')
            #     constvalue = non.right.var.value
            #     kc, k, index = const_obfu(constvalue, non, k, index)
            #     non.right = vast.Rvalue(kc, lineno=non.lineno)

            # if isinstance(non.right.var, vast.Plus) | isinstance(non.right.var, vast.Minus) | isinstance(non.right.var, vast.Divide):
            #     var1 = non.right.var
            #     if isinstance(var1.left, vast.IntConst):
            #         constvalue = var1.left.value
            #         kc, k, index = const_obfu(constvalue, non, k, index)
            #         var1.left = kc
            #     if isinstance(var1.right, vast.IntConst):
            #         constvalue = var1.right.value
            #         kc, k, index = const_obfu(constvalue, non, k, index)
            #         var1.right = kc

    # portlist = find_graph_node(full_ast, vast.Portlist)

    # for pl in portlist:
    #     plist = list(pl.ports)
    #     k_width = vast.Width(msb=vast.IntConst(0),lsb=vast.IntConst(index - 1))
    #     plist.append(vast.Ioport(first=vast.Input(name="k", width=k_width)))
    #     pl.ports = tuple(plist)
    #     # pl.show()

    # full_ast.show()
    with open('bran_code.v', 'w+') as f:
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
