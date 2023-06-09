from argparse import ArgumentParser
from pyverilog.vparser.parser import parse, ParseError
import pyverilog.vparser.ast as vast
from sys import stdout
from pyverilog.ast_code_generator.codegen import ASTCodeGenerator

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

def get_nonblocking_substitutions(ast):
    return find_graph_node(ast, vast.NonblockingSubstitution)

def output_verilog(ast, file=stdout):
    generator = ASTCodeGenerator()
    print(generator.visit(ast), file=file)

def const_obfu(constvalue, non, k, index):
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
        kc = vast.Pointer(var=vast.Identifier("k"), ptr=vast.IntConst(str(index)), lineno=non.lineno)
    else:
        kc = vast.Partselect(vast.Identifier("k", lineno=non.lineno), 
                            vast.IntConst(str(index), lineno=non.lineno), 
                            vast.IntConst(str(index + length - 1), lineno=non.lineno), 
                            lineno=non.lineno)
    index += length
    # kc = vast.Identifier(kname, lineno=non.lineno)
    # rv = vast.Rvalue(kc, lineno=non.lineno)
    # non.right = rv

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
        nonblockings = get_nonblocking_substitutions(always_node)
        index = 0
        k = ''
        for non in nonblockings:
            if isinstance(non.right.var, vast.IntConst):
                # intc = vast.IntConst('3')
                constvalue = non.right.var.value
                kc, k, index = const_obfu(constvalue, non, k, index)
                non.right = vast.Rvalue(kc, lineno=non.lineno)

            if isinstance(non.right.var, vast.Plus) | isinstance(non.right.var, vast.Minus) | isinstance(non.right.var, vast.Divide):
                var1 = non.right.var
                if isinstance(var1.left, vast.IntConst):
                    constvalue = var1.left.value
                    kc, k, index = const_obfu(constvalue, non, k, index)
                    var1.left = kc
                if isinstance(var1.right, vast.IntConst):
                    constvalue = var1.right.value
                    kc, k, index = const_obfu(constvalue, non, k, index)
                    var1.right = kc

    portlist = find_graph_node(full_ast, vast.Portlist)

    for pl in portlist:
        plist = list(pl.ports)
        k_width = vast.Width(msb=vast.IntConst(0),lsb=vast.IntConst(index - 1))
        plist.append(vast.Ioport(first=vast.Input(name="k", width=k_width)))
        pl.ports = tuple(plist)
        # pl.show()

    # full_ast.show()
    with open('confu_code.v', 'w+') as f:
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