"""
Python implementation of node2dot.c
Converts PostgreSQL node tree output to Graphviz DOT format
Based on original C code by yshen 2016
"""

import re
import sys

class Node:
    """Represents a node in the tree"""
    def __init__(self):
        self.name = ""
        self.elems = []  # list of element names
        self.links = []  # list of link strings
        self.color = "black"
        
    def add_elem(self, elem_name):
        """Add an element to the node"""
        self.elems.append(elem_name)
    
    def add_link(self, link_str):
        """Add a link to another node"""
        self.links.append(link_str)

class Node2DotParser:
    """Parser that converts PostgreSQL node tree to DOT format"""
    
    def __init__(self, skip_empty, skip_node_name=None, use_color=False):
        self.skip_empty = skip_empty
        self.skip_node_name = skip_node_name
        self.use_color = use_color
        
        # State tracking
        # Initialize with a dummy node at index 0 to match C implementation (1-based indexing)
        self.nodes = [None] 
        self.stack = []  # stack for tracking node hierarchy
        self.node_cnt = 0  # total node count
        self.node_num = 0  # current node number
        self.elem_num = 0  # current element number
        self.level = 0  # nesting level
        
    def parse(self, text):
        """Parse input text and return DOT format string"""
        self._reset_state()
        
        # Process character by character
        i = 0
        while i < len(text):
            c = text[i]
            
            if c == '{':
                # Start of a new node
                self.level += 1
                parent_node_num = self.node_num
                parent_elem_num = self.elem_num
                
                # Push current state to stack
                self.stack.append(parent_node_num)
                self.stack.append(parent_elem_num)
                
                # Reset element counter for new node
                self.elem_num = 0
                
                # Get node name
                name = self._get_one_name(text, i+1)
                if name is not None:
                    i += len(name)
                    # Create new node
                    new_node = Node()
                    new_node.name = name
                    self.nodes.append(new_node)
                    self.node_cnt = len(self.nodes) - 1
                    child_node_num = self.node_cnt
                    
                    # Set current node to new node
                    self.node_num = self.node_cnt
                    
                    # Add link from parent if not root
                    # FIX: Use level > 1 instead of node_cnt > 0.
                    # This ensures top-level nodes (Level 1) are not linked to previous nodes,
                    # allowing for disjoint trees (e.g. a list of Query nodes).
                    if self.level > 1:
                        link_str = f"node{parent_node_num}:f{parent_elem_num} -> node{child_node_num}:f0\n"
                        if parent_node_num < len(self.nodes) and self.nodes[parent_node_num]:
                            self.nodes[parent_node_num].add_link(link_str)
                else:
                    # No valid name found, skip this node
                    i += 1
                    # Skip to matching '}'
                    brace_count = 1
                    while i < len(text) and brace_count > 0:
                        if text[i] == '{':
                            brace_count += 1
                        elif text[i] == '}':
                            brace_count -= 1
                        i += 1
                    continue
                    
            elif c == '}':
                # End of current node
                if self.level <= 0:
                    i += 1
                    continue
                    
                # Restore parent state from stack
                if self.stack:
                    self.elem_num = self.stack.pop()
                    self.node_num = self.stack.pop()
                self.level -= 1
                
            elif c == ':':
                # New element/item
                if self.level <= 0:
                    i += 1
                    continue
                    
                name = self._get_one_name(text, i+1)
                if name is not None:
                    i += len(name)
                    if self.node_num < len(self.nodes) and self.nodes[self.node_num]:
                        # Add element to current node
                        self.nodes[self.node_num].add_elem(name)
                        self.elem_num += 1
                else:
                    i += 1
                    continue
                    
            i += 1
        
        # Generate DOT output
        return self._generate_dot()
    
    def _reset_state(self):
        """Reset parser state"""
        self.nodes = [None] # Reset with dummy node
        self.stack = []
        self.node_cnt = 0
        self.node_num = 0
        self.elem_num = 0
        self.level = 0
    
    def _get_one_name(self, text, start_pos):
        """
        Extract a node or element name from text starting at start_pos
        Returns the name or None if invalid
        """
        i = start_pos
        # Skip whitespace
        while i < len(text) and text[i].isspace():
            i += 1
            
        # Find end of name (next ':', '{', '}' or whitespace)
        start = i
        while i < len(text) and text[i] not in ':{}':
            i += 1
            
        if i <= start:
            return None
            
        name = text[start:i].strip()
        
        # Remove any illegal characters for DOT format
        name = name.replace('"', ' ')
        name = name.replace('<', '-')
        name = name.replace('>', '-')
        
        # Handle parentheses
        if '(' in name and ')' not in name:
            name = name.replace('(', ' ')
        
        # Skip empty elements if enabled
        # if self.skip_empty:
            # if '--' in name or 'false' in name or bool(re.search(r'(?<!\d)0(?!\d)', name)):
        if '--' in name or (self.skip_empty and ('false' in name or bool(re.search(r'(?<!\d)0(?!\d)', name)))):
            return None
        return name if name else None

    def _generate_dot(self):
        """Generate DOT format string from parsed nodes"""
        lines = []
        
        # Header
        lines.append("digraph Query {")
        lines.append("size=\"100000,100000\";")
        lines.append("rankdir=LR;")
        lines.append("node [shape=record];")
        lines.append("")
        
        # Color palette for node types (tags)
        # Extended color palette with 20 distinct colors
        COLOR_PALETTE = [
            "#FF6B6B", "#3F1414", "#FFD166", "#06D6A0", "#118AB2",
            "#073B4C", "#AA476F", "#7209B7", "#3A86FF", "#FB5607",
        ]
        
        # Cache for tag to color mapping
        tag_color_map = {}
        
        # Nodes
        for i, node in enumerate(self.nodes):
            # Skip dummy node at index 0
            if node is None:
                continue
                
            if not node.name:
                continue
                
            if self.skip_node_name and self.skip_node_name in node.name:
                continue
            
            # Determine color based on node type (tag)
            color = "black"
            if self.use_color:
                tag = node.name.upper()
                # Get or create color for this tag
                if tag not in tag_color_map:
                    # Use hash to get deterministic color for each tag
                    hash_val = hash(tag) % len(COLOR_PALETTE)
                    tag_color_map[tag] = COLOR_PALETTE[hash_val]
                
                color = tag_color_map[tag]  # Border color
            
            # Build label with elements
            label_parts = [f"<f0> {node.name}"]
            for j, elem in enumerate(node.elems, 1):
                if elem:  # Skip empty elements
                    label_parts.append(f"<f{j}> {elem}")
            
            label = " | ".join(label_parts)
            # Use color for border and fillcolor for fill
            lines.append(f"node{i} [shape=record, color=\"{color}\", label=\"{label}\"];")
        
        lines.append("")
        
        # Links
        for i, node in enumerate(self.nodes):
            # Skip dummy node
            if node is None:
                continue

            if not node.name:
                continue
                
            if self.skip_node_name and self.skip_node_name in node.name:
                continue
            
            for link in node.links:
                lines.append(link.rstrip()) # strip newline from link str to avoid double newlines
        
        # Footer
        lines.append("}")
        
        return "\n".join(lines)


def extract_quoted_content(text):
    """
    Extract content from PostgreSQL debug output following these rules:
    1. If double quotes exist, extract content inside quotes and remove outermost parentheses if present
    2. If no double quotes, extract content inside outermost parentheses (), excluding the parentheses
    3. If no parentheses, extract content inside outermost curly braces {}, including the braces
    
    Format examples:
    - $3 = 0x5dd220d06920 "({RAWSTMT :stmt {SELECTSTMT ...}})"
    - ({RAWSTMT :stmt {SELECTSTMT ...}})
    - {RAWSTMT :stmt {SELECTSTMT ...}}
    """

    first_quote = -1
    quote = ''
    for index, char in enumerate(text):
        if char == '"' or char == '(' or char == '{':
            first_quote = index
            quote = char

    if first_quote != -1:
        last_quote = text.rfind(quote)
        if last_quote != first_quote:
            # Extract content between quotes
            quoted = text[first_quote:last_quote+1]
            # Remove outermost parentheses if present
            if (quoted.startswith('(') and quoted.endswith(')')) or (quoted.startswith('"') and quoted.endswith('"')):
                quoted = quoted[1:-1]
            return quoted

    # If none of the above, return the original text
    return text


def node2dot(text, skip_empty=False, skip_node_name=None, use_color=False):
    """
    Main function to convert PostgreSQL node tree to DOT format
    """
    # Extract the actual node tree from PostgreSQL debug output
    content = extract_quoted_content(text)
    
    # Parse and convert to DOT
    parser = Node2DotParser(skip_empty=skip_empty, skip_node_name=skip_node_name, use_color=use_color)
    dot_output = parser.parse(content)
    
    return dot_output


if __name__ == "__main__":
    # Simple test with example data
    test_data = '''$7 = 0x63e291ff3d80 "({QUERY :commandType 3 :querySource 4 :canSetTag false :utilityStmt <> :resultRelation 4 :hasAggs false :hasWindowFuncs false :hasTargetSRFs false :hasSubLinks false :hasDistinctOn false :hasRecursive false :hasModifyingCTE false :hasForUpdate false :hasRowSecurity false :hasGroupRTE false :isReturn false :cteList <> :rtable ({RANGETBLENTRY :alias <> :eref {ALIAS :aliasname primary_log :colnames (\"id\" \"msg\")} :rtekind 0 :relid 24579 :inh true :relkind r :rellockmode 3 :perminfoindex 1 :tablesample <> :lateral false :inFromCl false :securityQuals <>} {RANGETBLENTRY :alias {ALIAS :aliasname old :colnames <>} :eref {ALIAS :aliasname old :colnames (\"id\" \"msg\")} :rtekind 0 :relid 24579 :inh false :relkind r :rellockmode 1 :perminfoindex 2 :tablesample <> :lateral false :inFromCl false :securityQuals <>} {RANGETBLENTRY :alias {ALIAS :aliasname new :colnames <>} :eref {ALIAS :aliasname new :colnames (\"id\" \"msg\")} :rtekind 0 :relid 24579 :inh false :relkind r :rellockmode 1 :perminfoindex 3 :tablesample <> :lateral false :inFromCl false :securityQuals <>} {RANGETBLENTRY :alias <> :eref {ALIAS :aliasname audit_log :colnames (\"log_time\" \"action\")} :rtekind 0 :relid 24584 :inh false :relkind r :rellockmode 3 :perminfoindex 4 :tablesample <> :lateral false :inFromCl false :securityQuals <>}) :rteperminfos ({RTEPERMISSIONINFO :relid 24579 :inh true :requiredPerms 10 :checkAsUser 0 :selectedCols (b 8) :insertedCols (b) :updatedCols (b)} {RTEPERMISSIONINFO :relid 24579 :inh false :requiredPerms 2 :checkAsUser 10 :selectedCols (b) :insertedCols (b) :updatedCols (b)} {RTEPERMISSIONINFO :relid 24579 :inh false :requiredPerms 2 :checkAsUser 10 :selectedCols (b) :insertedCols (b) :updatedCols (b)} {RTEPERMISSIONINFO :relid 24584 :inh false :requiredPerms 1 :checkAsUser 10 :selectedCols (b) :insertedCols (b 8 9) :updatedCols (b)}) :jointree {FROMEXPR :fromlist ({RANGETBLREF :rtindex 1}) :quals {OPEXPR :opno 96 :opfuncid 65 :opresulttype 16 :opretset false :opcollid 0 :inputcollid 0 :args ({VAR :varno 1 :varattno 1 :vartype 23 :vartypmod -1 :varcollid 0 :varnullingrels (b) :varlevelsup 0 :varreturningtype 0 :varnosyn 1 :varattnosyn 1 :location -1} {CONST :consttype 23 :consttypmod -1 :constcollid 0 :constlen 4 :constbyval true :constisnull false :location -1 :constvalue 4 [ 1 0 0 0 0 0 0 0 ]}) :location -1}} :mergeActionList <> :mergeTargetRelation 0 :mergeJoinCondition <> :targetList ({TARGETENTRY :expr {FUNCEXPR :funcid 2027 :funcresulttype 1114 :funcretset false :funcvariadic false :funcformat 2 :funccollid 0 :inputcollid 0 :args ({FUNCEXPR :funcid 1299 :funcresulttype 1184 :funcretset false :funcvariadic false :funcformat 0 :funccollid 0 :inputcollid 0 :args <> :location -1}) :location -1} :resno 1 :resname log_time :ressortgroupref 0 :resorigtbl 0 :resorigcol 0 :resjunk false} {TARGETENTRY :expr {CONST :consttype 25 :consttypmod -1 :constcollid 100 :constlen -1 :constbyval false :constisnull false :location -1 :constvalue 21 [ 84 0 0 0 65 32 114 111 119 32 119 97 115 32 100 101 108 101 116 101 100 ]} :resno 2 :resname action :ressortgroupref 0 :resorigtbl 0 :resorigcol 0 :resjunk false}) :override 0 :onConflict <> :returningOldAlias <> :returningNewAlias <> :returningList <> :groupClause <> :groupDistinct false :groupingSets <> :havingQual <> :windowClause <> :distinctClause <> :sortClause <> :limitOffset <> :limitCount <> :limitOption 0 :rowMarks <> :setOperations <> :constraintDeps <> :withCheckOptions <> :stmt_location -1 :stmt_len -1} {QUERY :commandType 4 :querySource 0 :canSetTag true :utilityStmt <> :resultRelation 1 :hasAggs false :hasWindowFuncs false :hasTargetSRFs false :hasSubLinks false :hasDistinctOn false :hasRecursive false :hasModifyingCTE false :hasForUpdate false :hasRowSecurity false :hasGroupRTE false :isReturn false :cteList <> :rtable ({RANGETBLENTRY :alias <> :eref {ALIAS :aliasname primary_log :colnames (\"id\" \"msg\")} :rtekind 0 :relid 24579 :inh true :relkind r :rellockmode 3 :perminfoindex 1 :tablesample <> :lateral false :inFromCl false :securityQuals <>}) :rteperminfos ({RTEPERMISSIONINFO :relid 24579 :inh true :requiredPerms 10 :checkAsUser 0 :selectedCols (b 8) :insertedCols (b) :updatedCols (b)}) :jointree {FROMEXPR :fromlist ({RANGETBLREF :rtindex 1}) :quals {OPEXPR :opno 96 :opfuncid 65 :opresulttype 16 :opretset false :opcollid 0 :inputcollid 0 :args ({VAR :varno 1 :varattno 1 :vartype 23 :vartypmod -1 :varcollid 0 :varnullingrels (b) :varlevelsup 0 :varreturningtype 0 :varnosyn 1 :varattnosyn 1 :location -1} {CONST :consttype 23 :consttypmod -1 :constcollid 0 :constlen 4 :constbyval true :constisnull false :location -1 :constvalue 4 [ 1 0 0 0 0 0 0 0 ]}) :location -1}} :mergeActionList <> :mergeTargetRelation 0 :mergeJoinCondition <> :targetList <> :override 0 :onConflict <> :returningOldAlias <> :returningNewAlias <> :returningList <> :groupClause <> :groupDistinct false :groupingSets <> :havingQual <> :windowClause <> :distinctClause <> :sortClause <> :limitOffset <> :limitCount <> :limitOption 0 :rowMarks <> :setOperations <> :constraintDeps <> :withCheckOptions <> :stmt_location -1 :stmt_len -1})"'''
    result = node2dot(test_data, use_color=False)
    print(result)