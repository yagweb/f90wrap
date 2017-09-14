"""
Created on Fri May 26 11:01:18 2017
@author: yagweb
"""
import os
import re

from f90wrap.fortran import Root, Module, Program, Element, Procedure, \
    Subroutine, Function, Interface, Type

from f90wrap import fortran as ft

pat_indent = re.compile(r'^\s+')
pat_identifier = re.compile(r'^\w+')
pat_identifier_full = re.compile(r'^[\w|*|.]+$') 
 
def prune(tree, files):
    _filter = Filter(tree)
    for file in files:
        _filter.add_file(file)
    return _filter.prune()

class Filter(object):
    def __init__(self, tree):
        assert(isinstance(tree, ft.Root))
        self.tree = tree
        root = RootNode(tree)
        self.root = root
        self._cache_modules = {}
        self._cache_types = {}
        self._cache_items = {}
        def __add_nodes_to_cache(cache, pnode, nodes_dict):
            for name, node in nodes_dict.items():
                cache[name] = FilterItem(node, pnode)
        for mod_name, mod in root._cache_modules.items():
            self._cache_modules[mod_name] = FilterItem(mod, root)
            #__add_nodes_to_cache(self._cache_items, mod, mod._cache_elements)
            __add_nodes_to_cache(self._cache_items, mod, mod._cache_procedures)
            __add_nodes_to_cache(self._cache_items, mod, mod._cache_interfaces)
            for name, _type in mod._cache_types.items():
                self._cache_types[name] = FilterItem(_type, mod)
                #register procedures in type
                __add_nodes_to_cache(self._cache_items, _type, _type._cache_procedures)
                __add_nodes_to_cache(self._cache_items, _type, _type._cache_interfaces)
        __add_nodes_to_cache(self._cache_items, root, root._cache_programs)
        __add_nodes_to_cache(self._cache_items, root, root._cache_procedures)
        self._cache_items.update(self._cache_modules)
        self._cache_items.update(self._cache_types)
        
        self.all_tree_nodes = [root]
        self.all_tree_nodes .extend([bb.node for bb in self._cache_modules.values()])
        self.all_tree_nodes .extend([bb.node for bb in self._cache_types.values()])
        
        self.keyword_actions = {
            keyword_top    : self._keyword_top,
            keyword_module : self._keyword_module,
            keyword_type   : self._keyword_type,
            keyword_add    : self._keyword_add,
            keyword_remove : self._keyword_remove
        }
        
        self.add_actions = {
            '*': self._add_all,
            'm.*' : self._add_all_modules,
            'prog.*' : self._add_all_programs,
            'e.*' : self._add_all_elements,
            'p.*' : self._add_all_procedures,
            'i.*' : self._add_all_interfaces,
            't.*' : self._add_all_types
        } 
        self.remove_actions = {
            '*': self._remove_all,
            'm.*' : self._remove_all_modules,
            'prog.*' : self._remove_all_programs,
            'e.*' : self._remove_all_elements,
            'p.*' : self._remove_all_procedures,
            'i.*' : self._remove_all_interfaces,
            't.*' : self._remove_all_types
        }
        
    def add_file(self, path):
        _filter = PruningRuleFile(path)
        rules = _filter.read_rules()
        self.execute_rules(rules)                    
     
    def prune(self):
        return self.root.prune() 
        
    def execute_rules(self, rules):
        for rule in rules:                
            self.execute_rule(rule)
            
    def execute_rule(self, rule):
        action = self.keyword_actions.get(rule.keyword)
        if not action:
            raise Exception("keyword not supported in type, file '%s' line_no %d" % \
                            (rule.path, rule.line_no))
        action(rule)
    def _keyword_top(self, rule):
        self.root._update_by_compound_rule(rule)

    def _keyword_module(self, rule):
        item = self._cache_modules.get(rule.name)
        if not item:
            raise Exception("type '%s' not exist, file '%s' line_no %d" % \
                            (rule.name, rule.path, rule.line_no))
        item.add_module(rule)

    def _keyword_type(self, rule):
        item = self._cache_types.get(rule.name)
        if not item:
            raise Exception("type '%s' not exist, file '%s' line_no %d" % \
                            (rule.name, rule.path, rule.line_no))
        item.add_type(rule)

    def _keyword_add(self, rule):
        for name in rule.identifiers:
            if name in self.add_actions:
                self.add_actions[name]()
                continue
            item = self._cache_items.get(name)
            if not item:
                raise Exception("member '%s' not exists, file '%s', line_no %d" %\
                                (name, rule.path, rule.line_no))
            item.add()

    def _keyword_remove(self, rule):
        for name in rule.identifiers:
            if name in self.remove_actions:
                self.remove_actions[name]()
                continue
            item = self._cache_items.get(name)
            if not item:
                raise Exception("member '%s' not exists, file '%s', line_no %d" %\
                                (name, rule.path, rule.line_no))
            item.remove()            

    def _add_all(self):
        for item in self.all_tree_nodes:
            item._add_all()

    def _add_all_modules(self):
        self.root._add_all_modules()

    def _add_all_programs(self):
        self.root._add_all_programs()

    def _add_all_elements(self):
        for item in self.all_tree_nodes:
            item._add_all_elements()

    def _add_all_procedures(self):
        for item in self.all_tree_nodes:
            item._add_all_procedures()

    def _add_all_interfaces(self):
        for item in self.all_tree_nodes:
            item._add_all_interfaces()

    def _add_all_types(self):
        for item in self.all_tree_nodes:
            item._add_all_types()

    def _remove_all(self):
        for item in self.all_tree_nodes:
            item._remove_all()

    def _remove_all_modules(self):
        self.root._remove_all_modules()

    def _remove_all_programs(self):
        self.root._remove_all_programs()

    def _remove_all_elements(self):
        for item in self.all_tree_nodes:
            item._remove_all_elements()

    def _remove_all_procedures(self):
        for item in self.all_tree_nodes:
            item._remove_all_procedures()

    def _remove_all_interfaces(self):
        for item in self.all_tree_nodes:
            item._remove_all_interfaces()

    def _remove_all_types(self):
        for item in self.all_tree_nodes:
            item._remove_all_types()

class FilterItem(object):
    def __init__(self, node, pruning_node):
        self.node = node
        #the pruning_node the node belongs to
        self.pruning_node = pruning_node

    def add_module(self, rule):
        module = self.node
        module._update_by_compound_rule(rule)
        self.pruning_node.modules[rule.name] = module

    def add_type(self, rule):
        _type = self.node
        _type._update_by_compound_rule(rule)
        self.pruning_node.types[rule.name] = _type

    def add(self):
        self.pruning_node._add_item(self.node)  

    def remove(self):
        self.pruning_node._remove_item(self.node) 
                    
class TreeNode(object):
    def __init__(self, node, type_nodes, is_add_all = True, new_name = None):
        self.node = node
        self.new_name = new_name
        self._cache_items = {}
        self._cache_modules = {}
        self._cache_programs = {}
        self._cache_elements = {}
        self._cache_procedures = {}
        self._cache_interfaces = {}
        self._cache_types = {}
        
        #kept nodes
        self.modules = {}
        self.programs = {}
        self.elements = {}
        self.procedures = {}
        self.interfaces = {}
        self.types = {}
         
        self._nodes_by_type = {}
               
        self.keyword_actions = {
            keyword_add : self._keyword_add,
            keyword_remove : self._keyword_remove
        }
        self.add_actions = {
            '*': self._add_all
        } 
        self.remove_actions = {
            '*': self._remove_all
        }
        #set cache
        for node_type, nodes in type_nodes.items():            
            if node_type == Module:
                for item in nodes:
                    self._cache_modules[item.orig_name] = ModuleNode(item)      
                self._cache_items.update(self._cache_modules)  
                self._nodes_by_type[ModuleNode] = self.modules 
                self.keyword_actions[keyword_module] = self._keyword_module
                self.add_actions['m.*'] = self._add_all_modules
                self.remove_actions['m.*'] = self._remove_all_modules
            elif node_type == Program:
                for item in nodes:
                    self._cache_programs[item.orig_name] = item
                self._cache_items.update(self._cache_programs)  
                self._nodes_by_type[Program] = self.programs
                self.add_actions['prog.*'] = self._add_all_programs
                self.remove_actions['prog.*'] = self._remove_all_programs
            elif node_type == Element:
                for item in nodes:
                    self._cache_elements[item.orig_name] = item
                self._cache_items.update(self._cache_elements)  
                self._nodes_by_type[Element] = self.elements
                self.add_actions['e.*'] = self._add_all_elements
                self.remove_actions['e.*'] = self._remove_all_elements
            elif node_type == Procedure:
                for item in nodes:
                    self._cache_procedures[item.orig_name] = item
                self._cache_items.update(self._cache_procedures)
                
                self._nodes_by_type[Subroutine] = self.procedures
                self._nodes_by_type[Function] = self.procedures
                
                self.add_actions['p.*'] = self._add_all_procedures
                self.remove_actions['p.*'] = self._remove_all_procedures
            elif node_type == Interface:
                for item in nodes:
                    self._cache_interfaces[item.orig_name] = item
                self._cache_items.update(self._cache_interfaces)  
                self._nodes_by_type[Interface] = self.interfaces
                self.add_actions['i.*'] = self._add_all_interfaces
                self.remove_actions['i.*'] = self._remove_all_interfaces
            elif node_type == Type:
                for item in nodes:
                    self._cache_types[item.orig_name] = TypeNode(item)
                self._cache_items.update(self._cache_types)
                self._nodes_by_type[TypeNode] = self.types
                self.keyword_actions[keyword_type] = self._keyword_type
                self.add_actions['t.*'] = self._add_all_types
                self.remove_actions['t.*'] = self._remove_all_types 
            #update cache
            if is_add_all:
                self._add_all() 

    def prune(self):
        return self.node   
         
    def _update_by_compound_rule(self, rule):
        assert(isinstance(rule, CompoundRule))
        self.new_name = rule.new_name
        for sub in rule.subrules:
            self.execute_rule(sub)

    def execute_rules(self, rules):
        for rule in rules:
            self.execute_rule(rule)

    def execute_rule(self, rule):
        action = self.keyword_actions.get(rule.keyword)
        if not action:
            raise Exception("keyword not supported in type, file '%s' line_no %d" % \
                            (rule.path, rule.line_no))
        action(rule)

    def _keyword_module(self, rule):
        module = self._cache_modules.get(rule.name)
        if not module:
            raise Exception("module '%s' not exist, file '%s' line_no %d" % \
                            (rule.name, rule.path, rule.line_no))
        module._update_by_compound_rule(rule)
        self.modules[rule.name] = module

    def _keyword_type(self, rule):
        _type = self._cache_types.get(rule.name)
        if not _type:
            raise Exception("type '%s' not exist, file '%s' line_no %d" % \
                            (rule.name, rule.path, rule.line_no))
        _type._update_by_compound_rule(rule)
        self.types[rule.name] = _type

    def _keyword_add(self, rule):
        for name in rule.identifiers:
            if name in self.add_actions:
                self.add_actions[name]()
                continue
            item = self._cache_items.get(name)
            if not item:
                raise Exception("member '%s' not exists, file '%s', line_no %d" %\
                                (name, rule.path, rule.line_no))
            self._add_item(item)

    def _keyword_remove(self, rule):
        for name in rule.identifiers:
            if name in self.remove_actions:
                self.remove_actions[name]()
                continue
            item = self._cache_items.get(name)
            if not item:
                raise Exception("member '%s' not exists, file '%s', line_no %d" %\
                                (name, rule.path, rule.line_no))
            self._remove_item(item)

    def _add_all(self):
        self.modules.update(self._cache_modules)
        self.programs.update(self._cache_programs)
        self.elements.update(self._cache_elements)
        self.procedures.update(self._cache_procedures)
        self.interfaces.update(self._cache_interfaces)
        self.types.update(self._cache_types)

    def _add_all_modules(self):
        self.modules.update(self._cache_modules)

    def _add_all_programs(self):
        self.programs.update(self._cache_programs)

    def _add_all_elements(self):
        self.elements.update(self._cache_elements)

    def _add_all_procedures(self):
        self.procedures.update(self._cache_procedures)

    def _add_all_interfaces(self):
        self.interfaces.update(self._cache_interfaces)

    def _add_all_types(self):
        self.types.update(self._cache_types)

    def _add_item(self, node):
        self._nodes_by_type[node.__class__][node.orig_name] = node

    def _remove_all(self):
        self.modules.clear()
        self.programs.clear()
        self.elements.clear()
        self.procedures.clear()
        self.interfaces.clear()
        self.types.clear()

    def _remove_all_modules(self):
        self.modules.clear()

    def _remove_all_programs(self):
        self.programs.clear()

    def _remove_all_elements(self):
        self.elements.clear()

    def _remove_all_procedures(self):
        self.procedures.clear()

    def _remove_all_interfaces(self):
        self.interfaces.clear()

    def _remove_all_types(self):
        self.types.clear()

    def _remove_item(self, node):
        cache = self._nodes_by_type[node.__class__]
        if node.orig_name in cache:
            del cache[node.orig_name] 

class RootNode(TreeNode):
    def __init__(self, node, is_add_all = True): 
        assert(isinstance(node, Root))
        TreeNode.__init__(self, node, {Module: node.modules,
                                        Program : node.programs, 
                                        Procedure : node.procedures
                                        }, is_add_all)

    def prune(self):
        self.node.modules[:] = [bb.prune() for bb in self.modules.values()]
        self.node.programs[:] = self.programs.values()
        self.node.procedures[:] = self.procedures.values()
        return self.node

class ModuleNode(TreeNode):
    def __init__(self, node, is_add_all = True):
        TreeNode.__init__(self, node, {Type : node.types, 
                                        Element : node.elements, 
                                        Interface : node.interfaces, 
                                        Procedure : node.procedures}, is_add_all)
        self.orig_name = node.orig_name

    def prune(self):
        self.node.elements[:] = self.elements.values()
        self.node.interfaces[:] = self.interfaces.values()
        self.node.procedures[:] = self.procedures.values()
        self.node.types[:] = [bb.prune() for bb in self.types.values()]
        return self.node
                
class TypeNode(TreeNode):
    def __init__(self, node, is_add_all = True): 
        TreeNode.__init__(self, node, {Element : node.elements, 
                                        Interface : node.interfaces, 
                                        Procedure : node.procedures}, is_add_all)
        self.orig_name = node.orig_name

    def prune(self):
        self.node.elements[:] = self.elements.values()
        self.node.interfaces[:] = self.interfaces.values()
        self.node.procedures[:] = self.procedures.values()  
        return self.node 

keyword_top = 0        
keyword_module = 1  
keyword_type = 2
keyword_add =  3    
keyword_remove =  4
   
keywords = {
    'top': keyword_top,
    'module': keyword_module,
    'type' : keyword_type,
    'public' : keyword_add,
    'private' : keyword_remove
}
keyword_names = {value: key for key, value in keywords.items()}   

class PruningRule(object):
    def __init__(self, path, line_no, indent, keyword):
        self.path = path
        self.line_no = line_no
        self.indent = indent
        self.keyword = keyword
        
class AtomicRule(PruningRule):
    def __init__(self, path, line_no, indent, keyword, identifiers):
        PruningRule.__init__(self, path, line_no, indent, keyword)
        self.identifiers = identifiers

    def __str__(self):
        return '(%s)%s %s %s' % (self.line_no, 
                                    '----'*self.indent, 
                                    keyword_names[self.keyword], 
                                    ','.join(self.identifiers))
class CompoundRule(PruningRule):
    def __init__(self, path, line_no, indent, keyword, name, new_name):
        PruningRule.__init__(self, path, line_no, indent, keyword)
        self.name = name
        self.new_name = new_name
        self.subrules = []

    def add_rule(self, rule):
        self.subrules.append(rule)

    def __str__(self):
        new_name = (' -> %s' % self.new_name) if self.new_name else ''
        return '(%s)%s %s %s%s:\n%s' % (self.line_no, 
                                    '----'*self.indent, 
                                    keyword_names[self.keyword], 
                                    self.name,
                                    new_name,
                                    '\n'.join([str(bb) for bb in self.subrules]))
        
class PruningRuleFile(object):
    def __init__(self, path):
        if not os.path.exists(path):
            raise Exception("pruning rule file '%s' not exist" % path)
        self.path = path
        self.fp = open(path)
        self.line_no = 0
        self.indent = 0
        self.indent_blanks = [0]

    def __readline(self):
        while True:
            line = self.fp.readline()
            self.line_no += 1
            line_no = self.line_no
            if not line: #file end
                break
            line = line.split('#')[0].rstrip()
            line_no = self.line_no
            if line: #not a empty line
                if line.endswith('\\'):
                    _line = self.__readline()[1]
                    if not _line:
                        raise Exception("pruning rule error, not line after end with '\\', path '%s' line_no %d"\
                                        % (self.path, line_no))
                    line = line[:len(line)-1] + _line
                break
        return line_no, line

    def __get_indent(self, line):
        line_no = self.line_no
        temp = re.match(pat_indent, line)
        if temp: #has indent
            blank_cnt = temp.span()[1]
            indent_blank_cnt = self.indent_blanks[-1]
            if blank_cnt > indent_blank_cnt:
                self.indent += 1
                self.indent_blanks.append(blank_cnt)
            elif blank_cnt < indent_blank_cnt:
                is_valid = False
                while len(self.indent_blanks) > 1:
                    self.indent_blanks.pop()
                    self.indent -= 1
                    indent_blank_cnt = self.indent_blanks[-1]
                    if blank_cnt == indent_blank_cnt:
                        is_valid = True
                        break
                    elif blank_cnt > indent_blank_cnt:
                        raise Exception("pruning rule indent error, path '%s' line_no %d"\
                                        % (self.path, line_no))
                if not is_valid:
                    raise Exception("pruning rule indent error, path '%s' line_no %d"\
                                        % (self.path, line_no))
            line = line[blank_cnt:]
        else:
            self.indent_blanks = [0]
            self.indent = 0
        return self.indent, line.strip()
        
    def read_rule(self):
        line_no, line = self.__readline()
        if not line:
            return None
        indent, content = self.__get_indent(line)
        identifier, content = read_identifier(content)
        if not identifier:
            raise Exception("pruning rule grammer error, keyword missing, path '%s' line_no %d"\
                          % (self.path, line_no))
        #read keyword
        keyword = keywords.get(identifier)
        if keyword is None:
            raise Exception("pruning rule grammer error, '%s' is not a valid keyword, path '%s' line_no %d"\
                          % (identifier, self.path, line_no))
        if not content:
            raise Exception("pruning rule grammer error, no content, path '%s' line_no %d"\
                          % (self.path, line_no))
        #wrap rule
        if keyword == keyword_top:
            if content != ':':
                raise Exception("pruning rule grammer error, must end with ':', path '%s' line_no %d"\
                              % (self.path, line_no))
            return CompoundRule(self.path, line_no, indent, keyword, None, None)
        elif keyword in (keyword_module, keyword_type):
            #read identifier as name
            name, content = read_identifier(content)
            if not name:
                raise Exception("pruning rule grammer error, no keyword, path '%s' line_no %d"\
                              % (self.path, line_no))
            if content.startswith("->"):
                content = content[2:].strip()
                new_name, content = read_identifier(content)  
                if not new_name:
                    raise Exception("pruning rule grammer error, new name illegal, path '%s' line_no %d"\
                                  % (self.path, line_no))
            else:
                new_name = None
            if content != ':':
                raise Exception("pruning rule grammer error, must end with ':', path '%s' line_no %d"\
                              % (self.path, line_no))
            return CompoundRule(self.path, line_no, indent, keyword, name, new_name)
        
        items = content.split(',')
        identifiers = []
        for item in items:
            identifier = item.strip()
            if not re.match(pat_identifier_full, identifier):
                raise Exception("pruning rule grammer error, '%s' no a valid identifier, path '%s' line_no %d"\
                          % (identifier, self.path, line_no))
            identifiers.append(identifier)
        return AtomicRule(self.path, line_no, indent, keyword, identifiers)

    def read_rules(self):
        res = []
        blocks = []
        current_block = None
            
        while True:
            rule = self.read_rule()
            if not rule:
                break
            
            if rule.indent == 0:
                res.append(rule)
                blocks.clear()
                if isinstance(rule, CompoundRule):
                    current_block = rule
                    blocks.append(rule)
                else:
                    current_block = None
                continue
            
            if current_block is None:
                raise Exception("pruning rule grammer error, indent error, path '%s' line_no %d"\
                    % (self.path, rule.line_no))
             
            for i in range(current_block.indent + 1 - rule.indent):
                blocks.pop()
            current_block = blocks[-1]
            current_block.add_rule(rule)
            if isinstance(rule, CompoundRule):
                current_block = rule
                blocks.append(rule)  
        return res

    def dump(self):
        rules = self.read_rules()
        print('\n'.join([str(bb) for bb in rules]))

def read_identifier(content):
    temp = re.match(pat_identifier, content)
    if not temp:
        return None, content
    identifier = content[:temp.span()[1]]
    content = content[temp.span()[1]:].strip()
    return identifier, content    
 