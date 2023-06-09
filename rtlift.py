from argparse import ArgumentParser
from pyverilog.vparser.parser import parse, ParseError
import pyverilog.vparser.ast as vast
from sys import stdout
from pyverilog.ast_code_generator.codegen import ASTCodeGenerator
import random
import copy


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

def get_assignment(ast):
    return find_graph_node(ast, vast.Assign)

def output_verilog(ast, file=stdout):
    generator = ASTCodeGenerator()
    print(generator.visit(ast), file=file)

def main(args):
	
    full_ast, directives = parse(args.file_list, 
				preprocess_include = args.include, 
		        preprocess_define = args.define, debug=False)
    
    # full_ast.show()
    modules = full_ast.children()[0].children()

    for module in modules:
        portlist_r = find_graph_node(module, vast.Portlist)
        portlist = portlist_r[0]
        plist = list(portlist.ports)
            
        for port in portlist.children():
            p_new = copy.deepcopy(port)
            p_new.first.name = port.first.name + '_t'
            plist.append(p_new)
        portlist.ports = tuple(plist)
	
        items = list(module.items)
        assignments = get_assignment(module)
        for assignment in assignments:
            if isinstance(assignment.right.var, vast.And):
                index = items.index(assignment)
                items.remove(assignment)
                portlist_ins = []
                X = assignment.right.var.left
                Y = assignment.right.var.right
                Z = assignment.left.var
                portlist_ins.append(vast.PortArg(portname= 'X', argname= X))
                portlist_ins.append(vast.PortArg(portname= 'Y', argname= Y))
                portlist_ins.append(vast.PortArg(portname= 'Z', argname= Z))
                Xt = copy.deepcopy(X)
                Yt = copy.deepcopy(Y)
                Zt = copy.deepcopy(Z)
                Xt.name = Xt.name + '_t'
                Yt.name = Yt.name + '_t'
                Zt.name = Zt.name + '_t'
                portlist_ins.append(vast.PortArg(portname= 'X_t', argname= Xt))
                portlist_ins.append(vast.PortArg(portname= 'Y_t', argname= Yt))
                portlist_ins.append(vast.PortArg(portname= 'Z_t', argname= Zt))

                instance_portlist = tuple(portlist_ins)
                parameterlist1 = []
                parameterlist = tuple(parameterlist1)
                instance = vast.Instance(module='and_IFT', name='and' + assignment.left.var.name, portlist=instance_portlist, parameterlist=parameterlist)

                instances = []
                instances.append(instance)
                instancelist = vast.InstanceList(module='and_IFT', instances=instances, parameterlist=parameterlist)

                items.insert(index, instancelist)
                module.items = tuple(items)
                # print(module.items)
        
    with open('ift.v', 'w+') as f:
        output_verilog(full_ast, file=f)



                


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