"""
ComfyUI Workflow Parser

Extracts and parses ComfyUI workflow metadata from PNG images,
building dictionaries for nodes, inputs/outputs, and connections.
"""

import json
from PIL import Image
from typing import Dict, Any, Tuple, Optional
import os


class WorkflowParser:
    """Parse ComfyUI workflow metadata from images."""
    
    def __init__(self, image_path: str):
        """
        Initialize the parser with an image path.
        
        Args:
            image_path: Path to the PNG image containing workflow metadata
        """
        self.image_path = image_path
        self.workflow_data = None
        self.nodes = {}
        self.io_map = {}
        self.connections = {}
        self.prompts = {
            'positive': [],
            'negative': []
        }
        self.loras = []
        self.uses_controlnet = False
    
    def load_workflow_from_image(self) -> Dict[str, Any]:
        """
        Load and extract workflow metadata from PNG image.
        
        Returns:
            Dictionary containing the workflow data
            
        Raises:
            FileNotFoundError: If image file doesn't exist
            ValueError: If no workflow metadata found in image
        """
        if not os.path.exists(self.image_path):
            raise FileNotFoundError(f"Image file not found: {self.image_path}")
        
        try:
            image = Image.open(self.image_path)
        except Exception as e:
            raise ValueError(f"Failed to open image: {e}")
        
        # Extract metadata from PNG chunks
        workflow_str = None
        
        # Check for workflow in PNG info
        if hasattr(image, 'info'):
            # ComfyUI stores workflow in 'workflow' or 'prompt' keys
            if 'workflow' in image.info:
                workflow_str = image.info['workflow']
            elif 'prompt' in image.info:
                workflow_str = image.info['prompt']
        
        if not workflow_str:
            raise ValueError("No workflow metadata found in image")
        
        # Parse JSON
        try:
            self.workflow_data = json.loads(workflow_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse workflow JSON: {e}")
        
        return self.workflow_data
    
    def build_nodes_dictionary(self) -> Dict[str, Dict[str, Any]]:
        """
        Build dictionary of nodes with their core properties.
        
        Returns:
            Dictionary mapping node IDs to node properties
        """
        if not self.workflow_data:
            raise ValueError("No workflow data loaded. Call load_workflow_from_image() first.")
        
        self.nodes = {}
        
        # Handle different workflow formats
        nodes_data = self.workflow_data
        if isinstance(self.workflow_data, dict):
            # If workflow has a 'nodes' key, use that
            if 'nodes' in self.workflow_data:
                nodes_data = self.workflow_data['nodes']
            # If it's the prompt format, the keys are node IDs
            elif all(isinstance(k, str) and k.isdigit() for k in list(self.workflow_data.keys())[:5]):
                nodes_data = self.workflow_data
        
        # Parse nodes
        if isinstance(nodes_data, dict):
            for node_id, node_data in nodes_data.items():
                self.nodes[str(node_id)] = {
                    "class_type": node_data.get("class_type", "Unknown"),
                    "pos": node_data.get("pos", [0, 0]),
                    "size": node_data.get("size", [0, 0]),
                    "widgets_values": node_data.get("widgets_values", []),
                    "order": node_data.get("order", 0),
                    "mode": node_data.get("mode", 0)
                }
        elif isinstance(nodes_data, list):
            for node_data in nodes_data:
                node_id = str(node_data.get("id", ""))
                self.nodes[node_id] = {
                    "class_type": node_data.get("type", "Unknown"),
                    "pos": node_data.get("pos", [0, 0]),
                    "size": node_data.get("size", [0, 0]),
                    "widgets_values": node_data.get("widgets_values", []),
                    "order": node_data.get("order", 0),
                    "mode": node_data.get("mode", 0)
                }
        
        return self.nodes
    
    def build_io_dictionary(self) -> Dict[str, Dict[str, Any]]:
        """
        Build dictionary of node inputs and outputs.
        
        Returns:
            Dictionary mapping node IDs to their inputs/outputs
        """
        if not self.workflow_data:
            raise ValueError("No workflow data loaded. Call load_workflow_from_image() first.")
        
        self.io_map = {}
        
        # Handle different workflow formats
        nodes_data = self.workflow_data
        if isinstance(self.workflow_data, dict):
            if 'nodes' in self.workflow_data:
                nodes_data = self.workflow_data['nodes']
            elif all(isinstance(k, str) and k.isdigit() for k in list(self.workflow_data.keys())[:5]):
                nodes_data = self.workflow_data
        
        # Parse I/O for each node
        if isinstance(nodes_data, dict):
            for node_id, node_data in nodes_data.items():
                self._parse_node_io(str(node_id), node_data)
        elif isinstance(nodes_data, list):
            for node_data in nodes_data:
                node_id = str(node_data.get("id", ""))
                self._parse_node_io(node_id, node_data)
        
        return self.io_map
    
    def _parse_node_io(self, node_id: str, node_data: Dict[str, Any]):
        """Parse inputs and outputs for a single node."""
        self.io_map[node_id] = {
            "inputs": {},
            "outputs": {}
        }
        
        # Parse inputs
        if "inputs" in node_data:
            inputs = node_data["inputs"]
            if isinstance(inputs, dict):
                for input_name, input_data in inputs.items():
                    if isinstance(input_data, dict):
                        self.io_map[node_id]["inputs"][input_name] = {
                            "type": input_data.get("type", "unknown"),
                            "link": input_data.get("link", None)
                        }
                    elif isinstance(input_data, list) and len(input_data) >= 1:
                        # Format: [source_node_id, output_index]
                        self.io_map[node_id]["inputs"][input_name] = {
                            "type": "connection",
                            "link": input_data
                        }
                    else:
                        # Direct value
                        self.io_map[node_id]["inputs"][input_name] = {
                            "type": "value",
                            "value": input_data
                        }
            elif isinstance(inputs, list):
                for i, input_data in enumerate(inputs):
                    input_name = input_data.get("name", f"input_{i}")
                    self.io_map[node_id]["inputs"][input_name] = {
                        "type": input_data.get("type", "unknown"),
                        "link": input_data.get("link", None)
                    }
        
        # Parse outputs
        if "outputs" in node_data:
            outputs = node_data["outputs"]
            if isinstance(outputs, dict):
                for output_name, output_data in outputs.items():
                    self.io_map[node_id]["outputs"][output_name] = {
                        "type": output_data.get("type", "unknown"),
                        "links": output_data.get("links", [])
                    }
            elif isinstance(outputs, list):
                for i, output_data in enumerate(outputs):
                    output_name = output_data.get("name", f"output_{i}")
                    self.io_map[node_id]["outputs"][output_name] = {
                        "type": output_data.get("type", "unknown"),
                        "links": output_data.get("links", [])
                    }
    
    def build_connections_dictionary(self) -> Dict[str, Dict[str, Any]]:
        """
        Build dictionary of connections between nodes.
        
        Returns:
            Dictionary mapping link IDs to connection details
        """
        if not self.workflow_data:
            raise ValueError("No workflow data loaded. Call load_workflow_from_image() first.")
        
        self.connections = {}
        
        # Extract links from workflow
        if 'links' in self.workflow_data:
            links = self.workflow_data['links']
            if isinstance(links, list):
                for link in links:
                    if isinstance(link, list) and len(link) >= 6:
                        # Format: [link_id, source_node, source_slot, target_node, target_slot, type]
                        link_id = str(link[0])
                        self.connections[link_id] = {
                            "source_node": str(link[1]),
                            "source_output": link[2],
                            "target_node": str(link[3]),
                            "target_input": link[4],
                            "type": link[5] if len(link) > 5 else "unknown"
                        }
        
        # Also extract connections from node inputs
        nodes_data = self.workflow_data
        if isinstance(self.workflow_data, dict):
            if 'nodes' in self.workflow_data:
                nodes_data = self.workflow_data['nodes']
            elif all(isinstance(k, str) and k.isdigit() for k in list(self.workflow_data.keys())[:5]):
                nodes_data = self.workflow_data
        
        # Build connections from inputs
        if isinstance(nodes_data, dict):
            for target_node_id, node_data in nodes_data.items():
                self._extract_connections_from_node(str(target_node_id), node_data)
        elif isinstance(nodes_data, list):
            for node_data in nodes_data:
                target_node_id = str(node_data.get("id", ""))
                self._extract_connections_from_node(target_node_id, node_data)
        
        return self.connections
    
    def _extract_connections_from_node(self, target_node_id: str, node_data: Dict[str, Any]):
        """Extract connections from a node's input data."""
        if "inputs" not in node_data:
            return
        
        inputs = node_data["inputs"]
        if isinstance(inputs, dict):
            for input_name, input_data in inputs.items():
                if isinstance(input_data, list) and len(input_data) >= 2:
                    # Format: [source_node_id, source_output_index]
                    source_node_id = str(input_data[0])
                    source_output = input_data[1]
                    
                    # Create a connection ID
                    conn_id = f"{source_node_id}_{source_output}_to_{target_node_id}_{input_name}"
                    
                    if conn_id not in self.connections:
                        self.connections[conn_id] = {
                            "source_node": source_node_id,
                            "source_output": source_output,
                            "target_node": target_node_id,
                            "target_input": input_name,
                            "type": "inferred"
                        }
    
    def detect_prompts(self) -> Dict[str, list]:
        """
        Detect positive and negative prompt nodes in the workflow.
        
        Identifies nodes that:
        1. Output CONDITIONING type
        2. Connect to positive/negative inputs of other nodes (following chains)
        3. Extracts the text content from these nodes (tracing through connections if needed)
        
        Returns:
            Dictionary with 'positive' and 'negative' prompt lists
        """
        if not self.nodes or not self.connections:
            return self.prompts
        
        # Find all conditioning nodes (typically CLIPTextEncode or similar)
        conditioning_nodes = {}
        for node_id, node_info in self.nodes.items():
            class_type = node_info.get('class_type', '')
            
            # Check if node outputs CONDITIONING
            if node_id in self.io_map:
                outputs = self.io_map[node_id].get('outputs', {})
                for output_name, output_info in outputs.items():
                    if output_info.get('type', '').upper() == 'CONDITIONING':
                        conditioning_nodes[node_id] = node_info
                        break
        
        # Trace connections to determine if positive or negative
        for node_id, node_info in conditioning_nodes.items():
            # Follow the conditioning chain forward to find final destination
            prompt_type = self._trace_conditioning_chain(node_id)
            
            # Skip if we can't determine the type
            if not prompt_type:
                continue
            
            # Only process nodes that actually generate text (not combiners/modifiers)
            # Typically CLIPTextEncode, String Literal, or similar
            class_type = node_info.get('class_type', '').lower()
            is_text_generator = (
                'text' in class_type or 
                'clip' in class_type or
                'string' in class_type or
                'prompt' in class_type
            )
            
            # Also check if it's a combiner/modifier that we should skip
            is_modifier = (
                'combine' in class_type or
                'concat' in class_type or
                'condition' in class_type and 'encode' not in class_type
            )
            
            if is_modifier:
                continue
            
            # Extract prompt text (may need to trace through connections)
            prompt_text = self._extract_prompt_text_with_trace(node_id, node_info)
            
            if prompt_text:
                # Find which node this connects to and get order info
                connected_nodes = []
                for conn_id, conn in self.connections.items():
                    if conn['source_node'] == node_id:
                        target_id = conn['target_node']
                        target_class = self.nodes.get(target_id, {}).get('class_type', 'Unknown')
                        target_order = self.nodes.get(target_id, {}).get('order', 999)
                        connected_nodes.append({
                            'node_id': target_id,
                            'class_type': target_class,
                            'order': target_order
                        })
                
                # Get this node's order
                node_order = node_info.get('order', 999)
                
                prompt_entry = {
                    'node_id': node_id,
                    'class_type': node_info.get('class_type', ''),
                    'text': prompt_text,
                    'type': prompt_type,
                    'order': node_order,
                    'connects_to': connected_nodes
                }
                
                if prompt_type == 'positive':
                    self.prompts['positive'].append(prompt_entry)
                elif prompt_type == 'negative':
                    self.prompts['negative'].append(prompt_entry)
        
        # Deduplicate prompts with same text - merge their connections
        self._deduplicate_prompts()
        
        return self.prompts
    
    def detect_loras(self) -> list:
        """
        Detect LoRA models used in the workflow.
        
        Identifies LoraLoader nodes and extracts:
        - LoRA filename
        - Model strength
        - CLIP strength
        - Execution order
        
        Returns:
            List of LoRA dictionaries
        """
        if not self.nodes:
            return self.loras
        
        # Find all LoraLoader nodes
        for node_id, node_info in self.nodes.items():
            class_type = node_info.get('class_type', '').lower()
            
            # Check if this is a LoRA loader node
            if 'lora' in class_type and 'load' in class_type:
                # Extract LoRA information from widget_values
                widgets = node_info.get('widgets_values', [])
                
                if len(widgets) >= 1:
                    lora_name = widgets[0] if isinstance(widgets[0], str) else None
                    model_strength = widgets[1] if len(widgets) > 1 else 1.0
                    clip_strength = widgets[2] if len(widgets) > 2 else 1.0
                    
                    if lora_name:
                        lora_entry = {
                            'node_id': node_id,
                            'class_type': node_info.get('class_type', ''),
                            'lora_name': lora_name,
                            'model_strength': model_strength,
                            'clip_strength': clip_strength,
                            'order': node_info.get('order', 999)
                        }
                        self.loras.append(lora_entry)
        
        # Sort by execution order
        self.loras.sort(key=lambda x: x['order'])
        
        return self.loras
    
    def detect_controlnet(self) -> bool:
        """
        Detect if ControlNet is used in the workflow.
        
        Returns:
            True if ControlNet nodes are found
        """
        if not self.nodes:
            return False
        
        # Check for ControlNet-related nodes
        for node_id, node_info in self.nodes.items():
            class_type = node_info.get('class_type', '').lower()
            
            if 'controlnet' in class_type or 'control_net' in class_type:
                self.uses_controlnet = True
                return True
        
        return False
    
    def _deduplicate_prompts(self):
        """Merge prompts with identical text, combining their connections."""
        for prompt_type in ['positive', 'negative']:
            if not self.prompts.get(prompt_type):
                continue
            
            # Group by text
            text_groups = {}
            for prompt in self.prompts[prompt_type]:
                text = prompt['text']
                if text not in text_groups:
                    text_groups[text] = {
                        'node_ids': [],
                        'class_types': set(),
                        'orders': [],
                        'connects_to': []
                    }
                
                text_groups[text]['node_ids'].append(prompt['node_id'])
                text_groups[text]['class_types'].add(prompt['class_type'])
                text_groups[text]['orders'].append(prompt['order'])
                
                # Merge connections
                for conn in prompt.get('connects_to', []):
                    # Avoid duplicates
                    if not any(c['node_id'] == conn['node_id'] for c in text_groups[text]['connects_to']):
                        text_groups[text]['connects_to'].append(conn)
            
            # Rebuild prompts list with deduplicated entries
            deduplicated = []
            for text, group in text_groups.items():
                # Use the earliest order
                min_order = min(group['orders'])
                
                # Create combined node_id string if multiple
                if len(group['node_ids']) > 1:
                    node_id_str = ', '.join(group['node_ids'])
                else:
                    node_id_str = group['node_ids'][0]
                
                deduplicated.append({
                    'node_id': node_id_str,
                    'class_type': ', '.join(group['class_types']),
                    'text': text,
                    'type': prompt_type,
                    'order': min_order,
                    'connects_to': sorted(group['connects_to'], key=lambda x: x['order'])
                })
            
            self.prompts[prompt_type] = deduplicated
    
    def _trace_conditioning_chain(self, node_id: str, visited: Optional[set] = None) -> Optional[str]:
        """
        Trace a conditioning node forward through the chain to find if it connects to positive/negative.
        
        Args:
            node_id: ID of the conditioning node
            visited: Set of visited nodes to prevent infinite loops
            
        Returns:
            'positive', 'negative', or None
        """
        if visited is None:
            visited = set()
        
        if node_id in visited:
            return None
        visited.add(node_id)
        
        # Find where this node connects to
        for conn_id, conn in self.connections.items():
            if conn['source_node'] == node_id:
                target_node_id = conn['target_node']
                target_input = conn['target_input']
                
                # Get the actual input name (might be an index or a name)
                input_name = self._get_input_name(target_node_id, target_input)
                
                if input_name:
                    input_name_lower = input_name.lower()
                    
                    # Check if this connection is to a positive/negative input
                    if 'positive' in input_name_lower:
                        return 'positive'
                    elif 'negative' in input_name_lower:
                        return 'negative'
                
                # If not, check if the target is also a conditioning node (chain continues)
                if target_node_id in self.io_map:
                    outputs = self.io_map[target_node_id].get('outputs', {})
                    for output_name, output_info in outputs.items():
                        if output_info.get('type', '').upper() == 'CONDITIONING':
                            # Continue tracing through this conditioning node
                            result = self._trace_conditioning_chain(target_node_id, visited)
                            if result:
                                return result
        
        return None
    
    def _get_input_name(self, node_id: str, input_ref: Any) -> Optional[str]:
        """
        Get the actual input name from a node's input reference.
        
        Args:
            node_id: ID of the node
            input_ref: Input reference (could be index or name)
            
        Returns:
            Input name or None
        """
        # If it's already a string name, return it
        if isinstance(input_ref, str):
            return input_ref
        
        # If it's an index, look it up in the io_map
        if node_id in self.io_map:
            inputs = self.io_map[node_id].get('inputs', {})
            input_names = list(inputs.keys())
            
            # Try to use it as an index
            try:
                index = int(input_ref)
                if 0 <= index < len(input_names):
                    return input_names[index]
            except (ValueError, TypeError):
                pass
        
        return None
    
    def _extract_prompt_text(self, node_info: Dict[str, Any]) -> Optional[str]:
        """
        Extract prompt text from a node's widget values or inputs.
        
        Args:
            node_info: Node information dictionary
            
        Returns:
            Prompt text if found, None otherwise
        """
        # Check widget_values (common in CLIPTextEncode)
        if 'widgets_values' in node_info:
            widgets = node_info['widgets_values']
            if isinstance(widgets, list) and len(widgets) > 0:
                # Usually the first widget is the text
                for widget in widgets:
                    if isinstance(widget, str) and len(widget) > 0:
                        return widget
        
        # Check inputs for text field
        if 'inputs' in node_info:
            inputs = node_info['inputs']
            if isinstance(inputs, dict):
                # Look for common text input names
                for key in ['text', 'prompt', 'conditioning', 'string']:
                    if key in inputs:
                        value = inputs[key]
                        if isinstance(value, str):
                            return value
        
        return None
    
    def _extract_prompt_text_with_trace(self, node_id: str, node_info: Dict[str, Any], visited: Optional[set] = None) -> Optional[str]:
        """
        Extract prompt text from a node, tracing through connections if needed.
        
        Args:
            node_id: ID of the node to extract text from
            node_info: Node information dictionary
            visited: Set of visited node IDs to prevent infinite loops
            
        Returns:
            Prompt text if found, None otherwise
        """
        if visited is None:
            visited = set()
        
        if node_id in visited:
            return None
        visited.add(node_id)
        
        # First try to get text directly from this node
        direct_text = self._extract_prompt_text(node_info)
        if direct_text:
            return direct_text
        
        # If no direct text, check if this node has text/string inputs that are connections
        if node_id in self.io_map:
            inputs = self.io_map[node_id].get('inputs', {})
            
            # Look for text/string inputs
            for input_name, input_info in inputs.items():
                if input_info.get('type', '').upper() in ['STRING', 'TEXT']:
                    # Find the connection that feeds this input
                    # Need to check both by name and by index
                    for conn_id, conn in self.connections.items():
                        if conn['target_node'] == node_id:
                            # Get the actual input name from the connection
                            conn_input_name = self._get_input_name(node_id, conn['target_input'])
                            
                            if conn_input_name == input_name:
                                # Trace back to the source node
                                source_node_id = conn['source_node']
                                if source_node_id in self.nodes:
                                    source_node_info = self.nodes[source_node_id]
                                    # Recursively extract text from source
                                    text = self._extract_prompt_text_with_trace(source_node_id, source_node_info, visited)
                                    if text:
                                        return text
        
        return None
    
    def parse_all(self) -> Tuple[Dict, Dict, Dict, Dict, list]:
        """
        Parse all workflow components.
        
        Returns:
            Tuple of (nodes, io_map, connections, prompts, loras)
        """
        self.load_workflow_from_image()
        self.build_nodes_dictionary()
        self.build_io_dictionary()
        self.build_connections_dictionary()
        self.detect_prompts()
        self.detect_loras()
        self.detect_controlnet()
        
        return self.nodes, self.io_map, self.connections, self.prompts, self.loras
    
    def save_to_file(self, output_path: str, format: str = "json", pretty: bool = True):
        """
        Save all dictionaries to a file for manual examination.
        
        Args:
            output_path: Path to save the output file
            format: Output format ('json' or 'txt')
            pretty: Whether to pretty-print the output (for JSON)
        """
        data = {
            "nodes": self.nodes,
            "io_map": self.io_map,
            "connections": self.connections,
            "prompts": self.prompts,
            "loras": self.loras,
            "metadata": {
                "source_image": self.image_path,
                "total_nodes": len(self.nodes),
                "total_connections": len(self.connections),
                "positive_prompts": len(self.prompts.get('positive', [])),
                "negative_prompts": len(self.prompts.get('negative', [])),
                "loras_used": len(self.loras)
            }
        }
        
        if format.lower() == "json":
            with open(output_path, 'w', encoding='utf-8') as f:
                if pretty:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                else:
                    json.dump(data, f, ensure_ascii=False)
        
        elif format.lower() == "txt":
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write("COMFYUI WORKFLOW ANALYSIS\n")
                f.write("=" * 80 + "\n\n")
                
                f.write(f"Source Image: {self.image_path}\n")
                f.write(f"Total Nodes: {len(self.nodes)}\n")
                f.write(f"Total Connections: {len(self.connections)}\n")
                f.write(f"Positive Prompts: {len(self.prompts.get('positive', []))}\n")
                f.write(f"Negative Prompts: {len(self.prompts.get('negative', []))}\n")
                f.write(f"LoRAs Used: {len(self.loras)}\n\n")
                
                # Write LoRAs section
                if self.loras:
                    f.write("=" * 80 + "\n")
                    f.write("LORAS USED\n")
                    f.write("=" * 80 + "\n\n")
                    
                    for i, lora in enumerate(self.loras, 1):
                        f.write(f"  [{i}] {lora['lora_name']}\n")
                        f.write(f"      Node: {lora['node_id']} ({lora['class_type']}) - Order: {lora['order']}\n")
                        f.write(f"      Model Strength: {lora['model_strength']}\n")
                        f.write(f"      CLIP Strength: {lora['clip_strength']}\n\n")
                
                # Write prompts section
                f.write("=" * 80 + "\n")
                f.write("DETECTED PROMPTS\n")
                f.write("=" * 80 + "\n\n")
                
                if self.prompts.get('positive'):
                    f.write("POSITIVE PROMPTS:\n")
                    # Sort by order to show workflow sequence
                    sorted_positive = sorted(self.prompts['positive'], key=lambda x: x.get('order', 999))
                    for i, prompt in enumerate(sorted_positive, 1):
                        f.write(f"\n  [{i}] Node {prompt['node_id']} ({prompt['class_type']}) - Order: {prompt.get('order', 'N/A')}\n")
                        f.write(f"      Text: {prompt['text']}\n")
                        if prompt.get('connects_to'):
                            f.write(f"      Connects to:\n")
                            for conn in prompt['connects_to']:
                                f.write(f"        → Node {conn['node_id']} ({conn['class_type']}) - Order: {conn['order']}\n")
                
                if self.prompts.get('negative'):
                    f.write("\nNEGATIVE PROMPTS:\n")
                    # Sort by order to show workflow sequence
                    sorted_negative = sorted(self.prompts['negative'], key=lambda x: x.get('order', 999))
                    for i, prompt in enumerate(sorted_negative, 1):
                        f.write(f"\n  [{i}] Node {prompt['node_id']} ({prompt['class_type']}) - Order: {prompt.get('order', 'N/A')}\n")
                        f.write(f"      Text: {prompt['text']}\n")
                        if prompt.get('connects_to'):
                            f.write(f"      Connects to:\n")
                            for conn in prompt['connects_to']:
                                f.write(f"        → Node {conn['node_id']} ({conn['class_type']}) - Order: {conn['order']}\n")
                
                f.write("\n")
                
                f.write("=" * 80 + "\n")
                f.write("NODES DICTIONARY\n")
                f.write("=" * 80 + "\n\n")
                for node_id, node_info in self.nodes.items():
                    f.write(f"Node ID: {node_id}\n")
                    for key, value in node_info.items():
                        f.write(f"  {key}: {value}\n")
                    f.write("\n")
                
                f.write("=" * 80 + "\n")
                f.write("INPUTS/OUTPUTS DICTIONARY\n")
                f.write("=" * 80 + "\n\n")
                for node_id, io_info in self.io_map.items():
                    f.write(f"Node ID: {node_id}\n")
                    f.write("  Inputs:\n")
                    for input_name, input_info in io_info["inputs"].items():
                        f.write(f"    {input_name}: {input_info}\n")
                    f.write("  Outputs:\n")
                    for output_name, output_info in io_info["outputs"].items():
                        f.write(f"    {output_name}: {output_info}\n")
                    f.write("\n")
                
                f.write("=" * 80 + "\n")
                f.write("CONNECTIONS DICTIONARY\n")
                f.write("=" * 80 + "\n\n")
                for conn_id, conn_info in self.connections.items():
                    f.write(f"Connection ID: {conn_id}\n")
                    for key, value in conn_info.items():
                        f.write(f"  {key}: {value}\n")
                    f.write("\n")
        
        print(f"Data saved to: {output_path}")


def main():
    """Example usage of the WorkflowParser."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python workflow_parser.py <image_path> [output_path]")
        print("Example: python workflow_parser.py workflow.png output.json")
        return
    
    image_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else "workflow_analysis.json"
    
    try:
        # Create parser
        parser = WorkflowParser(image_path)
        
        # Parse workflow
        print(f"Loading workflow from: {image_path}")
        nodes, io_map, connections, prompts, loras = parser.parse_all()
        
        # Print summary
        print(f"\nParsing complete!")
        print(f"  Nodes found: {len(nodes)}")
        print(f"  Connections found: {len(connections)}")
        print(f"  Positive prompts: {len(prompts.get('positive', []))}")
        print(f"  Negative prompts: {len(prompts.get('negative', []))}")
        print(f"  LoRAs used: {len(loras)}")
        
        # Display ControlNet warning
        if parser.uses_controlnet:
            print(f"\n⚠️  CONTROLNET DETECTED - This workflow uses ControlNet nodes")
        
        # Display LoRAs
        if loras:
            print(f"\n🎨 LoRAs Used:")
            for i, lora in enumerate(loras, 1):
                print(f"    [{i}] {lora['lora_name']}")
                print(f"        Model: {lora['model_strength']}, CLIP: {lora['clip_strength']}")
        
        # Display prompts
        if prompts.get('positive') or prompts.get('negative'):
            print(f"\n📝 Detected Prompts:")
            if prompts.get('positive'):
                print(f"\n  POSITIVE:")
                sorted_positive = sorted(prompts['positive'], key=lambda x: x.get('order', 999))
                for i, prompt in enumerate(sorted_positive, 1):
                    preview = prompt['text'][:80] + '...' if len(prompt['text']) > 80 else prompt['text']
                    print(f"    [{i}] Node {prompt['node_id']} (order {prompt.get('order')}): {preview}")
                    if prompt.get('connects_to'):
                        for conn in prompt['connects_to'][:2]:  # Show first 2 connections
                            print(f"        → {conn['class_type']} (order {conn['order']})")
            if prompts.get('negative'):
                print(f"\n  NEGATIVE:")
                sorted_negative = sorted(prompts['negative'], key=lambda x: x.get('order', 999))
                for i, prompt in enumerate(sorted_negative, 1):
                    preview = prompt['text'][:80] + '...' if len(prompt['text']) > 80 else prompt['text']
                    print(f"    [{i}] Node {prompt['node_id']} (order {prompt.get('order')}): {preview}")
                    if prompt.get('connects_to'):
                        for conn in prompt['connects_to'][:2]:  # Show first 2 connections
                            print(f"        → {conn['class_type']} (order {conn['order']})")
        
        # Save to file
        print(f"\nSaving analysis to: {output_path}")
        
        # Determine format from extension
        if output_path.endswith('.txt'):
            parser.save_to_file(output_path, format='txt')
        else:
            parser.save_to_file(output_path, format='json')
        
        print("\nDone!")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
