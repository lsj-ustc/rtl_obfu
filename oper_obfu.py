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

def get_assign_substitutions(ast):
    return find_graph_node(ast, vast.NonblockingSubstitution) + find_graph_node(ast, vast.BlockingSubstitution)

def output_verilog(ast, file=stdout):
    generator = ASTCodeGenerator()
    print(generator.visit(ast), file=file)

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

def main(args):
	
    full_ast, directives = parse(args.file_list, 
				preprocess_include = args.include, 
		        preprocess_define = args.define, debug=False)
    
    # full_ast.show()
    always_nodes = get_always_nodes(full_ast)

    for always_node in always_nodes:
        assignments = get_assign_substitutions(always_node)
        index = 0
        k = ''
        for assign in assignments:
            if isinstance(assign.right.var, vast.Plus):
                kc, k, index = oper_obfu(assign, k, index, '+')
                assign.right = vast.Rvalue(kc, lineno=assign.lineno)
            if isinstance(assign.right.var, vast.Minus):
                kc, k, index = oper_obfu(assign, k, index, '-')
                assign.right = vast.Rvalue(kc, lineno=assign.lineno)

    portlist = find_graph_node(full_ast, vast.Portlist)

    for pl in portlist:
        plist = list(pl.ports)
        k_width = vast.Width(msb=vast.IntConst(0),lsb=vast.IntConst(index - 1))
        plist.append(vast.Ioport(first=vast.Input(name="k", width=k_width)))
        pl.ports = tuple(plist)
        # pl.show()

    # full_ast.show()
    with open('operfu_code.v', 'w+') as f:
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